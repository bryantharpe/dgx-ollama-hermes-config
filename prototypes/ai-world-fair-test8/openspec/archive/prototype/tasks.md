# Tasks: AI World's Fair Companion

**Change:** prototype
**Slug:** ai-world-fair-test8

## Phase 1: Database Schema & Seed Data

- [x] Write `schema.sql` with all four tables: `talks`, `speakers`, `booths`, `user_bookmarks`, `contacts` — include all columns, types, constraints, foreign keys, and CHECK constraints exactly as specified in design.md
- [x] Write `app/database.py` with SQLite connection management: `get_connection()`, `init_db()`, and `seed_db()` functions
- [x] Write `seed.py` to populate the database with realistic sample data:
  - [x] 30+ talks across 3 days with varied topics (RAG, LLMs, orchestration, fine-tuning, MLOps, data engineering)
  - [x] 15+ speakers with bios, GitHub handles, Twitter handles, and company affiliations
  - [x] 20+ expo booths across 5 categories (Infrastructure, ML Ops, Data, AI Security, Generative AI) with grid coordinates
  - [x] Verify seed data covers all tags, tracks, and difficulty levels mentioned in proposal
- [x] Write `app/utils/search.py` to set up SQLite FTS5 virtual tables for full-text search across talk titles, abstracts, and tags
- [x] Verify database by running `seed.py` and querying all tables for correctness

## Phase 2: Core API Routes

- [x] Write `app/routes/health.py` — GET `/api/health` returning `{"status": "ok"}`
- [x] Write `app/routes/talks.py`:
  - [x] GET `/api/talks` with query params: `q` (text search), `tag`, `speaker`, `track`, `date` — returns filtered talk list
  - [x] GET `/api/talks/{id}` — returns single talk with speaker info joined
  - [x] GET `/api/talks/search` — full-text search endpoint using FTS5
- [x] Write `app/routes/speakers.py`:
  - [x] GET `/api/speakers` — list all speakers
  - [x] GET `/api/speakers/{id}` — speaker details with their talks
- [x] Write `app/routes/expo.py`:
  - [x] GET `/api/booths` — list all booths with optional `?category=` filter
  - [x] GET `/api/booths/{id}` — single booth details
  - [x] GET `/api/booths/pinned` — list pinned booths (stored in user_bookmarks)
- [x] Write `app/routes/networking.py`:
  - [x] GET `/api/badge` — returns badge JSON data (name, github, topic)
  - [x] POST `/api/contacts/scan` — accepts `{ "raw_json": "..." }`, decodes, validates, and inserts into contacts table
  - [x] GET `/api/contacts` — list all saved contacts
  - [x] DELETE `/api/contacts/{id}` — remove a contact
- [x] Write `app/routes/bookmarks.py`:
  - [x] GET `/api/bookmarks` — list all bookmarks
  - [x] POST `/api/bookmarks` — create bookmark with `{ "entity_id": "...", "type": "talk|booth|speaker" }`
  - [x] DELETE `/api/bookmarks/{id}` — remove a bookmark
- [x] Wire all routes into `app/main.py` and verify with `curl` against each endpoint
- [x] Write `app/models.py` with Pydantic models for all request/response schemas

## Phase 3: QR Code & Networking Utilities

- [x] Write `app/utils/qr.py`:
  - [x] `generate_badge_qr(name, github, topic)` — compresses JSON via zlib, generates QR code as base64 SVG
  - [x] `decode_contact_qr(raw_json)` — validates and parses contact JSON structure
- [x] Write `app/utils/routing.py`:
  - [x] `optimize_route(booths)` — greedy nearest-neighbor algorithm on grid coordinates
  - [x] `build_grid(booths, obstacles)` — constructs 2D grid from booth positions and obstacle cells
  - [x] Returns ordered list of booth IDs representing the optimized path
- [x] Write `app/utils/search.py` (continued):
  - [x] `search_talks(query)` — executes FTS5 search and returns ranked results
  - [x] `filter_talks(tags=None, speaker_id=None, track=None, date=None)` — applies WHERE clause filters

## Phase 4: Frontend — Base Layout & Command Palette

- [x] Write `frontend/css/style.css` — global dark theme styles:
  - [x] Background `#0d1117`, text `#c9d1d9`, accent `#58a6ff`
  - [x] Monospace font stack: `'JetBrains Mono', 'Fira Code', 'SF Mono', monospace`
  - [x] Base layout: sidebar navigation, main content area, responsive breakpoints
- [x] Write `frontend/css/components.css` — component styles:
  - [x] Command palette overlay (full-screen, centered, search input, results list)
  - [x] Talk cards (title, time, room, tags, bookmark button)
  - [x] Contact cards (name, GitHub, topic, scan button)
  - [x] Badge card (terminal-style JSON display)
  - [x] Expo map container (SVG wrapper, booth markers, route overlay)
- [x] Write `frontend/index.html` — main page with command palette overlay
- [x] Write `frontend/app.js` — main application logic:
  - [x] Client-side routing (hash-based: `#/talk/1`, `#/schedule`, `#/expo`, `#/badge`, `#/contacts`)
  - [x] API client helper (`fetchJSON(method, path, body)`)
  - [x] State management for bookmarks and contacts
- [x] Write `frontend/palette.js` — command palette:
  - [x] `Cmd+K` / `Ctrl+K` keyboard shortcut to open/close
  - [x] Type-ahead search against `/api/talks/search?q=`
  - [x] Results display: talk title, speaker, time, room, tags
  - [x] Arrow key navigation + Enter to select
  - [x] `Esc` to close
  - [x] Category tabs in palette: Talks, Speakers, Booths

## Phase 5: Frontend — Schedule & Talk Detail

- [x] Write `frontend/schedule.html` — schedule timeline view:
  - [x] Date selector tabs (June 29, 30, July 1, 2)
  - [x] Track filter dropdown (Keynote, Workshop, Talk, Panel)
  - [x] Tag filter chips (RAG, LLM, MLOps, etc.)
  - [x] Timeline rendering: talks positioned by time, color-coded by track
  - [x] Personal schedule toggle: show only bookmarked talks
  - [x] Conflict detection: overlapping talks highlighted in red
- [x] Write `frontend/talk.html` — talk detail page:
  - [x] Talk title, abstract, time, room, level badge
  - [x] Speaker card with name, company, bio, GitHub, Twitter links
  - [x] Related talks section (same speaker or same tags)
  - [x] Bookmark button (toggles `POST /api/bookmarks`)
  - [x] Back button to schedule view
- [x] Write `frontend/js/search.js` — client-side search utilities:
  - [x] Debounced input handler for search fields
  - [x] Tag filtering with multi-select
  - [x] Date range filtering

## Phase 6: Frontend — Expo Map & Route Optimization

- [x] Write `frontend/assets/expo-floor.svg` — vector SVG of expo floor:
  - [x] 20×15 grid layout with labeled zones
  - [x] Booth positions matching `booths.grid_x` / `booths.grid_y` coordinates
  - [x] Obstacle cells (stages, restrooms, food) marked with distinct styling
  - [x] Entrance/exit markers
- [x] Write `frontend/expo.html` — expo map page:
  - [x] SVG map rendering with booth markers
  - [x] Category filter sidebar (click to filter booths by category)
  - [x] Pin/unpin booth on click (visual toggle, calls `POST /api/booths/{id}/pin`)
  - [x] "Optimize Route" button (calls `POST /api/route/optimize`)
  - [x] Route display: SVG polyline overlay connecting pinned booths in optimized order
  - [x] Turn-by-turn visual cues along the route
- [x] Write `frontend/js/expo-map.js` — expo map interaction:
  - [x] SVG booth marker rendering from API data
  - [x] Click handler for pin/unpin with visual feedback
  - [x] Category filter logic
  - [x] Route polyline rendering
- [x] Write `frontend/js/routing.js` — route optimization visualization:
  - [x] Client-side route animation (step-by-step highlight)
  - [x] Distance estimation between consecutive booths
  - [x] "Start Navigation" mode: highlights current target booth

## Phase 7: Frontend — Digital Badge & Contacts

- [x] Write `frontend/badge.html` — digital badge page:
  - [x] Terminal-style display: monospace font, green-on-black aesthetic
  - [x] Shows: name, GitHub handle, current project/topic
  - [x] Large QR code display (generated by server via `/api/badge`)
  - [x] "Share" button to toggle full-screen QR mode for scanning
  - [x] Editable fields (name, GitHub, topic) saved to localStorage
- [x] Write `frontend/contacts.html` — contacts list page:
  - [x] List view of all scanned contacts
  - [x] Each contact card: name, GitHub link, topic, scan timestamp
  - [x] "Scan New" button that opens camera for QR scanning
  - [x] Delete button per contact
  - [x] Search/filter contacts by name or topic
- [x] Write `frontend/js/badge.js` — badge page logic:
  - [x] Fetch badge data from `/api/badge`
  - [x] Render QR code using vendored `qrcode.min.js`
  - [x] Edit mode for name/GitHub/topic fields
  - [x] Full-screen QR toggle for easy scanning
- [x] Write `frontend/js/contacts.js` — contacts page logic:
  - [x] Fetch and render contacts from `/api/contacts`
  - [x] Camera QR scanning using `qrcode.min.js` with WebRTC `getUserMedia`
  - [x] On successful scan: POST to `/api/contacts/scan` with decoded JSON
  - [x] Delete contact with confirmation
  - [x] Local storage fallback for contacts (in case API is unavailable)

## Phase 8: Integration & Polish

- [x] Wire all frontend pages to their respective API endpoints
- [x] Implement loading states and error handling across all views
- [x] Add keyboard shortcuts documentation (help overlay, `?` key)
- [x] Implement bookmark persistence (localStorage sync with API)
- [x] Add "Export Schedule" feature: generates standalone HTML file of personal schedule
- [x] Test full user journeys:
  - [x] Journey 1: Cmd+K search → talk detail → bookmark
  - [x] Journey 2: Badge view → QR scan → contact saved
  - [x] Journey 3: Expo map → pin booths → optimize route → view path
  - [x] Journey 4: Schedule view → filter by tag → build personal schedule
  - [x] Journey 5: Speaker search → speaker detail → view all their talks
- [x] Verify air-gapped operation: disconnect network, confirm all features work
- [x] Test on different screen sizes (laptop, tablet)
- [x] Performance check: verify search response time < 100ms on local SQLite
