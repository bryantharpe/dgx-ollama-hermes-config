# Tasks: World's Fair Companion

**Change:** prototype
**Phase:** Implementation

## Phase 1 — Schema & Seed Data

- [x] Create `schema.sql` with all four tables: `talks`, `speakers`, `expo_booths`, `saved_contacts` (including all columns, types, constraints, and foreign keys as defined in design.md)
- [x] Create `seed.py` that populates the SQLite database with realistic sample data:
  - [x] At least 30 talks across 4 days with varied topics (RAG, local LLMs, model orchestration, fine-tuning, MLOps, etc.)
  - [x] At least 15 speakers with names, bios, companies, and GitHub handles
  - [x] At least 20 expo booths with grid coordinates distributed across 2 halls
  - [x] Ensure every column referenced in seed data exists in the schema DDL
- [x] Create `requirements.txt` with dependencies: `fastapi`, `uvicorn[standard]`, `aiosqlite`
- [x] Verify seed script runs successfully and produces a valid SQLite database

## Phase 2 — Backend API

- [x] Create `main.py` with FastAPI application setup and Uvicorn configuration
- [x] Implement `GET /api/health` returning `{"status": "ok"}`
- [x] Implement `GET /api/talks` with optional `day`, `q`, and `tag` query parameters
- [x] Implement `GET /api/talks/search?q=<query>` with relevance-sorted full-text search (tag match > title match > description match)
- [x] Implement `GET /api/speakers` returning all speakers
- [x] Implement `GET /api/speakers/<id>` returning speaker detail
- [x] Implement `GET /api/booths` returning all expo booths
- [x] Implement `GET /api/booths/search?q=<query>` searching by company name, tags, and description
- [x] Implement `POST /api/booths/<id>/pin` to add a booth to the user's pinned list (store in SQLite)
- [x] Implement `GET /api/booths/pinned` returning list of pinned booth IDs
- [x] Implement `POST /api/routes/calculate` accepting pinned booth IDs and returning an optimized route (greedy nearest-neighbor heuristic)
- [x] Implement `GET /api/expo/map` returning expo floor SVG data
- [x] Implement `POST /api/contacts/scan` accepting contact JSON and saving to `saved_contacts` table
- [x] Implement `GET /api/contacts` returning all saved contacts
- [x] Implement `GET /api/contacts/<id>` returning a specific contact
- [x] Implement `DELETE /api/contacts/<id>` removing a saved contact
- [x] Implement `GET /api/badge` returning current user's badge data as JSON
- [x] Configure static file serving for `static/` directory
- [x] Test all API endpoints with curl or similar tool

## Phase 3 — Frontend Shell & Styling

- [x] Create `static/index.html` with single-page app structure:
  - [x] Command palette trigger button and overlay container
  - [x] Schedule view container
  - [x] QR badge view container
  - [x] Expo map view container
  - [x] Contacts list view container
  - [x] Navigation bar with view switcher
- [x] Create `static/style.css` with terminal/IDE dark theme:
  - [x] Dark background (#0d1117 or similar)
  - [x] Monospace font (JetBrains Mono, Fira Code, or system monospace fallback)
  - [x] Color-coded tag styles for different talk categories
  - [x] Command palette overlay styling with glow effects
  - [x] Terminal-inspired badge card styling
  - [x] Expo map SVG container styling
  - [x] Responsive layout for laptop and mini-PC screens
- [x] Verify page loads and renders all view containers

## Phase 4 — Command Palette & Schedule

- [x] Create `static/app.js` with application state management and routing
- [x] Implement Cmd+K keyboard shortcut to open/close command palette
- [x] Implement command palette input with debounced search
- [x] Connect command palette to `GET /api/talks/search?q=` endpoint
- [x] Display search results in palette with talk title, speaker, time, room, and matching tags
- [x] Clicking a result navigates to the schedule view filtered to that talk
- [x] Implement schedule view with day-by-day timeline layout
- [x] Implement day selector tabs (Day 1 through Day 4)
- [x] Implement tag filter bar above the schedule
- [x] Clicking a talk card shows speaker info and description in a detail panel
- [x] Handle schedule collision detection (highlight overlapping talks)

## Phase 5 — QR Networking

- [x] Include a lightweight client-side QR code library (embed `qrcode.js` or equivalent in `static/`)
- [x] Implement QR badge generation view:
  - [x] Display user profile card (name, GitHub, project) in terminal-style layout
  - [x] Generate QR code encoding JSON payload: `{ "name", "github", "project", "source_id" }`
  - [x] Display the QR code as a canvas or SVG element
- [x] Implement QR scanning view:
  - [x] Request camera access via `getUserMedia` API
  - [x] Include a client-side QR decoder library
  - [x] Decode scanned QR codes and extract JSON payload
  - [x] POST decoded data to `/api/contacts/scan`
  - [x] Show confirmation toast on successful save
- [x] Implement contacts list view:
  - [x] Display saved contacts with name, GitHub link, and project
  - [x] Show timestamp of when each contact was scanned
  - [x] Delete button for each contact

## Phase 6 — Expo Map & Routing

- [x] Create `static/expo-map.svg` with vector expo floor layout:
  - [x] Two halls (Hall A and Hall B) with grid overlay
  - [x] Entrance point marked
  - [x] Booth positions mapped to grid coordinates matching `expo_booths.grid_x`/`grid_y`
  - [x] Booth labels rendered as text elements
- [x] Implement expo map view in the frontend:
  - [x] Render SVG map from `expo-map.svg`
  - [x] Load booth data from `/api/booths` and overlay on map
  - [x] Pinned booths highlighted with accent color
  - [x] Clicking a booth shows company info in a side panel
  - [x] Pin/unpin toggle on each booth
- [x] Implement route calculation:
  - [x] "Calculate Route" button when 2+ booths are pinned
  - [x] Client-side greedy nearest-neighbor algorithm starting from entrance
  - [x] Draw route as SVG polyline overlay on the map
  - [x] Show estimated walking distance and booth order
- [x] Implement expo search:
  - [x] Search bar filtering booths by company name, tags, or description
  - [x] Search results highlight matching booths on the map

## Phase 7 — Polish & Integration

- [x] Add loading states for all API calls
- [x] Add error handling for offline scenarios (should be unnecessary but defensive)
- [x] Ensure all navigation between views works smoothly
- [x] Add keyboard shortcuts (Esc to close modals, arrow keys in command palette)
- [x] Test full user flows end-to-end:
  - [x] Search for a talk → view schedule → see speaker details
  - [x] Generate QR badge → simulate scan → view saved contact
  - [x] Pin 3 booths → calculate route → view optimized path
- [x] Verify zero external network calls (no CDN, no analytics, no external APIs)
- [x] Performance check: command palette search returns in <200ms
- [x] Final review: all design.md specifications implemented
