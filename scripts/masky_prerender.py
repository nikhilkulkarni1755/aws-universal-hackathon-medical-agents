"""Warm Masky's cache with Quinn's scripted lines as lip-synced video (about a minute each; replays are free).
Run from repo/:  set -a; . ./.env; set +a; python scripts/masky_prerender.py"""
import os
import sys
import time
from pathlib import Path

os.environ["TENKI_API_KEY"] = ""   # only the lines are needed, not the sandbox
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from handoff import masky  # noqa: E402
from handoff.personality import quip  # noqa: E402
from handoff.pipeline import run  # noqa: E402

lines = []
run(lambda sender, to, text, *rest: lines.append(text) if sender == "Quinn" else None)
lines += [f"{agent}, can you take this one? {quip('Quinn', 'route')}" for agent in ("Wren", "Mina", "Vera", "Iris")]
for text in dict.fromkeys(lines):
    start = time.time()
    url = masky.speak("Quinn", text, timeout=300, output="video")
    print(f"{'ready' if url else 'FAILED'} {time.time() - start:4.0f}s  {text[:70]}", flush=True)
