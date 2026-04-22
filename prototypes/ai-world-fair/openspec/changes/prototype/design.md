# Design: World's Fair Companion

**Slug:** ai-world-fair
**Stack:** Python 3.12-slim + FastAPI + Uvicorn + SQLite + vanilla HTML/CSS/JS
**Runtime:** Single-process, no background workers, no message queues.

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│              Private Wi-Fi Router            │
│                                              │
│  ┌──────────────┐    ┌──────────────────┐   │
│  │   Laptop /    │◄──►│  FastAPI Server   │   │
│  │   Mini-PC     │    │  (Uvicorn + SQLite)│  │
│  │   (Browser)   │    │                  │   │
│  └──────────────┘    └──────────────────┘   │
│                                              │
│  ┌──────────────┐    ┌──────────────────┐   │
│  │   Phone /     │◄──►│  QR Code Gen/    │   │
│  │   Tablet      │    │  Scan (Browser)  │   │
│  └──────────────┘    └──────────────────┘   │
└─────────────────────────────────────────────┘
```

The entire application runs as a single FastAPI process serving static HTML/CSS/JS from the filesystem. SQLite stores all conference data. The frontend is vanilla JavaScript with no build step. A lightweight CSS framework (Pico.css or similar) provides the base terminal aesthetic. The app is served on a configurable local port (default 8080).

**Cloud replacements:** No cloud services are used. All data is local. The only external dependency is the initial data fetch (schedule, speakers, expo booths) which happens once before air-gapping.

## Data Models

### Table: `talks`

| Column        | Type     | Constraints        | Description                          |
|---------------|----------|--------------------|--------------------------------------|
| id            | INTEGER  | PRIMARY KEY        | Unique talk identifier               |
| title         | TEXT     | NOT NULL           | Talk title                           |
| speaker_id    | INTEGER  | NOT NULL, FK → speakers.id | Speaker who gives the talk  |
| day           | TEXT     | NOT NULL           | Conference day (e.g. "day1", "day2") |
| start_time    | TEXT     | NOT NULL           | ISO 8601 start time (e.g. "2026-06-29T14:00:00") |
| end_time      | TEXT     | NOT NULL           | ISO 8601 end time                    |
| room          | TEXT     | NOT NULL           | Room or hall name                    |
| track         | TEXT     |                    | Track name (e.g. "Infrastructure", "ML Ops") |
| description   | TEXT     |                    | Talk abstract                        |
| tags          | TEXT     |                    | JSON array of tags (e.g. `["rag","local-models"]`) |

### Table: `speakers`

| Column        | Type     | Constraints        | Description                          |
|---------------|----------|--------------------|--------------------------------------|
| id            | INTEGER  | PRIMARY KEY        | Unique speaker identifier            |
| name          | TEXT     | NOT NULL           | Speaker full name                    |
| bio           | TEXT     |                    | Short bio / affiliation              |
| github        | TEXT     |                    | GitHub handle or URL                 |
| twitter       | TEXT     |                    | Twitter/X handle                     |

### Table: `booths`

| Column        | Type     | NOT NULL | Description                          |
|---------------|----------|----------|--------------------------------------|
| id            | INTEGER  | PRIMARY KEY | Unique booth identifier           |
| company       | TEXT     | YES      | Company / organization name          |
| description   | TEXT     | YES      | What they're showcasing              |
| tags          | TEXT     | YES      | JSON array of tags (e.g. `["llm","infra"]`) |
| grid_x        | REAL     | YES      | X coordinate on the expo grid        |
| grid_y        | REAL     | YES      | Y coordinate on the expo grid        |
| grid_w        | REAL     | YES      | Booth width on the grid              |
| grid_h        | REAL     | YES      | Booth height on the grid             |

### Table: `contacts`

| Column        | Type     | NOT NULL | Description                          |
|---------------|----------|----------|--------------------------------------|
| id            | INTEGER  | PRIMARY KEY | Unique contact identifier         |
| name          | TEXT     | YES      | Contact's name                       |
| github        | TEXT     | YES      | Contact's GitHub handle              |
| project       | TEXT     | YES      | What they're working on              |
| scanned_at    | TEXT     | YES      | ISO 8601 timestamp of scan           |

## API Endpoints

### Schedule & Search

- `GET /api/talks` — List all talks with optional query params:
  - `q` — free-text search across title, description, tags, speaker name
  - `day` — filter by day (e.g. "day1")
  - `track` — filter by track
  - `speaker` — filter by speaker name (partial match)
  - Returns JSON array of talk objects

- `GET /api/talks/<id>` — Get a single talk by ID with speaker details

### Speakers

- `GET /api/speakers` — List all speakers
- `GET /api/speakers/<id>` — Get a single speaker by ID

### Expo

- `GET /api/booths` — List all expo booths
- `GET /api/booths/<id>` — Get a single booth by ID

### Networking (QR)

- `POST /api/contacts` — Save a contact from QR scan. Body: `{ "name": "...", "github": "...", "project": "..." }`
- `GET /api/contacts` — List all saved contacts
- `DELETE /api/contacts/<id>` — Remove a contact
- `GET /api/badge` — Returns the current user's badge data as JSON (for QR generation). Body: `{ "name": "...", "github": "...", "project": "..." }` (set once via POST to same endpoint)

### Health

- `GET /api/health` — Returns `{ "status": "ok" }`

## Frontend Pages

### `/` — Schedule Search (Default View)

- Full-screen dark-mode layout
- Command palette overlay triggered by `Cmd+K` (or `Ctrl+K` on Linux)
- Palette contains a text input and live search results
- Results show talk title, speaker, time, room
- Clicking a result expands to show description and tags
- Below the palette: a filter bar (day, track, speaker) for refined searches
- `kind: source` — `index.html`, `css/main.css`, `js/schedule.js`

### `/badge` — Digital Badge

- Terminal-style display showing the user's badge info as raw JSON
- Large QR code rendered on screen (generated client-side from JSON payload)
- "Edit" button to update name, GitHub, project
- `kind: source` — `badge.html`, `css/badge.css`, `js/badge.js`

### `/expo` — Expo Map

- SVG-based vector map of the expo floor
- Booths rendered as colored rectangles on a grid
- Click to pin/unpin booths
- "Calculate Route" button runs a local pathfinding algorithm (nearest-neighbor TSP heuristic)
- Route drawn as a highlighted path connecting pinned booths
- `kind: source` — `expo.html`, `css/expo.css`, `js/expo.js`

### `/contacts` — Saved Contacts

- List view of all scanned contacts
- Each contact shows name, GitHub, project
- Click to open GitHub link (if network available)
- Delete button per contact
- `kind: source` — `contacts.html`, `css/contacts.css`, `js/contacts.js`

## Library Dependencies (vendored)

| Library | Kind | Source URL | Usage |
|---------|------|------------|-------|
| qrcode.js | library | `https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js` | Client-side QR code generation |
| Pico.css | library | `https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css` | Base CSS framework, terminal aesthetic |

## File Manifest

```
/app/
├── main.py                          # FastAPI app entry point (kind: source)
├── requirements.txt                 # Python dependencies (kind: source)
├── schema.sql                       # SQLite schema (kind: source)
├── seed.py                          # Seed data population script (kind: source)
├── start.sh                         # Container entrypoint (kind: source)
├── Dockerfile                       # Container image (kind: source)
├── docker-compose.yml               # Orchestration (kind: source)
├── src/
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── talks.py            # Schedule/search routes (kind: source)
│   │   │   ├── speakers.py         # Speaker routes (kind: source)
│   │   │   ├── booths.py           # Expo routes (kind: source)
│   │   │   └── contacts.py         # QR/networking routes (kind: source)
│   │   └── database.py             # SQLite connection helper (kind: source)
│   └── frontend/
│       ├── index.html              # Schedule search page (kind: source)
│       ├── badge.html              # Digital badge page (kind: source)
│       ├── expo.html               # Expo map page (kind: source)
│       ├── contacts.html           # Saved contacts page (kind: source)
│       ├── css/
│       │   ├── main.css            # Global styles, dark theme (kind: source)
│       │   ├── badge.css           # Terminal badge styling (kind: source)
│       │   ├── expo.css            # Expo map styling (kind: source)
│       │   └── contacts.css        # Contacts list styling (kind: source)
│       ├── js/
│       │   ├── schedule.js         # Command palette + search logic (kind: source)
│       │   ├── badge.js            # Badge edit + QR render (kind: source)
│       │   ├── expo.js             # Pinning + route calculation (kind: source)
│       │   └── contacts.js         # Contact CRUD (kind: source)
│       └── libs/
│           ├── qrcode.min.js       # QR code library (kind: library)
│           └── pico.min.css        # Pico CSS framework (kind: library)
└── data/
    └── worldsfair.db               # SQLite database (kind: runtime-generated)
```

## Pathfinding Algorithm (Expo)

For the expo route optimization, a nearest-neighbor greedy TSP heuristic is used:

1. Start at the expo entrance (fixed grid position, e.g., `grid_x=0, grid_y=0`).
2. From the current position, find the nearest unvisited pinned booth.
3. Move to that booth, mark it visited.
4. Repeat until all pinned booths are visited.
5. Return to entrance.

This is O(n²) and sufficient for <100 booths. The route is rendered as an SVG polyline overlay on the map.

## Security & Air-Gap Compliance

- No outbound network calls from the application.
- All data stored locally in SQLite.
- QR payloads are plain JSON, no encryption needed (contacts are opt-in, low-sensitivity).
- No analytics, telemetry, or crash reporting.
- The initial data fetch (schedule, speakers, booths) is a one-time operation performed before air-gapping.
