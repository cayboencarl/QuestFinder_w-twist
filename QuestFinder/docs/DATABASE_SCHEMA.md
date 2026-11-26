# QuestFinder — Database Schema (Deliverable 2)

PostgreSQL, normalized to 3NF. Managed by Flask-Migrate (Alembic); the initial migration is
`migrations/versions/0001_initial_schema.py`. Status-like columns are `VARCHAR` with `CHECK`
constraints instead of PostgreSQL `ENUM` types so they are easy to change in later migrations.
Money uses `NUMERIC(…, 2)` (never floats). All timestamps are `TIMESTAMPTZ` stored in UTC and shown
in Asia/Manila time.

## Entity-Relationship Diagram

```mermaid
erDiagram
    USERS ||--o| WALLETS : "owns"
    USERS ||--o{ VERIFICATION_REQUESTS : "submits"
    USERS ||--o{ VERIFICATION_REQUESTS : "reviews (admin)"
    USERS ||--o{ QUESTS : "posts (client)"
    USERS ||--o{ QUESTS : "is assigned (worker)"
    USERS ||--o{ QUEST_APPLICATIONS : "makes (worker)"
    QUESTS ||--o{ QUEST_APPLICATIONS : "receives"
    QUESTS ||--o| CONVERSATIONS : "opens after acceptance"
    CONVERSATIONS ||--o{ MESSAGES : "contains"
    USERS ||--o{ MESSAGES : "sends"
    WALLETS ||--o{ TRANSACTIONS : "records"
    QUESTS ||--o{ TRANSACTIONS : "is paid by"
    USERS ||--o{ NOTIFICATIONS : "receives"
    QUESTS ||--o{ RATINGS : "is rated in"
    USERS ||--o{ RATINGS : "gives / receives"

    USERS {
        int id PK
        varchar first_name
        varchar last_name
        varchar email UK
        varchar phone
        varchar password_hash
        date birthdate "must be 18+"
        varchar role "member | admin"
        text bio
        varchar skills
        varchar avatar_filename
        float latitude
        float longitude
        varchar location_label
        timestamptz location_updated_at
        bool is_verified
        timestamptz verified_at
        bool is_active
        timestamptz last_login_at
        timestamptz suspended_until "set by the Barangay Admin"
        timestamptz suspended_at
        varchar suspension_reason
    }
    VERIFICATION_REQUESTS {
        int id PK
        int user_id FK
        varchar id_type
        varchar id_number_last4
        varchar name_on_id
        date birthdate_on_id
        varchar id_image_filename
        varchar face_image_filename
        float face_match_distance
        bool face_match_passed
        varchar status "pending | approved | rejected"
        timestamptz submitted_at
        int reviewed_by_id FK
        timestamptz reviewed_at
        varchar rejection_reason
    }
    QUESTS {
        int id PK
        int client_id FK
        varchar title
        text description
        text qualification
        numeric pay "PHP"
        int duration_minutes
        varchar photo_filename
        float latitude "exact"
        float longitude "exact"
        varchar location_label
        float approx_latitude "public"
        float approx_longitude "public"
        varchar status "open | assigned | completed | cancelled"
        varchar payment_status "unpaid | held | released"
        int worker_id FK
        timestamptz assigned_at
        timestamptz completed_at
        timestamptz cancelled_at
    }
    QUEST_APPLICATIONS {
        int id PK
        int quest_id FK
        int worker_id FK
        varchar message
        varchar status "pending | accepted | rejected | withdrawn"
        float distance_km
    }
    WALLETS {
        int id PK
        int user_id FK "unique"
        numeric balance ">= 0"
    }
    TRANSACTIONS {
        int id PK
        int wallet_id FK
        varchar kind
        numeric amount "> 0"
        numeric balance_after
        int quest_id FK
        varchar method
        varchar reference UK
        varchar note
        timestamptz created_at
    }
    CONVERSATIONS {
        int id PK
        int quest_id FK "unique"
        int client_id FK
        int worker_id FK
        timestamptz last_message_at
    }
    MESSAGES {
        int id PK
        int conversation_id FK
        int sender_id FK
        text body
        varchar image_filename
        timestamptz created_at
        timestamptz read_at
    }
    NOTIFICATIONS {
        int id PK
        int user_id FK
        varchar kind
        varchar message
        varchar link
        bool is_read
        timestamptz created_at
    }
    RATINGS {
        int id PK
        int quest_id FK
        int rater_id FK
        int ratee_id FK
        smallint stars "1-5"
        varchar comment
        timestamptz created_at
    }
```

> The diagram renders in VS Code with the *Markdown Preview Mermaid Support* extension
> (recommended in `.vscode/extensions.json`) and on GitHub.

## Tables

| Table | Purpose | Key rules enforced in the database |
|---|---|---|
| `users` | One account per person. Members act as **client** or **task worker**; `admin` = Barangay Admin. Holds the user's own location for distance matching. | Unique email; `role` in (member, admin); lat/lng ranges. 18+ is checked on registration and again by the admin against the ID. A suspended user (`suspended_until` in the future) cannot log in and their open quests are hidden. |
| `verification_requests` | ID scan + face scan submissions and the Barangay Admin's decision. | `status` check. Only the **last 4** characters of the ID number are stored. Images are kept outside the public static folder. |
| `quests` | Posted tasks: Location, Work Description, Qualification, Offered Pay, Photo (prototype fields) + Title and Duration (shown on the quest card and details screens). | `pay > 0`, `duration_minutes > 0`, `worker_id <> client_id` (**a client can never take their own quest**), status checks. Exact and approximate coordinates are stored separately. |
| `quest_applications` | A task worker tapping **ACCEPT QUEST**; the client then accepts one worker. | One application per worker per quest (unique); status check. |
| `wallets` | Simulated e-wallet, one per user. | `balance >= 0`. |
| `transactions` | Every peso movement: deposit, withdraw, quest_hold (pay reserved on acceptance), quest_earning (pay released on completion), quest_refund. Powers the **Transaction History** tab. | `amount > 0`, `kind` check, unique reference. Wallet rows are locked (`SELECT … FOR UPDATE`) during changes. |
| `conversations` | One chat per quest between the client and the accepted worker. | One per quest (unique); `client_id <> worker_id`. |
| `messages` | Text and image messages in a chat thread. | Must have text or an image. |
| `notifications` | Bell notifications (accepted quests, completion, verification result). | `kind` check. |
| `ratings` | Two-way ratings and reviews after completion. | 1–5 stars; one rating per person per quest; cannot rate yourself. |

## Normalization notes

* No repeating groups or multi-valued columns (1NF). Every non-key column depends on the whole key (2NF).
* No transitive dependencies (3NF): a user's average rating is **computed** from `ratings`, a wallet's
  history from `transactions`, and a quest's applicant count from `quest_applications`, so none is stored twice.
* `transactions.balance_after` is a deliberate audit snapshot (the balance right after that entry), not a
  derived value used for logic; the source of truth is `wallets.balance`.
* `users.is_verified` caches the outcome of the latest approved `verification_requests` row so every page
  does not need a join; it is only changed by the admin approval service.
