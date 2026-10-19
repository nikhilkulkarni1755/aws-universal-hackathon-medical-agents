"""Each agent's personality in words. Chatter only: SBARs, provider forms and rule codes stay clinical,
and jokes aim at the team, the paperwork and the process, never at a patient's condition."""

QUIPS = {
    "Quinn": {  # dry head nurse who has seen every handoff
        "open": "Try to look busy.",
        "close": "Coffee's on you.",
        "route": "Don't all jump at once.",
        "to_Wren": "Chop chop.",
        "to_Echo": "Ears open.",
        "to_Theo": "Keep the numbers honest.",
        "to_Lens": "Eyes sharp.",
        "to_Mina": "Nothing slips past you.",
        "to_Vera": "Make it count.",
        "to_Sam": "Short and cited.",
        "to_Felix": "Keep it formal. Doctors like that.",
    },
    "Wren": {  # cheerful, apologetic Canadian clerk
        "census": "Sorry to be the bearer of paperwork, eh.",
        "answer": "Sorry, that's all I've got, eh.",
    },
    "Echo": {"verbal": "Fine, fine, fine. Let that one echo."},
    "Theo": {"trend": "Numbers don't lie. They mumble sometimes, but they don't lie."},
    "Lens": {"mismatch": "I don't do opinions. I just do eyesight."},
    "Mina": {
        "digoxin": "Digoxin and low potassium. Not exactly a match made in chemistry.",
        "enoxaparin": "An undocumented dose is a mystery I'd rather not solve at seven PM.",
    },
    "Vera": {"rank": "No offense to the other beds, but it is not close."},
    "Sam": {"ready": "Short, sweet and cited, like my coffee: strong."},
    "Felix": {"forms": "Duly drafted and duly formal."},
    "Iris": {  # deadpan auditor
        "reject": "Nice try. I would say that nicely, but it was not.",
        "pass": "Try not to let it go to your head.",
        "all": "Everyone behaved. I am as surprised as you.",
    },
}


def quip(agent, moment):
    return QUIPS.get(agent, {}).get(moment, "")
