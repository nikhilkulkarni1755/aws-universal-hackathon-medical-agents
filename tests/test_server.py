import json
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
    last = ans["turns"][-1]
    assert last["from"] == "Vera" and "402: Escalate" in last["text"] and last["citations"] and ans["how"].startswith("keyword router")
    assert client.post("/api/approve/402", json={"hash": "wrong"}).status_code == 409
    ok = client.post("/api/approve/402", json={"approver": "Incoming RN", "hash": result["hashes"]["402"]})
    assert ok.status_code == 200 and "page" in ok.json()["status"]
    msg = ok.json()["payload"]["message"]
    assert msg.startswith("Bed 402 (Escalate): Notify provider") and "Liu" not in msg   # readable page, bed number only
    assert server.AUDIT.read_text().count("\n") == 1
    assert "Liu" not in server.AUDIT.read_text()


def test_single_agent_demo_leaves_no_result(client):
    assert client.post("/api/run?agent=wren").status_code == 200
    _wait()
    state = client.get("/api/state").json()
    assert state["result"] is None and {e["from"] for e in state["events"] if "from" in e} == {"Quinn", "Wren"}
    assert client.post("/api/run?agent=theo").status_code == 404


def test_stream_delivers_events_while_a_run_is_in_progress(client):
    """Regression: the stream once held the lock while waiting, so the run never emitted a single event."""
    assert client.post("/api/run?agent=wren").status_code == 200
    seen = []
    for chunk in server.event_stream(server.STATE["start"]):
        if chunk.startswith("data:"):
            seen.append(json.loads(chunk[5:]))
            if seen[-1].get("done"):
                break
        assert len(seen) < 50
    assert any(e.get("from") == "Wren" for e in seen)
    assert client.post("/api/run?agent=wren").status_code == 200  # no stuck "run in progress"


def test_a_crashed_run_does_not_wedge_the_server(client, monkeypatch):
    monkeypatch.setattr(server.pipeline, "run", lambda emit, agent=None: 1 / 0)
    client.post("/api/run")
    _wait()
    assert server.STATE["running"] is False


def test_a_question_works_before_start_and_is_spoken_by_the_owning_agent(client):
    server.STATE.update(result=None, running=False)
    ans = client.post("/api/ask", json={"question": "Is 404 allergic to anything?"}).json()
    assert ans["turns"][-1]["from"] == "Wren" and "Codeine" in ans["turns"][-1]["text"]
    assert server.STATE["result"] is not None


def test_asking_to_run_the_handoff_starts_the_briefing(client):
    server.STATE.update(result=None, running=False)
    assert client.post("/api/ask", json={"question": "Please run the handoff for me"}).json() == {"started": True}
    _wait()


def test_asking_interrupts_a_scripted_run_and_the_team_answers_the_question(client, monkeypatch):
    monkeypatch.setattr(server, "PACE_S", 0.2)
    server.STATE.update(result=None, running=False)
    assert client.post("/api/run").status_code == 200
    time.sleep(0.6)
    assert server.STATE["running"] is True
    ans = client.post("/api/ask", json={"question": "Is 404 allergic to anything?"}).json()
    assert ans["turns"][-1]["from"] == "Wren" and "Codeine" in ans["turns"][-1]["text"]
    assert server.STATE["running"] is False and server.STATE["cancel"] is False
    spoken = [e for e in client.get("/api/state").json()["events"] if "from" in e]
    assert spoken[-1]["from"] == "Wren" and len(spoken) < 20   # the script was cut short, not played to the end
