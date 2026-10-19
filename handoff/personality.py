"""Each agent's personality in words. Chatter only: SBARs, provider forms and rule codes stay clinical,
and jokes aim at the team, the paperwork and the process, never at a patient's condition."""

QUIPS = {
    "Quinn": {  # dry head nurse who has seen every handoff; also the one who calls the doctor
        "open": "Try to look busy.",
        "close": "Coffee's on you.",
        "route": "Don't all jump at once.",
        "forms": "Forms are drafted and formal. Doctors like that.",
        "to_Wren": "Chop chop.",
        "to_Mina": "Nothing slips past you.",
        "to_Vera": "Make it count.",
    },
    "Wren": {  # cheerful, apologetic Canadian clerk who reads every source
        "census": "Sorry to be the bearer of paperwork, eh.",
        "answer": "Sorry, that's all I've got, eh.",
        "verbal": "Fine, fine, fine. Let that one echo, eh.",
        "trend": "Numbers don't lie, eh. They mumble sometimes, but they don't lie.",
    },
    "Mina": {  # precise pharmacist with a pun habit
        "digoxin": "Digoxin and low potassium. Not exactly a match made in chemistry.",
        "enoxaparin": "An undocumented dose is a mystery I'd rather not solve at seven PM.",
        "mismatch": "I only read the label. The label has some explaining to do.",
    },
    "Vera": {"rank": "No offense to the other beds, but it is not close.", "ready": "Short, cited, done. Iris, they are yours."},
    "Iris": {  # deadpan auditor
        "reject": "Nice try. I would say that nicely, but it was not.",
        "cleared": "Try not to let it go to your head.",
        "all": "Everyone behaved. I am as surprised as you.",
    },
}


def quip(agent, moment):
    return QUIPS.get(agent, {}).get(moment, "")
