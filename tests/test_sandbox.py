from handoff.agents import load_patients
from handoff.sandbox import THEO_SCRIPT, run_script, theo_script


def test_model_written_code_never_runs_locally(tmp_path):
    marker = tmp_path / "pwned"
    evil = f"open({str(marker)!r}, 'w').write('x')"
    results, badge = run_script(evil, load_patients()[:1], "claude")
    assert not marker.exists()
    assert badge.startswith("local template") and results[0]["svg"].startswith("<svg")


def test_theo_script_uses_template_without_a_key(monkeypatch):
    monkeypatch.delenv("FLATKEY_API_KEY", raising=False)
    assert theo_script() == (THEO_SCRIPT, "template")


def test_theo_script_strips_code_fences(monkeypatch):
    monkeypatch.setattr("handoff.sandbox.complete", lambda prompt: "```python\nprint(1)\n```")
    code, source = theo_script()
    assert code.strip() == "print(1)" and source == "claude"
