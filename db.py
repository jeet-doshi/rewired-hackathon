"""
db.py - everything about STORING data.

- On the laptop we use a simple file database (SQLite, file "wewed.db").
- On the internet (Render) we use Postgres, because Render's disk is wiped on every redeploy.
  Render gives us a DATABASE_URL; if it exists we use Postgres, otherwise SQLite.
- The same SQL works for both. We write "?" for values; for Postgres we swap it to "%s".

Tables:
  planners  - one row per wedding-planning business (its workspace, join code, magic-link token)
  weddings  - the weddings a planner is running (we use 4 per month)
  members   - everyone in a workspace: the planner, team members, vendors (name + WhatsApp number)
  tasks     - every task: who, which wedding, deadline, status, reminders sent, photo proof
  messages  - log of every WhatsApp message in and out (shown on dashboard + simulator)
  states    - "what is the bot waiting for from this phone?" (e.g. waiting for a wedding number)
"""
import os
import json
import secrets
import sqlite3
import datetime as dt

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SQLITE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wewed.db")

# India time. We store times as plain text "YYYY-MM-DD HH:MM" in IST so they sort correctly.
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
FMT = "%Y-%m-%d %H:%M"

# Demo phone numbers start with this. Messages to them are only shown in the simulator, never sent.
SIMULATED_PREFIX = "+91000"


def now():
    return dt.datetime.now(IST).replace(tzinfo=None)


def now_str():
    return now().strftime(FMT)


def parse_time(text):
    """Turn "2026-11-20 18:00" back into a datetime (or None)."""
    try:
        return dt.datetime.strptime(text, FMT) if text else None
    except ValueError:
        return None


# ---------- low-level helpers ----------

def _connect():
    if DATABASE_URL:
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    conn = sqlite3.connect(SQLITE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql, params=()):
    """Run one SQL statement and return the rows as a list of dictionaries."""
    if DATABASE_URL:
        sql = sql.replace("?", "%s")
    conn = _connect()
    try:
        cur = conn.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()] if cur.description else []
        conn.commit()
        return rows
    finally:
        conn.close()


def one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None


SCHEMA = """
CREATE TABLE IF NOT EXISTS planners (id SERIAL PRIMARY KEY, name TEXT, business TEXT, phone TEXT,
  join_code TEXT UNIQUE, token TEXT UNIQUE, is_demo INTEGER DEFAULT 0, created_at TEXT);
CREATE TABLE IF NOT EXISTS weddings (id SERIAL PRIMARY KEY, planner_id INTEGER, name TEXT, date TEXT, venue TEXT);
CREATE TABLE IF NOT EXISTS members (id SERIAL PRIMARY KEY, planner_id INTEGER, name TEXT, phone TEXT,
  role TEXT, specialty TEXT, language TEXT DEFAULT 'en-IN', joined_at TEXT);
CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, planner_id INTEGER, wedding_id INTEGER, assignee_id INTEGER,
  task TEXT, task_original TEXT, task_local TEXT, due_at TEXT, needs_proof INTEGER DEFAULT 0, status TEXT DEFAULT 'pending',
  created_at TEXT, done_at TEXT, reminders_sent INTEGER DEFAULT 0, last_reminded_at TEXT, escalated INTEGER DEFAULT 0,
  proof_image BYTEA, proof_mime TEXT, done_note TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS messages (id SERIAL PRIMARY KEY, planner_id INTEGER, phone TEXT, direction TEXT,
  body TEXT, media TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS states (phone TEXT PRIMARY KEY, kind TEXT, data TEXT, at TEXT);
CREATE TABLE IF NOT EXISTS audio_clips (id SERIAL PRIMARY KEY, data BYTEA, mime TEXT, at TEXT)
"""


def init():
    """Create tables if missing, and create the demo workspace the first time."""
    schema = SCHEMA
    if not DATABASE_URL:  # SQLite spells two things differently
        schema = schema.replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT").replace("BYTEA", "BLOB")
    for statement in schema.split(";"):
        if statement.strip():
            query(statement)
    if not one("SELECT id FROM planners WHERE is_demo = 1"):
        seed_demo()


# ---------- planners / workspaces ----------

def normalise_phone(raw):
    """'98450 12345' -> '+919845012345'. Keeps numbers that already start with +."""
    digits = "".join(ch for ch in (raw or "") if ch.isdigit() or ch == "+")
    if digits.startswith("+"):
        return digits
    if len(digits) == 10:
        return "+91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return "+" + digits
    return "+" + digits if digits else ""


def make_join_code(business):
    """e.g. 'Shubh Events' -> 'SHUBH-K7Q'. Short enough to type on WhatsApp."""
    word = "".join(ch for ch in (business or "TEAM").split()[0].upper() if ch.isalnum())[:6] or "TEAM"
    return f"{word}-{secrets.token_hex(2).upper()[:3]}"


def create_planner(name, business, phone, weddings, is_demo=False, join_code=None, token=None):
    """Create a workspace: planner row + their weddings + the planner as a member."""
    phone = normalise_phone(phone)
    join_code = join_code or make_join_code(business)
    token = token or secrets.token_urlsafe(12)
    p = one("INSERT INTO planners (name, business, phone, join_code, token, is_demo, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
            (name, business, phone, join_code, token, 1 if is_demo else 0, now_str()))
    for w in weddings:
        query("INSERT INTO weddings (planner_id, name, date, venue) VALUES (?, ?, ?, ?)",
              (p["id"], w["name"], w.get("date", ""), w.get("venue", "")))
    add_member(p["id"], name, phone, "planner", "Wedding planner")
    return get_planner(p["id"])


def get_planner(planner_id):
    return one("SELECT * FROM planners WHERE id = ?", (planner_id,))


def planner_by_token(token):
    return one("SELECT * FROM planners WHERE token = ?", (token,))


def planner_by_code(code):
    return one("SELECT * FROM planners WHERE UPPER(join_code) = ?", ((code or "").upper(),))


def planner_by_phone(phone):
    return one("SELECT * FROM planners WHERE phone = ? ORDER BY id DESC", (phone,))


def weddings_of(planner_id):
    return query("SELECT * FROM weddings WHERE planner_id = ? ORDER BY date, id", (planner_id,))


def get_wedding(wedding_id):
    return one("SELECT * FROM weddings WHERE id = ?", (wedding_id,))


# ---------- members ----------

def add_member(planner_id, name, phone, role, specialty="", language="en-IN"):
    m = one("INSERT INTO members (planner_id, name, phone, role, specialty, language, joined_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) RETURNING id",
            (planner_id, name, phone, role, specialty, language, now_str()))
    return get_member(m["id"])


def get_member(member_id):
    return one("SELECT * FROM members WHERE id = ?", (member_id,))


def member_by_phone(phone):
    """The workspace this phone belongs to (most recent join wins)."""
    return one("SELECT * FROM members WHERE phone = ? ORDER BY id DESC", (phone,))


def members_of(planner_id):
    return query("SELECT * FROM members WHERE planner_id = ? ORDER BY "
                 "CASE role WHEN 'planner' THEN 0 WHEN 'team' THEN 1 ELSE 2 END, name", (planner_id,))


def update_member(member_id, **fields):
    for key, value in fields.items():
        query(f"UPDATE members SET {key} = ? WHERE id = ?", (value, member_id))


def remove_phone_from_planner(planner_id, phone):
    query("DELETE FROM members WHERE planner_id = ? AND phone = ? AND role != 'planner'", (planner_id, phone))


# ---------- tasks ----------

TASK_SELECT = """
SELECT t.*, m.name AS assignee_name, m.phone AS assignee_phone, m.role AS assignee_role,
       m.specialty AS assignee_specialty, m.language AS assignee_language, w.name AS wedding_name, w.date AS wedding_date
FROM tasks t
LEFT JOIN members m ON m.id = t.assignee_id
LEFT JOIN weddings w ON w.id = t.wedding_id
"""


def create_task(planner_id, wedding_id, assignee_id, task, task_original, due_at, needs_proof, source, task_local=None):
    """task = English; task_original = planner's own words; task_local = in the assignee's chosen language."""
    t = one("INSERT INTO tasks (planner_id, wedding_id, assignee_id, task, task_original, task_local, due_at, "
            "needs_proof, status, created_at, last_reminded_at, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?) RETURNING id",
            (planner_id, wedding_id, assignee_id, task, task_original, task_local, due_at, 1 if needs_proof else 0,
             now_str(), now_str(), source))
    return get_task(t["id"])


def get_task(task_id):
    return one(TASK_SELECT + " WHERE t.id = ?", (task_id,))


def tasks_of(planner_id, wedding_id=None):
    if wedding_id:
        return query(TASK_SELECT + " WHERE t.planner_id = ? AND t.wedding_id = ? ORDER BY t.status DESC, t.due_at, t.id",
                     (planner_id, wedding_id))
    return query(TASK_SELECT + " WHERE t.planner_id = ? ORDER BY t.status DESC, t.due_at, t.id", (planner_id,))


def open_tasks_of_member(member_id):
    return query(TASK_SELECT + " WHERE t.assignee_id = ? AND t.status = 'pending' ORDER BY t.due_at, t.id",
                 (member_id,))


def all_open_tasks():
    return query(TASK_SELECT + " WHERE t.status = 'pending' AND t.assignee_id IS NOT NULL")


def mark_done(task_id, note="", image=None, mime=None):
    query("UPDATE tasks SET status = 'done', done_at = ?, done_note = ? WHERE id = ?", (now_str(), note, task_id))
    if image:
        query("UPDATE tasks SET proof_image = ?, proof_mime = ? WHERE id = ?", (image, mime, task_id))


def update_task(task_id, **fields):
    for key, value in fields.items():
        query(f"UPDATE tasks SET {key} = ? WHERE id = ?", (value, task_id))


def is_overdue(task):
    due = parse_time(task.get("due_at"))
    return task.get("status") == "pending" and due is not None and due < now()


# ---------- message log + conversation state ----------

def log_message(planner_id, phone, direction, body, media=""):
    query("INSERT INTO messages (planner_id, phone, direction, body, media, at) VALUES (?, ?, ?, ?, ?, ?)",
          (planner_id, phone, direction, body, media, now_str()))


def messages_for_phone(phone, limit=60):
    rows = query("SELECT * FROM messages WHERE phone = ? ORDER BY id DESC LIMIT ?", (phone, limit))
    return list(reversed(rows))


def recent_messages(planner_id, limit=25):
    return query("SELECT * FROM messages WHERE planner_id = ? ORDER BY id DESC LIMIT ?", (planner_id, limit))


def set_state(phone, kind, data=None):
    query("DELETE FROM states WHERE phone = ?", (phone,))
    query("INSERT INTO states (phone, kind, data, at) VALUES (?, ?, ?, ?)",
          (phone, kind, json.dumps(data or {}), now_str()))


def get_state(phone):
    s = one("SELECT * FROM states WHERE phone = ?", (phone,))
    if s:
        s["data"] = json.loads(s["data"] or "{}")
    return s


def clear_state(phone):
    query("DELETE FROM states WHERE phone = ?", (phone,))


def save_clip(data, mime):
    """Store a voice note (incoming or generated) so it can be played back / sent via a link."""
    return one("INSERT INTO audio_clips (data, mime, at) VALUES (?, ?, ?) RETURNING id", (data, mime, now_str()))["id"]


def get_clip(clip_id):
    return one("SELECT * FROM audio_clips WHERE id = ?", (clip_id,))


# ---------- demo data (all synthetic) ----------

def seed_demo():
    """A realistic but fake planning business with 4 weddings, a team, vendors and some tasks."""
    today = now().date()

    def day(n):
        return (today + dt.timedelta(days=n)).strftime("%Y-%m-%d")

    def at(days, hour):
        return (dt.datetime.combine(today, dt.time(hour, 0)) + dt.timedelta(days=days)).strftime(FMT)

    planner_phone = normalise_phone(os.environ.get("DEMO_PLANNER_PHONE", "")) or SIMULATED_PREFIX + "0000001"
    p = create_planner(
        "Riya Kapoor", "Shubh Events", planner_phone, is_demo=True, join_code="SHUBH-DEC", token="demo",
        weddings=[
            {"name": "Sharma - Iyer", "date": day(5), "venue": "Bangalore Palace"},
            {"name": "Mehta - Rao", "date": day(12), "venue": "Taj West End"},
            {"name": "Khan - D'Souza", "date": day(19), "venue": "Leela Palace"},
            {"name": "Reddy - Nair", "date": day(26), "venue": "Windflower Resort, Mysuru"},
        ])
    pid = p["id"]
    sim = SIMULATED_PREFIX
    people = [
        ("Ayush", sim + "0000002", "team", "Logistics & venue", "hi-IN"),
        ("Rahul", sim + "0000003", "team", "Vendor coordination", "en-IN"),
        ("Neha", sim + "0000004", "team", "Guest hospitality", "kn-IN"),
        ("Imran (Gulmohar Decor)", sim + "0000005", "vendor", "Decorator", "hi-IN"),
        ("Suresh (Annapurna Caterers)", sim + "0000006", "vendor", "Caterer", "kn-IN"),
        ("Kavya (Click Studio)", sim + "0000007", "vendor", "Photographer", "ta-IN"),
        ("DJ Sonu", sim + "0000008", "vendor", "DJ & sound", "hi-IN"),
    ]
    ids = {}
    for name, phone, role, spec, lang in people:
        ids[name.split()[0]] = add_member(pid, name, phone, role, spec, lang)["id"]
    w = {x["name"].split()[0]: x["id"] for x in weddings_of(pid)}

    seed_tasks = [
        # (wedding, person, task, due, needs_proof, status)
        ("Sharma", "Imran", "Send photo of the mehendi stage mock-up", at(1, 18), 1, "pending"),
        ("Sharma", "Ayush", "Confirm 3 buses for baraat pickup from hotel", at(0, 20), 0, "pending"),
        ("Sharma", "Suresh", "Share final menu with Jain food counter", at(-1, 18), 0, "pending"),
        ("Sharma", "Neha", "Send room list to Bangalore Palace front desk", at(-2, 12), 0, "done"),
        ("Sharma", "Kavya", "Confirm second shooter for haldi", at(-1, 12), 0, "done"),
        ("Mehta", "Rahul", "Get revised quote from florist", at(2, 18), 0, "pending"),
        ("Mehta", "DJ", "Share sangeet playlist draft", at(4, 18), 0, "pending"),
        ("Khan", "Neha", "Print and courier welcome cards to guests", at(6, 18), 1, "pending"),
        ("Reddy", "Ayush", "Book site visit at Windflower with family", at(3, 11), 0, "pending"),
    ]
    for wed, person, text, due, proof, status in seed_tasks:
        t = create_task(pid, w[wed], ids[person], text, text, due, proof, "seed")
        update_task(t["id"], reminders_sent=1)
        if status == "done":
            mark_done(t["id"], note="seed")
    return p


def reset_demo():
    """One-click reset: wipe the demo workspace's tasks and messages and rebuild the fake data.
    Real phones that joined the demo workspace stay joined (so you don't have to re-join before a demo)."""
    p = one("SELECT * FROM planners WHERE is_demo = 1")
    if not p:
        return seed_demo()
    pid = p["id"]
    real_members = [m for m in members_of(pid)
                    if m["role"] != "planner" and not (m["phone"] or "").startswith(SIMULATED_PREFIX)]
    phones = [m["phone"] for m in members_of(pid)]
    for phone in phones:
        clear_state(phone)
    query("DELETE FROM tasks WHERE planner_id = ?", (pid,))
    query("DELETE FROM messages WHERE planner_id = ?", (pid,))
    query("DELETE FROM members WHERE planner_id = ?", (pid,))
    query("DELETE FROM weddings WHERE planner_id = ?", (pid,))
    query("DELETE FROM planners WHERE id = ?", (pid,))
    new_p = seed_demo()
    for m in real_members:
        add_member(new_p["id"], m["name"], m["phone"], m["role"], m["specialty"], m["language"])
    return new_p
