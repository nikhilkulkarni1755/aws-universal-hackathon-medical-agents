# Clinical rules

These rules define what our agents may and may not write. Iris (the safety auditor agent) checks every SBAR and provider-form draft against them, and Prelint enforces them on every pull request.

Each rule has an ID that Iris cites when it rejects a draft, e.g. `Rejected: CR-2 (dose in recommendation)`.

> **Status:** drafted for the project lead's clinical review. Items marked **[NURSE REVIEW]** need a nurse's sign-off before the demo.

---

## Scope of practice

**CR-1. No diagnoses.** Agents describe patterns and ask for provider evaluation. They never state a diagnosis as fact.
- Fails: "402 has sepsis."
- Passes: "Pattern consistent with possible early sepsis; needs provider evaluation."

**CR-2. No treatment in recommendations.** The Recommendation section may not contain a dose, a fluid volume, a rate, or an instruction to start, stop, increase, decrease, or change a medication, fluid, lab or test.
- Fails: "Give 30 mL/kg NS bolus." / "Increase furosemide to 80 mg." / "Order a repeat lactate."
- Passes: "Notify provider now." / "Recheck vitals and mental status at 19:30." / "Verify the furosemide label with pharmacy before 21:00."

**CR-3. Doses are allowed as evidence.** Situation, Background and Assessment may quote a dose, volume or lab value as a cited fact.
- Passes: "Label 80 mg, MAR 40 mg [Label photo 18:45] [MAR Furosemide]."
- Fails: the same words placed in Recommendation as an instruction ("Give 40 mg, not 80 mg").

**CR-4. Escalations only.** Every Recommendation line is one of: notify provider, notify charge nurse, call rapid response per hospital criteria, recheck or reassess at a stated time, monitor a named parameter, verify with pharmacy, clarify with the outgoing nurse, or a nursing safety measure (bed alarm, fall precautions, NPO adherence). **[NURSE REVIEW: is this list complete and in scope for an RN?]**

**CR-5. Respect code status and allergies.** Any draft for a patient states code status and allergies in Situation. A recommendation must never conflict with them (e.g. no "call a code" for a DNR patient; no recommendation naming an allergen).
- Fails: SBAR for 404 with no code status.
- Passes: "Dorothy Evans, 81, bed 404, DNR, allergy: codeine."

## Evidence and citations

**CR-6. Every factual line is cited.** Each sentence in Situation, Background and Assessment that states a value, event or observation ends with at least one citation.
- Fails: "Her blood pressure is dropping."
- Passes: "SBP 128 to 104 over 11 h [Vitals 07:00–18:00]."

**CR-7. Citation format.** `[<Source> <time or item>]`, where Source is one of `Chart` (demographics, diagnosis, code status, allergies), `Vitals`, `Lab`, `I/O`, `Note`, `Verbal`, `Label photo`, `MAR`, `DailyMed`. Examples: `[Vitals 18:00]`, `[Lab Lactate 06:00]`, `[I/O 15:00–18:00]`, `[Note 17:30]`, `[Verbal 18:55 @0:09]`, `[Label photo 18:45]`, `[MAR Enoxaparin]`, `[DailyMed digoxin label]`.

**CR-8. Citations must resolve.** Every citation must point to a record that exists in the input data or a fetched source. A citation to a time or item that does not exist counts as uncited.

**CR-9. Conflicts are stated, not resolved.** When the verbal handoff and the chart disagree, the draft names both and cites both. It does not pick one as "true".
- Passes: "Verbal handoff: 'she's fine' [Verbal 18:55 @0:09]; chart shows temp 38.1, HR 104 [Vitals 18:00]."

**CR-10. Omissions are flagged.** A safety item present in the chart but missing from the verbal handoff is called out.
- Passes: "Enoxaparin 18:00 not documented and not mentioned at handoff [MAR Enoxaparin] [Verbal 18:55]."

## Language

**CR-11. Plain, nurse-to-nurse wording.** Short sentences. Standard abbreviations only (HR, RR, SBP, SpO2, I/O, PRN, NPO, MAR, IV, PO). No ambiguous abbreviations from the Joint Commission "Do Not Use" list (e.g. "U" for units, "QD", trailing zeros like "1.0 mg"). **[NURSE REVIEW]**

**CR-12. No false reassurance or alarm.** Do not write "stable", "fine" or "no concerns" for a patient with an open condition signal or safety item. Do not write "critical" or "emergency" unless rapid-response criteria are met.

**CR-13. Times are explicit.** Recommendations with a follow-up use a clock time ("recheck at 19:30"), not "later" or "soon".

## Privacy

**CR-14. Synthetic data only.** Only patients from `data/patients.json` (MRNs start with `SYN-`). Any other MRN, date of birth or full name pattern in code, tests or logs fails.

**CR-15. No PHI in logs or outbound messages.** Server logs record patient by bed number only. The n8n page and audit row contain bed number, tier, approving user and time; no name, MRN or date of birth. **[NURSE REVIEW: should the page to the charge nurse include the patient name? Real pages often do; for the demo we keep it out.]**

## Human approval

**CR-16. Nothing goes out before Approve.** No page, form, reminder or message leaves the system until the incoming nurse clicks Approve for that patient.

**CR-17. The nurse sees what gets sent.** The provider form that n8n sends must be byte-for-byte the version Iris passed and the nurse reviewed. Any change after approval requires a new approval.

**CR-18. Every approval is audited.** The audit row records: bed, tier, approver, timestamp, and the list of citations behind the escalation.

---

## Regex hints for Iris and Prelint

Starting points only. Apply the dose and verb patterns to the **Recommendation** section, not to Situation, Background or Assessment (CR-3).

```python
DOSE_UNIT   = r"\b\d+(\.\d+)?\s?(mg|mcg|g|mL|ml|L|units?|mEq|mL/kg|ml/kg|mg/kg|mL/hr|ml/h)\b"
ORDER_VERB  = r"\b(give|administer|start|stop|hold|discontinue|increase|decrease|titrate|bolus|push|hang|order|replace)\b"
DIAGNOSIS   = r"\b(has|have|is in|diagnosed with)\s+(sepsis|septic shock|pneumonia|PE|MI|stroke|AKI)\b"
FALSE_CALM  = r"\b(stable|fine|no concerns?)\b"          # flag when the patient has open signals (CR-12)
VAGUE_TIME  = r"\b(later|soon|in a while|when able)\b"   # flag in Recommendation (CR-13)
CITATION    = r"\[(Chart|Vitals|Lab|I/O|Note|Verbal|Label photo|MAR|DailyMed)[^\]]*\]"
NON_SYN_MRN = r"\bMRN[:\s]*(?!SYN-)\w+"
```

How to combine them in Recommendation: a line fails CR-2 if it matches `DOSE_UNIT` **or** `ORDER_VERB`. Every line in Situation, Background and Assessment that contains a digit must match `CITATION` (CR-6).

Wording notes:
- "Verify ... with pharmacy" contains no order verb and passes; "hold" is in `ORDER_VERB`, so "Hold the bag" fails. Use "verify" wording instead.
- "Monitor urine output hourly" passes because it has no unit or order verb.
