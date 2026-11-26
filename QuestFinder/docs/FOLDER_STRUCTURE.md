# QuestFinder — Folder Structure (Deliverable 3)

```
QuestFinder_w-twist/
├── run.py                      # entry point: `flask run` / `python run.py`
├── requirements.txt            # pinned Python packages
├── .env.example                # copy to .env and fill in (never commit .env)
├── .gitignore
├── README.md                   # setup: PostgreSQL, migrations, seeding, running
├── .vscode/                    # recommended VS Code extensions and settings (Git Bash terminal)
│
├── app/
│   ├── __init__.py             # application factory: config, extensions, blueprints, error pages
│   ├── config.py               # settings read from environment variables
│   ├── extensions.py           # db, migrate, csrf instances
│   │
│   ├── models/                 # SQLAlchemy models (one file per area)
│   │   ├── base.py             # timestamp mixin, utcnow()
│   │   ├── user.py             # User (member / Barangay Admin), age check
│   │   ├── verification.py     # VerificationRequest (ID scan + face scan)
│   │   ├── quest.py            # Quest, QuestApplication
│   │   ├── wallet.py           # Wallet, Transaction
│   │   ├── messaging.py        # Conversation, Message
│   │   ├── notification.py     # Notification
│   │   └── rating.py           # Rating
│   │
│   ├── data/
│   │   └── san_vicente_boundary.geojson  # official barangay boundary (OpenStreetMap)
│   │
│   ├── services/               # business logic, kept out of the routes
│   │   ├── boundary_service.py # point-in-barangay check for quest pins
│   │   ├── geo_service.py      # haversine km, radius box, approximate location
│   │   ├── wallet_service.py   # deposit, withdraw, reserve, release, refund
│   │   ├── quest_service.py    # post, search by distance, accept, complete, cancel
│   │   ├── verification_service.py  # 18+ rule, submission, admin decision
│   │   ├── admin_service.py    # suspend / lift / delete member accounts
│   │   ├── notification_service.py
│   │   ├── chat_service.py
│   │   ├── rating_service.py
│   │   └── upload_service.py   # safe image saving (type + size checks, re-encoding)
│   │
│   ├── blueprints/             # one package per feature: routes.py (+ forms.py)
│   │   ├── main/               # Home Page
│   │   ├── auth/               # register, login, logout
│   │   ├── profile/            # profile (skills dropdown), settings, change password
│   │   ├── location/           # set my location: GPS or map pin
│   │   ├── verification/       # ID scan → face scan → submit
│   │   ├── quests/             # Post, Quests (map + list), details, my quests, applicants
│   │   ├── wallet/             # Wallet, deposit, withdraw, Transaction History
│   │   ├── messages/           # Messages list, chat thread (polling JSON API)
│   │   ├── notifications/      # bell list
│   │   ├── ratings/            # rate after completion
│   │   ├── admin/              # Barangay Admin: verifications, posted quests, users (suspend/delete)
│   │   └── files/              # access-checked image serving (uploads are private)
│   │
│   ├── utils/
│   │   ├── auth.py             # sessions, login_required, admin_required, verified_required
│   │   ├── template_helpers.py # ₱ formatting, km, dates, Jinja globals
│   │   └── validators.py       # shared form validators
│   │
│   ├── templates/
│   │   ├── layouts/            # base.html, app.html (with bottom tab bar), plain.html
│   │   ├── partials/           # bottom_nav, flash, avatar, quest_card, map scripts
│   │   │   ├── main/  auth/  profile/  verification/  location/  quests/
│   │   ├── wallet/  messages/  notifications/  ratings/  admin/
│   │   └── errors/
│   │
│   └── static/
│       ├── css/main.css        # design system (mobile-first)
│       ├── js/                 # app.js (shared), map.js, chat.js, verification.js, skills.js
│       ├── img/                # QuestFinder logo and favicon (original artwork)
│       └── vendor/             # Leaflet, face-api (local copies, no build step)
│
├── migrations/                 # Flask-Migrate / Alembic
│   └── versions/0001_initial_schema.py
│
├── scripts/
│   └── start.sh                # one-command setup + run (Git Bash)
│
├── seeds/
│   └── seed_data.py            # `flask seed` and `flask create-admin`
│
├── docs/
│   ├── DATABASE_SCHEMA.md      # Deliverable 2: ERD and tables
│   ├── FOLDER_STRUCTURE.md     # Deliverable 3: this file
│   └── ASSUMPTIONS.md          # Deliverable 7
│
└── instance/                   # local only, git-ignored
    └── uploads/                # avatars, quest photos, chat images, ID and face scans
```

Uploads are saved in `instance/uploads/<kind>/` with random file names. They are served only through
`blueprints/files`, which checks who may see each image. For example, only the owner and the Barangay
Admin may see ID and face scans.
