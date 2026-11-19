# PLAN - WeWED Planner Assistant (Team Khao Khao)

Build started for real at ~12:00 IST (event ran late). Times below are our targets; update when organisers confirm deadlines.

## The one flow that must work
Planner sends a **voice note** (any language) on WhatsApp
-> AI splits it into tasks (who, what, by when, photo proof needed?)
-> bot asks **"Which wedding? 1-4"** -> planner replies a number
-> each person gets **their own task on WhatsApp**
-> bot **reminds them** until they reply **DONE** (with a **photo** when proof is needed)
-> planner is notified, **dashboard** updates.

## Time boxes
| Time (IST) | Work | Tag |
|---|---|---|
| 12:00 - 12:45 | Database + AI + WhatsApp bot logic + simulator, tested locally | `checkpoint-1` |
| 12:45 - 13:30 | Signup screen, join code, dashboard, ask-the-bot, photo proof | |
| 13:30 - 14:00 | Twilio sandbox + Gemini keys live, deploy to Render, test on real phones | `checkpoint-2` |
| 14:00 - 14:20 | Polish, README, HOW_IT_WORKS, cheat sheet, record fallback demo video | |
| 14:20 - freeze | Feature freeze, `final` tag, submit form | `final` |

## Cut list (only if we run out of time, in this order)
1. Login by WhatsApp magic link (signup link still works)
2. Members' voice notes being understood (text DONE still works)
3. Ask-the-bot questions
