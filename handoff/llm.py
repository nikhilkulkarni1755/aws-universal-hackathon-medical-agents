"""Claude through Flatkey's OpenAI-compatible router. Returns None without a key or on any failure,
so callers fall back to their template."""
import json
import os
import urllib.request

URL = "https://router.flatkey.ai/v1/chat/completions"


def complete(prompt, system="", max_tokens=1500):
    key = os.environ.get("FLATKEY_API_KEY")
    if not key:
        return None
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    body = {"model": os.environ.get("FLATKEY_MODEL", "claude-opus-5-5"), "max_tokens": max_tokens, "messages": messages}
    req = urllib.request.Request(URL, json.dumps(body).encode(),
                                 {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)["choices"][0]["message"]["content"]
    except (OSError, KeyError, IndexError, ValueError):
        return None
