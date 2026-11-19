# Declarations - Team Khao Khao

## Prior idea (declared)
- The product concept (a WhatsApp assistant + dashboard for wedding coordination, with join codes and photo/voice capture) comes from **WeWED**, a startup idea owned by **Jeet Doshi** (team member) and his co-founder **Soham Dixit**. An idea/planning document existed before the event (dated 18 Nov 2026).
- **No code, design or assets existed before the build window.** Everything in this repository was written on 19 Nov 2026 during the event. Today's build targets a different user (professional wedding planners running several weddings, coordinating their team and vendors) than the original family-focused plan.

## AI tools
- **Claude Code (Anthropic, model Claude Opus 5.5)**: wrote most of the code, docs and plan with the team, who reviewed and directed every decision.
- **Google Gemini API** (inside the app): listens to voice notes, splits them into tasks, answers questions from the app's own data.

## APIs and services
- **Twilio WhatsApp Sandbox**: sends and receives WhatsApp messages (no Meta approval needed for the sandbox).
- **Render** (free tier): hosts the web app and its Postgres database.

## Open-source libraries
- Flask (web server), Requests (HTTP calls), python-dotenv (reads the `.env` file), Gunicorn (production server), psycopg (Postgres driver)
- Pico CSS (styling, loaded from the jsDelivr CDN)

## Data
- All people, phone numbers, weddings and tasks in the demo are **synthetic**. Simulated phone numbers start with `+91000`. No scraped or confidential data.
