"""Hear Quinn route questions to Wren in their Masky voices.
Run from repo/:  set -a; . ./.env; set +a; .venv/bin/python scripts/try_quinn_wren.py   (add --silent to skip playback)"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import urlretrieve

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from handoff import masky  # noqa: E402
from handoff.agents import load_patients  # noqa: E402
from handoff.personality import quip  # noqa: E402
from handoff.pipeline import answer  # noqa: E402

QUESTIONS = ["Give me the census.", "What are the allergies in bed 402?", "What's the code status for 404?",
             "Anyone with a different allergy than sulfa in 403?"]


def say(agent, text, play=True):
    start = time.time()
    url = masky.speak(agent, text)
    print(f"{agent:>6}: {text}\n        ({'Masky voice' if url else 'NO AUDIO, check MASKY_API_KEY'}, {time.time() - start:.1f}s)")
    if url and play:
        handle, path = tempfile.mkstemp(suffix=Path(url.split("?")[0]).suffix or ".mp3")
        os.close(handle)
        urlretrieve(url, path)
        subprocess.run(["afplay", path])


def main(play):
    result = {"ranking": [{"bed": p["bed"]} for p in load_patients()]}
    say("Quinn", f"Okay Wren, let's get the unit squared away. {quip('Quinn', 'open')}", play)
    for question in QUESTIONS:
        ans = answer(question, result)
        print(f"\nNurse asks: {question}  -> Quinn routes to {ans['agent']}")
        say("Quinn", f"{ans['agent']}, {question[0].lower() + question[1:]} {quip('Quinn', 'route')}", play)
        say(ans["agent"], ans["text"], play)
    say("Quinn", f"Thanks, Wren. Census done. {quip('Quinn', 'close')}", play)


if __name__ == "__main__":
    main("--silent" not in sys.argv)
