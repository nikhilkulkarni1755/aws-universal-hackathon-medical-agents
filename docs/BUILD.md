# Build board (Oct 19, code freeze 4:30 PM, submit 5:30 PM)

## Test and demo each agent on its own

```bash
.venv/bin/python -m handoff.demo list        # agents: quinn echo theo lens mina vera sam felix iris | all
.venv/bin/python -m handoff.demo theo        # one agent's events in the terminal (upstream steps run silently)
.venv/bin/python -m pytest -q                # tests/test_agents.py has one row per agent; test_server.py covers the API
.venv/bin/python server.py                   # huddle page; pick "Demo: <agent>" in the header to run one agent alone
```

An agent is **demoable** when: (1) `python -m handoff.demo <agent>` prints its events with citations, (2) its row in `tests/test_agents.py` passes, (3) the "Demo: <agent>" option runs it in the huddle page. To change an agent, edit its step in `handoff/pipeline.py` (or its logic in `handoff/agents.py`, `iris.py`, `writers.py`), then update its row in `tests/test_agents.py`.

## External wrapper convention (for Masky, Tenki, Claude, DailyMed, n8n)

One function per service with a cached path that needs no network. The demo must still run with Wi-Fi off. Add a test that runs the cached path. Never log patient names; spoken lines and outbound payloads use bed numbers only.

## Components

| # | Component | Status | Files | Done when |
|---|---|---|---|---|
| 1 | Agent steps (9 agents, cached) | done, tested | `handoff/pipeline.py`, `agents.py` | `pytest` green; ranking 402, 403, 404, 401 |
| 2 | Iris rules (CR-1, 2, 5, 6, 12, 13) | done, tested | `handoff/iris.py` | red-team drafts rejected, gold SBARs pass |
| 3 | Sam / Felix templates | done | `handoff/writers.py` | gold SBAR + form per bed |
| 4 | API: run, stream, state, ask, approve + audit | done, tested | `server.py` | `tests/test_server.py` green |
| 5 | Huddle page (tiles, captions, board, cards, Ask, Approve) | built, **not yet browser-tested** | `static/index.html` | every "Demo:" option runs; no console errors |
| 6 | Masky avatars + voices: 5 of 9 created | **blocked on avatar limit (5)** | `scripts/masky_setup.py` | 9 avatars; per-agent conversation; pre-rendered lines |
| 7 | Masky audio into the huddle (`audio_url` on events, cache warm-up script) | not started | new `handoff/masky.py` | agent lines play in their Masky voice offline from cache |
| 8 | Avatar images in tiles (replace initials), idle loops | not started | `static/index.html` | tiles show Masky portraits |
| 9 | Theo on Tenki sandbox (outbound off) + local fallback | not started | new `handoff/sandbox.py` | "sandbox" badge on Theo's chart; fallback works |
| 10 | Claude-written SBAR (live) with template fallback | not started | `handoff/writers.py` | Iris still passes; refusal falls back |
| 11 | DailyMed live fetch with cached fallback | not started | `handoff/agents.py` | Mina's attachment shows fetched text |
| 12 | n8n workflow (webhook to Slack/Discord + audit row) | not started | n8n cloud + `N8N_WEBHOOK_URL` | page appears in channel on Approve |
| 13 | Echo live: record handoff audio + faster-whisper (P1) | not started | `assets/verbal/` | transcript matches cached claims |
| 14 | Lens live vision (P1) + blurry-label fixture | not started | `handoff/agents.py` | 3 labels classified |
| 15 | Browser smoke test of the huddle page | not started | `tests/` | headless page loads, Start runs, Approve works |
| 16 | Snyk scan + fixes + screenshot | not started | repo | clean report |
| 17 | Prelint GitHub App + one PR showing a flagged dose | not started | GitHub | screenshot |
| 18 | Deck (`/deck.html` or Canva), backup video, README polish | README done | | URL ready |
| 19 | Submissions: crewbase, Masky form, Twitch chat deck URL | not started | | all three before 5:30 |

## Suggested split between two people

- **Backend/integrations:** 6, 7, 9, 10, 11, 13, 14. Each has a cached path and a test.
- **Frontend/dev workflow/admin:** 5, 8, 12, 15, 16, 17, 18, 19. Start with 5 (open the page, click every demo option, fix what breaks).
- Touch different files where possible: backend owner edits `handoff/*`, frontend owner edits `static/index.html` and `tests/`. `docs/BUILD.md` status column is updated by whoever finishes a row.
