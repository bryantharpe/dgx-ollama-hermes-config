# Design: World's Fair Companion

**Slug:** `worlds-fair-companion`
**Status:** Draft

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│  Browser (vanilla HTML/CSS/JS)              │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Cmd+K     │  │ Badge    │  │ Expo Map │ │
│  │ Palette   │  │ / QR     │  │ SVG+Path │ │
│  └─────┬─────┘  └────┬─────┘  └────┬─────┘ │
│        │              │              │       │
│        └──────────────┼──────────────┘       │
│                       │ fetch / POST          │
└───────────────────────┼──────────────────────┘
                        │ HTTP (localhost)
┌───────────────────────┼──────────────────────┐
│  FastAPI (Uvicorn)    │                      │
│  ┌────────────────────┴──────────────────┐   │
│  │  /api/talks/search?q=...              │   │
│  │  /api/talks/:id                       │   │
│  │  /api/talks/watchlist                 │   │
│  │  /api/contacts                        │   │
│  │  /api/expo/booths                     │   │
│  │  /api/expo/route                      │   │
│  │  /api/health                          │   │
│  └───────────────────────────────────────┘   │
│                       │                      │
│              ┌────────┴────────┐             │
│              │  SQLite (.db)   │             │
│              └─────────────────┘             │
└─────────────────────────────────────────────┘
```

Everything runs in a single container. FastAPI serves both the API and the static frontend files. No reverse proxy, no separate frontend server.

## Data Models

### Table: `talks`

Core schedule data. Seeded once from the public conference schedule before air-gap.

| Column          | Type         | Notes                              |
|-----------------|--------------|------------------------------------|
| id              | INTEGER      | PRIMARY KEY AUTOINCREMENT          |
| title           | TEXT NOT NULL| Talk title                         |
| speaker         | TEXT NOT NULL| Speaker name                       |
| speaker_bio     | TEXT         | Optional short bio                 |
| description     | TEXT         | Talk abstract                      |
| track           | TEXT NOT NULL| Conference track (e.g. "ML Ops")   |
| start_time      | TEXT NOT NULL| ISO 8601 (e.g. "2026-06-29T14:00") |
| end_time        | TEXT NOT NULL| ISO 8601                           |
| room            | TEXT         | Room or stage name                 |
| tags            | TEXT         | Comma-separated tech tags          |
| day             | TEXT NOT NULL| "day1" through "day4"              |

**Seed example row:**

```
1, 'Building RAG Pipelines That Actually Work', 'Jane Chen', 'ML engineer at Acme Corp with 8 years in retrieval systems.', 'A practical deep-dive into chunking strategies, embedding selection, and re-ranking for production RAG.', 'AI Engineering', '2026-06-29T14:00:00', '2026-06-29T14:45:00', 'Hall A', 'rag,embedding,retrieval', 'day1'
```

### Table: `watchlist`

User's pinned talks, stored per-device in the DB (prototype scope — no multi-user).

| Column    | Type         | Notes                          |
|-----------|--------------|--------------------------------|
| id        | INTEGER      | PRIMARY KEY AUTOINCREMENT      |
| talk_id   | INTEGER NOT NULL| FOREIGN KEY → talks(id)     |
| created_at| TEXT NOT NULL| ISO 8601 timestamp             |

**Seed example row:**

```
1, 1, '2026-06-29T10:00:00'
```

### Table: `contacts`

Scanned QR contacts, stored in the DB (prototype scope).

| Column        | Type         | Notes                              |
|---------------|--------------|------------------------------------|
| id            | INTEGER      | PRIMARY KEY AUTOINCREMENT          |
| name          | TEXT NOT NULL| Full name                          |
| github        | TEXT         | GitHub handle                      |
| project       | TEXT         | What they're working on            |
| scanned_at    | TEXT NOT NULL| ISO 8601 timestamp                 |

**Seed example row:**

```
1, 'Alex Rivera', 'arivera', 'Building local LLM inference on edge devices.', '2026-06-30T11:30:00'
```

### Table: `expo_booths`

Expo floor booth data.

| Column        | Type         | Notes                              |
|---------------|--------------|------------------------------------|
| id            | INTEGER      | PRIMARY KEY AUTOINCREMENT          |
| name          | TEXT NOT NULL| Company / booth name               |
| category      | TEXT NOT NULL| Booth category (e.g. "Infrastructure", "Models") |
| grid_x        | INTEGER NOT NULL| Grid column position (0-based)  |
| grid_y        | INTEGER NOT NULL| Grid row position (0-based)     |
| description   | TEXT         | Short booth description            |

**Seed example row:**

```
1, 'NeuralForge', 'Infrastructure', 3, 5, 'GPU cluster management for training runs.'
```

### Table: `pinned_booths`

User's pinned expo booths.

| Column      | Type         | Notes                          |
|-------------|--------------|--------------------------------|
| id          | INTEGER      | PRIMARY KEY AUTOINCREMENT      |
| booth_id    | INTEGER NOT NULL| FOREIGN KEY → expo_booths(id)|
| pinned_at   | TEXT NOT NULL| ISO 8601 timestamp             |

**Seed example row:**

```
1, 1, '2026-06-29T16:00:00'
```

## API Endpoints

### Schedule

- `GET /api/talks/search?q=<query>&track=<track>&day=<day>` — Full-text search across talks. `q` matches title, speaker, description, and tags. `track` and `day` are optional filters. Returns JSON array of talk objects.
- `GET /api/talks/<id>` — Single talk by ID. Returns full talk object.
- `GET /api/talks/watchlist` — List user's pinned talks.
- `POST /api/talks/watchlist` — Add a talk to watchlist. Body: `{ "talk_id": 1 }`.
- `DELETE /api/talks/watchlist/<id>` — Remove from watchlist.

### Networking

- `GET /api/contacts` — List all scanned contacts.
- `POST /api/contacts` — Save a scanned contact. Body: `{ "name": "...", "github": "...", "project": "..." }`.

### Expo

- `GET /api/expo/booths` — List all expo booths with grid positions.
- `GET /api/expo/booths/<id>` — Single booth details.
- `POST /api/expo/pin` — Pin a booth. Body: `{ "booth_id": 1 }`.
- `DELETE /api/expo/pin/<id>` — Unpin a booth.
- `GET /api/expo/route` — Calculate walking route between all pinned booths. Returns ordered list of booth IDs and grid coordinates. Uses a nearest-neighbor heuristic on the grid.

### Health

- `GET /api/health` — Returns `{ "status": "ok" }`.

## Frontend Design

### Visual Style

- **Theme:** Dark mode, terminal/IDE aesthetic. Monospace font for data, clean sans-serif for headings.
- **Color palette:** Dark background (`#0d1117`), muted green text (`#3fb950`) for accents, gray (`#8b949e`) for secondary text, white (`#f0f6fc`) for primary text.
- **Layout:** Full-width, single-page application with tab navigation (Schedule | Networking | Expo).

### Components

1. **Command Palette (`Cmd+K`)** — Modal overlay with a single input field. As user types, results appear below in a scrollable list. Each result shows talk title, speaker, time, and track. Enter to select, Escape to close.

2. **Digital Badge** — Terminal-style card showing name, GitHub handle, and project description in a monospace block. A QR code rendered below encodes the compressed JSON payload. Uses a client-side QR library.

3. **Expo Map** — SVG-based floor plan with booth rectangles positioned at their grid coordinates. Clicking a booth toggles its pinned state (visual highlight). Route overlay draws lines between pinned booths in visit order.

### Client-Side Libraries (vendor, do not hand-write)

- **`qrcode.min.js`** — `kind: library` — Client-side QR code generation and decoding. Source: `https://cdn.jsdelivr.net/npm/qrcode@1.5.4/build/qrcode.min.js` (version 1.5.4).
- **No other external JS libraries** — vanilla JS only for everything else.

### File Manifest

| File | Kind | Description |
|------|------|-------------|
| `index.html` | source | Single-page app shell with tab navigation |
| `css/style.css` | source | Terminal-dark theme styles |
| `js/app.js` | source | App initialization, tab switching, routing |
| `js/schedule.js` | source | Command palette, search, watchlist UI |
| `js/badge.js` | source | Digital badge rendering, QR generation/decode |
| `js/expo.js` | source | Expo map SVG, booth pinning, route calculation |
| `api/main.py` | source | FastAPI application, route handlers |
| `api/database.py` | source | SQLite connection, schema init |
| `api/schema.sql` | source | DDL for all tables |
| `api/seed.py` | source | Seed data population script |
| `requirements.txt` | source | Python dependencies (fastapi, uvicorn, aiosqlite) |

## Air-Gap Strategy

1. **Initial data fetch:** Before the event, run `seed.py` to populate SQLite with the public schedule and expo booth data. This is the only network operation.
2. **Physical disconnect:** After seeding, the host device disconnects from the internet.
3. **Local serving:** FastAPI serves the app on the private Wi-Fi network. All queries run against the local SQLite file.
4. **Zero outbound calls:** The frontend makes no requests to external services. QR codes are generated and decoded entirely in the browser.

## Pathfinding Algorithm (Expo Route)

A simple nearest-neighbor heuristic on the grid:

1. Start at the user's current booth (or the first pinned booth).
2. Find the nearest unpinned booth by Manhattan distance on the grid.
3. Move to that booth, mark it visited.
4. Repeat until all pinned booths are visited.
5. Draw lines connecting the sequence on the SVG map.

This is not optimal but is fast, deterministic, and sufficient for a prototype.
