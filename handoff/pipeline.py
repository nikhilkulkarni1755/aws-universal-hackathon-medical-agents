"""Orchestrator: one step per agent, each emitting events. Spoken lines use bed numbers only (CR-15).
Every step can run alone (`run(emit, only="theo")`): upstream steps run silently to build the context."""
import hashlib
import json
import re

from .agents import (echo_claims, echo_notes, dailymed, lens, lens_signal, load_patients, mina, theo,
                     urine_trend, vera, verbal_conflict, wren)
from .iris import check_form, check_text, verdict
from .personality import quip
from .sandbox import run_script, theo_script
from .writers import felix_form, sam_draft

TIERS_LINE = "Cross-source validation (patent pending) ranks the unit."


def digest(sections, form):
    return hashlib.sha256(json.dumps({"sbar": sections, "form": form}, sort_keys=True).encode()).hexdigest()


def _cites(text):
    return re.findall(r"\[[^\]]+\]", text)


def assign(emit, agent, task):
    emit("Quinn", agent, f"{agent}, {task} {quip('Quinn', 'to_' + agent)}".strip())


def quinn_open(ctx, emit):
    emit("Quinn", "all", f"Loading 4 West. Four patients, handoff at 19:00. Let's work through it. {quip('Quinn', 'open')}")


def wren_step(ctx, emit):
    """Wren reads every source: the chart census, the outgoing nurse's handoff, the day-shift notes, and the trends."""
    assign(emit, "Wren", "give me the census, the verbal handoff and the trends.")
    emit("Wren", "Quinn", "Census for 4 West: " + "; ".join(wren(p) for p in ctx["pts"].values()) + ". " + quip("Wren", "census"), ["[Chart]"])


def echo_step(ctx, emit):
    status = next(c for c in ctx["claims"] if c["bed"] == "402" and c["type"] == "status")
    emit("Wren", "Quinn", f"Verbal handoff captured. For 402 the outgoing nurse said: {status['claim'].split(': ', 1)[-1]}. {quip('Wren', 'verbal')}",
         [status["citation"]])
    for bed, p in ctx["pts"].items():
        notes = echo_notes(p)
        ctx["signals"] += notes
        if notes:
            emit("Wren", "Vera", f"{bed}: day-shift note flags: "
                 + "; ".join(s["text"].split(". ")[0].rstrip(".") for s in notes) + ".", [s["citation"] for s in notes])


def theo_step(ctx, emit):
    charts, badge = {}, ""
    if not ctx["quiet"]:  # skip the sandbox when this only runs silently as an upstream step
        script, source = theo_script()
        runs, badge = run_script(script, list(ctx["pts"].values()), source)
        charts = dict(zip(ctx["pts"], runs))
    for bed, p in ctx["pts"].items():
        found = theo(p)
        ctx["signals"] += found
        if not found:
            continue
        att = None
        if charts and bed == "402":
            hr = charts[bed]["trends"]["hr"]
            att = {"type": "svg", "title": f"402 HR {hr['first']} to {hr['last']}", "svg": charts[bed]["svg"], "badge": badge}
        shown = []
        for src in dict.fromkeys(s["source"] for s in found):
            shown += [s for s in found if s["source"] == src][:2]
        emit("Wren", "Vera", f"{bed}: " + "; ".join(s["text"] for s in shown) + ". " + (quip("Wren", "trend") if bed == "402" else ""),
             list(dict.fromkeys(s["citation"] for s in shown)), att)


def lens_step(ctx, emit):
    """Mina checks the IV bag labels against the MAR, then the meds."""
    assign(emit, "Mina", "check the IV bag labels, the meds and anything missed.")
    for bed, p in ctx["pts"].items():
        res = lens(p)
        if res:
            ctx["signals"] += lens_signal(p, res)
            emit("Mina", "Vera", f"{bed}: label is a {res['classification']}. {res['finding']} "
                 + (quip("Mina", "mismatch") if res["classification"] == "mismatch" else ""), [res["citation"]],
                 {"type": "image", "src": f"/assets/labels/{res['image']}"})


def mina_step(ctx, emit):
    for bed, p in ctx["pts"].items():
        found = mina(p, ctx["claims"])
        ctx["signals"] += found
        for s in found:
            label = dailymed()
            att = {"type": "text", "title": f"DailyMed digoxin label ({label['badge']})", "text": label["warning"]} \
                if "DailyMed" in s["citation"] else None
            joke = quip("Mina", "digoxin" if "Digoxin" in s["text"] else "enoxaparin")
            emit("Mina", "Vera", f"{bed}: {s['text']}. {joke}", _cites(s["citation"]), att)


def vera_step(ctx, emit):
    assign(emit, "Vera", "rank the unit, then draft the SBARs. Iris will audit them.")
    ctx["ranking"] = ranking = vera(ctx["signals"])
    top = ranking[0]
    emit("Vera", "Wren", f"Before I escalate {top['bed']}, confirm its urine output trend.")
    io = urine_trend(ctx["pts"][top["bed"]])
    emit("Wren", "Vera", f"{top['bed']} urine: " + ", ".join(f"{ml} mL" for _, ml in io) + " across the day shift.",
         [f"[I/O {io[-1][0].replace('-', '–')}]"])
    conflict = verbal_conflict(ctx["pts"][top["bed"]], ctx["claims"])
    emit("Vera", "Quinn", f"{TIERS_LINE} " + ", ".join(f"{r['bed']} {r['tier']}" for r in ranking) + ". " + quip("Vera", "rank"),
         [conflict["citation"]] if conflict else [])


def sam_step(ctx, emit):
    """Vera drafts the SBARs, Iris audits. The 402 first draft is a labelled red-team draft with a treatment order."""
    ctx["drafts"] = {}
    for r in ctx["ranking"]:
        bed, p = r["bed"], ctx["pts"][r["bed"]]
        args = (r["tier"], p["code_status"], p["allergies"])
        draft = sam_draft(bed, red_team=bed == "402")
        if bed == "402":
            emit("Vera", "Iris", f"First draft for {bed} (red-team draft).", [], {"type": "sbar", "bed": bed, "sbar": draft})
            emit("Iris", "Vera", f"{verdict(check_text(draft, *args))['text']}. {quip('Iris', 'reject')}")
            draft = sam_draft(bed)
            emit("Vera", "Iris", f"Rewritten {bed} as an escalation.", [], {"type": "sbar", "bed": bed, "sbar": draft})
            emit("Iris", "Vera", f"{verdict(check_text(draft, *args))['text']} {quip('Iris', 'pass')}")
        ctx["drafts"][bed] = draft
    emit("Vera", "Iris", f"Drafts for the other beds are ready. {quip('Vera', 'ready')}")


def felix_step(ctx, emit):
    """Quinn prepares the provider forms; Iris audits them."""
    ctx["sbars"], ctx["forms"] = {}, {}
    for r in ctx["ranking"]:
        bed, p, draft = r["bed"], ctx["pts"][r["bed"]], ctx["drafts"][r["bed"]]
        form = felix_form(bed, r["tier"], draft)
        bad = check_text(draft, r["tier"], p["code_status"], p["allergies"]) + check_form(form)
        ctx["sbars"][bed] = {"sections": draft, "iris": verdict(bad)}
        ctx["forms"][bed] = form
    emit("Quinn", "Iris", f"Provider forms are drafted for all four beds. {quip('Quinn', 'forms')}", [], {"type": "form", "forms": ctx["forms"]})
    emit("Iris", "Quinn", "All drafts and forms: " + ("pass." if all(s["iris"]["ok"] for s in ctx["sbars"].values()) else "REJECTED.") + " " + quip("Iris", "all"))


def quinn_close(ctx, emit):
    emit("Quinn", "RN", f"Ready for RN review. Nothing leaves until you approve. {quip('Quinn', 'close')}")


# (agent, step). Five agents: Quinn also prepares forms, Wren reads every source, Mina also checks labels,
# Vera also writes the SBARs. "iris" has no step of its own: her guardrail demo is inside Vera's drafting step.
STEPS = [("quinn", quinn_open), ("wren", wren_step), ("wren", echo_step), ("wren", theo_step), ("mina", lens_step),
         ("mina", mina_step), ("vera", vera_step), ("vera", sam_step), ("quinn", felix_step), ("quinn", quinn_close)]
ALIASES = {"iris": "vera"}
AGENTS = sorted({a for a, _ in STEPS} | set(ALIASES))


def run(emit, only=None):
    """emit(sender, to, text, citations=(), attachment=None). With `only`, just that agent's events are emitted."""
    only = ALIASES.get(only, only)
    send = emit

    def emit(sender, to, text, *rest):  # quips are optional, so trim the gaps they leave
        send(sender, to, text.strip(), *rest)

    ctx = {"pts": {p["bed"]: p for p in load_patients()}, "claims": echo_claims(), "signals": []}
    for agent, step in STEPS:
        ctx["quiet"] = only not in (None, agent)
        step(ctx, (lambda *a, **k: None) if ctx["quiet"] else emit)
    if only:
        return None
    return {"ranking": ctx["ranking"], "sbars": ctx["sbars"], "forms": ctx["forms"],
            "hashes": {b: digest(ctx["sbars"][b]["sections"], ctx["forms"][b]) for b in ctx["sbars"]}}


ROUTES = [  # first match wins; Quinn handles anything else herself
    ("Iris", r"reject|audit|guardrail|rule|cr-\d"),
    ("Vera", r"rank|above|below|first|priority|escalat|tier|top"),
    ("Wren", r"allerg|code status|dnr|full code|census|diagnos|how many"),
    ("Mina", r"\bmeds?\b|medication|digoxin|enoxaparin|dose|interaction|missed"),
    ("Lens", r"label|bag|photo"),
    ("Theo", r"vital|trend|urine|output|temp|heart rate|\bhr\b|pressure|\blabs?\b|lactate|potassium|wbc"),
    ("Echo", r"verbal|said|outgoing|handoff|note"),
    ("Felix", r"form|provider|page|doctor"),
    ("Sam", r"sbar|draft|summar"),
]


OWNER = {"Theo": "Wren", "Echo": "Wren", "Wren": "Wren", "Lens": "Mina", "Mina": "Mina", "Sam": "Vera", "Vera": "Vera",
         "Felix": "Quinn", "Iris": "Iris", "Quinn": "Quinn"}  # skill -> the one of five agents who speaks it


def route(question):
    return next((agent for agent, pattern in ROUTES if re.search(pattern, question, re.I)), "Quinn")


def _facts(signals):
    return ("; ".join(s["text"].rstrip(".") for s in signals) + "." if signals else "nothing flagged."), \
        list(dict.fromkeys(s["citation"] for s in signals))


def _vera(bed, row, result):
    by_source = {}
    for s in sorted(row["signals"], key=lambda s: (s["kind"] != "condition", s["severity"] != "high")):
        by_source.setdefault(s["source"], s)
    text, cites = _facts(list(by_source.values())[:4])
    return f"{row['tier']}: {row['condition']} condition signals, {row['safety']} safety items; {text}", cites


def _by_agent(name):
    return lambda bed, row, result: _facts([s for s in row["signals"] if s["agent"] == name])


def _echo(bed, row, result):
    claims = [c for c in echo_claims() if c["bed"] == bed and c["type"] == "status"]
    text, cites = _facts([s for s in row["signals"] if s["agent"] == "Echo"])
    return " ".join(c["claim"] + "." for c in claims) + " Notes: " + text, [c["citation"] for c in claims] + cites


def _sam(bed, row, result):
    a = result["sbars"][bed]["sections"]["A"]
    return a, re.findall(r"\[[^\]]+\]", a)


def _felix(bed, row, result):
    form = result["forms"][bed]
    return "Ask: " + form["ask"], form["evidence"]


ANSWERERS = {
    "Vera": _vera, "Theo": _by_agent("Theo"), "Mina": _by_agent("Mina"), "Lens": _by_agent("Lens"), "Echo": _echo,
    "Sam": _sam, "Felix": _felix,
    "Iris": lambda bed, row, result: (result["sbars"][bed]["iris"]["text"], []),
    "Wren": lambda bed, row, result: (wren(next(p for p in load_patients() if p["bed"] == bed)) + ".", ["[Chart]"]),
}


def answer(question, result):
    """Quinn routes the question to the agent who owns it; that agent answers from cited evidence only."""
    agent = route(question)  # the skill; OWNER says which of the five agents answers
    if not result:
        return {"agent": "Quinn", "text": "Run the handoff first.", "citations": []}
    if agent == "Quinn":
        return {"agent": "Quinn", "text": "I can route questions on rankings, trends, meds, labels, the verbal handoff, "
                "SBARs, forms, allergies or the safety rules. Which bed?", "citations": []}
    rows = {r["bed"]: r for r in result["ranking"]}
    beds = list(dict.fromkeys(b for b in re.findall(r"\b40[1-4]\b", question) if b in rows))
    beds = beds or (list(rows) if agent == "Wren" else [result["ranking"][0]["bed"]])
    parts, cites = [], []
    for bed in beds[:2] if agent != "Wren" else beds:
        text, found = ANSWERERS[agent](bed, rows[bed], result)
        parts.append(text if agent == "Wren" else f"{bed}: {text}")
        cites += found
    return {"agent": OWNER[agent], "text": " ".join(parts + [quip(OWNER[agent], "answer")]).strip(),
            "citations": list(dict.fromkeys(cites))}
