"""
bot.py - the WhatsApp assistant's brain: what to do with each incoming message.

Every message (from real WhatsApp via Twilio, or from the on-screen simulator) goes to handle_incoming().

Who is sending?
  - Unknown number      -> must send "JOIN <code> <name>" to enter a planner's workspace
  - The planner         -> voice note / text becomes tasks -> "Which wedding? 1-4" -> tasks sent to people
                           (or a question like "what's pending?" gets answered from the database)
  - Team member/vendor  -> "DONE 12" (+ photo if proof needed) marks a task done and tells the planner;
                           anything else (even a voice note) is understood and passed to the planner

The reminder loop (bottom of file) runs every 30 seconds and nudges people until they reply DONE.
"""
import os
import re
import time
import threading
import datetime as dt

import db
import ai
import voice
import messaging

NUMBER_EMOJI = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
DONE_WORDS = r"(done|ho gaya|ho gya|hogaya|hogya|completed|complete|finished|kar diya|ayitu|aaythu|mudinchu)"


# ---------- small helpers ----------

def fmt_due(due_at):
    """'2026-11-22 18:00' -> 'Sat 22 Nov, 6:00 PM'"""
    d = db.parse_time(due_at)
    if not d:
        return "no deadline"
    return d.strftime("%a %d %b, ") + d.strftime("%I:%M %p").lstrip("0")


def send(planner_id, phone, text, media_url=None):
    messaging.send(planner_id, phone, text, media_url)


def dashboard_link(planner):
    return f"{messaging.public_url()}/w/{planner['token']}"


def bot_number():
    """The WhatsApp number people message (Meta test number, or Twilio's)."""
    if messaging.meta_configured():
        return os.environ.get("META_DISPLAY_NUMBER", "")
    return os.environ.get("TWILIO_WHATSAPP_FROM", "+14155238886")


def invite_text(planner):
    sandbox = "" if messaging.meta_configured() else os.environ.get("TWILIO_SANDBOX_JOIN", "")
    number = bot_number()
    if not sandbox:
        return (f"You're invited to *{planner['business']}* on WeWED, our wedding task assistant.\n"
                f"Send this on WhatsApp to {number}: *JOIN {planner['join_code']} Your Name*\n"
                f"https://wa.me/{number.lstrip('+').replace(' ', '')}?text=JOIN%20{planner['join_code']}%20")
    step1 = f"1) Send *{sandbox}* to {number} on WhatsApp (one-time).\n" if sandbox else ""
    return (f"You're invited to *{planner['business']}* on WeWED, our wedding task assistant.\n"
            f"{step1}{'2' if sandbox else '1'}) Then send: *JOIN {planner['join_code']} Your Name*")


def help_text_planner(planner):
    return ("🙏 I'm your WeWED assistant.\n\n"
            "🎤 Send me a *voice note* or text in any language, e.g.\n"
            "_\"Ayush, confirm the buses by tomorrow 5 PM. Imran, send a photo of the stage mock-up by Friday.\"_\n"
            "I'll ask which wedding, then send each person their task and keep reminding them.\n\n"
            "❓ Ask me anything: _\"What's pending for Sharma wedding?\"_\n"
            f"🔑 Team join code: *{planner['join_code']}*  (send *INVITE* for a ready message)\n"
            f"📊 Dashboard: {dashboard_link(planner)}")


def help_text_member(member):
    return (f"🙏 Hi {member['name']}! Your tasks come here.\n"
            "✅ Reply *DONE 12* when task #12 is finished (attach the photo if it asks for proof).\n"
            "📋 Send *TASKS* to see what's pending.\n"
            "🎤 Or just send a voice note — I'll understand it and tell the planner.")


def snapshot(planner):
    """Everything about a workspace as simple data, for the AI to answer questions from."""
    tasks = db.tasks_of(planner["id"])
    return {
        "business": planner["business"],
        "weddings": [{"name": w["name"], "date": w["date"], "venue": w["venue"]} for w in db.weddings_of(planner["id"])],
        "people": [{"name": m["name"], "role": m["role"], "does": m["specialty"]} for m in db.members_of(planner["id"])],
        "tasks": [{"id": t["id"], "wedding": t["wedding_name"], "assigned_to": t["assignee_name"] or "nobody yet",
                   "task": t["task"], "due": t["due_at"], "status": t["status"],
                   "overdue": db.is_overdue(t), "reminders_sent": t["reminders_sent"],
                   "photo_proof_received": bool(t["proof_mime"]), "completed_at": t["done_at"]} for t in tasks],
    }


# ---------- entry point ----------

def handle_incoming(phone, body, media):
    """phone like '+919845012345'; body = text; media = list of {"data": bytes, "mime": "audio/ogg"}."""
    body = (body or "").strip()
    audio = next(((m["data"], m["mime"]) for m in media if m["mime"].startswith("audio")), None)
    image = next((m for m in media if m["mime"].startswith("image")), None)
    member = db.member_by_phone(phone)
    planner = db.get_planner(member["planner_id"]) if member else None
    kind = "image" if image else ""

    # Voice note: keep a copy, then Sarvam turns it into text (+ detects the language)
    voice_info = None
    if audio:
        kind = f"audio:{db.save_clip(audio[0], audio[1])}"
        if voice.is_configured():
            transcript, lang = voice.transcribe(audio[0], audio[1])
            voice_info = {"transcript": transcript, "lang": lang}
            body = (body + " " + transcript).strip()
            audio = None  # from here on, everyone works with the text
    db.log_message(planner["id"] if planner else None, phone, "in", body, kind)

    if re.match(r"^join\b", body, re.I):
        return handle_join(phone, body)
    if body.strip().upper() == "DELETE MY DATA":  # privacy: anyone can remove themselves
        if member and member["role"] != "planner":
            db.query("UPDATE tasks SET assignee_id = NULL WHERE assignee_id = ?", (member["id"],))
            db.query("DELETE FROM members WHERE phone = ? AND role != 'planner'", (phone,))
        db.query("DELETE FROM messages WHERE phone = ?", (phone,))
        db.clear_state(phone)
        return messaging.send(None, phone, "🗑️ Done. Your profile and messages were deleted from WeWED.")
    if not member or not planner:
        return send(None, phone, "👋 Welcome to WeWED! To join your planner's workspace, send:\n"
                                 "*JOIN <code> <your name>*  e.g. JOIN SHUBH-DEC Ayush")

    state = db.get_state(phone)
    if state and state["kind"] in ("pick_role", "ask_specialty", "ask_language"):
        return handle_onboarding(member, planner, body, state)
    if member["role"] == "planner":
        return planner_flow(member, planner, body, audio, image, state, voice_info)
    return member_flow(member, planner, body, audio, image, state, voice_info)


# ---------- joining a workspace with the join code ----------

def handle_join(phone, body):
    parts = body.split(None, 2)
    code = parts[1] if len(parts) > 1 else ""
    name = parts[2].strip() if len(parts) > 2 else ""
    planner = db.planner_by_code(code)
    if not planner:
        return send(None, phone, f"❌ I couldn't find a workspace with code *{code or '?'}*. "
                                 "Please check the code your planner shared.")
    if phone == planner["phone"]:
        return send(planner["id"], phone, "You're the planner of this workspace 🙂\n\n" + help_text_planner(planner))
    db.remove_phone_from_planner(planner["id"], phone)  # re-joining replaces the old entry
    member = db.add_member(planner["id"], name or "New member", phone, "team", "")
    db.set_state(phone, "pick_role", {"member_id": member["id"]})
    send(planner["id"], phone,
         f"🎉 Welcome{', ' + name if name else ''}! You've joined *{planner['business']}*.\n\n"
         "Are you:\n1️⃣ Part of the planner's team\n2️⃣ A vendor (decor, catering, photo, etc.)\nReply 1 or 2.")


def handle_onboarding(member, planner, body, state):
    phone = member["phone"]
    if state["kind"] == "pick_role":
        if body.strip() not in ("1", "2"):
            return send(planner["id"], phone, "Please reply *1* (team) or *2* (vendor).")
        role = "team" if body.strip() == "1" else "vendor"
        db.update_member(member["id"], role=role)
        db.set_state(phone, "ask_specialty", {"member_id": member["id"]})
        question = ("What do you supply? (e.g. Decor, Catering, Photography)" if role == "vendor"
                    else "What do you handle? (e.g. Logistics, Guests, Vendors)")
        return send(planner["id"], phone, question)
    if state["kind"] == "ask_specialty":
        db.update_member(member["id"], specialty=body.strip()[:60] or "-")
        db.set_state(phone, "ask_language", {"member_id": member["id"]})
        options = "\n".join(f"{i}. {name}" for i, (code, name) in enumerate(voice.LANGUAGES, 1))
        return send(planner["id"], phone, f"🗣 Which language should I talk to you in?\n{options}\nReply with the number.")
    # ask_language: the language the user CHOOSES; their tasks + voice notes will come in it
    choice = body.strip()
    if not choice.isdigit() or not 1 <= int(choice) <= len(voice.LANGUAGES):
        return send(planner["id"], phone, f"Please reply a number from 1 to {len(voice.LANGUAGES)}.")
    code, lang_name = voice.LANGUAGES[int(choice) - 1]
    db.update_member(member["id"], language=code)
    db.clear_state(phone)
    member = db.get_member(member["id"])
    send(planner["id"], phone, f"✅ All set! I'll send your tasks in {lang_name}, with a voice note.\n\n"
         + help_text_member(member))
    send(planner["id"], planner["phone"],
         f"🆕 *{member['name']}* joined your workspace as {member['role']} ({member['specialty']}, prefers {lang_name}).")


# ---------- planner ----------

def planner_flow(member, planner, body, audio, image, state, voice_info=None):
    phone = member["phone"]
    is_voice = bool(audio or voice_info)
    upper = body.upper()

    # Waiting for "which wedding?" answer
    if state and state["kind"] == "pick_wedding" and re.fullmatch(r"\d", body):
        return assign_to_wedding(planner, phone, int(body), state["data"])

    if upper in ("HI", "HELLO", "HELP", "MENU", "START"):
        return send(planner["id"], phone, help_text_planner(planner))
    if upper in ("DASHBOARD", "LINK"):
        return send(planner["id"], phone, f"📊 Your dashboard: {dashboard_link(planner)}")
    if upper in ("INVITE", "CODE"):
        send(planner["id"], phone, "Forward this message to your team and vendors 👇")
        return send(planner["id"], phone, invite_text(planner))
    if not body and not audio:
        return send(planner["id"], phone, "I can read text and voice notes 🙂 Photos from planners aren't supported yet.")
    if not ai.is_configured():
        return send(planner["id"], phone, "⚠️ AI is not set up yet (missing GEMINI_API_KEY).")

    result = ai.understand_planner(body, audio, db.members_of(planner["id"]), db.weddings_of(planner["id"]), db.now())
    transcript = voice_info["transcript"] if voice_info else (result.get("transcript") or body).strip()
    intent = result.get("intent")
    valid_ids = {m["id"] for m in db.members_of(planner["id"]) if m["role"] != "planner"}

    if intent == "tasks" and result.get("tasks"):
        tasks = []
        for t in result["tasks"]:
            assignee = t.get("assignee_id")
            tasks.append({
                "assignee_id": assignee if assignee in valid_ids else None,
                "assignee_name": t.get("assignee_name") or "?",
                "task": (t.get("task") or "").strip(),
                "task_original": (t.get("task_original") or t.get("task") or "").strip(),
                "task_local": (t.get("task_local") or "").strip(),
                "due": t.get("due") if db.parse_time(t.get("due")) else None,
                "needs_proof": bool(t.get("needs_proof")),
            })
        db.set_state(phone, "pick_wedding", {"tasks": tasks, "transcript": transcript,
                                             "source": "voice" if is_voice else "text"})
        lines = []
        for i, t in enumerate(tasks, 1):
            who = db.get_member(t["assignee_id"])["name"] if t["assignee_id"] else f"❓{t['assignee_name']} (not in team)"
            proof = " 📷" if t["needs_proof"] else ""
            lines.append(f"{i}. *{who}*: {t['task']} — ⏰ {fmt_due(t['due'])}{proof}")
        weddings = db.weddings_of(planner["id"])
        options = "\n".join(f"{NUMBER_EMOJI[i] if i < 10 else i} {w['name']} ({w['date']})"
                            for i, w in enumerate(weddings, 1))
        heard = f"🎤 I heard: _{transcript}_\n\n" if is_voice else ""
        return send(planner["id"], phone,
                    f"{heard}📝 *{len(tasks)} task(s):*\n" + "\n".join(lines) +
                    f"\n\n💍 *Which wedding is this for?*\n{options}\n\nReply with the number (0 to cancel).")

    if intent == "question":
        question = transcript if is_voice else body
        answer = ai.answer_question(question, snapshot(planner), db.now())
        heard = f"🎤 _{transcript}_\n\n" if is_voice else ""
        send(planner["id"], phone, heard + answer)
        if voice_info:  # asked by voice -> also answer by voice, in the same language
            spoken = voice.speak(answer.replace("*", "").replace("_", ""), voice_info["lang"])
            if spoken:
                messaging.send_voice(planner["id"], phone, spoken)
        return

    heard = f"🎤 I heard: _{transcript}_\n\n" if is_voice else ""
    send(planner["id"], phone, heard + "I didn't find a task or question in that. Try:\n"
         "_\"Ayush, confirm the buses by tomorrow 5 PM\"_ or _\"What's pending for Sharma wedding?\"_")


def assign_to_wedding(planner, phone, choice, data):
    weddings = db.weddings_of(planner["id"])
    if choice == 0:
        db.clear_state(phone)
        return send(planner["id"], phone, "❌ Cancelled. Nothing was sent.")
    if choice > len(weddings):
        return send(planner["id"], phone, f"Please reply a number from 1 to {len(weddings)} (or 0 to cancel).")
    wedding = weddings[choice - 1]
    db.clear_state(phone)
    lines, unassigned = [], 0
    for t in data["tasks"]:
        task = db.create_task(planner["id"], wedding["id"], t["assignee_id"], t["task"], t["task_original"],
                              t["due"], t["needs_proof"], data.get("source", "text"), task_local=t.get("task_local"))
        if task["assignee_id"]:
            notify_assignee(planner, task)
            lines.append(f"#{task['id']} → {task['assignee_name']}")
        else:
            unassigned += 1
            lines.append(f"#{task['id']} → nobody yet ({t['assignee_name']} hasn't joined)")
    extra = (f"\n\n⚠️ {unassigned} task(s) have no one to send to. Share your join code *{planner['join_code']}* "
             "or assign them on the dashboard.") if unassigned else ""
    send(planner["id"], phone, f"✅ Saved for *{wedding['name']}*:\n" + "\n".join(lines) +
         "\n\nI'll keep reminding everyone until they reply DONE." + extra)


def notify_assignee(planner, task):
    """Text message with the task (English + their language), then a voice note in their chosen language."""
    local = (task.get("task_local") or "").strip()
    lang = task.get("assignee_language") or "en-IN"
    local_line = f"\n🗣 _{local}_" if local and local.lower() != task["task"].strip().lower() else ""
    proof = "\n📷 *Photo proof needed* — send the photo with your DONE reply." if task["needs_proof"] else ""
    send(planner["id"], task["assignee_phone"],
         f"🔔 *New task from {planner['name']}* ({planner['business']})\n"
         f"💍 {task['wedding_name']} wedding\n\n"
         f"*#{task['id']}: {task['task']}*{local_line}\n"
         f"⏰ Due: {fmt_due(task['due_at'])}{proof}\n\n"
         f"Reply *DONE {task['id']}* when finished (or just send a voice note).")
    # They talk, not type: give them the task as a voice note too (only if we have it in their language)
    spoken_text = local if local else (task["task"] if lang == "en-IN" else "")
    if spoken_text:
        spoken = voice.speak(f"{planner['name']}: {spoken_text}", lang)
        if spoken:
            messaging.send_voice(planner["id"], task["assignee_phone"], spoken)


# ---------- team members and vendors ----------

def member_flow(member, planner, body, audio, image, state, voice_info=None):
    phone = member["phone"]
    upper = body.upper()
    open_tasks = db.open_tasks_of_member(member["id"])

    # Waiting for a photo for a specific task
    if state and state["kind"] == "await_proof":
        task = db.get_task(state["data"]["task_id"])
        if image and task and task["status"] == "pending":
            return complete_task(task, member, planner, image=image)
        if upper == "CANCEL":
            db.clear_state(phone)
            return send(planner["id"], phone, "OK, cancelled.")
        if not audio and not voice_info and not re.match(r"^" + DONE_WORDS, body, re.I):
            return send(planner["id"], phone, f"📷 Please send the photo for task #{state['data']['task_id']} "
                                              "(or CANCEL).")

    if upper in ("HI", "HELLO", "HELP", "MENU", "START"):
        return send(planner["id"], phone, help_text_member(member))
    if upper in ("TASKS", "MY TASKS", "LIST", "PENDING"):
        return send(planner["id"], phone, task_list_text(open_tasks))

    # "DONE 12" / "done" / "ho gaya 12"  (also works as a photo caption)
    match = re.match(r"^\s*" + DONE_WORDS + r"\b\W*#?\s*(\d+)?", body, re.I)
    if match:
        return done_flow(member, planner, open_tasks, match.group(2), image)

    if image:
        return done_flow(member, planner, [t for t in open_tasks if t["needs_proof"]] or open_tasks, None, image)

    if (audio or body) and ai.is_configured():
        result = ai.understand_member(body, audio, open_tasks)
        done_id = result.get("done_task_id")
        if done_id and any(t["id"] == int(done_id) for t in open_tasks):
            return done_flow(member, planner, open_tasks, str(done_id), None)
        # Not a "done" message: pass it to the planner so nothing is lost
        transcript = voice_info["transcript"] if voice_info else (result.get("transcript") or body)
        english = result.get("english") or transcript
        original = f"\n🗣 _{transcript}_" if transcript.strip().lower() != english.strip().lower() else ""
        send(planner["id"], planner["phone"],
             f"💬 *{member['name']}* ({member['specialty'] or member['role']}) says:\n{english}{original}")
        return send(planner["id"], phone, f"👍 Got it — passed this to {planner['name']}.")

    send(planner["id"], phone, help_text_member(member))


def task_list_text(open_tasks):
    if not open_tasks:
        return "🎉 You have no pending tasks."
    lines = [f"#{t['id']} {t['task']} — {t['wedding_name']} — ⏰ {fmt_due(t['due_at'])}"
             f"{' 📷' if t['needs_proof'] else ''}{' ⚠️ OVERDUE' if db.is_overdue(t) else ''}"
             for t in open_tasks]
    return "📋 *Your pending tasks:*\n" + "\n".join(lines) + "\n\nReply *DONE <number>* when finished."


def done_flow(member, planner, candidates, task_number, image):
    phone = member["phone"]
    if task_number:
        task = next((t for t in db.open_tasks_of_member(member["id"]) if t["id"] == int(task_number)), None)
        if not task:
            return send(planner["id"], phone, f"I couldn't find an open task #{task_number} for you.\n\n"
                        + task_list_text(db.open_tasks_of_member(member["id"])))
    elif len(candidates) == 1:
        task = candidates[0]
    elif not candidates:
        return send(planner["id"], phone, "🎉 You have no pending tasks.")
    else:
        return send(planner["id"], phone, "Which task is finished? Reply *DONE <number>*"
                    f"{' with the photo' if image else ''}:\n\n" + task_list_text(candidates))
    if task["needs_proof"] and not image:
        db.set_state(phone, "await_proof", {"task_id": task["id"]})
        return send(planner["id"], phone, f"📷 Task #{task['id']} needs photo proof. Please send the photo now.")
    complete_task(task, member, planner, image=image)


def complete_task(task, member, planner, image=None):
    db.mark_done(task["id"], note="via WhatsApp", image=image["data"] if image else None,
                 mime=image["mime"] if image else None)
    db.clear_state(member["phone"])
    send(planner["id"], member["phone"], f"✅ Marked #{task['id']} as done. Thank you!")
    proof_url = f"{messaging.public_url()}/proof/{task['id']}/{planner['token']}" if image else None
    send(planner["id"], planner["phone"],
         f"✅ *#{task['id']} done* by {member['name']}\n💍 {task['wedding_name']}\n{task['task']}"
         + ("\n📷 Photo proof attached" if image else ""), media_url=proof_url)


# ---------- reminders (plain code, no AI) ----------

def reminder_settings():
    return int(os.environ.get("REMINDER_MINUTES", "2")), int(os.environ.get("MAX_REMINDERS", "3"))


def send_reminder(task, planner):
    overdue = db.is_overdue(task)
    n = (task["reminders_sent"] or 0) + 1
    send(planner["id"], task["assignee_phone"],
         f"⏰ *Reminder{' — OVERDUE' if overdue else ''}* from {planner['business']}\n"
         f"*#{task['id']}: {task['task']}*\n💍 {task['wedding_name']} • Due {fmt_due(task['due_at'])}\n"
         f"Reply *DONE {task['id']}*{' with the photo' if task['needs_proof'] else ''} when finished.")
    db.update_task(task["id"], reminders_sent=n, last_reminded_at=db.now_str())


def run_reminders():
    """Called every 30 seconds. For each open task decide: remind now? escalate to planner?"""
    every, max_reminders = reminder_settings()
    now = db.now()
    for task in db.all_open_tasks():
        if task["source"] == "seed":  # demo display data, never messages anyone
            continue
        planner = db.get_planner(task["planner_id"])
        if not planner:
            continue
        if (task["reminders_sent"] or 0) >= max_reminders:
            if not task["escalated"]:
                send(planner["id"], planner["phone"],
                     f"⚠️ *{task['assignee_name']}* hasn't confirmed *#{task['id']}* after "
                     f"{task['reminders_sent']} reminders:\n{task['task']} ({task['wedding_name']})\n"
                     f"Due {fmt_due(task['due_at'])}. Maybe give them a call?")
                db.update_task(task["id"], escalated=1)
            continue
        last = db.parse_time(task["last_reminded_at"]) or db.parse_time(task["created_at"]) or now
        due = db.parse_time(task["due_at"])
        urgent = due is None or due - now < dt.timedelta(hours=24)
        gap = dt.timedelta(minutes=every if urgent else every * 3)  # closer deadline -> more frequent nudges
        if now - last >= gap:
            send_reminder(task, planner)


def start_reminder_thread():
    def loop():
        while True:
            try:
                run_reminders()
            except Exception as e:  # never let one bad task stop all reminders
                print("Reminder loop error:", e)
            time.sleep(30)
    threading.Thread(target=loop, daemon=True).start()
