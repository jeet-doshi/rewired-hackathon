# WeWED - One-page cheat sheet (read this before the pitch)

## The 20-second answer
Wedding planners run 4 weddings a month through 40 WhatsApp groups. Tasks get lost in voice notes, nobody follows up, there's no proof.
WeWED: the planner sends **one voice note in any language** -> AI makes tasks -> bot asks **"which wedding?"** -> each person gets **their own task + a voice note in their language** -> bot **reminds until DONE** -> **photo proof** -> **dashboard**.

## Live links
- App: https://wewed-assistant.onrender.com  · Demo dashboard: https://wewed-assistant.onrender.com/w/demo
- Simulator (backup demo): https://wewed-assistant.onrender.com/w/demo/sim
- WhatsApp bot: **+1 555 169 1720** (Meta WhatsApp Cloud API test number; save it as "WeWED Bot"). Only phones registered as testers in Meta (max 5) can use it.
- Backup inbound: +1 737 250 8034 (Twilio trial) also reaches the same app; replies still come from the Meta number.

## What each file does
| File | Plain English |
|---|---|
| `app.py` | The website + the two WhatsApp "doors" (`/whatsapp` for Twilio, `/meta` for Meta) |
| `bot.py` | The brain: join codes, voice note -> tasks -> which wedding -> send, DONE + photo, reminders |
| `voice.py` | Sarvam AI: voice -> text (detects language), text -> voice note |
| `ai.py` | Gemini: text -> list of tasks (who/what/when/photo?), translation, answering questions |
| `messaging.py` | Sends WhatsApp messages (Meta or Twilio) and downloads voice notes/photos |
| `db.py` | Saves everything (Postgres online, SQLite on laptop) + fake demo data + reset |

## Data flow (say it like this)
Voice note -> WhatsApp -> our server -> **Sarvam** writes down the words -> **Gemini** finds who/what/when -> we check the people really exist -> ask which wedding -> save in **database** -> send each person their task (+ **Sarvam** voice in their language) -> **reminder loop every 30 s** (normal code, not AI) -> DONE / photo -> planner notified -> **dashboard**.

## Tech and why
- **Python + Flask**: one language, simple, easy to explain.
- **Sarvam AI**: built for Indian languages and accents, Hinglish included.
- **Gemini**: turns messy speech into structured tasks (JSON).
- **Postgres on Render**: free, survives restarts.
- **AI only for understanding language. Plain code for anything that must be exact** (deadlines, reminders, who gets what, status).

## Real vs demo
- **Real**: voice transcription, task extraction, translation, voice replies, WhatsApp in/out, reminders, escalation, photo proof, dashboard, signup, join code, ask-the-assistant.
- **Demo shortcuts**: reminders every 2 minutes (would be hours); Ayush/Imran etc. are fake numbers (+91000...) living in the simulator; WhatsApp uses Meta's free **test number**, so its name shows as "Test Number" and no profile photo (Meta locks branding on brand-new business accounts; a verified number shows "WeWED Bot" + logo). Production needs a verified WhatsApp Business number.

## 10 likely judge questions
1. **Why not just a WhatsApp group?** Groups scroll away, nobody owns a task, no reminders, no proof, no per-wedding view. We keep WhatsApp as the front door but the record lives in a database.
2. **What if the AI picks the wrong person?** AI can only choose from people who joined; unknown names are flagged and the planner confirms the wedding before anything is sent. Tasks can be reassigned on the dashboard.
3. **What languages?** 10 Indian languages + English; each person picks theirs when joining (ECHO: "in the language the user chooses").
4. **How did the constraint shape it?** Voice is the only input needed; output also comes back as voice; vendors can reply "ho gaya" by voice.
5. **Where does data come from?** Only what users send. Demo data is synthetic.
6. **Privacy?** Each person sees only their own tasks; dashboard is a secret link; `DELETE MY DATA` command; privacy page at /privacy.
7. **Cost?** Sarvam STT is cheap per minute; Gemini Flash is a fraction of a rupee per message; WhatsApp charges per conversation. Fine for a planner charging lakhs per wedding.
8. **Why reminders by code, not AI?** Deadlines must be exact and predictable; AI only writes/understands words.
9. **What breaks today?** WhatsApp test accounts limit numbers; free Render server sleeps after 15 min (first message slow). Simulator is the fallback.
10. **What's next?** Role-based access, verified WhatsApp Business number, vendor payments, chat-export import, pilot with 3 planners.

## Who explains what
- **Jeet**: idea, WhatsApp flow, `bot.py`, `messaging.py`
- **Divya**: AI + voice: `ai.py`, `voice.py`
- **Anushree**: hosting + data + dashboard: `app.py`, `db.py`, Render, Meta setup
