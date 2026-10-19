"""Demo one agent or the whole team in the terminal: python -m handoff.demo list | all | <agent>"""
import sys

from .pipeline import AGENTS, run


def show(sender, to, text, citations=(), attachment=None):
    print(f"{sender:>6} -> {to:<5} {text}")
    if citations:
        print(" " * 15 + " ".join(citations))
    if attachment:
        print(" " * 15 + f"[attachment: {attachment['type']} {attachment.get('badge', '')}]")


def main(argv):
    arg = argv[1] if len(argv) > 1 else "list"
    if arg not in AGENTS + ["all"]:
        print("usage: python -m handoff.demo", " | ".join(AGENTS + ["all"]))
        return
    run(show, None if arg == "all" else arg)


if __name__ == "__main__":
    main(sys.argv)
