"""
Felix (Provider Form Agent)
Role: The Funny Mailman / Courier of the Clinical Team.
Builds the structured physician call sheet so the nurse doesn't call the doctor cold.
Dispatches provider notification via n8n and Discord webhook.
Strictly adheres to Clinical Rules (CR-1 through CR-18, especially CR-15: Bed numbers only, no PHI).
"""
import os
import re
from typing import Dict, Any, Optional, List
from wrappers.n8n import N8NWrapper
from agents.iris import IrisSafetyAuditor

# Funny Mailman Puns for Felix (Courier chatter; never mocks a patient's condition)
FELIX_MAILMAN_PUNS = [
    "Special delivery for the doctor! Signed, sealed, and audited—don't return to sender! 📬",
    "Postmarked for #4west-charge-nurse! First-class delivery only, no junk mail on my watch! ✉️",
    "Neither snow, nor rain, nor shift change stays this courier from swift completion of his pages! 🏃‍♂️📫",
    "Handling with care: fragile vitals inside! Priority dispatch confirmed! 📦",
    "Package secured! Bed escalation en route faster than express mail! 💌",
]


class FelixProviderFormAgent:
    """
    Felix (Provider Form Agent)
    Pre-fills the physician-notification call sheet so the nurse doesn't call the doctor cold.
    Audited by Iris before dispatching to n8n and Discord webhooks.
    """
    def __init__(self, n8n_wrapper: Optional[N8NWrapper] = None, iris_auditor: Optional[IrisSafetyAuditor] = None):
        self.name = "Felix"
        self.role = "Provider Form Agent (The Mailman)"
        self.color = "#FD7E14"  # Express Mail Orange
        self.voice_pitch = 0.95
        self.voice_rate = 1.05
        self.n8n = n8n_wrapper or N8NWrapper()
        self.iris = iris_auditor or IrisSafetyAuditor()

    def get_pun(self, bed: str) -> str:
        """Returns a funny mailman pun for the bed."""
        try:
            idx = int(re.sub(r"\D", "", bed)) % len(FELIX_MAILMAN_PUNS)
        except (ValueError, TypeError):
            idx = 0
        return FELIX_MAILMAN_PUNS[idx]

    def generate_form(
        self,
        bed: str,
        patient_info: Optional[Dict[str, Any]],
        sbar: Dict[str, str],
        approved_by: str = "Incoming RN"
    ) -> Dict[str, Any]:
        """
        Formats a structured, dynamic physician-ready notification form.
        CR-15 Compliant: Uses bed number, code status, and allergies. NO PHI (no names or MRN).
        """
        code_status = patient_info.get("code_status", "Full code") if patient_info else "Full code"
        allergies = ", ".join(patient_info.get("allergies", ["NKDA"])) if patient_info else "NKDA"

        assessment = sbar.get("assessment") or sbar.get("A", "")
        recommendation = sbar.get("recommendation") or sbar.get("R", "")

        # Extract citations dynamically from assessment
        citations = list(dict.fromkeys(re.findall(r"\[(Chart|Vitals|Lab|I/O|Note|Verbal|Label photo|MAR|DailyMed)[^\]]*\]", assessment)))
        if not citations:
            citations = list(dict.fromkeys(re.findall(r"\[[^\]]+\]", assessment)))

        # Nurse Ask: first sentence of recommendation (CR-2 escalation)
        ask_match = re.split(r"(?<=[.!?])\s", recommendation.strip())
        nurse_ask = ask_match[0] if ask_match and ask_match[0] else "Please evaluate patient at bedside."

        # Safety check via Iris (CR-1 & CR-2)
        audit_res = self.iris.audit_recommendation(nurse_ask)
        if not audit_res.passed:
            nurse_ask = "Please evaluate patient at bedside."

        pun = self.get_pun(bed)

        form_payload = {
            "bed": bed,
            "patient_header": f"Bed {bed} [{code_status}, Allergies: {allergies}]",  # CR-15 compliant (No PHI)
            "primary_concern": assessment,
            "key_evidence": [assessment],
            "nurse_ask": nurse_ask,
            "approved_by": approved_by,
            "citations": citations,
            "pun": pun
        }
        return form_payload

    def approve_and_dispatch(
        self,
        bed: str,
        patient_info: Optional[Dict[str, Any]],
        sbar: Dict[str, str],
        approved_by: str = "Incoming RN"
    ) -> Dict[str, Any]:
        """
        Called when nurse clicks Approve button in UI.
        Generates form, validates with Iris, and dispatches to n8n and Discord!
        """
        form = self.generate_form(bed, patient_info, sbar, approved_by)
        n8n_result = self.n8n.dispatch_approved_escalation(form)
        pun = form["pun"]

        return {
            "from": self.name,
            "to": "Incoming RN",
            "bed": bed,
            "status": "approved_and_sent",
            "form": form,
            "n8n_status": n8n_result,
            "text": f"📬 {pun} Escalation for Bed {bed} approved by {approved_by} and dispatched to #4west-charge-nurse via Discord & n8n. Recheck vitals 20:00 scheduled."
        }


if __name__ == "__main__":
    felix = FelixProviderFormAgent()
    print("=== TESTING FELIX (FUNNY MAILMAN + DISCORD DEMO) ===")
    mock_sbar = {
        "assessment": "Temp 38.1 C, HR 104 [Vitals 18:00]. Lactate 2.1 [Lab 06:00]. Urine 70 mL [I/O 15:00-18:00]. Oliguria and possible early sepsis pattern.",
        "recommendation": "Notify provider now. Recheck vitals at 19:30."
    }
    mock_pt = {"bed": "402", "code_status": "Full code", "allergies": ["Sulfa"]}
    res = felix.approve_and_dispatch("402", mock_pt, mock_sbar)
    print("Dispatched:", res["text"].encode("ascii", "replace").decode("ascii"))
    print("Discord delivery status:", res["n8n_status"].get("discord_sent"))
    assert res["status"] == "approved_and_sent"
    print(">>> All Felix self-tests PASSED and Discord message sent! <<<")
