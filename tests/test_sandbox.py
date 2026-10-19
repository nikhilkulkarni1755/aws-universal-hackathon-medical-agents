import json
import os
import types

from handoff.agents import load_patients
from handoff.sandbox import THEO_SCRIPT, run_local, run_script, theo_script


def _patient(bed):
    return next(p for p in load_patients() if p["bed"] == bed)


def test_program_gathers_flags_and_writes_a_non_diagnostic_impression():
    out = run_local([_patient("402"), _patient("401")])
    sick, stable = out
    assert sick["gathered"]["notes"] == 2 and sick["gathered"]["labs"] == 4 and sick["gathered"]["io_blocks"] == 3
    assert {s["source"] for s in sick["signals"]} == {"Vitals", "Lab", "I/O"}
    assert sick["trends"]["hr"] == {"first": 82, "last": 104, "min": 82, "max": 104, "delta": 22}
    assert "not a diagnosis" in sick["impression"] and "needs provider evaluation" in sick["impression"]
    assert "sepsis" not in sick["impression"].lower()
    assert [s["text"] for s in stable["signals"]] == ["Hemoglobin 11.2 g/dL"]
    assert sick["svg"].startswith("<svg")


def test_model_written_code_never_runs_locally(tmp_path):
    marker = tmp_path / "pwned"
    evil = f"open({str(marker)!r}, 'w').write('x')"
    results, badge = run_script(evil, [_patient("402")], "claude")
    assert not marker.exists()
    assert badge.startswith("local template") and results[0]["svg"].startswith("<svg")


def _fake_tenki(monkeypatch, outputs):
    class Box:
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def exec(self, *args):
            return types.SimpleNamespace(stdout_text=outputs.pop(0), check=lambda: None)
    monkeypatch.setitem(__import__("sys").modules, "tenki", types.SimpleNamespace(Sandbox=types.SimpleNamespace(create=lambda **kw: Box())))
    monkeypatch.setenv("TENKI_API_KEY", "test")


def test_sandbox_result_is_used_when_it_matches(monkeypatch):
    p = _patient("402")
    _fake_tenki(monkeypatch, [json.dumps(run_local([p])[0])])
    _, badge = run_script(THEO_SCRIPT, [p], "template")
    assert badge.startswith("tenki sandbox")


def test_a_model_script_that_disagrees_with_the_reference_is_rejected(monkeypatch):
    p = _patient("402")
    wrong = {**run_local([p])[0], "signals": []}
    _fake_tenki(monkeypatch, [json.dumps(wrong)])
    results, badge = run_script("print('model script')", [p], "claude")
    assert badge.startswith("local template fallback (ValueError)")
    assert results[0]["signals"]  # the trusted findings, not the model's empty list


def test_a_script_missing_required_keys_is_rejected(monkeypatch):
    _fake_tenki(monkeypatch, [json.dumps({"svg": "<svg/>"})])
    _, badge = run_script(THEO_SCRIPT, [_patient("402")], "template")
    assert badge.startswith("local template fallback (ValueError)")


def test_theo_script_uses_template_without_a_key(monkeypatch):
    monkeypatch.delenv("FLATKEY_API_KEY", raising=False)
    assert theo_script() == (THEO_SCRIPT, "template")


def test_theo_script_strips_code_fences(monkeypatch):
    monkeypatch.setattr("handoff.sandbox.complete", lambda prompt, **kw: "```python\nprint(1)\n```")
    code, source = theo_script()
    assert code.strip() == "print(1)" and source == "claude"
