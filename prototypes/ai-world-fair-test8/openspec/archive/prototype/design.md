# Design: AI World's Fair Companion

**Change:** prototype
**Slug:** ai-world-fair-test8

## Architecture Overview

A single-process, airgapped web application served entirely from a local machine (laptop or mini-PC) on a closed Wi-Fi network. The stack is Python 3.12-slim + FastAPI + Uvicorn + SQLite + vanilla HTML/CSS/JS. No cloud services, no external APIs, no internet connectivity required after initial data population.

```
┌─────────────────────────────────────────────────┐
│                  Client (Browser)                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │Cmd+K     │  │Digital   │  │Expo Map      │  │
│  │Palette   │  │Badge     │  │+ Route Opt   │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │           │
│       └──────────────┼───────────────┘           │
│                      │ HTTP (localhost)          │
│              ┌───────┴───────┐                   │
│              │  Vanilla JS   │                   │
│              │  Frontend     │                   │
│              └───────┬───────┘                   │
└──────────────────────┼───────────────────────────┘
                       │
┌──────────────────────┼───────────────────────────┐
│              Server (FastAPI + Uvicorn)           │
│              ┌───────┴───────┐                   │
│              │  API Routes   │                   │
│              │  (Python)     │                   │
│              └───────┬───────┘                   │
│                      │                           │
│              ┌───────┴───────┐                   │
│              │   SQLite      │                   │
│              │   (local file)│                   │
│              └───────────────┘                   │
└─────────────────────────────────────────────────┘
```

**Deployment:** A single laptop or mini-PC runs the FastAPI server on a private Wi-Fi router. The initial schedule data is fetched from the public web once, then the device is disconnected from the internet. The app runs entirely on the local network.

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Runtime | Python 3.12-slim (Docker) | Lightweight, fast startup |
| Web Framework | FastAPI + Uvicorn | Async, fast, simple |
| Database | SQLite (single file) | Zero config, airgapped, queryable |
| Frontend | Vanilla HTML/CSS/JS | No build step, no dependencies |
| QR Generation | `qrcode` Python library (vendored) | Server-side badge QR codes |
| QR Scanning | `qrcode.js` (library, vendored) | Client-side QR decoding |
| Styling | Custom CSS (terminal aesthetic) | Dark mode, monospace fonts |

## Data Model

### Table: `talks`

Core entity representing conference talks.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique talk identifier |
| `talk_id` | TEXT | UNIQUE NOT NULL | External talk ID from conference data |
| `title` | TEXT NOT NULL | | Talk title |
| `abstract` | TEXT | | Talk description/abstract |
| `speaker_id` | INTEGER | REFERENCES speakers(id) | Foreign key to speaker |
| `start_time` | TEXT NOT NULL | ISO 8601 format | Talk start time (UTC) |
| `end_time` | TEXT NOT NULL | ISO 8601 format | Talk end time (UTC) |
| `room` | TEXT | | Room or stage name |
| `track` | TEXT | | Conference track (e.g., "Keynote", "Workshop") |
| `tags` | TEXT | JSON array as string | Topic tags (e.g., `["rag", "llm", "orchestration"]`) |
| `level` | TEXT | CHECK(level IN ('beginner','intermediate','advanced')) | Difficulty level |

### Table: `speakers`

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique speaker identifier |
| `speaker_id` | TEXT | UNIQUE NOT NULL | External speaker ID |
| `name` | TEXT NOT NULL | | Speaker full name |
| `bio` | TEXT | | Short biography |
| `github` | TEXT | | GitHub username or URL |
| `twitter` | TEXT | | Twitter/X handle or URL |
| `company` | TEXT | | Affiliated company/organization |

### Table: `booths`

Expo floor booths.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique booth identifier |
| `booth_id` | TEXT | UNIQUE NOT NULL | External booth ID |
| `name` | TEXT NOT NULL | | Company/booth name |
| `category` | TEXT | | Booth category (e.g., "Infrastructure", "ML Ops", "Data") |
| `grid_x` | INTEGER NOT NULL | | X coordinate on expo grid (0-indexed) |
| `grid_y` | INTEGER NOT NULL | | Y coordinate on expo grid (0-indexed) |
| `description` | TEXT | | Short description of what they do |
| `website` | TEXT | | Company website URL (informational only) |

### Table: `user_bookmarks`

User's personal bookmarks (stored in SQLite for prototype simplicity; in production would be per-user).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique bookmark identifier |
| `talk_id` | INTEGER | REFERENCES talks(id) | Foreign key to talks table |
| `created_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | When bookmarked |
| `type` | TEXT | CHECK(type IN ('talk','booth','speaker')) | What type of entity is bookmarked |
| `entity_id` | TEXT NOT NULL | | ID of the bookmarked entity (talk_id, booth_id, or speaker_id) |

### Table: `contacts`

Contacts exchanged via QR scanning.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique contact identifier |
| `name` | TEXT NOT NULL | | Contact's name |
| `github` | TEXT | | Contact's GitHub handle |
| `topic` | TEXT | | What they're working on (from badge) |
| `scanned_at` | TEXT | DEFAULT CURRENT_TIMESTAMP | When the contact was scanned |
| `raw_json` | TEXT | | Original compressed JSON from QR (for debugging) |

## API Endpoints

### Schedule & Talks

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/talks` | List all talks with optional query params: `?q=search_term`, `?tag=rag`, `?speaker=1`, `?track=workshop`, `?date=2026-06-29` |
| GET | `/api/talks/{id}` | Get a single talk with full details including speaker info |
| GET | `/api/talks/search` | Full-text search across talk titles, abstracts, and tags |
| GET | `/api/speakers` | List all speakers |
| GET | `/api/speakers/{id}` | Get speaker details and their talks |

### Networking

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/badge` | Generate badge data as JSON (for QR encoding) |
| POST | `/api/contacts/scan` | Decode and save a scanned contact: `{ "raw_json": "..." }` |
| GET | `/api/contacts` | List all saved contacts |
| DELETE | `/api/contacts/{id}` | Remove a contact |

### Expo

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/booths` | List all booths with optional `?category=...` filter |
| GET | `/api/booths/{id}` | Get booth details |
| POST | `/api/booths/{id}/pin` | Pin a booth to user's route |
| GET | `/api/booths/pinned` | List all pinned booths |
| POST | `/api/route/optimize` | Calculate optimized route through pinned booths: returns ordered list of booth IDs |

### User Data

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/bookmarks` | List all bookmarks |
| POST | `/api/bookmarks` | Create a bookmark: `{ "entity_id": "123", "type": "talk" }` |
| DELETE | `/api/bookmarks/{id}` | Remove a bookmark |

### Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check endpoint |

## Frontend Architecture

### Pages / Views

1. **Command Palette (`/`)** — Default view. Full-screen overlay triggered by `Cmd+K`. Shows search results in a list. Type-ahead filtering against local data.
2. **Talk Detail (`/talk/:id`)** — Full talk view with abstract, speaker info, related talks, and bookmark button.
3. **Schedule View (`/schedule`)** — Timeline view of all talks, filterable by date, track, and tags. Personal schedule with conflict detection.
4. **Expo Map (`/expo`)** — SVG-based vector map of the expo floor. Clickable booths, pin/unpin, route optimization button.
5. **Badge View (`/badge`)** — Terminal-style digital badge display. Shows user's name, GitHub, and current project. Generates QR code for scanning.
6. **Contacts (`/contacts`)** — List of scanned contacts with name, GitHub, and topic.

### UI Design System

- **Theme:** Dark mode default (`#0d1117` background, `#c9d1d9` text, `#58a6ff` accents)
- **Typography:** Monospace font stack (`'JetBrains Mono', 'Fira Code', 'SF Mono', monospace`)
- **Layout:** IDE-like sidebar navigation (collapsible), main content area, minimal chrome
- **Interactions:** Keyboard-first (`Cmd+K` for search, `Esc` to close modals, arrow keys for navigation)
- **Components:** Command palette (type-ahead search), badge card (terminal aesthetic), expo map (SVG with interactive overlays), contact cards (compact list)

### QR Code Implementation

**Badge Generation (server-side):**
- Python `qrcode` library generates QR from compressed JSON string
- JSON payload: `{ "name": "...", "github": "...", "topic": "..." }`
- Compressed via `zlib` before encoding to keep QR size small
- Rendered as inline SVG in the badge view

**Contact Scanning (client-side):**
- `qrcode.js` (vendored library) decodes QR from camera feed
- Uses WebRTC `getUserMedia` for camera access
- Decoded JSON is sent to `/api/contacts/scan` for storage
- No network calls beyond the local FastAPI server

### Expo Map Route Optimization

- Expo floor is represented as a 2D grid (e.g., 20×15 cells)
- Each booth has `grid_x` and `grid_y` coordinates
- Pinned booths are connected using a greedy nearest-neighbor algorithm (sufficient for prototype)
- Route is rendered as an SVG polyline overlay on the map
- Obstacles (stages, restrooms) are marked as non-traversable cells

## File Manifest

### Backend (kind: source)

| File | Description |
|------|-------------|
| `app/main.py` | FastAPI application entry point, middleware, static file serving |
| `app/database.py` | SQLite connection management, schema initialization |
| `app/models.py` | Pydantic models for request/response validation |
| `app/routes/talks.py` | Talk listing, search, detail endpoints |
| `app/routes/speakers.py` | Speaker listing and detail endpoints |
| `app/routes/expo.py` | Booth listing, pinning, route optimization |
| `app/routes/networking.py` | Badge generation, contact scanning endpoints |
| `app/routes/bookmarks.py` | Bookmark CRUD endpoints |
| `app/routes/health.py` | Health check endpoint |
| `app/utils/qr.py` | QR code generation (badge) and decoding helpers |
| `app/utils/routing.py` | Grid-based route optimization algorithm |
| `app/utils/search.py` | SQLite full-text search setup and query helpers |
| `schema.sql` | SQLite schema DDL (all tables) |
| `seed.py` | Seed data population script (talks, speakers, booths) |
| `requirements.txt` | Python dependencies |

### Frontend (kind: source)

| File | Description |
|------|-------------|
| `frontend/index.html` | Main page with command palette overlay |
| `frontend/talk.html` | Talk detail page |
| `frontend/schedule.html` | Schedule timeline view |
| `frontend/expo.html` | Expo map page with SVG rendering |
| `frontend/badge.html` | Digital badge page with QR display |
| `frontend/contacts.html` | Contacts list page |
| `frontend/css/style.css` | Global styles, dark theme, terminal aesthetic |
| `frontend/css/components.css` | Component-specific styles (palette, cards, map) |
| `frontend/js/app.js` | Main application logic, routing, state management |
| `frontend/js/palette.js` | Command palette implementation (Cmd+K, type-ahead) |
| `frontend/js/expo-map.js` | Expo map SVG rendering, booth pinning, route display |
| `frontend/js/routing.js` | Route optimization client-side visualization |
| `frontend/js/badge.js` | Badge rendering and QR code display |
| `frontend/js/contacts.js` | Contact list rendering and management |
| `frontend/js/search.js` | Client-side search and filtering utilities |

### Libraries (kind: library)

| File | Source URL | Description |
|------|-----------|-------------|
| `frontend/lib/qrcode.min.js` | `https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js` | Client-side QR code decoding from camera |

### Assets (kind: asset)

| File | Description |
|------|-------------|
| `frontend/assets/expo-floor.svg` | Vector SVG of the expo floor plan with booth positions |
| `frontend/assets/favicon.svg` | Terminal-style favicon |

### Runtime-generated (kind: runtime-generated)

| File | Description |
|------|-------------|
| `data/ai-world-fair.db` | SQLite database file (created by seed.py at startup) |

## Air-Gapped Constraints

- **Zero external network calls** after initial data load. All data is in the local SQLite file.
- **No CDN dependencies** — all JavaScript libraries are vendored locally.
- **No analytics, telemetry, or crash reporting.**
- **No authentication** — the app runs on a trusted local network.
- **No user accounts** — bookmarks and contacts are stored locally per device.
- **Static data** — the schedule, speakers, and booths are populated once before the event and never change during the event.

## Security Considerations

- The app runs on a private Wi-Fi network; no internet-facing exposure.
- QR codes contain only non-sensitive data (name, GitHub, topic).
- No user input is stored beyond contacts and bookmarks.
- SQLite file is local-only; no file sharing or network exposure of the database.
