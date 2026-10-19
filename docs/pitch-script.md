# Pitch script — SBAR Handoff Team (3 minutes)

The project lead presents and a teammate runs the demo. Lines in **[brackets]** are cues for the teammate. Target is about 400 spoken words, so speak slowly.

---

## 0:00 – 0:15 Hook

> It's 6:55 PM. I'm a nurse, and in fifteen minutes I'm going home. I have four patients to hand off, and about four minutes per patient.
>
> **[MY STORY: 1–2 sentences about a handoff where something was missed. If you'd rather not share one, use the line below.]**
>
> *Fallback:* Every nurse has a story about the patient who was "fine" at handoff and wasn't fine an hour later.

**[Click "Start handoff". Countdown starts at 15:00.]**

## 0:15 – 0:35 The verbal handoff

> This is a real-sounding handoff, recorded by me. Listen to bed 402.

**[Play the recording. Echo's transcript appears line by line.]**

> "She's fine, honestly it's just the UTI." Remember that sentence.

## 0:35 – 1:15 The team goes to work

> Meet the team. Quinn is our charge nurse. She splits the work across specialists who run in parallel.

**[Lines animate from Quinn to Theo, Mina and Lens.]**

> Theo writes analysis code and runs it in a Tenki sandbox. Those charts were just generated.
>
> Lens reads a photo of the IV bag for 403. The label says 80 milligrams. The order says 40. Lens hands that to Mina.
>
> Mina pulls the digoxin label from DailyMed live, because 403's potassium is low and his digoxin is due at nine.

## 1:15 – 1:45 The moment

**[Convergence view for 402: four yellow cards pull into one red node.]**

> Now look at 402. A slightly high temperature. A heart rate creeping up. Blood pressure drifting down. Less urine every few hours. A note that she seemed confused. Each one alone looks borderline.

**[Vera speaks.]**

> Vera brings them together. The verbal handoff said she's fine. The chart disagrees. 402 is priority one, with a pattern consistent with possible early sepsis that needs a provider to evaluate it now.

## 1:45 – 2:15 Guardrails and the briefing

**[Iris rejects a draft. Red strike-through, new wording types in.]**

> Iris just rejected a draft because it recommended a fluid volume. Treatment orders belong to the provider. Our agents escalate. They never prescribe.

**[Sam's avatar reads the 402 SBAR. Felix's provider form appears beside it.]**

> Sam briefs me, and Felix has the provider call ready. Every line cites where it came from.

## 2:15 – 2:40 The nurse decides

> I'm the incoming nurse, and I'm in charge.

**[Push-to-talk.]** "Why is 402 above 403?"

**[Answer appears with citations.]**

> Nothing leaves this screen until I approve it.

**[Click Approve. Show the page arriving in Slack or Discord, then the n8n canvas for 5 seconds.]**

## 2:40 – 3:00 Why it matters

> Communication failures were a factor in 30 percent of more than 23,000 malpractice cases in one national study, cases that included 1,744 deaths.
>
> Hospitals pay for nursing time, and today handoff prep is manual chart review under a clock. We give that time back and catch what a tired handoff misses.
>
> Our agents don't replace nurses. They make sure the nurse walking in knows what the nurse walking out didn't say.
>
> Cross-source validation is patent pending. Thank you.

**Source for the statistic:** CRICO Strategies analysis of 23,658 malpractice cases from 2009 to 2013, as reported by [STAT, Feb 1, 2016](https://www.statnews.com/2016/02/01/communication-failures-malpractice-study/). The figure covers communication failures in general, not only shift handoffs, so say it as written above. Put the source on the slide.

---

## Likely judge questions

**"Isn't the agent conversation just a script?"**
> The ranking, trends, label check and drug lookup are computed live from the data every run, and the evidence citations come from those results. The demo data is fixed so it runs the same way on stage; change a vital sign and the ranking changes.

*(Only say the last sentence if the developer confirms it is true. Test it before the pitch.)*

**"What about patient privacy?"**
> Everything you saw is synthetic data, and our clinical rules block PHI from logs and from anything sent out. Nothing leaves the system until a nurse approves it, and every approval is written to an audit log.

**"Why would a hospital buy this?"**
> It targets the most error-prone fifteen minutes of every shift, using data the hospital already has. It runs as a safety net beside the nurse, so it fits existing workflows instead of replacing them.

**"How does Vera decide the ranking?"**
> That's our cross-source validation method, and it's patent pending, so I can't go into detail today. What I can show you is the outcome and the evidence behind every decision.
