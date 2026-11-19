"""
ai.py - the ONLY place we use AI (Google Gemini).

AI is used for the messy human part: listening to voice notes in any Indian language and
understanding "Ayush, decorator ko Friday tak confirm karo". Everything that must be exact
(deadlines, reminders, who gets which message, status) is done by plain code in app.py.

Three jobs:
  1. understand_planner()  - planner's voice/text -> list of tasks (who, what, by when, photo needed?) or a question
  2. understand_member()   - team member / vendor voice/text -> "is this saying a task is done?" + English summary
  3. answer_question()     - answer "what is pending for Sharma wedding?" using ONLY our database
"""
import os
import json
import base64
import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _key():
    return os.environ.get("GEMINI_API_KEY", "")


def is_configured():
    return bool(_key())


def _ask_gemini(prompt, audio=None, want_json=True):
    """Send a prompt (and optionally a voice note) to Gemini and return its answer.
    audio = (bytes, mime_type) e.g. a WhatsApp voice note is (b'...', 'audio/ogg')."""
    parts = [{"text": prompt}]
    if audio:
        data, mime = audio
        mime = (mime or "audio/ogg").split(";")[0]
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
    config = {"temperature": 0.2}
    if want_json:
        config["responseMimeType"] = "application/json"
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    resp = requests.post(GEMINI_URL.format(model=model),
                         headers={"x-goog-api-key": _key()},
                         json={"contents": [{"role": "user", "parts": parts}], "generationConfig": config},
                         timeout=90)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini error {resp.status_code}: {resp.text[:300]}")
    text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text) if want_json else text.strip()


def understand_planner(text, audio, members, weddings, now):
    """Planner message -> {"intent": "tasks"|"question"|"other", "transcript", "language", "tasks": [...], "question"}"""
    team = "\n".join(f"- id {m['id']}: {m['name']} ({m['role']}, {m['specialty'] or '-'})"
                     for m in members if m["role"] != "planner")
    wed = "\n".join(f"- {w['name']} on {w['date']} at {w['venue']}" for w in weddings)
    prompt = f"""You are the WhatsApp assistant of an Indian wedding planner. The planner sent a message
(text and/or a voice note). It may be in Hindi, English, Kannada, Tamil, Telugu, Marathi, Gujarati, Bengali or a mix.

Current date and time (IST): {now.strftime('%Y-%m-%d %H:%M')} ({now.strftime('%A')}).

People in this workspace (team members and vendors):
{team}

Weddings being planned:
{wed}

Decide what the planner wants:
- "tasks": they are giving work to one or more people.
- "question": they are asking about status, who is doing what, what is pending, payments, etc.
- "other": greeting, thanks, or anything else.

For "tasks", make ONE task per person per action. For each task give:
- assignee_id: the id of the person from the list above (match names loosely, e.g. "Ayush bhai" -> Ayush;
  a role like "decorator wale" -> the Decorator vendor). Use null if nobody in the list matches.
- assignee_name: the name as the planner said it.
- task: a short clear instruction in English, starting with a verb, max 20 words.
- task_original: the same instruction in the language the planner used (in the script they would normally write it;
  Hindi may be in Roman letters). If they spoke English, repeat the English.
- due: deadline as "YYYY-MM-DD HH:MM" (IST) if said or implied: "by tomorrow evening" -> tomorrow 18:00,
  "by Friday" -> the coming Friday 18:00, "today" -> today 20:00, "in 2 hours" -> now + 2 hours,
  "before the wedding" -> the day before that wedding 18:00. null if no deadline at all.
- needs_proof: true if the planner asks for a photo/proof, or if the task produces something physical that the
  planner would want to see (a setup, a sample, a delivery, printed items). false for calls, confirmations, sharing info.

Return ONLY JSON:
{{"intent": "...", "transcript": "exact words heard or read, in the original language",
  "language": "language name", "tasks": [ ... ], "question": "the question in English, if intent is question"}}

Planner's text message (may be empty): {text or '(none - see voice note)'}"""
    return _ask_gemini(prompt, audio=audio)


def understand_member(text, audio, open_tasks):
    """Team member/vendor message -> {"transcript", "english", "done_task_id", "language"}"""
    tasks = "\n".join(f"- #{t['id']}: {t['task']}" for t in open_tasks) or "(no open tasks)"
    prompt = f"""A team member or vendor of an Indian wedding planner sent a WhatsApp message (text or voice note,
any Indian language or a mix). Their open tasks are:
{tasks}

Return ONLY JSON:
{{"transcript": "exact words in the original language",
  "language": "language name",
  "english": "one or two line English summary for the planner",
  "done_task_id": the task number they say is finished/completed (e.g. "ho gaya", "done", "confirm kar diya"),
                  or null if they are not saying a task is done}}

Their text message (may be empty): {text or '(none - see voice note)'}"""
    return _ask_gemini(prompt, audio=audio)


def answer_question(question, snapshot, now):
    """Answer from the planner's own data only. Returns plain WhatsApp-style text."""
    prompt = f"""You are a wedding planner's assistant. Answer the planner's question using ONLY the data below.
Current time (IST): {now.strftime('%Y-%m-%d %H:%M')}.
Rules: WhatsApp style, short (max 10 lines), use names, task numbers like #12, deadlines in a friendly format
("Fri 6 PM"). Reply in the same language the question was asked in. If the data does not contain the answer,
say you don't have that information. Never invent tasks or people.

DATA (JSON):
{json.dumps(snapshot, ensure_ascii=False)}

QUESTION: {question}"""
    return _ask_gemini(prompt, want_json=False)
