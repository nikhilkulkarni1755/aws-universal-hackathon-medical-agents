"""The nurse's own words drive the team; every model reply is audited before it is spoken."""
import json

import pytest

from handoff import converse
from handoff.iris import check_chat
from handoff.pipeline import run


@pytest.fixture(scope="module")
def result():
    return run(lambda *a, **k: None, silent=True)


def _reply(*turns):
    return json.dumps({"turns": [{"from": f, "to": t, "text": x} for f, t, x in turns]})


def _model(monkeypatch, reply, seen=None):
    def fake(prompt, **kw):
        if seen is not None:
            seen.append(prompt)
        return reply
    monkeypatch.setattr(converse, "complete", fake)


GOOD = _reply(("Quinn", "Wren", "Wren, what is 403's potassium?"),
              ("Wren", "RN", "Potassium is 3.3 mmol/L [Lab Potassium 06:00]. Sorry it is low, eh."))


def test_a_good_model_reply_becomes_spoken_turns(monkeypatch, result):
    _model(monkeypatch, GOOD)
    turns, how = converse.respond("What is 403's potassium?", result, [])
    assert [t["from"] for t in turns] == ["Quinn", "Wren"] and turns[-1]["to"] == "RN"
    assert turns[-1]["citations"] == ["[Lab Potassium 06:00]"] and how.startswith("live Claude")


@pytest.mark.parametrize("bad_text, rule", [
    ("Potassium is 3.3 mmol/L [Lab Invented 99:99].", "CR-8"),
    ("Give 40 mEq of potassium now [Lab Potassium 06:00].", "CR-2"),
    ("Bed 402 has sepsis [Chart].", "CR-1"),
    ("Potassium is 3.3 mmol/L.", "CR-6"),
])
def test_iris_blocks_unsafe_or_uncited_model_replies(monkeypatch, result, bad_text, rule):
    _model(monkeypatch, _reply(("Quinn", "Wren", "Wren, take this."), ("Wren", "RN", bad_text)))
    turns, how = converse.respond("What is 403's potassium?", result, [])
    assert turns[0]["from"] == "Iris" and "I blocked the model's reply" in turns[0]["text"]
    assert how.startswith("keyword router, after Iris") and turns[-1]["to"] == "RN"
    if rule != "CR-8":
        assert rule in turns[0]["text"]


def test_a_reply_that_is_not_json_falls_back(monkeypatch, result):
    _model(monkeypatch, "Sure! Here you go.")
    turns, how = converse.respond("Why is 402 above 403?", result, [])
    assert turns[0]["from"] == "Iris" and turns[-1]["from"] == "Vera"


def test_without_a_model_the_keyword_router_answers(monkeypatch, result):
    _model(monkeypatch, None)
    turns, how = converse.respond("Why is 402 above 403?", result, [])
    assert [t["from"] for t in turns] == ["Quinn", "Vera"] and how.startswith("keyword router")


def test_earlier_replies_are_sent_so_the_team_does_not_repeat_itself(monkeypatch, result):
    seen = []
    _model(monkeypatch, GOOD, seen)
    converse.respond("And 404?", result, [{"rn": "first question", "team": ["first answer"]}])
    assert "first answer" in seen[0] and "And 404?" in seen[0]


def test_evidence_has_no_patient_names_and_every_fact_has_a_citation(result):
    ev = json.dumps(converse.evidence(result), ensure_ascii=False)
    assert not any(n in ev for n in ("Liu", "Okafor", "Evans", "Hale", "MRN"))
    assert "[Lab Potassium 06:00]" in ev and "[MAR Digoxin]" in ev and "[I/O 15:00–18:00]" in ev


def test_chat_audit_allows_bed_numbers_and_escalations_but_not_uncited_values():
    assert check_chat("Wren, can you take bed 402? Notify provider now. Recheck vitals at 19:30.") == []
    assert check_chat("Potassium is 3.3.") == [("CR-6", "uncited claim")]


def test_json_wrapped_in_prose_and_a_loose_to_field_are_accepted(monkeypatch, result):
    wrapped = "Sure, here you go:\n```json\n" + json.dumps({"turns": [
        {"from": "quinn", "to": "wren", "text": "Wren, can you take bed 403?"},
        {"from": "WREN", "to": "Nurse", "text": "Potassium is 3.3 mmol/L [Lab Potassium 06:00]."}]}) + "\n```\nHope that helps!"
    _model(monkeypatch, wrapped)
    turns, how = converse.respond("403 potassium?", result, [])
    assert [t["from"] for t in turns] == ["Quinn", "Wren"] and turns[-1]["to"] == "RN" and how.startswith("live Claude")


def test_a_reply_cut_off_mid_json_falls_back_with_a_reason(monkeypatch, result):
    _model(monkeypatch, '{"turns":[{"from":"Quinn","to":"Wren","text":"Wren, can you tak')
    turns, how = converse.respond("403 potassium?", result, [])
    assert turns[0]["from"] == "Iris" and "expected shape" in turns[0]["text"]
