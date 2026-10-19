# Prelint, n8n, Snyk — implementation notes

## Prelint (PR checks against specs) — https://prelint.com/docs
- It is an AI product-spec reviewer, not a regex linter. Install the **GitHub App** on the repo (no YAML/CI). It auto-indexes markdown in the repo (80K-char context budget) and comments inline on PRs within seconds. It does not do style or security.
- Put the rules where it indexes them: `docs/clinical-rules.md` (already written, CR-1..CR-18). **Do not add `docs/**` to `ignore_patterns`.**
- Optional `prelint.json` at repo root: `{"version":1,"trigger_mode":"auto","ignore_patterns":[]}`. `@prelint` comment on a PR triggers a review (needs write access). Draft PRs are skipped.
- Needs real PRs (branch -> PR), not pushes to main. Billing: $1 per completed review, prepaid credits (get promo/credits in the event Discord). Auto-approves when no findings.
- Demo plan: open one PR that puts a dose in an agent template's Recommendation, screenshot the inline finding; fix; screenshot the clean result. Do not rely on it as the only CR-2 guard; Iris's regex stays the runtime check.
- Also: https://prelint.com/docs/ai-agents , https://prelint.com/docs/mcp (MCP server) exist.

## n8n (Approve -> page + audit) — https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/
- Webhook node: has a **test URL** (works while "Listen for test event") and a **production URL** (only after the workflow is published). Use the production URL in `N8N_WEBHOOK_URL`. POST, JSON, max payload 16 MB.
- Auth options: Basic / Header / JWT / none. Respond: Immediately | When Last Node Finishes | Respond to Webhook node.
- Flow from the plan: Webhook -> format message -> Slack/Discord node (`#4west-charge-nurse`) -> append audit row (Google Sheets/Data Table node; pick one) -> optional Wait/Schedule node for the "recheck 20:00" reminder.
- Payload per CR-15/CR-18: bed, tier, approver, timestamp, citation list only. No name/MRN/DOB.
- Fallback when `N8N_WEBHOOK_URL` is unset: show "page queued (demo)".

## Snyk (security scan + remediation) — https://docs.snyk.io/developer-tools/snyk-cli/getting-started-with-the-snyk-cli
- Free signup at https://app.snyk.io/signup (event link in the Luma page gives a free AI Security Engineer certificate).
- `npm install -g snyk` (or brew), `snyk auth`.
- Dependencies: `snyk test` in a folder with `requirements.txt` (build/install deps first). Source: `snyk code test`. Secrets: `snyk secrets test`. Flags: `--severity-threshold=high`, `--json`, `--all-projects`.
- Test limits do not apply to public repos (the repo is public).
- Plan: run, fix findings, re-run, screenshot the clean report for the pitch and the Masky/AWS deck.
