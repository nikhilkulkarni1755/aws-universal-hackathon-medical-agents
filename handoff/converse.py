"""Prompt-driven conversation: Quinn hands the nurse's request to the agents who own it, they answer from the evidence
in their own voices, and Iris audits every reply. Without a model (or if it fails) the keyword router answers."""
import json
import re
import sys

from .agents import PERSONAS, echo_claims, load_patients
from .iris import check_chat, verdict
from .llm import complete
from .personality import quip
from .pipeline import answer

NAMES = [p["name"] for p in PERSONAS]
SYSTEM = """You run the 4 West handoff team for the incoming nurse (RN). Agents: Quinn (head nurse: dry, routes work, \
prepares provider forms), Wren (chart and handoff clerk: cheerful Canadian, census, verbal handoff, notes, trends), \
Mina (medication safety: precise, loves a pun), Vera (risk validator and SBAR writer: blunt and decisive), Iris \
(safety auditor: deadpan, strict).
Answer the RN's request using ONLY the evidence JSON. Reply with JSON only: \
{"turns":[{"from":"Quinn","to":"Wren","text":"..."}]}.
Rules: 1 to 4 turns. The first turn is Quinn handing the request to the best agent or agents by name. Later turns are \
those agents answering in their own voice (at most one joke, about the team or the paperwork, never a patient's \
condition); the last turn is addressed to "RN". Each turn is at most 2 short sentences. Refer to patients by bed number \
only, never by name. After every sentence that states a value, event or observation, put a citation copied exactly from \
the evidence (for example [Lab Potassium 06:00]). Never diagnose, never name a condition as the cause, never give a \
dose, and never tell the RN to start, stop, give, hold or order any treatment; recommendations are only: notify provider, \
recheck at a stated time, monitor, verify with pharmacy, clarify with the outgoing nurse. If the evidence does not \
answer the request, say so and name who could check. Do not repeat earlier replies word for word."""


def evidence(result):
    """Everything the agents may cite, with a ready-made citation next to each fact. No patient names."""
    claims, out = echo_claims(), {}
    for p in load_patients():
        bed = p["bed"]
        row = next(r for r in result["ranking"] if r["bed"] == bed)
        out[bed] = {
            "chart": {"text": f"{p['age']}{p['sex']}, {p['code_status']}, allergies {', '.join(p['allergies'])}, "
                              f"admitted for {p['diagnosis']}", "cite": "[Chart]"},
            "tier": row["tier"],
            "findings": [{"text": s["text"], "cite": s["citation"], "found_by": s["agent"]} for s in row["signals"]],
            "vitals": [{"text": f"temp {v['temp_c']}, HR {v['hr']}, RR {v['rr']}, BP {v['sbp']}/{v['dbp']}, SpO2 {v['spo2']}",
                        "cite": f"[Vitals {v['time']}]"} for v in p["vitals"]],
            "labs": [{"text": f"{l['name']} {l['value']} {l['unit']} (reference {l['ref_low']} to {l['ref_high']})",
                      "cite": f"[Lab {l['name']} {l['time']}]"} for l in p["labs"]],
            "intake_output": [{"text": f"urine {b['urine_ml']} mL", "cite": f"[I/O {b['time'].replace('-', '–')}]"}
                              for b in p["intake_output"]],
            "meds": [{"text": f"{m['drug']}, {m['schedule']}, status {m['status']}", "cite": f"[MAR {m['drug'].split()[0]}]"}
                     for m in p["meds"]],
            "notes": [{"text": n["text"], "cite": f"[Note {n['time']}]"} for n in p["notes"]],
            "verbal_handoff": [{"text": c["claim"], "cite": c["citation"]} for c in claims if c["bed"] == bed],
            "sbar": {k: v for k, v in result["sbars"][bed]["sections"].items() if k != "S"},  # S opens with the patient's name
        }
    return out


def _scripted(question, result, note):
    ans = answer(question, result)
    turns = [] if ans["agent"] == "Quinn" else [
        {"from": "Quinn", "to": ans["agent"], "text": f"{ans['agent']}, can you take this one? {quip('Quinn', 'route')}", "citations": []}]
    turns.append({"from": ans["agent"], "to": "RN", "text": ans["text"], "citations": ans["citations"]})
    return turns, note


def _turns(reply):
    """Pull the turns out of a model reply, tolerating prose around the JSON, loose names and a loose 'to' field."""
    match = re.search(r"\{.*\}", reply, re.S)
    try:
        raw = json.loads(match.group(0))["turns"]
        by_name = {n.lower(): n for n in NAMES}
        turns = [{"from": by_name[str(t["from"]).strip().lower()],
                  "to": by_name.get(str(t.get("to", "")).strip().lower(), "RN"), "text": str(t["text"]).strip()}
                 for t in raw if str(t.get("from", "")).strip().lower() in by_name and str(t.get("text", "")).strip()]
    except (AttributeError, ValueError, KeyError, TypeError):
        turns = []
    if turns:
        turns[-1]["to"] = "RN"
    return turns[:4]


def _valid(reply, allowed):
    """Parse the model's turns and audit each one. Returns (turns, None) or (None, reason)."""
    turns = _turns(reply)
    if not turns:
        print(f"model reply was not usable turns: {reply[:300]!r}", file=sys.stderr)
        return None, "the model's reply was not in the expected shape"
    for t in turns:
        t["citations"] = re.findall(r"\[[^\]]+\]", t["text"])
        if any(c not in allowed for c in t["citations"]):
            return None, "a citation did not exist in the evidence (CR-8)"
        bad = check_chat(t["text"])
        if bad:
            return None, verdict(bad)["text"]
    return turns, None


def respond(question, result, history):
    """Returns (turns, how). Each turn is {"from","to","text","citations"}; `how` says what produced them."""
    ev = evidence(result)
    prompt = json.dumps({"request": question, "earlier": history[-4:], "evidence": ev}, ensure_ascii=False)
    reply = complete(prompt, system=SYSTEM, max_tokens=1500)
    if not reply:
        return _scripted(question, result, "keyword router (no live model reply)")
    turns, why = _valid(reply, set(re.findall(r"\[[^\]]+\]", json.dumps(ev, ensure_ascii=False))))
    if turns:
        return turns, "live Claude via Flatkey, each reply audited by Iris"
    scripted, _ = _scripted(question, result, "")
    return [{"from": "Iris", "to": "Quinn", "text": f"I blocked the model's reply. {why}", "citations": []}] + scripted, \
        "keyword router, after Iris blocked the model's reply"
