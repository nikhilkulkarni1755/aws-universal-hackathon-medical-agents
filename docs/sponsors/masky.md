# Masky (avatars + voices) — implementation notes

Full reference: `masky-api-full.md` (saved copy of https://masky.ai/masky-api.md). Skill entry: https://masky.ai/skill.md. Hackathon guide: https://masky.ai/hackathon.md.

## Hackathon rules (Masky prize, not judged without)
1. Public GitHub repo. 2. Masky avatars used in the project. 3. Deck URL (Canva / Google Slides / single-page HTML) posted in chat at twitch.tv/aijudge. 4. Submit at https://masky.ai/blog/2026-10-14-ai-workforce-hackathon/#submissions (Masky sign-in; project name, project URL, GitHub URL). Deadline **5:30 PM PT Oct 19**.
Judging: community flourishing, agent autonomy (agent-run company scores highest), wellbeing impact, honest demo. Luma page (AWS event) says the $800 Masky prize is for agents that participate in human communities, not replace them.

## Account setup (do first)
- Free tier = 1 avatar. Redeem **AIWORKFORCE2026** at https://masky.ai/?membership=true (Creator tier, first month free) before creating avatars.
- New accounts start with $10 credits. API key: https://masky.ai/developer (`mky_...`), or device-code flow (POST /api/oauth/device, user approves link, poll /api/oauth/token).
- `export MASKY_API_KEY=mky_...`; check: `curl -s https://masky.ai/api/avatars -H "Authorization: Bearer $MASKY_API_KEY"`.

## Core flow (base URL https://masky.ai/api)
1. `POST /images/generate {"prompt","aspectRatio":"1:1"}` -> `imageUrl` (sync, ~0.005 credits)
2. `GET /voices` -> pick a distinct voice `id` per agent
3. `POST /avatars {"displayName","imageUrl","personalityPrompt","voiceId"}` -> `avatarId`, `avatarOwnerUserId`
4. `POST /conversations {"avatarOwnerUserId","avatarId"}` -> `conversationId`, `shareSlug`, `liveUrl` (private, `?token=`)
5. `POST /conversations/{id}/turn {"userText":"<line>","mode":"speak","output":"video"|"audio"}` -> 202 pending turn
6. Poll `GET /conversations/by-slug/{shareSlug}` every ~2s; audio ~5-10s, video ~30-60s. Or just embed `liveUrl` (auto-plays turns in order).

## Gotchas that shape the design
- `userText` max 500 chars; replies auto-chunk to <=3 sentences, each its own turn id. Keep lines <=3 sentences.
- Lip-synced talking head = `speak` turn. `/videos/generate` is NOT lip-sync.
- **Scripted renders are cached across conversations** (speak mode, no `reinterpret`; same avatar, voice, output, quality, image) -> instant and free (`fromSpeakCache: true`). Warm the cache by running the demo script once before judging. Any text change = cache miss.
- Claude-written lines are not cacheable: use `output:"audio"` (5-10s) or browser TTS for those.
- Don't overlap turns within one conversation (one conversation per agent avatar is fine).
- Media URLs are signed, ~1h TTL. Conversations start private; keep them private (bed numbers only in spoken lines).
- `402` = out of credits (`requiredCredits`/`availableCredits`).
- Idle loop: `POST /conversations/{id}/silent-renders {"enabled":true}` (poll GET until ready) gives natural idle blinking between lines. Example quote ~0.75 credits per avatar; check `GET .../silent-renders` quote first.
- Voice delivery: `voiceStyle {"emotion","style","prosody":[]}` or inline `<|prosody:pause|>`. Emotions: elation, amusement, enthusiasm, determination, pride, contentment, affection, relief, contemplation, confusion, surprise, awe, longing, anger, fear, sadness, ... Style: singing|shouting|whispering. Prosody: speed_very_slow|speed_slow|speed_fast|speed_very_fast|pitch_low|pitch_high|expressive_high|expressive_low.
- Two-avatar single call: `speakerAvatarId` + `userText` (speaker line) + `avatarText` (conversation avatar line), `mode:"chat"`.
- Pricing: `GET /api/videos/pricing` (no auth).
- Optional (not required by judging): "Login with Masky" (masky-sso.md), credit tip button (`POST /api/donations/intents`).
