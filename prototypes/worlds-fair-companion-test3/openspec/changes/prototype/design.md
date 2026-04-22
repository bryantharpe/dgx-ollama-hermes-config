# Design: World's Fair Companion

**Change:** prototype
**Stack:** Python 3.12-slim + FastAPI + Uvicorn + SQLite + vanilla HTML/CSS/JS

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│  Browser (vanilla HTML/CSS/JS)                  │
│  ┌─────────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Cmd+K Search│  │ QR Badge │  │ Expo Map   │ │
│  │ (talks)     │  │ Gen/Scan │  │ + Routing  │ │
│  └──────┬──────┘  └────┬─────┘  └──────┬─────┘ │
│         │               │               │        │
│         └───────────────┼───────────────┘        │
│                         │ HTTP (local)            │
│                    ┌────▼────┐                    │
│                    │ FastAPI │                    │
│                    │ Uvicorn │                    │
│                    └────┬────┘                    │
│                         │                         │
│                    ┌────▼────┐                    │
│                    │ SQLite  │                    │
│                    │ (local) │                    │
│                    └─────────┘                    │
└─────────────────────────────────────────────────┘
```

The app is served by a single FastAPI instance running on a local port (assigned by the build-phase skill). All data lives in a SQLite database file. The frontend is vanilla HTML/CSS/JS — no framework, no build step. The entire stack runs on a single laptop or mini-PC connected to a closed Wi-Fi network. After initial data seeding (schedule, speakers, expo booths), the device is fully air-gapped.

## Data Model

### Table: `talks`

Conference talks with metadata for filtering and search.

| Column          | Type     | Constraints        | Description                          |
|-----------------|----------|--------------------|--------------------------------------|
| id              | INTEGER  | PRIMARY KEY        | Unique talk identifier               |
| title           | TEXT     | NOT NULL           | Talk title                           |
| speaker_id      | INTEGER  | NOT NULL, FK       | References `speakers.id`             |
| day             | TEXT     | NOT NULL           | Day of conference (e.g. "Day 1")     |
| start_time      | TEXT     | NOT NULL           | Start time in HH:MM format           |
| end_time        | TEXT     | NOT NULL           | End time in HH:MM format             |
| room            | TEXT     | NOT NULL           | Room or stage name                   |
| description     | TEXT     |                    | Talk abstract                        |
| tags            | TEXT     | NOT NULL           | Comma-separated topic tags           |
| track           | TEXT     |                    | Broad track category (e.g. "ML Ops") |

### Table: `speakers`

Speaker information.

| Column       | Type    | Constraints        | Description                    |
|--------------|---------|--------------------|--------------------------------|
| id           | INTEGER | PRIMARY KEY        | Unique speaker identifier      |
| name         | TEXT    | NOT NULL           | Speaker full name              |
| bio          | TEXT    |                    | Short bio                      |
| company      | TEXT    |                    | Company or organization        |
| github       | TEXT    |                    | GitHub handle (no @ prefix)    |
| twitter      | TEXT    |                    | Twitter/X handle (optional)    |

### Table: `expo_booths`

Expo floor booths with location data for routing.

| Column        | Type     | Constraints        | Description                          |
|---------------|----------|--------------------|--------------------------------------|
| id            | INTEGER  | PRIMARY KEY        | Unique booth identifier              |
| company_name  | TEXT     | NOT NULL           | Company or organization name         |
| description   | TEXT     |                    | What the company does                |
| tags          | TEXT     |                    | Comma-separated topics they cover    |
| grid_x        | REAL     | NOT NULL           | X coordinate on the expo grid        |
| grid_y        | REAL     | NOT NULL           | Y coordinate on the expo grid        |
| hall          | TEXT     | NOT NULL           | Hall name (e.g. "Hall A")            |
| booth_number  | TEXT     |                    | Booth number label (e.g. "A-142")    |

### Table: `saved_contacts`

Contacts saved via QR scanning.

| Column       | Type    | Constraints        | Description                    |
|--------------|---------|--------------------|--------------------------------|
| id           | INTEGER | PRIMARY KEY        | Unique contact record          |
| name         | TEXT    | NOT NULL           | Contact's name                 |
| github       | TEXT    |                    | GitHub handle                  |
| project      | TEXT    |                    | What they're working on        |
| scanned_at   | TEXT    | NOT NULL           | ISO-8601 timestamp of scan     |
| source_id    | TEXT    |                    | Unique ID from the scanned QR  |

## API Routes

### Schedule & Search

- `GET /api/talks` — List all talks with optional query params:
  - `day` — filter by day
  - `q` — full-text search across title, description, and tags
  - `tag` — filter by exact tag match
- `GET /api/talks/search?q=<query>` — Command-palette search endpoint returning matching talks sorted by relevance (tag match > title match > description match)
- `GET /api/speakers` — List all speakers
- `GET /api/speakers/<id>` — Get speaker detail by ID

### Expo

- `GET /api/booths` — List all expo booths
- `GET /api/booths/search?q=<query>` — Search booths by company name, tags, or description
- `POST /api/booths/<id>/pin` — Pin a booth for routing
- `GET /api/booths/pinned` — Get list of pinned booth IDs
- `POST /api/routes/calculate` — Calculate optimized route through pinned booths (returns ordered list of booth IDs)
- `GET /api/expo/map` — Return expo floor SVG data (static vector map with grid overlay)

### Networking / QR

- `POST /api/contacts/scan` — Decode and save a contact from a scanned QR payload
  - Request body: `{ "name": "string", "github": "string", "project": "string", "source_id": "string" }`
- `GET /api/contacts` — List all saved contacts
- `GET /api/contacts/<id>` — Get a specific contact
- `DELETE /api/contacts/<id>` — Remove a saved contact
- `GET /api/badge` — Generate current user's badge data as JSON (for QR encoding on the frontend)

### Health

- `GET /api/health` — Health check (returns `{"status": "ok"}`)

## Frontend Design

### Visual Style

- **IDE-like, terminal aesthetic** — dark mode by default
- Monospace font for primary text
- Minimal chrome, high information density
- Raw JSON/terminal-inspired badge design
- Color-coded tags for talk categories

### Key UI Components

1. **Command Palette (`Cmd+K`)** — Centered search overlay with instant results. Type to filter talks by topic, speaker, or time. Results show title, speaker, time, room, and matching tags.

2. **Schedule View** — Day-by-day timeline view. Clicking a talk shows speaker info and description. Filter bar at top for day and tag selection.

3. **QR Badge** — Full-screen view displaying the user's digital badge as a terminal-style card with name, GitHub, and project. Generates a QR code (client-side JS library) encoding the JSON payload. Also includes a "scan" mode that uses the device camera to decode incoming QR codes.

4. **Expo Map** — SVG-based vector map of the expo floor. Booths rendered as labeled rectangles on a grid. Pinned booths highlighted in accent color. Route button calculates and draws a path connecting pinned booths in optimized order.

5. **Contacts List** — Simple list of scanned contacts with name, GitHub link, and project description.

### QR Code Handling

- **Generation:** Client-side QR encoding using a lightweight JS library (e.g., `qrcode.js`). Encodes JSON: `{ "name": "...", "github": "...", "project": "...", "source_id": "uuid" }`.
- **Scanning:** Client-side QR decoding using the device camera (`getUserMedia` API) with a JS QR decoder library. Decoded JSON is POSTed to `/api/contacts/scan` for local storage.

### Expo Route Optimization

- Grid-based pathfinding using a simplified A* algorithm running in the browser.
- Booth positions defined by `grid_x`/`grid_y` coordinates on the expo floor.
- Route optimization uses a greedy nearest-neighbor heuristic starting from the map entrance point.
- Path drawn as SVG polyline overlay on the expo map.

## Security & Air-Gap Constraints

- **Zero external dependencies** after initial data seeding. No CDN links, no external APIs, no analytics.
- All JS and CSS bundled inline or served from the local FastAPI static directory.
- QR codes contain only non-sensitive profile data (name, GitHub, project). No email, no phone, no location.
- SQLite database stored locally on the serving device. No replication or sync.
- The app runs on a private Wi-Fi network. No public-facing exposure.

## File Structure

```
worlds-fair-companion-test3/
├── schema.sql          # SQLite schema (all tables)
├── seed.py             # Seed data population script
├── requirements.txt    # Python dependencies
├── main.py             # FastAPI application entry point
├── static/
│   ├── index.html      # Single-page app shell
│   ├── app.js          # Frontend application logic
│   ├── style.css       # Terminal/IDE dark theme styles
│   └── expo-map.svg    # Static expo floor vector map
└── openspec/
    └── changes/
        └── prototype/
            ├── proposal.md
            ├── design.md
            └── tasks.md
```
