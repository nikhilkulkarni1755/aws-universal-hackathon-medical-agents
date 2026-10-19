# SBAR Handoff Team

An agent-run shift-handoff service for nurses. Nine agents, each with a role, personality, avatar and voice, listen to the outgoing nurse, cross-check synthetic chart data, rank patients, draft SBAR reports and provider forms, and audit each other. The incoming nurse is the customer: nothing is sent until they click Approve.

Built at the AWS Universal Hackathon (Oct 19, 2026). **All data is synthetic** (`data/patients.json`). No real patient information is used anywhere.

## Run

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python server.py        # http://localhost:8000; integrations without a key or network use their cached copy
.venv/bin/python -m pytest -q
```

Optional environment variables: `N8N_WEBHOOK_URL` (production webhook URL; unset shows "page queued (demo)"), `EVENT_PACE_S` (delay between events, default 0.4).

## The team

| Agent | Role |
|---|---|
| Quinn | Supervisor: assigns work, answers the nurse's questions from cited evidence |
| Echo | Listener: the outgoing nurse's verbal handoff and day-shift notes |
| Theo | Trend analyst: vitals, labs, intake/output |
| Lens | Label check: IV bag photo against the MAR |
| Mina | Medication safety: interactions, undocumented doses, omissions |
| Vera | Risk validator: ranks patients using cross-source validation (patent pending) |
| Sam | SBAR writer |
| Felix | Provider-notification form |
| Iris | Safety auditor: rejects drafts that break `docs/clinical-rules.md` |

## Guardrails

- Agents escalate; they never diagnose or order treatment (CR-1, CR-2, CR-4). Iris rejects any draft that does.
- Every factual line is cited (CR-6, CR-7). Spoken lines and outbound messages use bed numbers, not names (CR-15).
- The provider form the nurse sees is the exact form that is sent; Approve is bound to a hash of the reviewed SBAR and form (CR-17). Each approval is written to an audit log (CR-18).
- A red-team draft (a treatment order) is shown on purpose in the demo and labelled as such.

## What is cached vs live today

Until the live integrations land (see `docs/BUILD.md`), these run from cached copies: cached transcript, cached label-check results, cached DailyMed excerpt, template SBARs from `docs/gold-sbar.md`. The ranking, trends, safety flags and Iris checks are computed from the data on every run.

## Development workflow

Code review and spec checks with Prelint (rules in `docs/clinical-rules.md`), security scanning with Snyk, sandboxed analysis with Tenki. Sponsor notes are in `docs/sponsors/`.
