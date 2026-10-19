"""Mina's safety checks and Vera's placeholder ranking rule, including the pitch claim that changing the data changes the ranking."""
import copy

from handoff.agents import echo_claims, lens, lens_signal, load_patients, mina, sig, vera
from handoff.sandbox import run_local


def _patient(bed):
    return copy.deepcopy(next(p for p in load_patients() if p["bed"] == bed))


def _rank(patients):
    """Condition signals from Theo's program, safety signals from Mina and Lens, then Vera's rule."""
    claims, signals = echo_claims(), []
    for p, run in zip(patients, run_local(patients)):
        signals += [sig(p, s["source"], s["text"], s["citation"], agent="Theo") for s in run["signals"]]
        signals += mina(p, claims) + lens_signal(p, lens(p))
    return {r["bed"]: r for r in vera(signals, [p["bed"] for p in patients])}


def _signals(n_sources, n_signals, kind="condition", severity="low", bed="999"):
    sources = ["Vitals", "Lab", "I/O", "Note"][:n_sources]
    return [{"bed": bed, "source": sources[i % n_sources], "kind": kind, "severity": severity, "text": "x", "citation": "[Chart]", "agent": "t"}
            for i in range(n_signals)]


# ---- Mina
def test_mina_flags_digoxin_with_low_potassium_and_cites_the_label():
    found = mina(_patient("403"), echo_claims())
    assert len(found) == 1 and found[0]["severity"] == "high" and found[0]["kind"] == "safety"
    assert "[Lab Potassium 06:00]" in found[0]["citation"] and "[MAR Digoxin]" in found[0]["citation"]


def test_mina_stays_quiet_when_potassium_is_normal():
    p = _patient("403")
    p["labs"][0]["value"] = 4.2
    assert mina(p, echo_claims()) == []


def test_mina_flags_an_undocumented_dose_and_notes_whether_it_was_mentioned():
    p = _patient("404")
    assert "not mentioned at handoff" in mina(p, echo_claims())[0]["text"]
    said = echo_claims() + [{"bed": "404", "type": "med", "claim": "Enoxaparin given at six", "citation": "[Verbal 18:55]"}]
    assert "not mentioned" not in mina(p, said)[0]["text"]


def test_mina_has_nothing_to_say_about_a_clean_chart():
    assert mina(_patient("401"), echo_claims()) == []


def test_label_mismatch_is_a_high_severity_safety_signal_and_a_match_is_not():
    mismatch, match = _patient("403"), _patient("402")
    assert lens_signal(mismatch, lens(mismatch))[0]["severity"] == "high"
    assert lens_signal(match, lens(match)) == []


# ---- Vera
def test_baseline_ranking():
    rows = _rank(load_patients())
    assert {b: r["tier"] for b, r in rows.items()} == {"402": "Escalate", "403": "Act this shift", "404": "Act this shift", "401": "Routine"}


def test_escalation_needs_four_signals_from_three_sources():
    assert vera(_signals(3, 4))[0]["tier"] == "Escalate"
    assert vera(_signals(3, 3))[0]["tier"] == "Routine"   # too few signals
    assert vera(_signals(2, 6))[0]["tier"] == "Routine"   # too few sources


def test_safety_items_put_a_patient_in_act_this_shift_and_never_escalate_alone():
    assert vera(_signals(1, 5, kind="safety", severity="high"))[0]["tier"] == "Act this shift"


def test_within_a_tier_more_high_severity_safety_items_rank_first():
    rows = vera(_signals(1, 1, kind="safety", severity="high", bed="A") + _signals(1, 3, kind="safety", severity="high", bed="B"))
    assert [r["bed"] for r in rows] == ["B", "A"]


def test_changing_the_data_changes_the_ranking():
    patients = load_patients()
    calm_402 = next(p for p in patients if p["bed"] == "402")
    for v in calm_402["vitals"]:
        v.update(temp_c=36.8, hr=78, rr=16, sbp=130, spo2=97)
    calm_402["labs"] = [dict(l, value=l["ref_low"]) for l in calm_402["labs"]]
    calm_402["intake_output"] = [dict(b, urine_ml=200) for b in calm_402["intake_output"]]
    assert _rank(patients)["402"]["tier"] == "Routine"

    patients = load_patients()
    sick_401 = next(p for p in patients if p["bed"] == "401")
    sick_401["vitals"][-1].update(temp_c=38.6, hr=112, rr=24, sbp=98)
    sick_401["labs"][1]["value"] = 15.0   # WBC
    sick_401["intake_output"][-1]["urine_ml"] = 60
    assert _rank(patients)["401"]["tier"] == "Escalate"


def test_a_single_abnormal_lab_never_escalates():
    p = _patient("401")  # post-op hemoglobin is the false-positive case
    assert _rank([p])["401"]["tier"] == "Routine"


def test_a_patient_with_no_findings_is_still_ranked_as_routine():
    rows = vera(_signals(3, 4, bed="A"), ["A", "B"])
    assert {r["bed"]: r["tier"] for r in rows} == {"A": "Escalate", "B": "Routine"}
