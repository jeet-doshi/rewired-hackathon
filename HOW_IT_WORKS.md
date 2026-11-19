# How WeWED works (plain English)

## The big picture
```
 Planner's phone ──voice note──►  WhatsApp (Twilio)  ──►  our app /whatsapp  ──►  bot.py decides what to do
                                                                                    │
                                     ai.py (Gemini): "who should do what, by when?" ◄┘
                                                                                    │
 Ayush's phone ◄──"New task #12"── WhatsApp (Twilio) ◄── messaging.py ◄─────────────┤
                                                                                    ▼
                                                     db.py (database) ──► Dashboard page (app.py + templates)
 Reminder loop (every 30 s, plain code) ──► nudges people until DONE ──► tells planner if they never reply
```

## The files (only 5 Python files)
| File | What it does |
|---|---|
| `app.py` | The web server: signup page, dashboard, simulator, and the `/whatsapp` address Twilio calls |
| `bot.py` | The bot's brain: join codes, planner → tasks → "which wedding?", DONE + photo proof, reminders |
| `ai.py` | The only AI: listens to voice notes, splits them into tasks, answers questions from our data |
| `messaging.py` | Sends WhatsApp messages through Twilio and downloads voice notes/photos |
| `db.py` | Saves everything (SQLite on laptop, Postgres online) + the fake demo data + one-click reset |
| `templates/*.html` | The pages people see |

## Step by step: one voice note
1. Planner records *"Ayush, buses confirm karo kal 5 baje tak. Imran, stage ka photo bhejo Friday tak."*
2. Twilio receives it and calls our `/whatsapp` address with a link to the audio. We reply "OK" instantly and work in the background.
3. `ai.py` sends the audio + the list of team members + weddings + today's date to Gemini.
   Gemini returns JSON: `[{assignee: Ayush, task: "Confirm buses", due: "2026-11-20 17:00", needs_proof: false}, {Imran ... needs_proof: true}]`.
4. `bot.py` checks every person really exists in the team (AI can't invent people), saves the tasks as "waiting",
   and asks the planner **"Which wedding? 1–4"**.
5. Planner replies `1`. Tasks are saved to the database and each person gets their own WhatsApp message.
6. **Reminder loop** (plain code, every 30 s): if a task is still open, nudge again
   (more often when the deadline is under 24 h away). After 3 reminders with no reply, the planner gets a warning.
7. Ayush replies `DONE 12`. If the task needs proof, the bot asks for a photo first. The photo is saved and sent to the planner.
8. The dashboard shows everything: per wedding, per person, overdue, photo proofs, and a live message feed.

## Why this design
- **AI only for messy human language; code for anything that must be exact** (dates stored, who gets messages, reminders, status).
- **WhatsApp stays the front door** (ECHO: people keep talking), but the *record* lives in a database, not in a chat that scrolls away.
- **Join code instead of WhatsApp groups**: everyone talks 1-to-1 with the bot, so each person only sees their own tasks.
- **Simulator** uses exactly the same `bot.handle_incoming()` as real WhatsApp, so the demo works even if the venue Wi-Fi or Twilio fails.

## Real vs demo
- Real: voice-note understanding, task creation, WhatsApp sending/receiving (Twilio sandbox), reminders, photo proof, dashboard, signup, join codes.
- Demo shortcuts: reminder gaps are **minutes** instead of hours so judges can see them; demo team members have fake numbers (`+91000…`) and live in the simulator; Twilio **sandbox** requires each phone to send a one-time "join" message (a real launch uses an approved WhatsApp Business number).
