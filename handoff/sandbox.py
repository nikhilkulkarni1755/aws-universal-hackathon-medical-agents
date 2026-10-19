"""Theo's program runs in a Tenki sandbox (outbound off); the trusted template is the only local fallback."""
import json
import os
import re
import subprocess
import sys
import time

from .llm import complete

# Theo's program. Step 1 gathers every source for a bed (vitals, labs, intake/output, notes); step 2 flags the abnormal
# findings; step 3 writes a pattern impression. It never names a condition: that stays with Vera's wording and Iris.
THEO_SCRIPT = '''
import json, sys
p = json.loads(sys.argv[1])
LIMITS = (("temp_c", "Temp", lambda x: x >= 38.0), ("hr", "HR", lambda x: x >= 100), ("rr", "RR", lambda x: x >= 20),
          ("sbp", "SBP", lambda x: x <= 105), ("spo2", "SpO2", lambda x: x <= 94))
first, last = p["vitals"][0], p["vitals"][-1]
hours = int(last["time"][:2]) - int(first["time"][:2])

# 1. gather
trends = {}
for k, _, _ in LIMITS:
    v = [r[k] for r in p["vitals"]]
    trends[k] = {"first": v[0], "last": v[-1], "min": min(v), "max": max(v), "delta": round(v[-1] - v[0], 1)}
gathered = {"vitals": trends, "labs": len(p["labs"]), "io_blocks": len(p["intake_output"]), "notes": len(p["notes"])}

# 2. flag abnormal findings
signals = []
for k, label, bad in LIMITS:
    if bad(last[k]):
        signals.append({"source": "Vitals", "text": f"{label} {first[k]} to {last[k]} over {hours} h",
                        "citation": f"[Vitals {first['time']}–{last['time']}]"})
for lab in p["labs"]:
    if not lab["ref_low"] <= lab["value"] <= lab["ref_high"]:
        signals.append({"source": "Lab", "text": f"{lab['name']} {lab['value']} {lab['unit']}".strip(),
                        "citation": f"[Lab {lab['name']} {lab['time']}]"})
io = p["intake_output"]
if io[-1]["urine_ml"] < 0.5 * io[0]["urine_ml"]:
    signals.append({"source": "I/O", "text": f"Urine {io[0]['urine_ml']} to {io[-1]['urine_ml']} mL",
                    "citation": f"[I/O {io[-1]['time'].replace('-', '–')}]"})

# 3. impression (a pattern summary, never a diagnosis)
sources = sorted({s["source"] for s in signals})
impression = (f"{len(signals)} abnormal findings across {len(sources)} sources ({', '.join(sources)}). "
              "A pattern summary, not a diagnosis; it needs provider evaluation.") if signals else "No abnormal findings."

hr = [r["hr"] for r in p["vitals"]]
w, h, lo, span = 120, 28, min(hr), (max(hr) - min(hr)) or 1
pts = " ".join(f"{i * w / (len(hr) - 1):.1f},{h - (x - lo) / span * h:.1f}" for i, x in enumerate(hr))
svg = f'<svg width="{w}" height="{h}"><polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="2"/></svg>'
print(json.dumps({"gathered": gathered, "signals": signals, "impression": impression, "trends": trends, "svg": svg}))
'''
KEYS = {"gathered", "signals", "impression", "trends", "svg"}

PROMPT = f"""Re-implement the Python program below independently, from scratch, in your own style (standard library \
only, no network). It must print exactly the same JSON as the reference for every patient record. Reply with only \
the code.

REFERENCE:
{THEO_SCRIPT}"""


def theo_script():
    """Ask Claude for an independent re-implementation; the template when there is no reply. Returns (code, source)."""
    reply = complete(PROMPT, max_tokens=3000)
    if not reply:
        return THEO_SCRIPT, "template"
    return re.sub(r"^```(?:python)?\n|```\s*$", "", reply.strip(), flags=re.M), "claude"


def run_local(payloads):
    """Runs only the trusted template, never model-written code, outside the sandbox."""
    return [json.loads(subprocess.run([sys.executable, "-c", THEO_SCRIPT, json.dumps(p)], capture_output=True,
                                      text=True, timeout=30, check=True).stdout) for p in payloads]


def run_script(script, payloads, source="template"):
    """One sandbox per call, one exec per payload. A model-written script is accepted only if its findings equal the
    trusted template's. Returns (results, badge) where the badge says what actually ran."""
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
                    if not KEYS <= out[-1].keys():
                        raise ValueError("script output is missing required keys")
            if source == "claude" and [o["signals"] for o in out] != [r["signals"] for r in run_local(payloads)]:
                raise ValueError("model script disagrees with the trusted reference")
            return out, f"tenki sandbox · {source} script · {time.time() - start:.1f}s"
        except Exception as exc:  # any sandbox or script failure falls back to the trusted local template
            note = f"local template fallback ({exc.__class__.__name__})"
    else:
        note = "local template (no TENKI_API_KEY)"
    return run_local(payloads), f"{note} · {time.time() - start:.1f}s"
