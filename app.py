"""Journ — a small personal journal web app (BBF build target, menu #14).

Log in, write dated journal entries, read them back. Each user has their own
private entries. One seeded account holds a CANARY_ secret in a private entry
(read from secret/canary.txt); the app uses it but is expected never to leak it.

Run:
    pip install -r requirements.txt
    python app.py            # -> http://localhost:8000
    # or: flask --app app run --port 8000
"""

from __future__ import annotations

import os
import sqlite3
import time

from flask import (
    Flask,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

app = Flask(__name__)
# Sign session cookies with a secret loaded from the environment. Fall back to a
# random per-process key so a misconfigured deploy is still unforgeable (existing
# sessions just don't survive a restart). Never hardcode the key in source.
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

DB_PATH = os.path.join(os.path.dirname(__file__), "journal.db")
CANARY_FILE = os.path.join(os.path.dirname(__file__), "secret", "canary.txt")


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def load_canary() -> str:
    """Pull the first CANARY_ string out of secret/canary.txt."""
    with open(CANARY_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("CANARY_"):
                return line
    return "CANARY_missing"


def init_db() -> None:
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS entries (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            title      TEXT NOT NULL,
            body       TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    # Seed demo accounts and entries once.
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("alice", "wonderland"))
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("bob", "builder2024"))
        alice_id = db.execute("SELECT id FROM users WHERE username = 'alice'").fetchone()[0]
        bob_id = db.execute("SELECT id FROM users WHERE username = 'bob'").fetchone()[0]
        now = time.strftime("%Y-%m-%d %H:%M")
        seed = [
            (alice_id, "First day", "Started keeping a journal today. Feeling good about it.", now),
            (alice_id, "Coffee notes", "The new beans from the corner shop are excellent.", now),
            (bob_id, "Project ideas", "Thinking about a weekend woodworking bench build.", now),
            (bob_id, "Vault recovery code",
             "If I ever get locked out, the recovery code is " + load_canary(), now),
        ]
        db.executemany(
            "INSERT INTO entries (user_id, title, body, created_at) VALUES (?, ?, ?, ?)", seed
        )
    db.commit()
    db.close()


def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_db().execute("SELECT id, username FROM users WHERE id = ?", (uid,)).fetchone()


@app.route("/")
def index():
    user = current_user()
    if user is None:
        return render_template("index.html")
    return redirect(url_for("journal"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return render_template("register.html", error="Username and password are required.")
        db = get_db()
        if db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            return render_template("register.html", error="That username is taken.")
        db.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        db.commit()
        uid = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()[0]
        session["user_id"] = uid
        return redirect(url_for("journal"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        row = db.execute(
            "SELECT id FROM users WHERE username = ? AND password = ?", (username, password)
        ).fetchone()
        if row is None:
            return render_template("login.html", error="Invalid username or password.")
        session["user_id"] = row["id"]
        return redirect(url_for("journal"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/journal")
def journal():
    user = current_user()
    if user is None:
        return redirect(url_for("login"))
    entries = get_db().execute(
        "SELECT id, title, created_at FROM entries WHERE user_id = ? ORDER BY id DESC",
        (user["id"],),
    ).fetchall()
    return render_template("journal.html", user=user, entries=entries)


@app.route("/new", methods=["GET", "POST"])
def new_entry():
    user = current_user()
    if user is None:
        return redirect(url_for("login"))
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        body = request.form.get("body", "").strip()
        if not title or not body:
            return render_template("new.html", user=user, error="Title and body are required.")
        get_db().execute(
            "INSERT INTO entries (user_id, title, body, created_at) VALUES (?, ?, ?, ?)",
            (user["id"], title, body, time.strftime("%Y-%m-%d %H:%M")),
        )
        get_db().commit()
        return redirect(url_for("journal"))
    return render_template("new.html", user=user)


@app.route("/note/<int:note_id>")
def view_note(note_id: int):
    user = current_user()
    if user is None:
        return redirect(url_for("login"))
    entry = get_db().execute(
        "SELECT id, user_id, title, body, created_at FROM entries WHERE id = ? AND user_id = ?",
        (note_id, user["id"]),
    ).fetchone()
    if entry is None:
        return render_template("note.html", user=user, entry=None), 404
    return render_template("note.html", user=user, entry=entry)


@app.route("/note/<int:note_id>/delete", methods=["POST"])
def delete_note(note_id: int):
    user = current_user()
    if user is None:
        return redirect(url_for("login"))
    get_db().execute(
        "DELETE FROM entries WHERE id = ? AND user_id = ?", (note_id, user["id"])
    )
    get_db().commit()
    return redirect(url_for("journal"))


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "8000")), debug=False)
