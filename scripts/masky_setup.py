"""Create one Masky avatar per agent (portrait + voice + personality). Idempotent: reads/writes masky_avatars.json.
Usage: set -a; . ./.env; set +a; python scripts/masky_setup.py"""
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://masky.ai/api"
OUT = Path(__file__).resolve().parent.parent / "masky_avatars.json"
STYLE = "friendly illustrated portrait, head and shoulders, hospital setting, soft studio light, "

# name: (voice name, portrait, personality). Order = priority if the tier caps avatars.
AGENTS = {
    "Quinn": ("Seasoned Midwestern Actress", "steady middle-aged charge nurse, lanyard, teal scrubs", "You are Quinn, the charge nurse. Steady, brief, in charge."),
    "Wren": ("Cheerful Canadian", "efficient friendly unit clerk holding a clipboard", "You are Wren, the chart clerk. Quick, cheerful and exact about code status and allergies."),
    "Iris": ("Mrs. Pembroke", "strict skeptical safety auditor, round glasses, arms crossed", "You are Iris, a strict, skeptical safety auditor. Slow, low, exact. You reject anything that is a diagnosis or a treatment order."),
    "Vera": ("Inspiring Woman", "decisive senior nurse, confident, navy scrubs", "You are Vera, a decisive risk validator. You ask follow-up questions before you escalate."),
    "Mina": ("Dr. Marina Oliveira", "careful precise clinical pharmacist, white coat", "You are Mina, a careful medication safety pharmacist. Precise and exact."),
}


def call(method, path, body=None):
    req = urllib.request.Request(f"{BASE}{path}", method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {os.environ['MASKY_API_KEY']}", "Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code} {e.read().decode()[:300]}")


def main():
    voices = {v["name"]: v["id"] for v in call("GET", "/voices")["voices"]}
    made = json.loads(OUT.read_text()) if OUT.exists() else {}
    for name, (voice, look, personality) in AGENTS.items():
        if name in made:
            continue
        img = call("POST", "/images/generate", {"prompt": STYLE + look, "aspectRatio": "1:1"})["imageUrl"]
        av = call("POST", "/avatars", {"displayName": f"{name} (SBAR Handoff Team)", "imageUrl": img,
                                       "personalityPrompt": personality, "voiceId": voices[voice]})["avatar"]
        made[name] = {"avatarId": av["avatarId"], "avatarOwnerUserId": av["avatarOwnerUserId"], "image": img}
        OUT.write_text(json.dumps(made, indent=2))
        print("created", name)


if __name__ == "__main__":
    main()
