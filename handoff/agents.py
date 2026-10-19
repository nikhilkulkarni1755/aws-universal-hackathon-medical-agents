"""Agent logic over data/patients.json. Every finding is a signal dict with a citation."""
import html
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from urllib.request import urlopen

DAILYMED = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
ROOT = Path(__file__).resolve().parent.parent

PERSONAS = [
    {"name": "Quinn", "role": "Head Nurse", "color": "#4C6EF5", "pitch": 0.8, "rate": 0.95},
    {"name": "Wren", "role": "Chart & Handoff", "color": "#868E96", "pitch": 1.1, "rate": 1.05},
    {"name": "Mina", "role": "Medication Safety", "color": "#E64980", "pitch": 1.25, "rate": 1.0},
    {"name": "Vera", "role": "Risk & SBAR", "color": "#7048E8", "pitch": 1.0, "rate": 0.9},
    {"name": "Iris", "role": "Safety Auditor", "color": "#E03131", "pitch": 0.6, "rate": 0.85},
]

NOTE_PATTERN = re.compile(r"confus|not herself|cramp|pain [7-9]/10", re.I)
VITAL_LIMITS = (
    ("temp_c", "Temp", lambda x: x >= 38.0),
    ("hr", "HR", lambda x: x >= 100),
    ("rr", "RR", lambda x: x >= 20),
    ("sbp", "SBP", lambda x: x <= 105),
    ("spo2", "SpO2", lambda x: x <= 94),
)


def load_patients():
    return json.loads((ROOT / "data" / "patients.json").read_text())["patients"]


def _sig(p, source, text, citation, kind="condition", severity="low", agent=""):
    return {"bed": p["bed"], "source": source, "text": text, "citation": citation,
            "kind": kind, "severity": severity, "agent": agent}


def _span(t):
    return t.replace("-", "–")


def wren(p):
    """Chart clerk: code status and allergies straight from the chart."""
    return f"{p['bed']} {p['code_status']}, allergy {', '.join(p['allergies'])}"


def theo(p):
    """Trend analyst: condition signals from vitals, labs and I/O."""
    first, last = p["vitals"][0], p["vitals"][-1]
    hours = int(last["time"][:2]) - int(first["time"][:2])
    cite = f"[Vitals {first['time']}–{last['time']}]"
    out = [_sig(p, "Vitals", f"{label} {first[k]} to {last[k]} over {hours} h", cite, agent="Theo")
           for k, label, bad in VITAL_LIMITS if bad(last[k])]
    for lab in p["labs"]:
        if not lab["ref_low"] <= lab["value"] <= lab["ref_high"]:
            out.append(_sig(p, "Lab", f"{lab['name']} {lab['value']} {lab['unit']}".strip(),
                            f"[Lab {lab['name']} {lab['time']}]", agent="Theo"))
    io = p["intake_output"]
    if io[-1]["urine_ml"] < 0.5 * io[0]["urine_ml"]:
        out.append(_sig(p, "I/O", f"Urine {io[0]['urine_ml']} to {io[-1]['urine_ml']} mL",
                        f"[I/O {_span(io[-1]['time'])}]", agent="Theo"))
    return out


def urine_trend(p):
    """Numbers Theo posts when Vera asks him to confirm the urine output."""
    return [(b["time"], b["urine_ml"]) for b in p["intake_output"]]


def echo_notes(p):
    """Listener: condition signals from day-shift nursing notes."""
    return [_sig(p, "Note", n["text"], f"[Note {n['time']}]", agent="Echo")
            for n in p["notes"] if NOTE_PATTERN.search(n["text"])]


def echo_claims():
    """Cached transcript of the outgoing nurse's verbal handoff (live whisper is a later upgrade)."""
    path = ROOT / "assets" / "verbal" / "handoff_1855_transcript.json"
    return json.loads(path.read_text())["claims"]


@lru_cache(maxsize=1)
def dailymed():
    """Digoxin label warning fetched live from DailyMed; the cached excerpt if it is unreachable (badge says which)."""
    cached = json.loads((ROOT / "assets" / "dailymed_digoxin.json").read_text())
    if os.environ.get("NO_LIVE"):
        return {**cached, "badge": "cached excerpt"}
    try:
        found = json.load(urlopen(f"{DAILYMED}/spls.json?drug_name=digoxin&pagesize=25", timeout=10))["data"]
        setid = next(d["setid"] for d in found if d["title"].startswith("DIGOXIN TABLET"))
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", urlopen(f"{DAILYMED}/spls/{setid}.xml", timeout=15).read().decode()))
        warning = next(s for s in re.split(r"(?<=[.!?]) ", text) if re.search(r"hypokalemia.*digoxin toxicity", s, re.I))
        return {**cached, "warning": html.unescape(warning), "badge": "live from DailyMed"}
    except (OSError, StopIteration, KeyError, ValueError):
        return {**cached, "badge": "cached excerpt"}


def mina(p, claims):
    """Medication safety: safety items from the MAR, labs and the verbal handoff."""
    out = []
    pot = next((l for l in p["labs"] if l["name"] == "Potassium"), None)
    dig = next((m for m in p["meds"] if m["drug"].startswith("Digoxin")), None)
    if dig and pot and pot["value"] < pot["ref_low"]:
        out.append(_sig(p, "MAR", f"Digoxin due {dig['next_due']} with potassium {pot['value']} {pot['unit']} "
                        "and no replacement ordered",
                        f"[Lab Potassium {pot['time']}] [MAR Digoxin] {dailymed()['citation']}",
                        "safety", "high", "Mina"))
    verbal = " ".join(c["claim"].lower() for c in claims if c["bed"] == p["bed"])
    for m in p["meds"]:
        if m["status"] == "not_documented":
            name = m["drug"].split()[0]
            said = "mentioned" if name.lower() in verbal else "not mentioned"
            out.append(_sig(p, "MAR", f"{name} due {m['next_due']} not documented and {said} at handoff",
                            f"[MAR {name}] [Verbal 18:55]", "safety", "high", "Mina"))
    return out


def lens(p):
    """Label check: cached classification of the bag photo against the MAR."""
    results = json.loads((ROOT / "assets" / "labels" / "lens_cached_results.json").read_text())["results"]
    return next((r for r in results if r["bed"] == p["bed"]), None)


def lens_signal(p, res):
    if not res or res["classification"] == "match":
        return []
    return [_sig(p, "Label", res["finding"], res["citation"], "safety", res["severity"], "Lens")]


def verbal_conflict(p, claims):
    """CR-9: a verbal 'fine' that the chart disagrees with is stated, not resolved."""
    return next((c for c in claims if c["bed"] == p["bed"] and c["type"] == "status"
                 and re.search(r"fine|great|stable", c["claim"], re.I)), None)


def vera(signals):
    """Risk validator (PLACEHOLDER RULE ONLY): escalate on 4+ condition signals from 3+ sources.
    Safety items put a patient in Act this shift. Order: tier, high-severity safety count, condition count."""
    rows = []
    for bed in sorted({s["bed"] for s in signals}):
        mine = [s for s in signals if s["bed"] == bed]
        cond = [s for s in mine if s["kind"] == "condition"]
        safety = [s for s in mine if s["kind"] == "safety"]
        if len(cond) >= 4 and len({s["source"] for s in cond}) >= 3:
            tier = "Escalate"
        elif safety:
            tier = "Act this shift"
        else:
            tier = "Routine"
        high = sum(s["severity"] == "high" for s in safety)
        rows.append({"bed": bed, "tier": tier, "condition": len(cond), "safety": len(safety),
                     "high": high, "signals": mine})
    order = {"Escalate": 0, "Act this shift": 1, "Routine": 2}
    rows.sort(key=lambda r: (order[r["tier"]], -r["high"], -r["condition"]))
    return rows
