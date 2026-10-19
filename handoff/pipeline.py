"""Orchestrator: one step per agent, each emitting events. Spoken lines use bed numbers only (CR-15).
Every step can run alone (`run(emit, only="theo")`): upstream steps run silently to build the context."""
import hashlib
import json
import re

from .agents import (echo_claims, echo_notes, dailymed, lens, lens_signal, load_patients, mina, theo,
                     urine_trend, vera, verbal_conflict)
from .iris import check_form, check_text, verdict
from .writers import felix_form, sam_draft

TIERS_LINE = "Cross-source validation (patent pending) ranks the unit."


def spark(values, w=120, h=28):
    lo, span = min(values), (max(values) - min(values)) or 1
    pts = " ".join(f"{i * w / (len(values) - 1):.1f},{h - (v - lo) / span * h:.1f}" for i, v in enumerate(values))
    return f'<svg width="{w}" height="{h}"><polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="2"/></svg>'


def digest(sections, form):
    return hashlib.sha256(json.dumps({"sbar": sections, "form": form}, sort_keys=True).encode()).hexdigest()


def _cites(text):
    return re.findall(r"\[[^\]]+\]", text)


def quinn_open(ctx, emit):
    emit("Quinn", "all", "Loading 4 West. Echo, Theo, Lens and Mina, start your checks.")


def echo_step(ctx, emit):
    status = next(c for c in ctx["claims"] if c["bed"] == "402" and c["type"] == "status")
    emit("Echo", "Quinn", f"Verbal handoff captured. For 402 the outgoing nurse said: {status['claim'].split(': ', 1)[-1]}",
         [status["citation"]])
    for bed, p in ctx["pts"].items():
        notes = echo_notes(p)
        ctx["signals"] += notes
        if notes:
            emit("Echo", "Vera", f"{bed}: day-shift note flags: "
                 + "; ".join(s["text"].split(". ")[0].rstrip(".") for s in notes) + ".", [s["citation"] for s in notes])


def theo_step(ctx, emit):
    for bed, p in ctx["pts"].items():
        found = theo(p)
        ctx["signals"] += found
        if not found:
            continue
        att = None
        if bed == "402":
            hr = [v["hr"] for v in p["vitals"]]
            att = {"type": "svg", "title": f"402 HR {hr[0]} to {hr[-1]}", "svg": spark(hr), "badge": "local"}
        shown = []
        for src in dict.fromkeys(s["source"] for s in found):
            shown += [s for s in found if s["source"] == src][:2]
        emit("Theo", "Vera", f"{bed}: " + "; ".join(s["text"] for s in shown) + ".",
             list(dict.fromkeys(s["citation"] for s in shown)), att)


def lens_step(ctx, emit):
    for bed, p in ctx["pts"].items():
        res = lens(p)
        if res:
            ctx["signals"] += lens_signal(p, res)
            emit("Lens", "Mina", f"{bed}: label is a {res['classification']}. {res['finding']}", [res["citation"]],
                 {"type": "image", "src": f"/assets/labels/{res['image']}"})


def mina_step(ctx, emit):
    for bed, p in ctx["pts"].items():
        found = mina(p, ctx["claims"])
        ctx["signals"] += found
        for s in found:
            att = {"type": "text", "title": "DailyMed digoxin label (cached)", "text": dailymed()["warning"]} \
                if "DailyMed" in s["citation"] else None
            emit("Mina", "Vera", f"{bed}: {s['text']}.", _cites(s["citation"]), att)


def vera_step(ctx, emit):
    ctx["ranking"] = ranking = vera(ctx["signals"])
    top = ranking[0]
    emit("Vera", "Theo", f"Before I escalate {top['bed']}, confirm its urine output trend.")
    io = urine_trend(ctx["pts"][top["bed"]])
    emit("Theo", "Vera", f"{top['bed']} urine: " + ", ".join(f"{ml} mL" for _, ml in io) + " across the day shift.",
         [f"[I/O {io[-1][0].replace('-', '–')}]"])
    conflict = verbal_conflict(ctx["pts"][top["bed"]], ctx["claims"])
    emit("Vera", "Quinn", f"{TIERS_LINE} " + ", ".join(f"{r['bed']} {r['tier']}" for r in ranking) + ".",
         [conflict["citation"]] if conflict else [])


def sam_step(ctx, emit):
    """Sam drafts, Iris audits. The 402 first draft is a labelled red-team draft with a treatment order."""
    ctx["drafts"] = {}
    for r in ctx["ranking"]:
        bed, p = r["bed"], ctx["pts"][r["bed"]]
        args = (r["tier"], p["code_status"], p["allergies"])
        draft = sam_draft(bed, red_team=bed == "402")
        if bed == "402":
            emit("Sam", "Iris", f"First draft for {bed} (red-team draft).", [], {"type": "sbar", "bed": bed, "sbar": draft})
            emit("Iris", "Sam", verdict(check_text(draft, *args))["text"])
            draft = sam_draft(bed)
            emit("Sam", "Iris", f"Rewritten {bed} as an escalation.", [], {"type": "sbar", "bed": bed, "sbar": draft})
            emit("Iris", "Sam", verdict(check_text(draft, *args))["text"])
        ctx["drafts"][bed] = draft
    emit("Sam", "Iris", "Drafts for the other beds are ready.")


def felix_step(ctx, emit):
    ctx["sbars"], ctx["forms"] = {}, {}
    for r in ctx["ranking"]:
        bed, p, draft = r["bed"], ctx["pts"][r["bed"]], ctx["drafts"][r["bed"]]
        form = felix_form(bed, r["tier"], draft)
        bad = check_text(draft, r["tier"], p["code_status"], p["allergies"]) + check_form(form)
        ctx["sbars"][bed] = {"sections": draft, "iris": verdict(bad)}
        ctx["forms"][bed] = form
    emit("Felix", "Iris", "Provider forms are drafted for all four beds.", [], {"type": "form", "forms": ctx["forms"]})
    emit("Iris", "Quinn", "All drafts and forms: " + ("pass." if all(s["iris"]["ok"] for s in ctx["sbars"].values()) else "REJECTED."))


def quinn_close(ctx, emit):
    emit("Quinn", "RN", "Ready for RN review. Nothing leaves until you approve.")


# (agent, step). "iris" has no step of its own: its guardrail demo is Sam's step. Quinn opens and closes.
STEPS = [("quinn", quinn_open), ("echo", echo_step), ("theo", theo_step), ("lens", lens_step), ("mina", mina_step),
         ("vera", vera_step), ("sam", sam_step), ("felix", felix_step), ("quinn", quinn_close)]
ALIASES = {"iris": "sam"}
AGENTS = sorted({a for a, _ in STEPS} | set(ALIASES))


def run(emit, only=None):
    """emit(sender, to, text, citations=(), attachment=None). With `only`, just that agent's events are emitted."""
    only = ALIASES.get(only, only)
    ctx = {"pts": {p["bed"]: p for p in load_patients()}, "claims": echo_claims(), "signals": []}
    for agent, step in STEPS:
        step(ctx, emit if only in (None, agent) else (lambda *a, **k: None))
    if only:
        return None
    return {"ranking": ctx["ranking"], "sbars": ctx["sbars"], "forms": ctx["forms"],
            "hashes": {b: digest(ctx["sbars"][b]["sections"], ctx["forms"][b]) for b in ctx["sbars"]}}


def answer(question, result):
    """Quinn answers a nurse question from cited evidence only (no new analysis)."""
    if not result:
        return {"text": "Run the handoff first.", "citations": []}
    rows = {r["bed"]: r for r in result["ranking"]}
    beds = [b for b in re.findall(r"\b40[1-4]\b", question) if b in rows]
    if not beds:
        return {"text": "Ask about a bed, for example: why is 402 above 403?", "citations": []}
    parts, cites = [], []
    for bed in dict.fromkeys(beds[:2]):
        r = rows[bed]
        ordered = sorted(r["signals"], key=lambda s: (s["kind"] != "condition", s["severity"] != "high"))
        by_source = {}
        for s in ordered:
            by_source.setdefault(s["source"], s)
        top = list(by_source.values())[:4]
        parts.append(f"{bed} is {r['tier']}: {r['condition']} condition signals, {r['safety']} safety items; "
                     + "; ".join(s["text"].rstrip(".") for s in top) + ".")
        cites += [s["citation"] for s in top]
    return {"text": " ".join(parts), "citations": list(dict.fromkeys(cites))}
