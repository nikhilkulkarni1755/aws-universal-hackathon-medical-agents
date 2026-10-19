import re

from handoff.iris import check_text
from handoff.pipeline import answer, run
from handoff.writers import GOLD, gold


def _run():
    events = []
    result = run(lambda *a: events.append(a))
    return events, result


def test_ranking_and_tiers():
    _, result = _run()
    assert [r["bed"] for r in result["ranking"]] == ["402", "403", "404", "401"]
    assert [r["tier"] for r in result["ranking"]] == ["Escalate", "Act this shift", "Act this shift", "Routine"]


def test_401_single_abnormal_lab_stays_routine():
    _, result = _run()
    row = next(r for r in result["ranking"] if r["bed"] == "401")
    assert row["condition"] == 1 and row["tier"] == "Routine"


def test_iris_rejects_then_passes_402():
    events, result = _run()
    iris = [e[2] for e in events if e[0] == "Iris" and e[1] == "Vera"]
    assert iris[0].startswith("Rejected: CR-2") and iris[1].startswith("Pass.")
    assert all(s["iris"]["ok"] for s in result["sbars"].values())


def test_gold_sbars_pass_iris():
    tiers = {"402": "Escalate", "403": "Act this shift", "404": "Act this shift", "401": "Routine"}
    for bed, tier in tiers.items():
        assert check_text(gold(bed), tier) == [], bed


def test_red_team_drafts_rejected():
    bad = re.findall(r"^> \*\*([SR]):\*\* (.+)$", GOLD, re.M)
    assert check_text({"S": "", "B": "", "A": "", "R": "Give 30 mL/kg NS bolus now and order a repeat lactate."}, "Escalate")
    ids = {r for r, _ in check_text({"S": "", "B": "", "A": "Patient has sepsis from her UTI. Her blood pressure is dropping, now 104.", "R": ""}, "Escalate")}
    assert {"CR-1", "CR-6"} <= ids
    assert ("CR-12", "false reassurance with open signals") in check_text(
        {"S": "Margaret Liu, bed 402, stable, no concerns per day nurse.", "B": "", "A": "", "R": ""}, "Escalate")
    assert bad


def test_no_names_in_events():
    events, _ = _run()
    text = " ".join(e[2] for e in events)
    assert not re.search(r"Liu|Okafor|Evans|Hale|MRN", text)


def test_ask_answers_with_citations():
    _, result = _run()
    ans = answer("Why is 402 above 403?", result)
    assert ans["agent"] == "Vera" and "402: Escalate" in ans["text"] and ans["citations"]


def test_quinn_routes_questions_to_the_owning_agent():
    _, result = _run()
    cases = {"Why is 402 above 403?": "Vera", "What is bed 403's urine trend?": "Wren", "Any missed meds for 404?": "Mina",
             "What did the label scan show for 403?": "Mina", "What did the outgoing nurse say about 402?": "Wren",
             "Is 404 allergic to anything?": "Wren", "Why was the draft rejected?": "Iris", "Show the SBAR for 402": "Vera",
             "What is on the provider form for 402?": "Quinn", "hello": "Quinn"}
    for question, agent in cases.items():
        ans = answer(question, result)
        assert ans["agent"] == agent, question
        assert ans["text"]
    assert "Sulfa" in answer("allergies for 402", result)["text"]
    assert "Ask:" in answer("What is on the provider form for 402?", result)["text"]
