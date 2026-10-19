"""Run Theo's analysis script in a Tenki sandbox (outbound off); fall back to a local subprocess."""
import json
import os
import re
import subprocess
import sys
import time

from .llm import complete

# Stand-in for the Claude-written script: trend stats per vital sign plus a heart-rate sparkline.
THEO_SCRIPT = '''
import json, sys
d = json.loads(sys.argv[1])
trends = {}
for k in ("temp_c", "hr", "rr", "sbp", "spo2"):
    v = [r[k] for r in d["vitals"]]
    trends[k] = {"first": v[0], "last": v[-1], "min": min(v), "max": max(v), "delta": round(v[-1] - v[0], 1)}
hr = [r["hr"] for r in d["vitals"]]
w, h, lo, span = 120, 28, min(hr), (max(hr) - min(hr)) or 1
pts = " ".join(f"{i * w / (len(hr) - 1):.1f},{h - (x - lo) / span * h:.1f}" for i, x in enumerate(hr))
svg = f'<svg width="{w}" height="{h}"><polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="2"/></svg>'
print(json.dumps({"trends": trends, "svg": svg}))
'''


PROMPT = """Write a complete Python 3 script (standard library only, no network). It reads one JSON patient record \
from sys.argv[1] with a "vitals" list of {time, temp_c, hr, rr, sbp, dbp, spo2}. It prints exactly one line of JSON: \
{"trends": {"temp_c"|"hr"|"rr"|"sbp"|"spo2": {"first","last","min","max","delta"}}, "svg": "<svg ...>...</svg>"} where \
the svg is a heart-rate sparkline. Reply with only the code."""


def theo_script():
    """Ask Claude for the analysis script; keep the template when there is no reply. Returns (code, source)."""
    reply = complete(PROMPT)
    if not reply:
        return THEO_SCRIPT, "template"
    return re.sub(r"^```(?:python)?\n|```\s*$", "", reply.strip(), flags=re.M), "claude"


def _local(payloads):
    """Fallback runs only the trusted template, never model-written code, outside the sandbox."""
    return [json.loads(subprocess.run([sys.executable, "-c", THEO_SCRIPT, json.dumps(p)], capture_output=True,
                                      text=True, timeout=30, check=True).stdout) for p in payloads]


def run_script(script, payloads, source="template"):
    """One sandbox per call, one exec per payload. Returns (results, badge) where badge says what actually ran."""
    start = time.time()
    if os.environ.get("TENKI_API_KEY"):
        try:
            from tenki import Sandbox
            with Sandbox.create(name="theo-run", cpu_cores=1, memory_mb=1024, allow_outbound=False) as sb:
                out = []
                for p in payloads:
                    res = sb.exec("python3", "-c", script, json.dumps(p))
                    res.check()
                    out.append(json.loads(res.stdout_text))
                    if not {"trends", "svg"} <= out[-1].keys():
                        raise ValueError("script output missing trends or svg")
            return out, f"tenki sandbox · {source} script · {time.time() - start:.1f}s"
        except Exception as exc:  # any sandbox or script failure falls back to the trusted local template
            note = f"local template fallback ({exc.__class__.__name__})"
    else:
        note = "local template (no TENKI_API_KEY)"
    return _local(payloads), f"{note} · {time.time() - start:.1f}s"
