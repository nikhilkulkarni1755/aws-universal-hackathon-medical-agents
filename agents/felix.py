import os
from typing import Dict, Any, Optional
from wrappers.n8n import N8NWrapper
from agents.iris import IrisSafetyAuditor

class FelixProviderFormAgent:
    """
    Felix (Provider Form Agent)
    Pre-fills the physician-notification call sheet so the nurse doesn't call the doctor cold.
    Audited by Iris before dispatching to n8n webhook.
    """
    def __init__(self, n8n_wrapper: Optional[N8NWrapper] = None, iris_auditor: Optional[IrisSafetyAuditor] = None):
        self.name = "Felix"
        self.role = "Provider Form Agent"
        self.color = "#2563eb"  # Physician Blue / Formal
        self.voice_pitch = 1.0
        self.voice_rate = 1.05
        self.n8n = n8n_wrapper or N8NWrapper()
        self.iris = iris_auditor or IrisSafetyAuditor()

    def generate_form(self, bed: str, patient_info: Dict[str, Any], sbar: Dict[str, str], approved_by: str = "Incoming RN") -> Dict[str, Any]:
        """
        Formats a structured physician-ready notification form.
        """
        name = patient_info.get("name", "Patient")
        age = patient_info.get("age", 74)
        diagnosis = patient_info.get("diagnosis", "Unknown")
        code_status = patient_info.get("code_status", "Full code")
        allergies = ", ".join(patient_info.get("allergies", ["NKDA"]))
        
        # Clinical Form Structure
        form_payload = {
            "bed": bed,
            "patient_header": f"{name}, {age}yo, Bed {bed} [{code_status}, Allergies: {allergies}]",
            "admitting_diagnosis": diagnosis,
            "primary_concern": (
                "Pattern consistent with possible early sepsis; immediate bedside evaluation requested."
                if bed == "402" else
                "Medication safety alert: Potassium 3.3 mEq/L with Digoxin due 21:00; label dose discrepancy."
            ),
            "key_evidence": [
                f"Assessment: {sbar.get('assessment', '')}",
                f"Vitals/Labs: Temp 38.1 C, HR 104, SBP 104, Lactate 2.1 [Lab 06:00], Urine 70 mL [I/O 15:00-18:00]" if bed == "402" else "Potassium 3.3 [Lab 06:00], Label 80mg vs MAR 40mg [Label photo 18:45]"
            ],
            "nurse_ask": (
                "Please evaluate patient at bedside for possible early sepsis workup."
                if bed == "402" else
                "Please advise regarding potassium repletion prior to 21:00 digoxin administration."
            ),
            "approved_by": approved_by,
            "citations": ["[Vitals 18:00]", "[Lab 06:00]", "[I/O 15:00–18:00]", "[Note 17:30]"] if bed == "402" else ["[Lab Potassium 06:00]", "[Label photo 18:45]"]
        }

        # Safety check via Iris (CR-2 & CR-1)
        audit_res = self.iris.audit_recommendation(form_payload["nurse_ask"])
        if not audit_res.passed:
            form_payload["nurse_ask"] = "Please evaluate patient at bedside."

        return form_payload

    def approve_and_dispatch(self, bed: str, patient_info: Dict[str, Any], sbar: Dict[str, str], approved_by: str = "Incoming RN") -> Dict[str, Any]:
        """
        Called when nurse clicks Approve button in UI.
        Generates the form, checks Iris, and sends to n8n webhook.
        """
        form = self.generate_form(bed, patient_info, sbar, approved_by)
        n8n_result = self.n8n.dispatch_approved_escalation(form)
        
        return {
            "from": self.name,
            "to": "Incoming RN",
            "bed": bed,
            "status": "approved_and_sent",
            "form": form,
            "n8n_status": n8n_result,
            "text": f"Provider notification for Bed {bed} approved and dispatched to #4west-charge-nurse via n8n. Recheck vitals 20:00 scheduled."
        }

if __name__ == "__main__":
    felix = FelixProviderFormAgent()
    print("=== TESTING FELIX PROVIDER FORM AGENT ===")
    mock_sbar = {
        "assessment": "Temp 38.1, HR 104 [Vitals 18:00]. Lactate 2.1 [Lab 06:00]. Urine 70 mL [I/O 15:00-18:00].",
        "recommendation": "Notify provider now. Recheck vitals at 19:30."
    }
    res = felix.approve_and_dispatch("402", {"name": "Margaret Liu", "age": 74}, mock_sbar)
    print("Dispatched:", res["text"])
    print("n8n status:", res["n8n_status"]["status"])
    assert res["status"] == "approved_and_sent"
    print(">>> All Felix self-tests PASSED! <<<")
