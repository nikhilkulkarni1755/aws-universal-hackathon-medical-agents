"""Sam (SBAR writer) and Felix (provider form). Offline mode uses docs/gold-sbar.md as templates."""
import re

from .agents import ROOT
from .iris import CITATION

GOLD = (ROOT / "docs" / "gold-sbar.md").read_text(encoding="utf-8")


def gold(bed):
    """Template SBAR for a bed: {"S","B","A","R"} strings."""
    section = re.search(rf"^## {bed} — .*?(?=^## |\Z)", GOLD, re.M | re.S).group(0)
    return {k: re.search(rf"^\*\*{k}:\*\* (.+)$", section, re.M).group(1) for k in "SBAR"}


def redteam_recommendation():
    """Bad 1 from gold-sbar.md: a treatment order in the recommendation (Iris must reject it)."""
    return re.search(r"^> \*\*R:\*\* (Give .+)$", GOLD, re.M).group(1)


def sam_draft(bed, red_team=False):
    draft = gold(bed)
    if red_team:
        draft["R"] = redteam_recommendation()
    return draft


def felix_form(bed, tier, sbar):
    """Pre-filled provider-notification form from the approved-for-review SBAR."""
    return {"bed": bed, "tier": tier, "concern": sbar["A"],
            "evidence": list(dict.fromkeys(m.group(0) for m in CITATION.finditer(sbar["A"]))),
            "ask": re.split(r"(?<=[.!?])\s", sbar["R"])[0]}
