# Rewired (Tech Hackathon) - Offline Round: Context for Claude Code

Read this fully before doing anything. Drop this file in the repo root as `CLAUDE.md`.

## 1. Who we are
- **Team Khao Khao**, Mesa School of Business: Jeet Doshi, Divya Bharti, Anushree Laddhad.
- Event: **Rewired (Tech Hackathon), Road to Milky Way - Bangalore**, organised by Masters' Union / Milkyway. Offline round on **19 Nov 2026** (IST).
- We are in the **Top 20** shortlisted from the online round.
- Our online-round idea was **Thaali** (food-surplus matching via WhatsApp/Telegram bot + volunteer dashboard). **The offline round has a NEW problem statement.** Do not assume Thaali applies. Use it only if the new problem genuinely fits, and any code must still be written fresh today.

## 2. Event theme and what judges reward
- Theme: **"The Invisible City"**. Every city runs on things nobody sees: voices no system understands, people who keep everything working but never appear in any database, waste nobody counts, needs nobody says out loud. Build technology that makes something real that the city overlooks **heard, seen, counted or said**.
- It rewards: **problem sharpness, sound execution, original thinking, and the ability to explain why the idea matters to a real user.** Coders, designers and business minds are all welcome.
- Technical execution is scored out of **25**. If the team cannot explain a core part of the project when a judge asks, that score is **capped at 10/25**.

## 3. Hard timeline (all IST, 19 Nov 2026)
| Time | What |
|---|---|
| 10:00 AM | Build clock starts. Problem case revealed; team picks 1 of 2 envelopes ("The Gravity Well") that reveals a real-world constraint we must build around |
| by 11:30 AM | Push git tag `checkpoint-1` |
| by 2:30 PM | Push git tag `checkpoint-2` |
| 4:30 PM (our internal target) | Feature freeze, record demo video, finish README |
| before 5:00 PM | Push tag `final`; submit Google Form |
| 5:00 PM | **Event Horizon Crossing: code frozen.** No pushes, Drive changes or redeployments after this. The recorded final commit is what is judged |
| After | Pitch: **5 minutes + 3 minutes Q&A** to one of four panels. Pitches over 5 min are cut off. Top teams per panel go to the Final Orbit and pitch to the Grand Jury |

GitHub server push times are the official record. Clock runs through meals and mentor check-ins (2 check-ins of about 20 minutes with an assigned mentor; not scored).

## 4. Rules that shape how we code
1. **Original work only.** Everything (code, design, assets) must be created inside the build window. No pre-existing projects, old code or borrowed products.
2. **Allowed if declared:** open-source libraries, public APIs, templates, UI kits, official project generators (create-next-app, vite, etc.), any AI tool.
3. **Declare everything.** Keep a running `DECLARATIONS.md`/README section listing every library, API, template, generator and AI tool used (including Claude Code).
4. **Working prototype required.** Slide-only is not allowed; a partial working prototype is fine. If the live demo fails, we may play our demo video during the pitch.
5. **No confidential or scraped personal data.** Use synthetic/demo data or properly public datasets.
6. **Any judge can ask any member to explain any part of the code.** So: keep the code simple, readable and commented, and explain decisions to the team as you go.
7. Team members cannot change. Conduct rules apply (no sabotage, no misuse of venue network).
8. Teams keep the IP of what they build; the organisers may feature submissions with credit.

## 5. Submission checklist (Google Form given at the venue start)
- Repository link **and final commit hash**
- **Demo link** (deployed app or hosted demo; must work without our laptop if possible)
- **Demo video, max 2 minutes**, mandatory (.mp4/.mov), with subtitles in English or Hindi
- **Completed README** (see section 8)
- Drive folder named exactly `REWIRED_<TeamID>_MWRTMB`, links set to "Anyone with the link can view". We get the TeamID at the venue; ask us for it.
- Language for all of the above: English or Hindi.

## 6. How we want you (Claude Code) to work
1. **First message to us:** ask us to paste (a) the problem case, (b) the chosen envelope constraint, (c) our stack skills and what is installed. Do not start coding before this.
2. **Then propose 2 or 3 scoped options** (one paragraph each) with: sharp problem, real user, what is demoable in about 5 hours, the invisible-city angle, and what the envelope constraint forces. Recommend one. Wait for our pick.
3. **Scope ruthlessly.** One end-to-end flow that works beats five half-built features. Build the thin vertical slice first, then polish. Cut features before cutting the demo.
4. **Stack bias:** boring, fast, debuggable. Prefer one language, one framework, a hosted free-tier backend (Supabase/Firebase/SQLite), and a deployed URL (Vercel/Netlify/Render). Avoid anything needing account approval or long setup (e.g. WhatsApp Business API; use Telegram bot or a web UI).
5. **Git discipline:** small commits with clear messages from minute one. Create tags exactly as `checkpoint-1`, `checkpoint-2`, `final` and push tags (`git tag checkpoint-1 && git push origin checkpoint-1`). Remind us 20 minutes before each deadline.
   - **Check the real time yourself:** run `date` (the machine should be on IST; if not, ask us the time) before each major step and warn us when a tag deadline is within 30 minutes.
   - **Set up git first:** `git init`, add the GitHub remote, make a first commit, and confirm `git push` works (ask us to authenticate if needed) before writing features. Verify each tag landed on GitHub; GitHub's server time is the official record.
6. **Plan against the clock.** Write a time-boxed plan in `PLAN.md` mapped to the three tags. Update it as we go.
7. **Keep us able to explain it:** after each major piece, give a 3-line plain-English summary of what it does and why, so any of us can answer a judge.
8. **Demo safety:** seed realistic synthetic data, add a one-click reset, and make a fallback screen recording early (by 3:30 PM at the latest).
9. **Do not** fetch scraped personal data, copy old projects, or hide AI usage.

## 6A. IMPORTANT: the team is non-technical - you choose the stack and drive the build
- Jeet, Divya and Anushree are business students with little or no coding experience. **You pick the stack and make all technical decisions.** Do not ask us to choose frameworks, databases or libraries.
- Choose the **simplest stack that still gives a real working demo and a public demo link.** Strongly prefer: one language, minimal dependencies, free hosting, no paid keys, no account approvals. A single web app (for example Python + Streamlit/Flask, or a plain Next.js/Vite app) with SQLite or a free hosted DB is usually better than anything complex. If an LLM API is truly needed, tell us exactly what key to get and how, step by step.
- **Do all the terminal work for us.** Give exact copy-paste commands one step at a time, and tell us what we should see. Install and set up everything yourself where you can. If something fails, diagnose it and fix it; do not hand us raw error logs to figure out.
- **Because any judge can ask any of us to explain any part of the code (otherwise the technical score is capped at 10/25), you must make us able to explain it.** After each feature: (a) a 3-line plain-English explanation, (b) a one-line "why this approach", (c) update `HOW_IT_WORKS.md` with a simple diagram or bullet flow of how data moves through the app. Keep files few and names obvious; comment the code in plain English.
- By 3:30 PM, write us a **one-page cheat sheet**: what each file does, the data flow, the tech used and why, what is real versus mocked/seeded, and 10 likely judge questions with simple answers. Quiz us on it if we ask.
- Be honest in the README and pitch about what is mocked or partial. Never fake functionality.
- We will also supply the business side: user story, evidence, pitch. Ask us for that early (first-hand stories, numbers, who the user is) so the product matches the problem.

## 7. Pitch (5 min + 3 min Q&A) - help us prepare
Structure to support: (1) the invisible thing and who suffers, with a real number or first-hand story, (2) the user, (3) live demo of the core flow, (4) how the constraint shaped the design, (5) why this is original, (6) impact and next steps. Also draft likely judge questions and short answers (data source, scale, failure cases, privacy, why this tech).

## 8. README template (must be complete before submit)
```
# <Project name> - Team Khao Khao
Problem (the invisible thing) | Target user | Solution | Demo link | Demo video
How the envelope constraint shaped the build
Architecture (short diagram or bullets) | Setup and run instructions
What works / what is partial / what is next
Declarations: libraries, APIs, templates, generators, AI tools (incl. Claude Code)
Data: synthetic only, no scraped or confidential data
Team: Jeet Doshi, Divya Bharti, Anushree Laddhad (who built/can explain what)
```

## 9. Fill in at 10:00 AM
- **Problem case:** _(paste here)_
- **Envelope chosen and constraint:** _(paste here)_
- **TeamID:** REW-NAD3SS (Drive folder: `REWIRED_REW-NAD3SS_MWRTMB`)
- **Stack we know:** None. The team is almost entirely non-technical. **Claude Code chooses the stack** (see section 6A).
