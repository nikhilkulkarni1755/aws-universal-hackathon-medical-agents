"""python server.py -> http://localhost:8000. Runs with no API key and no internet (offline fallbacks everywhere)."""
import json
import os
import threading
import time
import urllib.request

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from handoff import pipeline
from handoff.agents import PERSONAS, ROOT

for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    key, _, value = line.partition("=")
    os.environ.setdefault(key.strip(), value.strip())

app = FastAPI()
EVENTS, STATE = [], {"result": None, "running": False}
CV = threading.Condition()
AUDIT = ROOT / "audit.jsonl"
PACE_S = float(os.environ.get("EVENT_PACE_S", "0.4"))


def emit(sender, to, text, citations=(), attachment=None):
    with CV:
        EVENTS.append({"id": len(EVENTS), "from": sender, "to": to, "text": text,
                       "citations": list(citations), "attachment": attachment, "ts": time.time()})
        CV.notify_all()
    time.sleep(PACE_S)


def _worker(agent):
    STATE["result"] = pipeline.run(emit, agent)
    STATE["running"] = False
    with CV:
        EVENTS.append({"id": len(EVENTS), "done": True})
        CV.notify_all()


@app.get("/api/agents")
def agents():
    return {"agents": PERSONAS, "demo": pipeline.AGENTS, "mode": "CACHED (live integrations pending)"}


@app.post("/api/run")
def run(agent: str | None = None):
    """No agent = full handoff. With ?agent=theo, only that agent's events run (upstream steps stay silent)."""
    if agent and agent not in pipeline.AGENTS:
        raise HTTPException(404, "unknown agent")
    if STATE["running"]:
        raise HTTPException(409, "run in progress")
    with CV:
        EVENTS.clear()
    STATE.update(result=None, running=True)
    threading.Thread(target=_worker, args=(agent,), daemon=True).start()
    return {"started": True}


@app.get("/api/stream")
def stream():
    def gen():
        i = 0
        while True:
            with CV:
                while i >= len(EVENTS):
                    CV.wait(timeout=15)
                    if i >= len(EVENTS):
                        yield ": keepalive\n\n"
                batch, i = EVENTS[i:], len(EVENTS)
            for e in batch:
                yield f"data: {json.dumps(e)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/state")
def state():
    return {"result": STATE["result"], "running": STATE["running"], "events": EVENTS}


@app.post("/api/ask")
async def ask(req: Request):
    question = (await req.json()).get("question", "")
    ans = pipeline.answer(question, STATE["result"])
    emit("RN", "Quinn", question)
    emit("Quinn", "RN", ans["text"], ans["citations"])
    return ans


def _page(bed, tier, approver, citations):
    """n8n payload: bed, tier, approver, time and citations only (CR-15)."""
    body = {"bed": bed, "tier": tier, "approver": approver, "time": time.strftime("%H:%M:%S"),
            "citations": citations}
    url = os.environ.get("N8N_WEBHOOK_URL")
    if not url:
        return body, "page queued (demo)"
    try:
        req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5)
        return body, "page sent via n8n"
    except OSError as exc:
        return body, f"n8n unreachable ({exc.__class__.__name__}); page queued (demo)"


@app.post("/api/approve/{bed}")
async def approve(bed: str, req: Request):
    result = STATE["result"]
    body = await req.json()
    if not result or bed not in result["sbars"]:
        raise HTTPException(404, "no draft for that bed")
    if not result["sbars"][bed]["iris"]["ok"]:
        raise HTTPException(409, "Iris has not passed this draft")
    if body.get("hash") != result["hashes"][bed]:
        raise HTTPException(409, "draft changed since review; approve again")
    tier = next(r["tier"] for r in result["ranking"] if r["bed"] == bed)
    form = result["forms"][bed]
    payload, status = _page(bed, tier, body.get("approver", "Incoming RN"), form["evidence"])
    with AUDIT.open("a") as f:
        f.write(json.dumps({**payload, "hash": result["hashes"][bed]}) + "\n")
    emit("Felix", "RN", f"{bed}: {status}.", form["evidence"])
    return {"status": status, "payload": payload}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
