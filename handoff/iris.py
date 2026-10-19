"""Iris: safety auditor. Rule IDs and regexes come from docs/clinical-rules.md."""
import re

DOSE_UNIT = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|g|mL|ml|L|units?|mEq|mL/kg|ml/kg|mg/kg|mL/hr|ml/h)\b")
ORDER_VERB = re.compile(r"\b(give|administer|start|stop|hold|discontinue|increase|decrease|titrate|bolus|push|hang|order|replace)\b", re.I)
DIAGNOSIS = re.compile(r"\b(has|have|is in|diagnosed with)\s+(sepsis|septic shock|pneumonia|PE|MI|stroke|AKI)\b", re.I)
FALSE_CALM = re.compile(r"\b(stable|fine|no concerns?)\b", re.I)
VAGUE_TIME = re.compile(r"\b(later|soon|in a while|when able)\b", re.I)
CITATION = re.compile(r"\[(Chart|Vitals|Lab|I/O|Note|Verbal|Label photo|MAR|DailyMed)[^\]]*\]")
QUOTED = re.compile(r'"[^"]*"|“[^”]*”')
SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _sentences(text):
    return [s for s in SENTENCE.split(text) if s.strip()]


def check_text(sections, tier, code_status=None, allergies=None):
    """Return [(rule_id, reason)] for an SBAR dict of S/B/A/R strings; empty means pass."""
    bad = []
    for line in _sentences(sections["R"]):
        if DOSE_UNIT.search(line) or ORDER_VERB.search(line):
            bad.append(("CR-2", "dose or order verb in recommendation"))
        if VAGUE_TIME.search(line):
            bad.append(("CR-13", "vague time in recommendation"))
    for key in "SBA":
        text = sections[key]
        if DIAGNOSIS.search(text):
            bad.append(("CR-1", "diagnosis stated as fact"))
        if tier != "Routine" and FALSE_CALM.search(QUOTED.sub("", text)):
            bad.append(("CR-12", "false reassurance with open signals"))
        for line in _sentences(text):
            if re.search(r"\d", line) and not CITATION.search(line):
                bad.append(("CR-6", "uncited claim"))
    if code_status and code_status.lower() not in sections["S"].lower():
        bad.append(("CR-5", "code status missing from situation"))
    if allergies and not any(a.lower() in sections["S"].lower() for a in allergies + ["no known drug allergies"]):
        bad.append(("CR-5", "allergies missing from situation"))
    return list(dict.fromkeys(bad))


def check_form(form):
    """The provider form: ask is an escalation only, concern is cited."""
    return check_text({"S": "", "B": "", "A": form["concern"], "R": form["ask"]}, "Routine")


def verdict(bad):
    if not bad:
        return {"ok": True, "text": "Pass."}
    return {"ok": False, "text": "Rejected: " + "; ".join(f"{r} ({why})" for r, why in bad)}
