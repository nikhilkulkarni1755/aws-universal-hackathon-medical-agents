import re

from handoff.masky import STYLE, VIDEO, spoken

POSITIVE = {"elation", "amusement", "enthusiasm", "determination", "pride", "contentment", "affection", "relief", "awe"}


def test_each_agent_has_a_different_positive_emotion():
    emotions = [s["emotion"] for s in STYLE.values()]
    assert set(STYLE) == {"Quinn", "Wren", "Mina", "Vera", "Iris"}
    assert len(set(emotions)) == len(emotions) and set(emotions) <= POSITIVE


def test_chart_shorthand_is_spoken_the_way_a_nurse_says_it():
    said = spoken("402: Temp 37.4 to 38.1 over 11 h; HR 82 to 104. Urine 180 to 70 mL [I/O 15:00–18:00]")
    assert said.startswith("Bed 402: temperature 37.4 to 38.1 over 11 hours")
    assert "heart rate 82 to 104" in said and "milliliters" in said and ";" not in said and "[" not in said
    assert "<|prosody:pause|>" in said
    assert "B N P 890 picograms per milliliter" in spoken("BNP 890 pg/mL")


def test_personality_beats_are_in_the_voice_but_stay_within_three_sentences():
    joke = spoken("403: Digoxin due 21:00 with potassium 3.3 mmol/L. Digoxin and low potassium. Not exactly a match made in chemistry.")
    assert "<|sfx:laughter|>Haha!" in joke
    assert "<|prosody:long_pause|>" in spoken("Rejected: CR-2 (dose or order verb in recommendation). Nice try. I would say that nicely, but it was not.")
    for text in ("One. Two. Three. Four. Five.", "word " * 200):
        out = spoken(text)
        assert len(re.split(r"(?<=[.!?])\s+", out.strip())) <= 3 and len(out) <= 480


def test_only_quinn_is_shown_as_video():
    assert VIDEO == {"Quinn"}
