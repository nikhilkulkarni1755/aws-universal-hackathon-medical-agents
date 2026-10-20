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
STYLE = {  # one distinct positive emotion per agent, plus delivery that suits the personality
    "Quinn": {"emotion": "contentment", "prosody": ["expressive_high"]},
    "Wren": {"emotion": "elation", "prosody": ["speed_fast", "expressive_high"]},
    "Mina": {"emotion": "amusement", "prosody": ["expressive_high"]},
    "Vera": {"emotion": "determination", "prosody": ["pitch_low"]},
    "Iris": {"emotion": "pride", "prosody": ["speed_slow", "pitch_low"]},
}
VIDEO = {"Quinn"}   # agents shown as lip-synced video when the line is already rendered (Masky caches identical lines)

SAY = [  # chart shorthand, read the way a nurse says it
    (r"\bTemp\b", "temperature"), (r"\bHR\b", "heart rate"), (r"\bRR\b", "respiratory rate"), (r"\bSBP\b", "systolic pressure"),
    (r"\bSpO2\b", "oxygen saturation"), (r"\bWBC\b", "white count"), (r"\bBNP\b", "B N P"), (r"\bMAR\b", "M A R"),
    (r"\bIV\b", "I V"), (r"\bDNR\b", "D N R"), (r"\bNKDA\b", "no known drug allergies"), (r"\bSBARs\b", "S B A R's"),
    (r"\bSBAR\b", "S B A R"), (r"\bUTI\b", "U T I"), (r"\bI/O\b", "intake and output"), (r"\bRN\b", "R N"),
    (r"(\d) h\b", r"\1 hours"), (r"mmol/L", "millimoles per liter"), (r"mg/dL", "milligrams per deciliter"),
    (r"g/dL", "grams per deciliter"), (r"K/uL", "thousand per microliter"), (r"pg/mL", "picograms per milliliter"),
    (r"\bmL\b", "milliliters"), (r"\bmg\b", "milligrams"), (r"\bCR-(\d+)\b", r"rule \1"), (r"\b(40[1-4]):", r"Bed \1:"),
    (r"\s*\(([^)]*)\)", r", \1"), (r"\s*;\s*", " <|prosody:pause|> "),
]
FLOURISH = [  # a beat of personality in the voice that the caption does not need
    (r"Digoxin and low potassium\. Not exactly a match made in chemistry\.", "Digoxin and low potassium, not exactly a match made in chemistry <|sfx:laughter|>Haha!"),
    (r"Nice try\.", r"\g<0> <|prosody:long_pause|>"),
]


def _call(method, path, body=None):
    req = Request(BASE + path, method=method, data=json.dumps(body).encode() if body else None,
                  headers={"Authorization": f"Bearer {os.environ['MASKY_API_KEY']}", "Content-Type": "application/json"})
    return json.load(urlopen(req, timeout=30))


def has_voice(agent):
    return bool(os.environ.get("MASKY_API_KEY")) and FILE.exists() and agent in json.loads(FILE.read_text())


def spoken(text):
    """Written for the ear. Citations are for the eye, so they go; Masky splits replies at 3 sentences, so send at most 3."""
    text = re.sub(r"\[[^\]]+\]", "", text)
    for pattern, said in SAY + FLOURISH:
        text = re.sub(pattern, said, text)
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    out = " ".join(sentences[:3])
    return out if len(out) <= 480 else out[:480].rsplit(" ", 1)[0]


def _conversation(agent):
    with LOCK:
        avatars = json.loads(FILE.read_text())
        a = avatars[agent]
        if "shareSlug" not in a:
            made = _call("POST", "/conversations", {"avatarOwnerUserId": a["avatarOwnerUserId"], "avatarId": a["avatarId"]})
            a.update(conversationId=made["conversationId"], shareSlug=made["shareSlug"])
            FILE.write_text(json.dumps(avatars, indent=2))
        return a


def speak(agent, text, timeout=25, output="audio"):
    """URL of the rendered line ("audio" or lip-synced "video"), or None if it is not ready within `timeout`."""
    if not has_voice(agent):
        return None
    try:
        a = _conversation(agent)
        turn = _call("POST", f"/conversations/{a['conversationId']}/turn",
                     {"userText": spoken(text), "mode": "speak", "output": output,
                      **({"voiceStyle": STYLE[agent]} if agent in STYLE else {})})["turn"]["id"]
        deadline = time.time() + timeout
        while time.time() < deadline:
            found = next((t for t in _call("GET", f"/conversations/by-slug/{a['shareSlug']}")["turns"] if t["id"] == turn), None)
            if found and found.get(f"{output}Url"):
                return found[f"{output}Url"]
            if found and found.get("status") == "error":
                return None
            time.sleep(1)
    except (OSError, KeyError, ValueError):
        pass
    return None
