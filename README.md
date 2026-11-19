# WeWED Planner Assistant - Team Khao Khao

**Rewired (Tech Hackathon) · Road to Milky Way, Bangalore · 19 Nov 2026 · Team ID REW-NAD3SS**

| | |
|---|---|
| **Problem (the invisible thing)** | Indian wedding planners run 4+ weddings a month out of dozens of WhatsApp groups and voice notes. Instructions to their team and vendors scroll away, nobody tracks who promised what, follow-ups live in the planner's head, and there is no proof a job was done. The planner's coordination work is invisible, and so are the people doing the work. |
| **Target user** | A wedding planner (and their team members + vendors: decorators, caterers, photographers) who talk, not type. |
| **Solution** | A WhatsApp assistant. The planner sends **one voice note in any Indian language**; it becomes tasks, the bot asks **which wedding**, sends **each person their own task (text + voice note in their language)**, **reminds them until they reply DONE**, collects **photo proof**, and shows everything on a **dashboard**. |
| **Demo link** | https://wewed-assistant.onrender.com (demo workspace: https://wewed-assistant.onrender.com/w/demo) |
| **Demo video** | _(add Drive link)_ |

## How the envelope constraint (ECHO) shaped the build
*"They don't type. They talk, and they'll keep talking."*
- The **only way in is a voice note** (text also works). Sarvam AI transcribes Hindi, Kannada, Tamil, Hinglish and more, and detects the language.
- People **choose their language when they join**, and tasks come back to them **as a voice note in that language** - nobody has to read or type.
- Team members can reply **by voice** too ("ho gaya") - the bot understands it means the task is done.
- The voice note leads to something the process can act on: an **assigned, dated, tracked task** with reminders and proof.

## Architecture
```
Planner WhatsApp voice note ─► WhatsApp API (Meta Cloud API / Twilio) ─► /meta or /whatsapp webhook (Flask, app.py)
   ─► voice.py  Sarvam speech-to-text (text + language)
   ─► ai.py     Gemini: who / what / by when / photo needed? + translate per assignee
   ─► bot.py    "Which wedding? 1-4" ─► save tasks ─► message each person (text + Sarvam voice note)
   ─► reminder loop (plain code, every 30 s) ─► nudge until DONE ─► escalate to planner after 3
   ─► db.py     Postgres (Render) / SQLite (laptop) ─► dashboard (templates/)
```
Python + Flask, Postgres, Sarvam AI (voice), Google Gemini (understanding), WhatsApp via Meta Cloud API or Twilio, hosted on Render. See `HOW_IT_WORKS.md`.

## Setup and run
```bash
pip install -r requirements.txt
cp .env.example .env      # fill in GEMINI_API_KEY, SARVAM_API_KEY, WhatsApp keys
python app.py             # open http://localhost:5000
```
Deploy: Render Blueprint (`render.yaml`) creates the web service + free Postgres. Point the WhatsApp webhook to `https://<app>/meta` (Meta) or `https://<app>/whatsapp` (Twilio).

## What works / what is partial / what is next
**Works (real, live):**
- Sign-up screen -> workspace with 4 weddings, a **join code** and a private dashboard link (magic link)
- **JOIN code** onboarding on WhatsApp: team vs vendor, what they handle, preferred language
- Voice note / text -> AI tasks -> "Which wedding?" -> per-person tasks with deadlines
- Tasks delivered as text + **voice note in the assignee's language** (Sarvam text-to-speech)
- DONE replies (text or voice), **photo proof** required where needed, forwarded to the planner
- **Reminders** until done, escalation to the planner after 3 ignored reminders
- Dashboard: per wedding, per person, overdue, proofs, nudge / mark done / assign, live message feed, **ask-the-assistant** ("what's pending for Sharma wedding?")
- WhatsApp **simulator** that runs the exact same bot logic (demo fallback)

**Partial / honest limits:**
- WhatsApp access is via **test/trial accounts**: Twilio's free trial delivers incoming messages to our app but only lets the bot reply with Twilio's fixed templates; Meta's free test number allows replies but only to up to 5 registered test phones. A production launch needs an approved WhatsApp Business number.
- Reminder gaps are **minutes** in demo mode (hours in real life) so judges can see them.
- Demo team members use fake numbers (+91000...) and live in the simulator.
- Access control (who sees what) is minimal: the dashboard link is secret; per-role permissions are next.

**Next:** roles & permissions, WhatsApp Business number, payment tracking per vendor, chat-export import, analytics on time saved.

## Declarations
See `DECLARATIONS.md` (libraries, APIs, AI tools incl. Claude Code, and the declared prior WeWED idea).

## Data
Synthetic only. All people, numbers, weddings and tasks in the demo are made up. No scraped or confidential data.

## Team
- **Jeet Doshi** - product idea (WeWED co-founder), WhatsApp + deployment setup, pitch
- **Divya Bharti** - AI keys and voice flow testing, can explain `ai.py` / `voice.py`
- **Anushree Laddhad** - hosting (Render), dashboard walkthrough, can explain `app.py` / `db.py`
- Code written with **Claude Code** (AI) during the event; the team directed and reviewed every decision.
