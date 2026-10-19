"""One test per agent, run in isolation. Add a row here when you build or change an agent."""
import pytest

from handoff.pipeline import run

# agent -> (senders allowed in the demo, phrases that must appear)
CASES = {
    "quinn": ({"Quinn"}, ["Loading 4 West", "Ready for RN review"]),
    "echo": ({"Echo"}, ["She's fine","[Verbal 18:55 @0:09]", "[Note 17:30]"]),
    "theo": ({"Theo"}, ["HR 82 to 104", "Urine 180 to 70 mL", "Potassium 3.3"]),
    "lens": ({"Lens"}, ["80 mg does not match", "[Label photo 18:45]"]),
    "mina": ({"Mina"}, ["Digoxin due 21:00", "Enoxaparin due 18:00 not documented", "[DailyMed digoxin label]"]),
    "vera": ({"Vera", "Theo"}, ["180 mL, 120 mL, 70 mL", "402 Escalate, 403 Act this shift, 404 Act this shift, 401 Routine"]),
    "iris": ({"Sam", "Iris"}, ["red-team draft", "Rejected: CR-2", "Pass."]),
    "sam": ({"Sam", "Iris"}, ["Rewritten 402 as an escalation"]),
    "felix": ({"Felix", "Iris"}, ["Provider forms are drafted", "All drafts and forms: pass."]),
}


@pytest.mark.parametrize("agent", CASES)
def test_agent_demo(agent):
    senders, phrases = CASES[agent]
    events = []
    run(lambda *a: events.append(a), agent)
    assert events, f"{agent} emitted nothing"
    assert {e[0] for e in events} <= senders
    text = " ".join(e[2] + " " + " ".join(e[3] if len(e) > 3 else []) for e in events)
    for phrase in phrases:
        assert phrase in text, phrase
