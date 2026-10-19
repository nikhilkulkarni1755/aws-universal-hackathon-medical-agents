# Build board (Oct 19, code freeze 4:30 PM, submit 5:30 PM)

**Roster is five agents (Quinn, Wren, Mina, Vera, Iris).** Felix's form work lives in Quinn, Echo and Theo in Wren, Lens in Mina, Sam in Vera. Step functions in `handoff/pipeline.py` keep their old names (`echo_step`, `theo_step`, `lens_step`, `sam_step`, `felix_step`); `agents.py` signals keep the old skill tags.

## Test and demo each agent on its own

```bash
.venv/bin/python -m handoff.demo list        # agents: iris mina quinn vera wren | all
.venv/bin/python -m handoff.demo theo        # one agent's events in the terminal (upstream steps run silently)
.venv/bin/python -m pytest -q                # tests/test_agents.py has one row per agent; test_server.py covers the API
.venv/bin/python server.py                   # huddle page; pick "Demo: <agent>" in the header to run one agent alone
```

An agent is **demoable** when: (1) `python -m handoff.demo <agent>` prints its events with citations, (2) its row in `tests/test_agents.py` passes, (3) the "Demo: <agent>" option runs it in the huddle page. To change an agent, edit its step in `handoff/pipeline.py` (or its logic in `handoff/agents.py`, `iris.py`, `writers.py`), then update its row in `tests/test_agents.py`.

## External wrapper convention (for Masky, Tenki, Claude, DailyMed, n8n)

One function per service: live is the default, with a cached copy as an automatic fallback if the call fails or no key is set. Show which one ran (LIVE/CACHED badge). Add a test that runs the cached path. Never log patient names; spoken lines and outbound payloads use bed numbers only.

## Components

| # | Component | Status | Files | Done when |
|---|---|---|---|---|
| 1 | Agent steps (9 agents, cached) | done, tested | `handoff/pipeline.py`, `agents.py` | `pytest` green; ranking 402, 403, 404, 401 |
| 2 | Iris rules (CR-1, 2, 5, 6, 12, 13) | done, tested | `handoff/iris.py` | red-team drafts rejected, gold SBARs pass |
| 3 | Sam / Felix templates | done | `handoff/writers.py` | gold SBAR + form per bed |
| 4 | API: run, stream, state, ask, approve + audit | done, tested | `server.py` | `tests/test_server.py` green |
| 5 | Huddle page (tiles, captions, board, cards, Ask, Approve) | built, **not yet browser-tested** | `static/index.html` | every "Demo:" option runs; no console errors |
| 6 | Masky avatars + voices: 5 of 10 created (Quinn, Wren, Iris, Vera, Mina) | **capped at 5 on Creator; Theo, Sam, Felix, Echo, Lens use browser voice** | `scripts/masky_setup.py` | second account or Pro for the rest |
| 7 | Masky audio into the huddle | **done**: server renders each line in the agent's voice (6 s cold, 1.3 s repeat) and the page plays it; browser voice if none | `handoff/masky.py`, `server.py`, `static/index.html` | cache warm-up script still to do |
| 7b | Quinn routes questions to the owning agent; Wren (chart clerk) added | **done, tested** | `handoff/pipeline.py` (`ROUTES`, `ANSWERERS`) | `pytest` green |
| 8 | Avatar images in tiles (replace initials), idle loops | not started | `static/index.html` | tiles show Masky portraits |
| 9 | Theo on Tenki sandbox (outbound off) + local fallback | **done, verified live** (template script; Claude-written script needs `FLATKEY_API_KEY`) | `handoff/sandbox.py`, `llm.py` | badge reads "tenki sandbox · <source> script · Ns" |
| 10 | Claude-written SBAR (live) with template fallback | not started | `handoff/writers.py` | Iris still passes; refusal falls back |
| 11 | DailyMed live fetch with cached fallback | **done, verified live** | `handoff/agents.py` | attachment title says "live from DailyMed" |
| 12 | n8n workflow (webhook to Slack/Discord + audit row) | not started | n8n cloud + `N8N_WEBHOOK_URL` | page appears in channel on Approve |
| 13 | Echo live: record handoff audio + faster-whisper (P1) | not started | `assets/verbal/` | transcript matches cached claims |
| 14 | Lens live vision (P1) + blurry-label fixture | not started | `handoff/agents.py` | 3 labels classified |
| 15 | Browser smoke test of the huddle page | not started | `tests/` | headless page loads, Start runs, Approve works |
| 16 | Snyk scan + fixes + screenshot | not started | repo | clean report |
| 17 | Prelint GitHub App + one PR showing a flagged dose | **done**: finding on closed PR #1 (CR-2, CR-4) | GitHub | screenshot for the deck |
| 18 | Deck (`/deck.html` or Canva), backup video, README polish | README done | | URL ready |
| 19 | Submissions: crewbase, Masky form, Twitch chat deck URL | not started | | all three before 5:30 |

## Suggested split between two people

- **Backend/integrations:** 6, 7, 9, 10, 11, 13, 14. Each has a cached path and a test.
- **Frontend/dev workflow/admin:** 5, 8, 12, 15, 16, 17, 18, 19. Start with 5 (open the page, click every demo option, fix what breaks).
- Touch different files where possible: backend owner edits `handoff/*`, frontend owner edits `static/index.html` and `tests/`. `docs/BUILD.md` status column is updated by whoever finishes a row.
