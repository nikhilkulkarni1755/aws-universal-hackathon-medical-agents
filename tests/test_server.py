import os
import time

os.environ["EVENT_PACE_S"] = "0"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import server  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "AUDIT", tmp_path / "audit.jsonl")
    return TestClient(server.app)


def _wait():
    for _ in range(100):
        if not server.STATE["running"]:
            return
        time.sleep(0.05)
    raise AssertionError("run did not finish")


def test_full_run_ask_and_approve(client):
    assert client.post("/api/run").json() == {"started": True}
    _wait()
    result = client.get("/api/state").json()["result"]
    assert [r["bed"] for r in result["ranking"]] == ["402", "403", "404", "401"]
    ans = client.post("/api/ask", json={"question": "Why is 402 above 403?"}).json()
    assert ans["agent"] == "Vera" and "402: Escalate" in ans["text"] and ans["citations"]
    assert client.post("/api/approve/402", json={"hash": "wrong"}).status_code == 409
    ok = client.post("/api/approve/402", json={"approver": "Incoming RN", "hash": result["hashes"]["402"]})
    assert ok.status_code == 200 and "page" in ok.json()["status"]
    assert server.AUDIT.read_text().count("\n") == 1
    assert "Liu" not in server.AUDIT.read_text()


def test_single_agent_demo_leaves_no_result(client):
    assert client.post("/api/run?agent=theo").status_code == 200
    _wait()
    state = client.get("/api/state").json()
    assert state["result"] is None and {e["from"] for e in state["events"] if "from" in e} == {"Quinn", "Theo"}
    assert client.post("/api/run?agent=nobody").status_code == 404
