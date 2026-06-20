"""
memory.py
---------
Persistent + working memory for the agent system.

WHY THIS COUNTS AS "MEMORY" (for the internship write-up):

1. Long-term memory: a SQLite database file (nayapankh_memory.db) stores
   donors, volunteers, tasks, events, and the full conversation log. This
   persists across separate runs of the program -- close the script, reopen
   it tomorrow, and the agents still remember everything.

2. Working/short-term memory: the `session_context` dict passed around
   during a single run holds the recent conversation turns so agents can
   resolve references like "him" or "that event" within one session.

Using SQLite (Python's built-in `sqlite3`) keeps the prototype dependency-free
and easy to inspect/grade -- you can open nayapankh_memory.db with any SQLite
browser to see exactly what the agents have learned over time.
"""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "nayapankh_memory.db"


class Memory:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
        # short-term / working memory for the current process only
        self.session_context = {"recent_turns": []}

    def _init_schema(self):
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS donors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                total_donated REAL DEFAULT 0,
                last_donation_date TEXT
            );

            CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT,
                skills TEXT,
                available INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                assigned_to TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'open',
                created_by_agent TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                date TEXT,
                location TEXT,
                feasibility_note TEXT
            );

            CREATE TABLE IF NOT EXISTS conversation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                role TEXT,
                agent TEXT,
                message TEXT
            );
            """
        )
        self.conn.commit()

    # ---------- conversation / working memory ----------
    def log_conversation(self, role, agent, message):
        ts = datetime.now().isoformat(timespec="seconds")
        self.conn.execute(
            "INSERT INTO conversation_log (timestamp, role, agent, message) VALUES (?, ?, ?, ?)",
            (ts, role, agent, message),
        )
        self.conn.commit()
        self.session_context["recent_turns"].append({"role": role, "agent": agent, "message": message})
        # keep working memory bounded to last 20 turns
        self.session_context["recent_turns"] = self.session_context["recent_turns"][-20:]

    def recent_history(self, n=5):
        return self.session_context["recent_turns"][-n:]

    # ---------- donors ----------
    def add_or_update_donor(self, name, contact=None, amount=0):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM donors WHERE name = ?", (name,))
        row = cur.fetchone()
        today = datetime.now().date().isoformat()
        if row:
            new_total = row["total_donated"] + amount
            cur.execute(
                "UPDATE donors SET total_donated = ?, last_donation_date = ?, contact = COALESCE(?, contact) WHERE id = ?",
                (new_total, today, contact, row["id"]),
            )
            self.conn.commit()
            return dict(name=name, contact=contact or row["contact"], total_donated=new_total, new=False)
        else:
            cur.execute(
                "INSERT INTO donors (name, contact, total_donated, last_donation_date) VALUES (?, ?, ?, ?)",
                (name, contact, amount, today),
            )
            self.conn.commit()
            return dict(name=name, contact=contact, total_donated=amount, new=True)

    def list_donors(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM donors ORDER BY total_donated DESC")]

    # ---------- volunteers ----------
    def add_or_update_volunteer(self, name, contact=None, skills=None, available=1):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM volunteers WHERE name = ?", (name,))
        row = cur.fetchone()
        if row:
            cur.execute(
                "UPDATE volunteers SET contact = COALESCE(?, contact), skills = COALESCE(?, skills), available = ? WHERE id = ?",
                (contact, skills, available, row["id"]),
            )
            self.conn.commit()
            return dict(name=name, new=False)
        else:
            cur.execute(
                "INSERT INTO volunteers (name, contact, skills, available) VALUES (?, ?, ?, ?)",
                (name, contact, skills, available),
            )
            self.conn.commit()
            return dict(name=name, new=True)

    def list_volunteers(self, only_available=False):
        q = "SELECT * FROM volunteers"
        if only_available:
            q += " WHERE available = 1"
        return [dict(r) for r in self.conn.execute(q)]

    # ---------- tasks ----------
    def add_task(self, description, assigned_to=None, due_date=None, created_by_agent="System"):
        ts = datetime.now().isoformat(timespec="seconds")
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO tasks (description, assigned_to, due_date, status, created_by_agent, created_at) VALUES (?, ?, ?, 'open', ?, ?)",
            (description, assigned_to, due_date, created_by_agent, ts),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_tasks(self, status=None):
        q = "SELECT * FROM tasks"
        params = ()
        if status:
            q += " WHERE status = ?"
            params = (status,)
        q += " ORDER BY id DESC"
        return [dict(r) for r in self.conn.execute(q, params)]

    def complete_task(self, task_id):
        self.conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
        self.conn.commit()

    # ---------- events ----------
    def add_event(self, name, date, location, feasibility_note=""):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO events (name, date, location, feasibility_note) VALUES (?, ?, ?, ?)",
            (name, date, location, feasibility_note),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_events(self):
        return [dict(r) for r in self.conn.execute("SELECT * FROM events ORDER BY date")]

    def close(self):
        self.conn.close()
