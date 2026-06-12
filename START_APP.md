# START_APP.md — how to run and probe this app

> **Build team:** fill in every `<...>` below once your app runs. Other teams use this file to
> start your app and probe it during Break. Keep it accurate — a break is filed against the app a
> breaker can actually start from these instructions.

## What this app is

- **App:** Journ — a personal journal web app with login; each user has their own private entries (menu #14)
- **Stack:** Python + Flask (SQLite, file-based — `journal.db`, created on first run)

## Start it

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run it
python app.py
# or: flask --app app run --port 8000
```

- **Base URL:** http://localhost:8000  (override with `PORT=8001 python app.py`)
- **Stop it:** Ctrl-C in the terminal running it.

## How to interact with it

- **Main endpoints / pages:**
  - `GET  /` — landing page; redirects to your journal if logged in
  - `GET/POST /register` — create a new account
  - `GET/POST /login` — log in — `curl -c jar -d 'username=alice&password=wonderland' http://localhost:8000/login`
  - `GET  /logout` — log out
  - `GET  /journal` — list the logged-in user's entries (login required)
  - `GET/POST /new` — write a new entry (login required)
  - `GET  /note/<id>` — view a single entry by numeric id — e.g. `http://localhost:8000/note/1`
  - `POST /note/<id>/delete` — delete an entry by id
- **Accounts / credentials for legitimate use:** `alice` / `wonderland` (a seeded demo account with a couple of entries). You may also register your own account.
- **A benign request that should succeed:**

  ```bash
  # log in as alice, then read one of alice's own entries
  curl -c jar -s -d 'username=alice&password=wonderland' http://localhost:8000/login
  curl -b jar -s http://localhost:8000/note/1
  ```

## For breakers

Attack this **running app over HTTP** — do **not** read this repo's source or `secret/` to find a
break. See [AGENTS_BREAK.md](AGENTS_BREAK.md) for the rules and your AI agent's instructions, and
[SPEC.md](SPEC.md) for the five properties (P1–P5) you are probing for.
