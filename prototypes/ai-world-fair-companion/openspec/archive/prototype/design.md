# Design: AI Engineer World's Fair Companion

## Stack

| Layer | Choice |
|-------|--------|
| Runtime | Python 3.12-slim + FastAPI + Uvicorn |
| Database | SQLite (single file, populated once before air-gap) |
| Frontend | Vanilla HTML + CSS + JavaScript |
| QR | `qrcode.js` (library, vendored) |
| Styling | Lightweight CSS framework (e.g., Pico.css or bare custom CSS with terminal aesthetic) |
| Server | FastAPI serves static frontend files and API routes |

**No cloud services. No external APIs after initialization. No BaaS. No CDN dependencies.**

## Architecture

```
┌─────────────────────────────────────────────┐
│  Private Wi-Fi Router (closed network)       │
│                                              │
│  ┌──────────┐    HTTP/JSON    ┌───────────┐  │
│  │  Laptop  │ ◄─────────────► │  Browser   │  │
│  │  / Mini- │                 │  (any dev) │  │
│  │  PC      │                 │            │  │
│  │          │                 │            │  │
│  │  FastAPI │                 │  Vanilla   │  │
│  │  Server  │                 │  JS/HTML   │  │
│  │          │                 │  + CSS     │  │
│  │  SQLite  │                 │            │  │
│  │  (local) │                 │  QR gen/   │  │
│  │          │                 │  scan (lib)│  │
│  └──────────┘                 └───────────┘  │
└─────────────────────────────────────────────┘
```

The FastAPI server serves both the static frontend and the JSON API. All data lives in a single SQLite file (`data/fair.db`). The frontend uses `localStorage` for user preferences and scanned contacts.

## Data Model

### Table: `talks`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique talk identifier |
| `title` | TEXT NOT NULL | | Talk title |
| `speaker_name` | TEXT NOT NULL | | Speaker's full name |
| `speaker_bio` | TEXT | | Short bio (nullable) |
| `speaker_github` | TEXT | | Speaker's GitHub handle (nullable) |
| `start_time` | TEXT NOT NULL | ISO 8601 format | Talk start time (e.g., "2025-06-29T14:00:00") |
| `end_time` | TEXT NOT NULL | ISO 8601 format | Talk end time |
| `room` | TEXT NOT NULL | | Room name or number |
| `description` | TEXT | | Talk description (nullable) |
| `tags` | TEXT NOT NULL | | Comma-separated tags (e.g., "rag,pipelines,llm") |
| `track` | TEXT | | Optional track name (nullable) |

### Table: `speakers`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique speaker identifier |
| `name` | TEXT NOT NULL | | Speaker's full name |
| `bio` | TEXT | | Short bio (nullable) |
| `github` | TEXT | | GitHub handle (nullable) |
| `talks_count` | INTEGER | DEFAULT 0 | Number of talks (denormalized for quick queries) |

### Table: `expo_booths`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique booth identifier |
| `company_name` | TEXT NOT NULL | | Company / organization name |
| `booth_number` | TEXT NOT NULL | | Booth number/letter (e.g., "A12") |
| `description` | TEXT | | What the company does (nullable) |
| `tags` | TEXT NOT NULL | | Comma-separated tags (e.g., "llm,infra,open-source") |
| `x` | REAL NOT NULL | | X coordinate on the expo map grid (0–100) |
| `y` | REAL NOT NULL | | Y coordinate on the expo map grid (0–100) |
| `category` | TEXT | | Booth category (e.g., "infrastructure", "tools", "research") (nullable) |

### Table: `contacts`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique contact identifier |
| `name` | TEXT NOT NULL | | Contact's name |
| `github` | TEXT | | Contact's GitHub handle (nullable) |
| `project` | TEXT | | What they're working on (nullable) |
| `scanned_at` | TEXT NOT NULL | ISO 8601 format | When the contact was scanned |
| `source_hash` | TEXT NOT NULL | | Hash of the QR payload for deduplication |

## API Routes

### Schedule & Talks

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/talks` | List all talks with optional query params: `?tag=rag&speaker=alice&date=2025-06-29` |
| `GET` | `/api/talks/search` | Full-text search across title, description, speaker_name, and tags. Query param: `?q=local+model+orchestration` |
| `GET` | `/api/talks/<id>` | Get a single talk by ID |
| `GET` | `/api/speakers` | List all speakers |
| `GET` | `/api/speakers/<id>` | Get a single speaker with their talks |

### Expo

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/booths` | List all booths with optional query params: `?tag=llm&category=infrastructure` |
| `GET` | `/api/booths/<id>` | Get a single booth by ID |
| `GET` | `/api/booths/pins` | Get the current user's pinned booths (reads from localStorage, no DB needed — but returns JSON for consistency) |
| `POST` | `/api/booths/pins` | Toggle a booth pin. Body: `{"booth_id": 1, "action": "pin"|"unpin"}` |
| `GET` | `/api/route` | Calculate path between pinned booths. Query params: `?from=1&to=2` (returns ordered list of booth IDs) |

### Networking

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/contacts/scan` | Decode and store a scanned contact. Body: `{"payload": "<base64-encoded JSON>"}` |
| `GET` | `/api/contacts` | List all scanned contacts |
| `GET` | `/api/contacts/<id>` | Get a single contact |
| `DELETE` | `/api/contacts/<id>` | Remove a contact |
| `GET` | `/api/badge` | Return the current user's badge data as JSON (for QR generation). Body: `{"name": "User", "github": "user", "project": "what I'm building"}` |

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Health check — returns `{"status": "ok"}` |

## Frontend Pages

### 1. Command Palette (`/` — default view)

- Full-screen overlay triggered by `Cmd+K` (or `Ctrl+K` on Linux).
- Single input field with autocomplete suggestions from `/api/talks/search`.
- Results render as a list: talk title, speaker, time, room, matching tags highlighted.
- Clicking a result navigates to the talk detail view.
- **kind: source** — `index.html`, `css/style.css`, `js/app.js`, `js/palette.js`

### 2. Schedule View (`/schedule`)

- Table or card list of talks grouped by day and time.
- Filter bar at top: tag chips, speaker search, date selector.
- Clicking a talk opens a detail modal.
- **kind: source** — `schedule.html`, `js/schedule.js`

### 3. Expo Map (`/expo`)

- SVG-based vector map of the Moscone Center floor plan (simplified grid).
- Booths rendered as labeled circles at their (x, y) positions.
- Pinned booths highlighted with a distinct color.
- "Route" button calculates and draws a path between consecutive pinned booths.
- **kind: source** — `expo.html`, `js/expo.js`, `assets/expo-map.svg`
- **kind: asset** — `assets/expo-map.svg` (hand-authored minimalist floor plan)

### 4. Networking / Badge (`/badge`)

- Digital badge view showing the user's name, GitHub handle, and project description.
- QR code rendered from the badge JSON payload using `qrcode.js`.
- "Scan" mode: uses device camera (via `getUserMedia`) to scan incoming QR codes.
- Scanned contacts appear in a list below with timestamp.
- **kind: source** — `badge.html`, `js/badge.js`

### 5. Contacts View (`/contacts`)

- List of all scanned contacts.
- Each contact card shows name, GitHub link, project, and scan time.
- Delete button per contact.
- **kind: source** — `contacts.html`, `js/contacts.js`

## QR Code Format

Badge QR payload is a compact JSON string, base64-encoded:

```json
{
  "n": "Alice Chen",
  "g": "alicechen",
  "p": "Building local LLM agents"
}
```

Keys are intentionally short to keep the QR code simple and scannable. The base64 encoding avoids special characters that could confuse QR scanners.

## Expo Map Pathfinding

The expo map uses a 100×100 grid coordinate system. Pathfinding between booths uses a simplified A* algorithm running in the browser (vanilla JS). The grid treats non-booth areas as walkable; obstacles (walls, stages) are represented as blocked grid cells defined in the SVG map data. For the prototype, the pathfinding is "good enough" — it connects booths efficiently without perfect obstacle avoidance.

## Styling & Aesthetic

- **Dark mode by default** — near-black background (`#0d1117`), monospace or semi-mono font (e.g., JetBrains Mono or Fira Code via system fallback).
- **Terminal-inspired** — subtle green/cyan accent colors, minimal chrome, high contrast.
- **Command palette** — centered overlay with a blinking cursor, matching the IDE aesthetic.
- **Badge view** — styled to look like a raw terminal output or JSON dump.
- **No heavy CSS frameworks** — custom CSS is preferred for the terminal vibe; if a lightweight framework is used, it must be easily overridable.

## Vendor Libraries

| Library | Kind | Source URL | Usage |
|---------|------|------------|-------|
| `qrcode.js` | library | `https://cdn.jsdelivr.net/npm/qrcode@1.5.4/build/qrcode.min.js` | QR code generation and scanning |

## Seed Data

The `seed.py` script populates `data/fair.db` with:

- 20–30 realistic talks across 4 days with tags like `rag`, `llm`, `local-models`, `agents`, `pipelines`, `fine-tuning`, `vector-dbs`
- 15–20 speakers with GitHub handles
- 20–30 expo booths with grid coordinates and company descriptions
- Sample contacts for testing

Seed data is injected once before the air-gap. The `seed.py` script is a standalone Python script that runs against the SQLite file.

## File Manifest

```
ai-world-fair-companion/
├── openspec/
│   └── changes/
│       └── prototype/
│           ├── proposal.md
│           ├── design.md
│           └── tasks.md
├── app/
│   ├── main.py                    # kind: source — FastAPI app entry point
│   ├── requirements.txt           # kind: source — Python deps
│   ├── schema.sql                 # kind: source — DDL for all tables
│   ├── seed.py                    # kind: source — seed data population script
│   ├── database.py                # kind: source — SQLite connection helper
│   ├── api/
│   │   ├── __init__.py            # kind: source
│   │   ├── talks.py               # kind: source — /api/talks routes
│   │   ├── speakers.py            # kind: source — /api/speakers routes
│   │   ├── booths.py              # kind: source — /api/booths routes
│   │   ├── contacts.py            # kind: source — /api/contacts routes
│   │   └── badge.py               # kind: source — /api/badge route
│   └── frontend/
│       ├── index.html             # kind: source — command palette (home)
│       ├── schedule.html          # kind: source — schedule view
│       ├── expo.html              # kind: source — expo map view
│       ├── badge.html             # kind: source — digital badge view
│       ├── contacts.html          # kind: source — contacts list view
│       ├── css/
│       │   └── style.css          # kind: source — dark terminal theme
│       ├── js/
│       │   ├── app.js             # kind: source — shared utilities
│       │   ├── palette.js         # kind: source — command palette logic
│       │   ├── schedule.js        # kind: source — schedule view logic
│       │   ├── expo.js            # kind: source — expo map + pathfinding
│       │   ├── badge.js           # kind: source — QR gen + scan logic
│       │   └── contacts.js        # kind: source — contacts management
│       └── assets/
│           └── expo-map.svg       # kind: asset — minimalist floor plan
```
