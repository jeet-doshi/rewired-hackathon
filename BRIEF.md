# WeWED - Project brief for the pitch deck (Team Khao Khao)

## One line
**WeWED is a WhatsApp assistant for wedding planners: talk once (a voice note, any language), and WeWED turns it into tasks, sends each person their own task in their language, follows up until it's done, and collects photo proof - all on one live dashboard.**
Tagline: *Talk once. WeWED follows up.*

## Theme fit - "The Invisible City"
The invisible thing: the **coordination work behind every Indian wedding**. Planners, their team and dozens of vendors (decorators, caterers, photographers, DJs) run everything on WhatsApp groups and voice notes. Nobody counts who promised what, nobody owns follow-ups, and the people doing the work (vendors, junior staff) are invisible in any system. WeWED makes that work **heard** (voice in), **seen** (dashboard) and **counted** (tasks, reminders, proof).

## Problem statement (from the brief)
India runs on WhatsApp jugaad. Pick a real process running on groups / forwards / voice notes, prove where it breaks, redesign it.
**Our process:** a wedding planner running ~4 weddings a month coordinating her team and vendors.

### Today (the jugaad)
- 1 planner, 4 weddings/month, ~40 WhatsApp groups (one per wedding x team / decor / catering / family...)
- Instructions are sent as **voice notes and messages** inside busy groups
- Follow-up = the planner remembering and calling people
- Proof = "haan ho gaya" in chat, maybe a photo somewhere in the scroll

### Where it breaks
1. **Lost instructions** - a voice note in a group of 200 unread messages gets missed
2. **No owner** - "someone confirm the buses" -> nobody does
3. **No follow-up system** - reminders depend on the planner's memory
4. **No proof** - was the stage actually set? no photo, no timestamp
5. **Cross-wedding confusion** - same vendor, 3 weddings, which one was that message for?
6. **Language gap** - planner speaks Hinglish, decorator prefers Hindi, caterer Kannada
7. **Cognitive load** - the planner is the database; if she's sick, the wedding stalls

## Envelope constraint: ECHO
*"They don't type. They talk, and they'll keep talking."* The way in must be a voice note, in the language the user chooses, and it must lead to something the process can act on.
How it shaped WeWED:
- The planner's **only input is a voice note** (text also works)
- Every member **chooses their language when joining**; tasks reach them as **text + a voice note in that language**
- Members can **reply by voice too** ("ho gaya") - WeWED understands it means DONE
- The voice note becomes an **actionable, assigned, dated, tracked task**

## What we built (working prototype)
1. **Signup + workspace** - planner creates a workspace with her 4 weddings, gets a **join code** and a private dashboard link
2. **Join with a code** - team members and vendors send `JOIN SHUBH-DEC Name` on WhatsApp -> bot asks: team or vendor? what do you handle? which language? -> they're in the shared workspace (replaces the WhatsApp group)
3. **Voice note -> tasks** - Sarvam AI transcribes the planner's voice note (Indian languages, Hinglish); Gemini splits it into tasks: who, what, by when, photo needed?
4. **"Which wedding? 1-4"** - one reply files every task under the right wedding
5. **Personal delivery** - each person gets only their task: English + their language + a **voice note in their language** (Sarvam text-to-speech)
6. **Follow-up engine** - automatic reminders until DONE; after 3 ignored reminders the planner is alerted ("maybe call them?")
7. **DONE + photo proof** - `DONE 12`; if proof is needed the bot asks for a photo and forwards it to the planner
8. **Ask the assistant** - "What's pending for Sharma wedding?" answered from the real data, in the language asked
9. **Live dashboard** - every wedding, every person, overdue, photo proofs, live message feed, nudge / mark done / reassign, Send-on-WhatsApp buttons
10. **Live phone views** - WhatsApp-style screens for each team member (demo)

## How it works (architecture - 1 slide)
Voice note -> WhatsApp API -> our server (Python + Flask on Render)
-> **Sarvam AI** (speech-to-text, language detection) -> **Gemini** (task extraction, translation)
-> code checks people exist -> "which wedding?" -> **Postgres** database
-> messages + **Sarvam** voice notes to each person -> **reminder loop** (plain code, every 30 s) -> DONE + photo -> **dashboard**
Principle: **AI only for understanding messy human language; plain code for anything that must be exact** (deadlines, reminders, who gets what, status).

## Demo flow (for the live demo slide)
1. Divya & Anushree join with the code (show phone screens)
2. Jeet sends a **real WhatsApp voice note** (Hinglish) to the bot
3. Bot: "I heard ... 2 tasks ... Which wedding?" -> "1"
4. Divya's phone: task in Hindi + Hindi voice note; Anushree's: English
5. Divya: DONE + photo -> dashboard shows done + proof; planner notified
6. Ask: "What's pending for Sharma wedding?"

## Honest status (say it before judges ask)
- **Real:** voice transcription (Sarvam), AI task extraction, translation, voice replies, join codes, reminders, escalation, photo proof, dashboard, signup; WhatsApp messages from a real phone reach the bot.
- **Limited today:** Meta locks brand-new business accounts from *replying* until **business verification** (1-3 days) - we added billing; verification is the only step left. So in the demo, team members' WhatsApp screens are shown in our WhatsApp-style view (same code, same messages).
- Demo shortcut: reminders every 2 minutes instead of hours so judges can see them.

## Why it's original
- Not a task app people must install - **WhatsApp stays the front door**; the system lives behind it
- **Voice-first in both directions**, per-person language
- **Wedding-aware** (which wedding?) - built for planners juggling several events
- **Follow-up + proof** built in, not just a to-do list

## Impact / business (fill numbers from research)
- User: professional wedding planners (and their vendor network)
- Pricing idea: per wedding (e.g. Rs 2,000-5,000/wedding) or monthly for planners - tiny vs the planner fee
- Next: verified WhatsApp Business number, role-based access, vendor payments tracking, chat-export import, pilot with 3 planners in Bangalore

## Suggested deck (8-9 slides, 5 minutes)
1. Title - WeWED: Talk once. WeWED follows up. (Team Khao Khao)
2. The invisible city: a planner's day - 40 groups, 600 messages, voice notes (story)
3. Where it breaks - the 5-7 breaks above
4. ECHO constraint - "they talk" -> voice in, voice out, their language
5. Solution - the flow (voice note -> tasks -> which wedding -> phones -> DONE + proof -> dashboard)
6. Live demo
7. How it works - architecture + AI vs code principle
8. Status, impact & next steps (honest status + pilot plan)
9. Team + thank you

## Links
- App: https://wewed-assistant.onrender.com
- Dashboard: https://wewed-assistant.onrender.com/w/demo
- Demo film: https://wewed-assistant.onrender.com/film
- Code: https://github.com/jeet-doshi/rewired-hackathon
- Logo: `static/wewed-logo.jpg` in the repo
