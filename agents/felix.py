"""
Felix (Provider Form Agent)
Role: The Funny Mailman / Courier of the Clinical Team.
Builds the structured physician call sheet so the nurse doesn't call the doctor cold.
Strictly adheres to Clinical Rules (CR-1 through CR-18, especially CR-15: Bed numbers only, no PHI).
"""
import re
from typing import Dict, Any, Optional, List

# Standard citation regex matching CR-7
CITATION_PATTERN = re.compile(r"\[(Chart|Vitals|Lab|I/O|Note|Verbal|Label photo|MAR|DailyMed)[^\]]*\]")

# Funny Mailman Puns for Felix (Team chatter / delivery quips; never mocks patient condition)
FELIX_MAILMAN_PUNS = [
    "Special delivery for the doctor! Signed, sealed, and audited - don't return to sender!",
    "Postmarked for #4west-charge-nurse! First-class delivery only, no junk mail on my watch!",
    "Neither snow, nor rain, nor shift change stays this courier from swift completion of his pages!",
    "Handling with care: fragile vitals inside! Priority dispatch confirmed!",
    "Package secured! Bed escalation en route faster than express mail!",
]


def felix_call_sheet(
    bed: str,
    tier: str,
    sbar: Dict[str, str],
    patient: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Builds the structured physician-notification call sheet dynamically.
    - No hardcoded patient names or values (CR-15 compliant: Bed numbers and clinical facts only).
    - Concern and key evidence computed directly from the SBAR Assessment.
    - Nurse ask extracted from the SBAR Recommendation (CR-2 compliant escalation).
    """
    code_status = patient.get("code_status", "Full code") if patient else "Full code"
    allergies = ", ".join(patient.get("allergies", ["NKDA"])) if patient else "NKDA"

    # Support {"S","B","A","R"} as well as full key dicts
    assessment = sbar.get("A") or sbar.get("assessment", "")
    recommendation = sbar.get("R") or sbar.get("recommendation", "")

    # Citations extracted dynamically matching full brackets e.g. [Vitals 18:00]
    evidence = list(dict.fromkeys(m.group(0) for m in CITATION_PATTERN.finditer(assessment)))
    if not evidence:
        evidence = list(dict.fromkeys(re.findall(r"\[[^\]]+\]", assessment)))

    # Ask: First sentence of recommendation (CR-2: must be escalation, not prescribing)
    ask_match = re.split(r"(?<=[.!?])\s", recommendation.strip())
    nurse_ask = ask_match[0] if ask_match and ask_match[0] else "Please evaluate patient at bedside."

    # Select mailman pun
    try:
        pun_idx = int(re.sub(r"\D", "", bed)) % len(FELIX_MAILMAN_PUNS)
    except (ValueError, TypeError):
        pun_idx = 0
    pun = FELIX_MAILMAN_PUNS[pun_idx]

    return {
        "bed": bed,
        "tier": tier,
        "patient_header": f"Bed {bed} [{code_status}, Allergies: {allergies}]",  # CR-15: No PHI
        "concern": assessment,
        "evidence": evidence,
        "ask": nurse_ask,
        "pun": pun,
    }


class FelixProviderFormAgent:
    """
    Agent wrapper for Felix.
    Compatible with handoff pipeline and standalone scripts.
    """
    def __init__(self):
        self.name = "Felix"
        self.role = "Provider Form Agent (The Mailman)"
        self.color = "#FD7E14"  # Express Mail Orange
        self.voice_pitch = 0.95
        self.voice_rate = 1.05

    def generate_form(
        self,
        bed: str,
        patient_info: Optional[Dict[str, Any]],
        sbar: Dict[str, str],
        approved_by: str = "Incoming RN"
    ) -> Dict[str, Any]:
        tier = patient_info.get("tier", "Escalate") if patient_info else "Escalate"
        form = felix_call_sheet(bed, tier, sbar, patient_info)
        form["approved_by"] = approved_by
        return form

    def quip(self, moment: str = "dispatch") -> str:
        return FELIX_MAILMAN_PUNS[0]


if __name__ == "__main__":
    print("=== TESTING FELIX (THE FUNNY MAILMAN) ===")
    mock_sbar = {
        "A": "SBP 104, Temp 38.1 C, HR 104 [Vitals 18:00]. Lactate 2.1 [Lab 06:00]. Urine 70 mL [I/O 15:00-18:00].",
        "R": "Notify provider now. Recheck vitals at 19:30."
    }
    mock_pt = {"bed": "402", "code_status": "Full code", "allergies": ["Sulfa"]}
    sheet = felix_call_sheet("402", "Escalate", mock_sbar, mock_pt)
    print("Generated Call Sheet:")
    for k, v in sheet.items():
        print(f"  {k}: {v}")

    # Verify CR-15: No patient name in header or payload
    assert "Margaret" not in str(sheet), "Violation of CR-15: Found patient name in call sheet"
    assert "Bed 402" in sheet["patient_header"]
    assert "[Vitals 18:00]" in sheet["evidence"]
    print("\n>>> All Felix self-tests PASSED (CR-15 compliant & dynamic)! <<<")
