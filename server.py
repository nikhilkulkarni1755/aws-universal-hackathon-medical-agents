"""python server.py -> http://localhost:8000. Runs with no API key and no internet (offline fallbacks everywhere)."""
import json
import os
import re
import threading
import time
import urllib.request

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from handoff import converse, masky, pipeline
from handoff.agents import PERSONAS, ROOT

for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    key, _, value = line.partition("=")
    os.environ.setdefault(key.strip(), value.strip())

app = FastAPI()
class Cancelled(Exception):
    """Raised inside a run when the nurse asks a question, so the team stops the script and answers."""


EVENTS, STATE = [], {"result": None, "running": False, "start": 0, "cancel": False}  # start = index of the current run's first event
CV = threading.Condition()
AUDIT = ROOT / "audit.jsonl"
PACE_S = float(os.environ.get("EVENT_PACE_S", "0.4"))


def _voice(event):
    """Render the line in the agent's Masky voice, then tell the page which event the audio belongs to."""
    kinds = ["audio"] + (["video"] if event["from"] in masky.VIDEO else [])
    def render(kind):   # video only answers quickly when Masky already holds this exact line; otherwise audio plays
        url = masky.speak(event["from"], event["text"], timeout=25 if kind == "audio" else 6, output=kind)
        if url:
            with CV:
                EVENTS.append({"id": len(EVENTS), f"{kind}_for": event["id"], f"{kind}_url": url})
                CV.notify_all()
    for kind in kinds[1:]:
        threading.Thread(target=render, args=(kind,), daemon=True).start()
    render("audio")


def emit(sender, to, text, citations=(), attachment=None):
    if STATE["cancel"] and threading.current_thread().name == "run":
        raise Cancelled
    with CV:
        event = {"id": len(EVENTS), "from": sender, "to": to, "text": text,
                 "citations": list(citations), "attachment": attachment, "ts": time.time()}
        EVENTS.append(event)
        CV.notify_all()
    if masky.has_voice(sender):
        threading.Thread(target=_voice, args=(event,), daemon=True).start()
    time.sleep(PACE_S)


def _worker(agent):
    try:
        STATE["result"] = pipeline.run(emit, agent)
    except Cancelled:
        pass
    finally:  # a crashed run must never leave the server stuck on "run in progress"
        STATE["running"] = False
        with CV:
            EVENTS.append({"id": len(EVENTS), "done": True})
            CV.notify_all()


@app.get("/api/agents")
def agents():
    return {"agents": [{**p, "masky": masky.has_voice(p["name"]), "video": p["name"] in masky.VIDEO, "image": (ROOT / "assets" / "portraits" / f"{p['name']}.jpg").exists()} for p in PERSONAS], "demo": pipeline.AGENTS, "mode": "CACHED (live integrations pending)"}


@app.post("/api/run")
def run(agent: str | None = None):
    """No agent = full handoff. With ?agent=theo, only that agent's events run (upstream steps stay silent)."""
    if agent and agent not in pipeline.AGENTS:
        raise HTTPException(404, "unknown agent")
    if STATE["running"]:
        raise HTTPException(409, "run in progress")
    with CV:
        STATE["start"] = len(EVENTS)
    STATE.update(result=None, running=True)
    threading.Thread(target=_worker, args=(agent,), daemon=True, name="run").start()
    return {"started": True}


def event_stream(i):
    """Server-sent events from index i on. Never yield while holding the lock, or emit() blocks and the run freezes."""
    while True:
        with CV:
            if i >= len(EVENTS):
                CV.wait(timeout=15)
            batch, i = EVENTS[i:], len(EVENTS)
        if not batch:
            yield ": keepalive\n\n"
        for e in batch:
            yield f"data: {json.dumps(e)}\n\n"


@app.get("/api/stream")
def stream():
    return StreamingResponse(event_stream(STATE["start"]), media_type="text/event-stream")


@app.get("/api/state")
def state():
    return {"result": STATE["result"], "running": STATE["running"], "events": EVENTS[STATE["start"]:]}


class Ask(BaseModel):
    question: str


HISTORY = []   # earlier asks and replies, so the team does not repeat itself


def ensure_result():
    """The nurse's question interrupts any scripted run. If there is no result yet, run the handoff silently once."""
    STATE["cancel"] = True
    for _ in range(100):  # the run stops at its next line (a sandbox call can take a few seconds)
        if not STATE["running"]:
            break
        time.sleep(0.2)
    STATE["cancel"] = False
    if STATE["result"] is None:
        STATE["result"] = pipeline.run(lambda *a, **k: None, silent=True)


@app.post("/api/ask")
def ask(body: Ask):
    """The nurse's own words drive the team (a sync endpoint, so the model call never blocks the event stream)."""
    question = body.question.strip()
    if re.search(r"\b(run|start|begin)\b.*\b(handoff|briefing)\b", question, re.I) and not STATE["running"]:
        return run()
    ensure_result()
    emit("RN", "Quinn", question)
    turns, how = converse.respond(question, STATE["result"], HISTORY)
    for i, t in enumerate(turns):
        note = {"type": "text", "title": "How this was answered", "text": how} if i == 0 else None
        emit(t["from"], t["to"], t["text"], t["citations"], note)
    HISTORY.append({"rn": question, "team": [t["text"] for t in turns]})
    return {"turns": turns, "how": how}


def _page(bed, tier, approver, form):
    """n8n payload: bed, tier, approver, time and citations only (CR-15)."""
    stamp = time.strftime("%H:%M")
    body = {"bed": bed, "tier": tier, "approver": approver, "time": stamp, "ask": form["ask"],
            "message": f"Bed {bed} ({tier}): {form['ask']} Approved by {approver} at {stamp}.",
            "citations": form["evidence"]}
    url = os.environ.get("N8N_WEBHOOK_URL")
    if not url or not url.startswith(("https://", "http://")):  # urlopen would also accept file:// and other schemes
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
    payload, status = _page(bed, tier, body.get("approver", "Incoming RN"), form)
    with AUDIT.open("a") as f:
        f.write(json.dumps({**payload, "hash": result["hashes"][bed]}) + "\n")
    emit("Quinn", "RN", f"{bed}: {status}.", form["evidence"])
    return {"status": status, "payload": payload}


@app.get("/")
def index():
    return FileResponse(ROOT / "static" / "index.html")


app.mount("/assets", StaticFiles(directory=ROOT / "assets"), name="assets")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
