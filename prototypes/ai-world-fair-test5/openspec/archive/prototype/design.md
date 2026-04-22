# Design: AI Engineer World's Fair Companion

## Architecture Overview

A single Python FastAPI application serves a vanilla HTML/CSS/JS frontend. All data lives in a local SQLite database. The app runs on a laptop or mini-PC connected to a closed, private Wi-Fi router. Once the initial schedule data is loaded, the machine is physically disconnected from the internet.

```
┌─────────────────────────────────────────────┐
│  Laptop / Mini-PC (airgapped)               │
│                                             │
│  ┌──────────┐    ┌──────────────────────┐   │
│  │ FastAPI  │───▶│  SQLite              │   │
│  │ (Uvicorn)│    │  /app/data/fair.db   │   │
│  └────┬─────┘    └──────────────────────┘   │
│       │                                     │
│       │ serves static HTML/CSS/JS           │
│       ▼                                     │
│  ┌──────────────────────────────────────┐   │
│  │  Frontend (vanilla JS, HTML, CSS)    │   │
│  │  - Command Palette (Cmd+K)           │   │
│  │  - Schedule View                     │   │
│  │  - Digital Badge + QR Generator      │   │
│  │  - Expo Floor Map + Route Planner    │   │
│  └──────────────────────────────────────┘   │
│                                             │
│  Private Wi-Fi Router (closed network)      │
│       ▲                                     │
│       │                                     │
│  ┌────┴─────┐  ┌────────────────────────┐  │
│  │  Phone   │  │  Phone                 │  │
│  │  (scan)  │  │  (scan)                │  │
│  └──────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Runtime | Python 3.12-slim Docker image |
| Web Framework | FastAPI + Uvicorn |
| Database | SQLite (single file, no server) |
| Frontend | Vanilla HTML5 + CSS3 + ES6 JavaScript |
| QR Library | `qrcode.js` (v7.1.0, library) |
| CSS Framework | None — custom terminal/IDE theme |
| Deployment | Single container, private Wi-Fi |

## Data Model

### Table: `talks`

Talks at the conference with metadata for filtering.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique talk identifier |
| `title` | TEXT NOT NULL | | Talk title |
| `speaker_name` | TEXT NOT NULL | | Speaker's full name |
| `speaker_bio` | TEXT | | Short speaker biography |
| `speaker_github` | TEXT | | Speaker's GitHub handle |
| `start_time` | TEXT NOT NULL | | ISO 8601 start time (e.g. "2026-06-29T14:00:00") |
| `end_time` | TEXT NOT NULL | | ISO 8601 end time |
| `room` | TEXT NOT NULL | | Room or hall name |
| `description` | TEXT | | Talk abstract |
| `topics` | TEXT NOT NULL | | Comma-separated topic tags (e.g. "rag,pipelines,local-models") |
| `track` | TEXT | | Conference track (e.g. "AI Infra", "ML Ops", "Agents") |
| `level` | TEXT | | Difficulty: "beginner", "intermediate", "advanced" |

**Seed example row:**
```
1, 'Building RAG Pipelines That Actually Work', 'Dr. Maya Chen', 'ML engineer specializing in retrieval-augmented generation systems', 'mayachen', '2026-06-29T14:00:00', '2026-06-29T14:45:00', 'Moscone South 201', 'Most RAG systems fail at retrieval quality. This talk covers embedding strategies, chunking heuristics, and re-ranking techniques for production-grade pipelines.', 'rag,pipelines,retrieval,embeddings', 'AI Infra', 'intermediate'
```

### Table: `speakers`

Speaker directory (can be derived from talks, but stored separately for the speaker search feature).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique speaker identifier |
| `name` | TEXT NOT NULL | | Speaker's full name |
| `bio` | TEXT | | Short biography |
| `github` | TEXT | | GitHub handle |
| `company` | TEXT | | Company or organization |
| `talk_ids` | TEXT | | Comma-separated talk IDs |

**Seed example row:**
```
1, 'Dr. Maya Chen', 'ML engineer specializing in retrieval-augmented generation systems', 'mayachen', 'Hugging Face', '1'
```

### Table: `booths`

Expo floor booths with location metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique booth identifier |
| `name` | TEXT NOT NULL | | Company or booth name |
| `description` | TEXT | | What the booth does / demos |
| `zone` | TEXT NOT NULL | | Expo floor zone (e.g. "Hall A", "Hall B") |
| `grid_x` | INTEGER NOT NULL | | X coordinate on the grid overlay |
| `grid_y` | INTEGER NOT NULL | | Y coordinate on the grid overlay |
| `topics` | TEXT | | Comma-separated topics the booth covers |

**Seed example row:**
```
1, 'NeuralForge', 'Open-source model training infrastructure for small teams', 'Hall A', 12, 8, 'training,distributed,open-source'
```

### Table: `contacts`

Hallway-track contacts saved via QR scan.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique contact identifier |
| `name` | TEXT NOT NULL | | Contact's full name |
| `github` | TEXT | | GitHub handle |
| `hacking_on` | TEXT | | What they're currently working on |
| `scanned_at` | TEXT NOT NULL | | ISO 8601 timestamp of scan |
| `badge_json` | TEXT | | Raw compressed JSON from the QR code |

**Seed example row:**
```
1, 'Alex Rivera', 'arivera', 'Building a multi-agent orchestration framework for code review', '2026-06-29T16:30:00', '{"name":"Alex Rivera","github":"arivera","hacking_on":"Building a multi-agent orchestration framework for code review"}'
```

### Table: `user_schedule`

User's pinned/favorite talks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique entry identifier |
| `talk_id` | INTEGER NOT NULL | FOREIGN KEY → talks(id) | Referenced talk |
| `pinned_at` | TEXT NOT NULL | | ISO 8601 timestamp |

**Seed example row:**
```
1, 1, '2026-06-29T13:55:00'
```

### Table: `user_pins`

User's pinned expo booths.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique entry identifier |
| `booth_id` | INTEGER NOT NULL | FOREIGN KEY → booths(id) | Referenced booth |
| `pinned_at` | TEXT NOT NULL | | ISO 8601 timestamp |

**Seed example row:**
```
1, 1, '2026-06-29T10:00:00'
```

## API Endpoints

### Schedule

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/talks` | List all talks with optional query params: `q` (text search across title, speaker, topics, description), `topic` (filter by topic tag), `track` (filter by track), `level` (filter by difficulty), `speaker` (filter by speaker name) |
| GET | `/api/talks/{id}` | Get a single talk by ID |
| GET | `/api/speakers` | List all speakers with optional `q` param |
| GET | `/api/speakers/{id}` | Get a single speaker by ID |
| GET | `/api/schedule` | Get the user's pinned schedule (joins `user_schedule` with `talks`) |
| POST | `/api/schedule/pin` | Pin a talk: `{ "talk_id": 1 }` |
| DELETE | `/api/schedule/unpin/{talk_id}` | Unpin a talk |

### Networking

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/contacts` | List all scanned contacts, optionally with `q` param for search |
| POST | `/api/contacts` | Save a contact from QR scan: `{ "name": "...", "github": "...", "hacking_on": "...", "badge_json": "..." }` |
| GET | `/api/badge` | Get the current user's badge data as JSON (for QR generation) |
| POST | `/api/badge` | Update the current user's badge: `{ "name": "...", "github": "...", "hacking_on": "..." }` |

### Expo

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/booths` | List all booths, optionally with `q` param or `zone` filter |
| GET | `/api/booths/{id}` | Get a single booth by ID |
| GET | `/api/expo/pins` | Get the user's pinned booths |
| POST | `/api/expo/pin` | Pin a booth: `{ "booth_id": 1 }` |
| DELETE | `/api/expo/unpin/{booth_id}` | Unpin a booth |
| GET | `/api/expo/route` | Get route between all pinned booths (returns ordered list of booth IDs using grid-based pathfinding) |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check — returns `{ "status": "ok" }` |

## Frontend Architecture

### File Structure

```
frontend/
├── index.html              kind: source
├── css/
│   ├── main.css            kind: source
│   └── terminal.css        kind: source
├── js/
│   ├── app.js              kind: source
│   ├── command-palette.js  kind: source
│   ├── schedule.js         kind: source
│   ├── badge.js            kind: source
│   ├── expo-map.js         kind: source
│   └── qrcode.js           kind: library  (qrcode.js v7.1.0, pinned: https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js)
```

### Command Palette (Cmd+K)

- A full-screen overlay triggered by `Cmd+K` / `Ctrl+K`.
- Debounced input (200ms) sends GET requests to `/api/talks?q=...` and `/api/speakers?q=...`.
- Results rendered in a ranked list with title, speaker, time, and room.
- Arrow-key navigation + Enter to select. Escape to dismiss.
- Supports topic-tag filtering via `/api/talks?topic=...`.

### Schedule View

- Default landing page showing today's talks in a timeline layout.
- Each talk card shows: time, room, title, speaker, topics as tags.
- Pin/unpin toggle on each card (updates `user_schedule`).
- Filter bar: topic chips, track dropdown, level selector.

### Digital Badge

- Terminal-style card displaying name, GitHub handle, and "hacking on" description.
- Generates a QR code from a compressed JSON payload using `qrcode.js`.
- QR payload format: `{"name":"...","github":"...","hacking_on":"..."}` (URL-safe base64 encoded, max ~200 chars to keep QR scannable).
- Editable inline — click to modify fields, then regenerate QR.

### Expo Map

- SVG vector floor map with zones (Hall A, Hall B, etc.).
- Booths rendered as clickable markers at their `grid_x`/`grid_y` positions.
- Pinned booths highlighted in a distinct color.
- Route overlay: a polyline connecting pinned booths in optimized order (nearest-neighbor heuristic on grid coordinates).
- Clicking a booth marker shows a tooltip with name and description.

### Grid-Based Pathfinding

- The expo map overlays a coordinate grid.
- Route calculation uses a nearest-neighbor greedy algorithm on booth grid positions.
- Path rendered as an SVG `<polyline>` between booth positions.
- No external mapping libraries — pure client-side SVG manipulation.

### Terminal/IDE Theme

- Dark background (`#1a1b26`), monospace font (JetBrains Mono or system monospace).
- Accent colors: green (`#73daca`) for success/active, yellow (`#e5c07b`) for highlights, red (`#ff5370`) for errors.
- Minimal chrome — no rounded corners, no shadows, no gradients.
- Command palette uses a frosted-glass overlay with a blinking cursor.

## Security & Air-Gap Considerations

- **Zero external network calls** after initial data load. All API endpoints serve from local SQLite.
- **No analytics, no telemetry, no CDN dependencies** at runtime.
- QR library (`qrcode.js`) is vendored during build — no runtime network fetch.
- User data (contacts, pinned talks, pinned booths) stored in SQLite only — no cloud sync.
- The badge QR payload is plain JSON, no encryption needed (it contains only public info).

## Asset Manifest

| Asset | Kind | Source / Notes |
|-------|------|----------------|
| `frontend/js/qrcode.js` | library | `https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js` — vendored at build time |
| `frontend/index.html` | source | Single-page app shell |
| `frontend/css/main.css` | source | Layout and utility styles |
| `frontend/css/terminal.css` | source | Terminal/IDE theme variables and components |
| `frontend/js/app.js` | source | App initialization, routing, API client |
| `frontend/js/command-palette.js` | source | Cmd+K overlay, search, keyboard nav |
| `frontend/js/schedule.js` | source | Schedule timeline, filters, pin/unpin |
| `frontend/js/badge.js` | source | Digital badge display, QR generation, edit mode |
| `frontend/js/expo-map.js` | source | SVG map rendering, booth markers, route overlay |
| `schema.sql` | source | SQLite schema with all tables |
| `seed.py` | source | Populates SQLite with sample conference data |
