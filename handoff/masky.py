"""Masky voices: one conversation per agent avatar. speak() returns an audio URL in the agent's own voice
(Masky reuses the render for identical scripted lines) or None, and the caller falls back to browser speech."""
import json
import os
import re
import threading
import time
from urllib.request import Request, urlopen

from .agents import ROOT

BASE = "https://masky.ai/api"
FILE = ROOT / "masky_avatars.json"
LOCK = threading.Lock()
STYLE = {  # delivery cues (Masky voiceStyle) that sharpen each personality
    "Quinn": {"emotion": "contentment"},
    "Wren": {"emotion": "enthusiasm"},
    "Vera": {"emotion": "determination"},
    "Iris": {"prosody": ["speed_slow", "pitch_low"]},
    "Mina": {"emotion": "contemplation"},
}


def _call(method, path, body=None):
    req = Request(BASE + path, method=method, data=json.dumps(body).encode() if body else None,
                  headers={"Authorization": f"Bearer {os.environ['MASKY_API_KEY']}", "Content-Type": "application/json"})
    return json.load(urlopen(req, timeout=30))


def has_voice(agent):
    return bool(os.environ.get("MASKY_API_KEY")) and FILE.exists() and agent in json.loads(FILE.read_text())


def image(agent):
    """Portrait URL of the agent's Masky avatar, or None."""
    return json.loads(FILE.read_text()).get(agent, {}).get("image") if FILE.exists() else None


def spoken(text):
    """Citations are for the eye, not the ear; Masky splits replies at 3 sentences, so send at most 3."""
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\[[^\]]+\]", "", text).strip())
    return " ".join(sentences[:3])[:480]


def _conversation(agent):
    with LOCK:
        avatars = json.loads(FILE.read_text())
        a = avatars[agent]
        if "shareSlug" not in a:
            made = _call("POST", "/conversations", {"avatarOwnerUserId": a["avatarOwnerUserId"], "avatarId": a["avatarId"]})
            a.update(conversationId=made["conversationId"], shareSlug=made["shareSlug"])
            FILE.write_text(json.dumps(avatars, indent=2))
        return a


def speak(agent, text, timeout=25):
    if not has_voice(agent):
        return None
    try:
        a = _conversation(agent)
        turn = _call("POST", f"/conversations/{a['conversationId']}/turn",
                     {"userText": spoken(text), "mode": "speak", "output": "audio",
                      **({"voiceStyle": STYLE[agent]} if agent in STYLE else {})})["turn"]["id"]
        deadline = time.time() + timeout
        while time.time() < deadline:
            found = next((t for t in _call("GET", f"/conversations/by-slug/{a['shareSlug']}")["turns"] if t["id"] == turn), None)
            if found and found.get("audioUrl"):
                return found["audioUrl"]
            if found and found.get("status") == "error":
                return None
            time.sleep(1)
    except (OSError, KeyError, ValueError):
        pass
    return None
