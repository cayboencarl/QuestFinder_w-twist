# QuestFinder

A location-based task marketplace for **Brgy. San Vicente, Baguio City**. Homeowners and small business
owners post short-term tasks (**quests**). Verified residents, students and freelancers (**task workers**, 18+)
find them sorted by distance in kilometres, accept them, chat with the client, and get paid through an
in-app wallet (simulated, in ₱).

**Stack:** Python Flask (Blueprints) · PostgreSQL · Flask-SQLAlchemy · Flask-Migrate · Flask-WTF (CSRF) ·
HTML/CSS/vanilla JavaScript · Leaflet + OpenStreetMap · face-api (in-browser face matching).

---

## Features

| Area | What it does |
|---|---|
| Accounts | Register (strict **18+** check), log in/out, 5-try lockout, change password. One account can both post and accept quests. |
| Identity verification | **ID scan → live face scan → face match score →** Barangay Admin approves or rejects. Verified badge. |
| Geolocation (main technology) | GPS via the browser Geolocation API (explained before the permission prompt) or a manual map pin. Haversine distance in **km**, radius filter, nearest-first sorting. Quest locations stay **approximate** until the client accepts a worker. |
| Post (client) | Location, title, work description, qualification, offered pay (₱), duration, photo → Publish. The quest pin can **only be placed inside Brgy. San Vicente's official boundary** (outlined on the map; also checked on the server). |
| Quest (task worker) | Map + list of nearby open quests with distance, pay and qualification; search, radius, sort, minimum pay. **You can't accept your own quest.** |
| Acceptance | Worker taps **ACCEPT QUEST** → client reviews task workers (distance, rating, skills) → accepts one → pay is **reserved** from the client's wallet → exact location and chat open for both. |
| Completion | Client marks the quest completed → pay is **released** to the worker's wallet. |
| Notifications | Bell next to Settings: a worker accepted your quest, you were accepted, pay released, verification result. |
| Messages | One chat per accepted quest, text and photos, auto-refresh every 3 s, unread badge on the tab. |
| Wallet & history | Balance, amount on hold, simulated Deposit/Withdraw (GCash, Maya, bank), full transaction history with references. |
| Ratings | Two-way 1–5 star ratings and reviews after completion, shown on profiles. |
| Profile | Photo, mobile number, **skills dropdown** (local skills such as Gardening, Plumbing, Computer & Wi-Fi setup), bio. |
| Barangay Admin | Separate panel with three tabs: **Verifications** (review ID + face scans with automatic checks: face match %, age, birthdate, name), **Posted Quests** (every quest with its client, worker, pay, location and applications), and **Users** (all registered members; suspend for a set number of hours/days/weeks with a reason, lift a suspension, or delete the account). |

---

## Requirements

* **Python 3.13** (3.12 also works)
* **PostgreSQL 16+** (tested on 16 and 18)
* **Git for Windows** (Git Bash) and **VS Code** (recommended)
* Internet access in the browser for the map tiles (OpenStreetMap)

---

## Quick start on Windows (Git Bash)

From the repository folder (the one that contains `QuestFinder/`):

```bash
bash QuestFinder/scripts/start.sh
```

The first run:

1. creates the virtual environment `.venv` and installs `requirements.txt`;
2. creates `.env` with random secrets (only if `.env` does not exist yet);
3. creates the PostgreSQL user and database. **Type your `postgres` password once** when asked;
4. applies the migrations and loads the demo data;
5. starts the server at **http://127.0.0.1:5000** and prints the demo logins.

Later runs just start the server. To wipe everything and reload the demo data:

```bash
bash QuestFinder/scripts/start.sh --reseed
```

Stop the server with **Ctrl+C**.

---

## Manual setup (any OS)

### 1. PostgreSQL

```sql
-- in psql as the postgres superuser
CREATE ROLE questfinder LOGIN PASSWORD 'choose-a-strong-password';
CREATE DATABASE questfinder OWNER questfinder ENCODING 'UTF8';
```

### 2. Python environment

```bash
cd QuestFinder
python -m venv .venv
source .venv/Scripts/activate      # Git Bash on Windows
# source .venv/bin/activate        # macOS / Linux
pip install -r requirements.txt
```

### 3. Settings

```bash
cp .env.example .env
```

Edit `.env`: set `SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`),
`DATABASE_URL` (with the password from step 1), `ADMIN_PASSWORD` and `SEED_USER_PASSWORD`.
`.env` is git-ignored; never commit it.

### 4. Database tables (migrations)

```bash
flask db upgrade
```

After changing a model later: `flask db migrate -m "describe the change"` then `flask db upgrade`.

### 5. Demo data

```bash
flask seed            # into an empty database
flask seed --reset    # wipe all tables first
flask create-admin    # add another Barangay Admin account
```

### 6. Run

```bash
flask run --debug
```

Open **http://127.0.0.1:5000**.

---

## Demo accounts (`flask seed`)

| Email | Role | Notes |
|---|---|---|
| `admin@questfinder.test` | Barangay Admin | password = `ADMIN_PASSWORD` in `.env` |
| `carl@questfinder.test` | Member | ₱1,321 wallet; posted *Clean Roots*; chat with Jake; completed quest with Dave |
| `marc@questfinder.test` | Member | posted *Router Config*, *Repaint Store Sign* |
| `aldous@questfinder.test` | Member | posted *Carry Groceries Uphill* |
| `jake@questfinder.test` | Member | task worker; hired for *Fix Leaking Faucet* |
| `dave@questfinder.test` | Member | task worker with 5★ review |
| `bea@questfinder.test` | Member | **not verified**: use her to try the ID + face verification |

All members use the password `SEED_USER_PASSWORD` from `.env`. `start.sh` prints both passwords when it starts.

### Try the full flow

1. Log in as **jake** → **Quest** → open *Router Config* → **ACCEPT QUEST**.
2. Log in as **marc** (another browser or a private window) → 🔔 → **Accept** Jake → ₱260 is reserved → chat opens.
3. Chat both ways (text and photos).
4. As marc, open the quest → **Mark as completed & release pay** → rate Jake. As jake, rate marc.
5. Check both **Wallet** and **History** tabs.

---

## Letting someone else test it

Never share the normal `start.sh` server: it runs in debug mode, and the debugger lets anyone who can open
it run commands on your PC. Use the sharing mode instead (debug OFF):

```bash
bash QuestFinder/scripts/start.sh --share
```

* **Same Wi-Fi:** the tester opens the `http://<your-PC-IP>:5000` address printed in the terminal. Allow Python
  through Windows Firewall (Private networks) if asked. Camera and GPS need HTTPS, so on this address use
  "Upload photo" and "Place a pin" instead.
* **Anywhere, over HTTPS** (camera and GPS work): install Cloudflare's tunnel once
  (`winget install --id Cloudflare.cloudflared`), keep the server running, and in a second terminal run
  `cloudflared tunnel --url http://localhost:5000`. Send the `https://….trycloudflare.com` link it prints.
  The link stops working when you close that terminal.
* **Their own copy:** push the repository to GitHub; the tester clones it and runs `start.sh` with their own PostgreSQL.

Your PC must stay on with the server running while they test. Testers can register their own account, or use a
demo account (password = `SEED_USER_PASSWORD`).

## Camera and location on a phone

Browsers only allow the **camera** (ID/face scan) and **GPS** on `localhost`/`127.0.0.1` or over **HTTPS**.
On the PC both work at `http://127.0.0.1:5000`. To test on a phone on the same Wi-Fi, serve the app over
HTTPS, for example with a tunnel such as `ngrok http 5000` or `cloudflared tunnel --url http://localhost:5000`,
then set `SESSION_COOKIE_SECURE=true` in `.env`. Without HTTPS the phone can still use the
"Upload photo" and "Place a pin on the map" fallbacks.

---

## Project structure

See [`docs/FOLDER_STRUCTURE.md`](docs/FOLDER_STRUCTURE.md), the database design and ERD in
[`docs/DATABASE_SCHEMA.md`](docs/DATABASE_SCHEMA.md), and the assumptions in
[`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md).

## Security notes

* Passwords are hashed (Werkzeug PBKDF2/scrypt); sessions are signed, HTTP-only cookies.
* CSRF tokens on every form and on every JavaScript `fetch` (header `X-CSRFToken`).
* Role checks: member vs Barangay Admin; posting, accepting and wallet actions require verification.
* Uploads are re-encoded with Pillow (metadata such as GPS EXIF removed) and stored outside the public
  static folder, served only through access-checked routes. ID images are visible only to the owner and the admin.
* Only the last 4 characters of an ID number are stored.
* Wallet changes lock rows (`SELECT … FOR UPDATE`); balances can't go negative (database check).
* Database rules also prevent a client from being the worker of their own quest.

## Third-party assets

Leaflet (BSD-2-Clause), OpenStreetMap tiles and the barangay boundary (relation 15790886) (© OpenStreetMap contributors, ODbL),
@vladmandic/face-api (MIT). Licences are in `app/static/vendor/*/LICENSE.txt`. The QuestFinder logo
and design are original; no Airtasker assets are used.
