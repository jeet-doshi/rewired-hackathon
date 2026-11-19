"""
app.py - the web server (Flask). Start it with:  py app.py   then open http://localhost:5000

Pages and addresses:
  /                      landing page + planner SIGN UP form
  /login                 planner types their number -> magic link sent to their WhatsApp
  /w/<token>             the planner's DASHBOARD (the secret token in the link is the "magic link")
  /w/<token>/sim         WhatsApp SIMULATOR: act as any team member on screen (demo fallback + testing)
  /whatsapp              Twilio sends every real incoming WhatsApp message here (the "webhook")
  /proof/<id>/<token>    shows a photo proof
"""
from dotenv import load_dotenv
load_dotenv()  # read keys from .env before anything else

import os
import hmac
import threading
from flask import Flask, request, render_template, redirect, url_for, abort, Response, jsonify

import db
import ai
import bot
import voice
import messaging

app = Flask(__name__)
db.init()
bot.start_reminder_thread()


def planner_or_404(token):
    planner = db.planner_by_token(token)
    if not planner:
        abort(404)
    return planner


# ---------- landing, signup, login ----------

@app.get("/")
def home():
    return render_template("home.html")


@app.post("/signup")
def signup():
    f = request.form
    weddings = []
    for i in range(1, 5):
        name = f.get(f"w{i}_name", "").strip()
        if name:
            weddings.append({"name": name, "date": f.get(f"w{i}_date", ""), "venue": f.get(f"w{i}_venue", "").strip()})
    phone = db.normalise_phone(f.get("phone"))
    if not f.get("name") or not f.get("business") or len(phone) < 11 or not weddings:
        return render_template("home.html", error="Please fill your name, business, WhatsApp number and at least one wedding.",
                               form=f), 400
    planner = db.create_planner(f["name"].strip(), f["business"].strip(), phone, weddings)
    bot.send(planner["id"], planner["phone"],
             f"🎉 Welcome to WeWED, {planner['name']}!\n\n" + bot.help_text_planner(planner))
    return redirect(url_for("dashboard", token=planner["token"], welcome=1))


@app.route("/login", methods=["GET", "POST"])
def login():
    sent = False
    if request.method == "POST":
        planner = db.planner_by_phone(db.normalise_phone(request.form.get("phone")))
        if planner:  # we always show the same message, so nobody can test which numbers exist
            bot.send(planner["id"], planner["phone"], f"🔐 Your WeWED dashboard link:\n{bot.dashboard_link(planner)}")
        sent = True
    return render_template("login.html", sent=sent)


@app.get("/demo")
def demo():
    p = db.one("SELECT * FROM planners WHERE is_demo = 1") or db.seed_demo()
    return redirect(url_for("dashboard", token=p["token"]))


# ---------- dashboard ----------

@app.get("/w/<token>")
def dashboard(token):
    planner = planner_or_404(token)
    wedding_id = request.args.get("wedding", type=int)
    weddings = db.weddings_of(planner["id"])
    all_tasks = db.tasks_of(planner["id"])
    tasks = [t for t in all_tasks if not wedding_id or t["wedding_id"] == wedding_id]
    members = db.members_of(planner["id"])
    for m in members:
        m["open"] = sum(1 for t in all_tasks if t["assignee_id"] == m["id"] and t["status"] == "pending")
        m["overdue"] = sum(1 for t in all_tasks if t["assignee_id"] == m["id"] and db.is_overdue(t))
    for w in weddings:
        mine = [t for t in all_tasks if t["wedding_id"] == w["id"]]
        w["total"], w["done"] = len(mine), sum(1 for t in mine if t["status"] == "done")
        w["overdue"] = sum(1 for t in mine if db.is_overdue(t))
    for t in tasks:
        t["overdue"] = db.is_overdue(t)
        t["due_text"] = bot.fmt_due(t["due_at"])
    stats = {
        "open": sum(1 for t in all_tasks if t["status"] == "pending"),
        "overdue": sum(1 for t in all_tasks if db.is_overdue(t)),
        "done": sum(1 for t in all_tasks if t["status"] == "done"),
        "proofs": sum(1 for t in all_tasks if t["proof_mime"]),
    }
    names = {m["phone"]: m["name"] for m in members}
    feed = db.recent_messages(planner["id"], 30)
    for msg in feed:
        msg["who"] = names.get(msg["phone"], msg["phone"])
    return render_template("dashboard.html", planner=planner, weddings=weddings, tasks=tasks, members=members,
                           stats=stats, feed=feed, wedding_id=wedding_id, welcome=request.args.get("welcome"),
                           invite=bot.invite_text(planner), link=bot.dashboard_link(planner),
                           ai_ready=ai.is_configured(), twilio_ready=messaging.is_configured(),
                           voice_ready=voice.is_configured(), languages=voice.LANGUAGE_NAMES,
                           sandbox_join=os.environ.get("TWILIO_SANDBOX_JOIN", "") if messaging.twilio_configured() else "",
                           sandbox_number=bot.bot_number(), provider=messaging.provider_name())


@app.post("/w/<token>/task/new")
def task_new(token):
    """Planner can also add a task by hand from the dashboard; it goes out on WhatsApp the same way."""
    planner = planner_or_404(token)
    f = request.form
    due = f.get("due", "").replace("T", " ") or None
    assignee = f.get("assignee_id", type=int)
    task = db.create_task(planner["id"], f.get("wedding_id", type=int), assignee, f["task"].strip(), f["task"].strip(),
                          due, f.get("needs_proof") == "on", "dashboard")
    if task["assignee_id"]:
        bot.notify_assignee(planner, task)
    return redirect(url_for("dashboard", token=token, wedding=request.args.get("wedding")))


@app.post("/w/<token>/task/<int:task_id>/<action>")
def task_action(token, task_id, action):
    planner = planner_or_404(token)
    task = db.get_task(task_id)
    if not task or task["planner_id"] != planner["id"]:
        abort(404)
    if action == "done":
        db.mark_done(task_id, note="marked by planner on dashboard")
    elif action == "reopen":
        db.update_task(task_id, status="pending", done_at=None, reminders_sent=0, escalated=0,
                       last_reminded_at=db.now_str())
    elif action == "nudge" and task["assignee_id"]:
        bot.send_reminder(task, planner)
    elif action == "assign":
        assignee = request.form.get("assignee_id", type=int)
        db.update_task(task_id, assignee_id=assignee, last_reminded_at=db.now_str())
        if assignee:
            bot.notify_assignee(planner, db.get_task(task_id))
    return redirect(url_for("dashboard", token=token, wedding=request.args.get("wedding")))


@app.post("/w/<token>/ask")
def ask(token):
    planner = planner_or_404(token)
    question = (request.json or {}).get("q", "").strip()
    if not question:
        return jsonify(answer="Please type a question.")
    if not ai.is_configured():
        return jsonify(answer="AI is not set up yet (missing GEMINI_API_KEY).")
    try:
        return jsonify(answer=ai.answer_question(question, bot.snapshot(planner), db.now()))
    except Exception as e:
        return jsonify(answer=f"Sorry, AI error: {e}")


@app.post("/w/<token>/reset")
def reset(token):
    planner = planner_or_404(token)
    if not planner["is_demo"]:
        abort(403)
    db.reset_demo()
    return redirect(url_for("dashboard", token="demo"))


@app.get("/proof/<int:task_id>/<token>")
def proof(task_id, token):
    planner = planner_or_404(token)
    task = db.one("SELECT proof_image, proof_mime, planner_id FROM tasks WHERE id = ?", (task_id,))
    if not task or task["planner_id"] != planner["id"] or not task["proof_image"]:
        abort(404)
    return Response(bytes(task["proof_image"]), mimetype=task["proof_mime"] or "image/jpeg")


@app.get("/audio/<int:clip_id>/<sig>")
def audio(clip_id, sig):
    """Plays a stored voice note. Twilio fetches generated voice notes from here to deliver them on WhatsApp."""
    if not hmac.compare_digest(sig, messaging.clip_signature(clip_id)):
        abort(404)
    clip = db.get_clip(clip_id)
    if not clip:
        abort(404)
    return Response(bytes(clip["data"]), mimetype=(clip["mime"] or "audio/mpeg").split(";")[0])


@app.template_filter("clip_url")
def clip_url_filter(media):
    """'audio:12' -> a relative link the browser can play."""
    clip_id = int(media.split(":")[1])
    return f"/audio/{clip_id}/{messaging.clip_signature(clip_id)}"


# ---------- WhatsApp simulator (same bot logic, messages shown on screen) ----------

@app.route("/w/<token>/sim", methods=["GET", "POST"])
def simulator(token):
    planner = planner_or_404(token)
    members = db.members_of(planner["id"])
    phone = request.values.get("phone") or planner["phone"]
    error = None
    if request.method == "POST":
        media = []
        upload = request.files.get("file")
        if upload and upload.filename:
            mime = upload.mimetype or "application/octet-stream"
            media.append({"data": upload.read(), "mime": mime})
        try:
            bot.handle_incoming(phone, request.form.get("body", ""), media)
        except Exception as e:
            error = str(e)
            print("Simulator error:", e)
        if not error:
            return redirect(url_for("simulator", token=token, phone=phone))
    me = next((m for m in members if m["phone"] == phone), None)
    return render_template("simulator.html", planner=planner, members=members, phone=phone, me=me,
                           messages=db.messages_for_phone(phone), error=error)


# ---------- real WhatsApp (Twilio webhook) ----------

def _process_twilio(phone, body, media_refs):
    """Runs in the background so Twilio gets an instant 'OK' (Twilio gives up after 15 seconds)."""
    try:
        media = [{"data": messaging.download_twilio_media(url), "mime": mime} for url, mime in media_refs]
        bot.handle_incoming(phone, body, media)
    except Exception as e:
        print("Error handling WhatsApp message:", e)
        member = db.member_by_phone(phone)
        bot.send(member["planner_id"] if member else None, phone,
                 "😕 Sorry, something went wrong reading that. Please try again or send it as text.")


@app.post("/whatsapp")
def whatsapp_webhook():
    phone = request.form.get("From", "").replace("whatsapp:", "")
    body = request.form.get("Body", "")
    count = int(request.form.get("NumMedia", "0") or 0)
    media_refs = [(request.form.get(f"MediaUrl{i}"), request.form.get(f"MediaContentType{i}", "")) for i in range(count)]
    threading.Thread(target=_process_twilio, args=(phone, body, media_refs), daemon=True).start()
    return Response("<Response></Response>", mimetype="text/xml")


# ---------- real WhatsApp (Meta WhatsApp Cloud API webhook) ----------

@app.get("/meta")
def meta_verify():
    """Meta checks our webhook once: it sends a secret word, we prove we know it by echoing the challenge."""
    if (request.args.get("hub.mode") == "subscribe"
            and request.args.get("hub.verify_token") == os.environ.get("META_VERIFY_TOKEN", "wewed-verify-2026")):
        return request.args.get("hub.challenge", "")
    abort(403)


_seen_meta_ids = set()


def _process_meta(msg):
    """One incoming WhatsApp message from Meta -> our bot (runs in the background)."""
    phone = "+" + msg.get("from", "")
    try:
        kind = msg.get("type")
        body, media = "", []
        if kind == "text":
            body = msg["text"]["body"]
        elif kind in ("audio", "image", "document", "video"):
            part = msg[kind]
            media = [{"data": messaging.download_meta_media(part["id"]), "mime": part.get("mime_type", "")}]
            body = part.get("caption", "")
        elif kind == "button":
            body = msg["button"].get("text", "")
        else:
            body = ""
        bot.handle_incoming(phone, body, media)
    except Exception as e:
        print("Error handling Meta WhatsApp message:", e)
        member = db.member_by_phone(phone)
        bot.send(member["planner_id"] if member else None, phone,
                 "😕 Sorry, something went wrong reading that. Please try again or send it as text.")


@app.post("/meta")
def meta_webhook():
    """Meta sends every incoming WhatsApp message (and delivery receipts, which we ignore) here."""
    data = request.get_json(silent=True) or {}
    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            for msg in change.get("value", {}).get("messages", []):
                if msg.get("id") in _seen_meta_ids:  # Meta sometimes delivers the same message twice
                    continue
                _seen_meta_ids.add(msg.get("id"))
                threading.Thread(target=_process_meta, args=(msg,), daemon=True).start()
    return "ok"  # answer Meta fast; real work happens in the background


@app.get("/privacy")
def privacy():
    """Privacy policy + data deletion instructions (Meta requires these links to publish the app)."""
    return render_template("privacy.html")


@app.get("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
