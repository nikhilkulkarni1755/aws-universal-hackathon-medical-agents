"""Live-service checks. Run with: LIVE=1 .venv/bin/python -m pytest tests/test_live.py (needs keys in .env)."""
import os

import pytest

from handoff.sandbox import THEO_SCRIPT, run_script
from handoff.agents import load_patients


def test_sandbox_local_fallback_runs_the_script():
    results, badge = run_script(THEO_SCRIPT, load_patients()[1:2])
    assert badge.startswith(("local", "tenki sandbox"))
    assert results[0]["trends"]["hr"] == {"first": 82, "last": 104, "min": 82, "max": 104, "delta": 22}
    assert results[0]["svg"].startswith("<svg")


@pytest.mark.skipif(not os.environ.get("LIVE"), reason="set LIVE=1 to call Tenki")
def test_tenki_sandbox_is_used_when_key_present():
    from server import ROOT  # noqa: F401  (loads .env)
    _, badge = run_script(THEO_SCRIPT, load_patients()[:1])
    assert badge.startswith("tenki sandbox")
