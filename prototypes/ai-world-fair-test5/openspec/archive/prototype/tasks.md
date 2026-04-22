# Tasks: AI Engineer World's Fair Companion

## Phase 1 — Database Schema & Seed Data

- [-] Create `schema.sql` with all six tables: `talks`, `speakers`, `booths`, `contacts`, `user_schedule`, `user_pins` — include all columns, types, constraints, foreign keys, and indexes as specified in design.md
- [-] Create `seed.py` that populates SQLite with realistic sample data:
  - [ ] 15+ talks spanning multiple tracks, levels, and topics (include RAG, local models, agents, MLOps, embeddings)
  - [ ] 10+ speakers with bios, GitHub handles, and companies
  - [ ] 20+ booths across 3 expo zones with grid coordinates
  - [ ] Verify seed data is consistent with schema (every column in seed rows exists in DDL)

## Phase 2 — Core API Routes

- [-] Implement `GET /api/health` returning `{"status": "ok"}`
- [-] Implement `GET /api/talks` with query params: `q` (full-text search across title, speaker, topics, description), `topic`, `track`, `level`, `speaker` — return JSON array of talks
- [-] Implement `GET /api/talks/{id}` returning a single talk object
- [-] Implement `GET /api/speakers` with optional `q` param for name search — return JSON array
- [-] Implement `GET /api/speakers/{id}` returning a single speaker object
- [-] Implement `GET /api/booths` with optional `q` and `zone` params — return JSON array
- [-] Implement `GET /api/booths/{id}` returning a single booth object

## Phase 3 — Schedule Management API

- [-] Implement `GET /api/schedule` returning user's pinned talks (JOIN `user_schedule` with `talks`)
- [-] Implement `POST /api/schedule/pin` accepting `{ "talk_id": int }` — insert into `user_schedule`
- [-] Implement `DELETE /api/schedule/unpin/{talk_id}` — delete from `user_schedule`

## Phase 4 — Networking (QR Badge) API

- [-] Implement `GET /api/contacts` with optional `q` param — return JSON array of contacts
- [-] Implement `POST /api/contacts` accepting `{ "name", "github", "hacking_on", "badge_json" }` — insert into `contacts`
- [-] Implement `GET /api/badge` returning current user's badge as JSON
- [-] Implement `POST /api/badge` accepting `{ "name", "github", "hacking_on" }` — update badge data (store in a simple JSON file or a single-row table)

## Phase 5 — Expo Map API

- [-] Implement `GET /api/expo/pins` returning user's pinned booths (JOIN `user_pins` with `booths`)
- [-] Implement `POST /api/expo/pin` accepting `{ "booth_id": int }` — insert into `user_pins`
- [-] Implement `DELETE /api/expo/unpin/{booth_id}` — delete from `user_pins`
- [-] Implement `GET /api/expo/route` — nearest-neighbor pathfinding on booth grid coordinates, return ordered list of booth IDs with grid positions

## Phase 6 — Frontend Shell & Terminal Theme

- [-] Create `frontend/index.html` with single-page app structure: command palette overlay, main content area, and navigation
- [-] Create `frontend/css/terminal.css` with terminal/IDE theme:
  - [ ] Dark background (`#1a1b26`), monospace font, accent colors (green `#73daca`, yellow `#e5c07b`, red `#ff5370`)
  - [ ] No rounded corners, no shadows, no gradients — flat utilitarian design
  - [ ] Component styles: cards, tags, buttons, inputs, overlays
- [-] Create `frontend/css/main.css` with layout utilities: grid, flex, spacing, responsive breakpoints
- [-] Create `frontend/js/app.js` with:
  - [ ] API client wrapper (fetch-based, no external deps)
  - [ ] Simple client-side router (hash-based: `#schedule`, `#expo`, `#badge`, `#contacts`)
  - [ ] App initialization and navigation wiring

## Phase 7 — Command Palette

- [-] Create `frontend/js/command-palette.js`:
  - [ ] Full-screen frosted-glass overlay triggered by `Cmd+K` / `Ctrl+K`
  - [ ] Debounced input (200ms) calling `/api/talks?q=...` and `/api/speakers?q=...`
  - [ ] Results rendered as ranked list with title, speaker, time, room
  - [ ] Arrow-key navigation + Enter to select + Escape to dismiss
  - [ ] Topic-tag filtering via `/api/talks?topic=...`
  - [ ] Blinking cursor animation in the input field

## Phase 8 — Schedule View

- [-] Create `frontend/js/schedule.js`:
  - [ ] Default landing page showing today's talks in a vertical timeline
  - [ ] Each talk card: time, room, title, speaker, topic tags, pin toggle
  - [ ] Filter bar with topic chips, track dropdown, level selector
  - [ ] Pin/unpin buttons calling `/api/schedule/pin` and `/api/schedule/unpin/{id}`
  - [ ] "My Schedule" view showing only pinned talks
  - [ ] Empty state messaging when no talks are pinned

## Phase 9 — Digital Badge & QR

- [-] Vendor `qrcode.js` library into `frontend/js/qrcode.js` at build time
- [-] Create `frontend/js/badge.js`:
  - [ ] Terminal-style badge card: name, GitHub handle, "hacking on" description
  - [ ] QR code generation from JSON payload using `qrcode.js`
  - [ ] Payload format: URL-safe base64 encoded JSON (max ~200 chars)
  - [ ] Inline edit mode — click to modify fields, regenerate QR on save
  - [ ] Badge data persisted via `/api/badge` endpoints
  - [ ] QR code displayed as a canvas/SVG element

## Phase 10 — Expo Map & Route Planning

- [-] Create `frontend/js/expo-map.js`:
  - [ ] SVG vector floor map with zones (Hall A, Hall B, Hall C)
  - [ ] Booths rendered as clickable markers at `grid_x`/`grid_y` positions
  - [ ] Pinned booths highlighted in a distinct color (e.g., green)
  - [ ] Tooltip on booth hover/click showing name and description
  - [ ] Route overlay: SVG `<polyline>` connecting pinned booths in nearest-neighbor order
  - [ ] Route data fetched from `/api/expo/route`
  - [ ] Pin/unpin buttons on booth markers calling `/api/expo/pin` and `/api/expo/unpin/{id}`
  - [ ] Clear route button to reset the overlay

## Phase 11 — Contacts View

- [-] Extend `frontend/js/app.js` or create a new module for contacts list:
  - [ ] List view of all scanned contacts with name, GitHub, and "hacking on"
  - [ ] Search bar filtering contacts by name or topic
  - [ ] Click a contact to see full details (including raw badge JSON)
  - [ ] Empty state when no contacts have been scanned

## Phase 12 — Polish & Integration

- [-] Ensure all API endpoints return proper JSON with error handling (404 for missing resources, 400 for bad input)
- [-] Add loading states to all async UI operations (spinner or skeleton)
- [-] Ensure keyboard navigation works throughout (tab order, arrow keys in palette)
- [-] Test QR code scannability at various distances and angles
- [-] Verify the app works with zero network connectivity (all assets served locally)
- [-] Add a "About" page or footer noting this is an unofficial community prototype
