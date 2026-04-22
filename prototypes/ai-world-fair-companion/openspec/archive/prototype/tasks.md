# Tasks: AI Engineer World's Fair Companion

## Phase 1 — Schema & Seed Data

- [ ] Write `schema.sql` with all four tables: `talks`, `speakers`, `expo_booths`, `contacts` — include all columns, types, constraints, and primary keys as specified in design.md
- [ ] Write `database.py` — SQLite connection helper with a `get_db()` function that returns a connection to `data/fair.db`
- [ ] Write `seed.py` — populate `talks` with 25 realistic talks across 4 days (June 29–July 2) with tags like `rag`, `llm`, `local-models`, `agents`, `pipelines`, `fine-tuning`, `vector-dbs`; populate `speakers` with 18 speakers including GitHub handles; populate `expo_booths` with 25 booths with grid coordinates (x, y on 0–100 scale) and company descriptions; populate `contacts` with 3 sample contacts for testing
- [ ] Run `seed.py` and verify all tables are populated with correct data

## Phase 2 — API Backend

- [ ] Write `main.py` — FastAPI app with Uvicorn, serving static files from `frontend/` directory, mounting API routers
- [ ] Write `api/__init__.py` — package init
- [ ] Write `api/talks.py` — implement `GET /api/talks` (with `?tag`, `?speaker`, `?date` query params), `GET /api/talks/search` (full-text search across title, description, speaker_name, tags via `?q=`), `GET /api/talks/<id>`
- [ ] Write `api/speakers.py` — implement `GET /api/speakers` (list all), `GET /api/speakers/<id>` (speaker with their talks)
- [ ] Write `api/booths.py` — implement `GET /api/booths` (with `?tag`, `?category` query params), `GET /api/booths/<id>`, `GET /api/booths/pins` (reads pinned booth IDs from request context — note: pins are stored client-side in localStorage, this endpoint returns the current session's pins), `POST /api/booths/pins` (toggle pin — body `{"booth_id": 1, "action": "pin"|"unpin"}`), `GET /api/route` (pathfinding between two pinned booths — body `{"from": 1, "to": 2}`)
- [ ] Write `api/contacts.py` — implement `POST /api/contacts/scan` (decode base64 JSON payload, store contact with dedup via `source_hash`), `GET /api/contacts` (list all), `GET /api/contacts/<id>`, `DELETE /api/contacts/<id>`
- [ ] Write `api/badge.py` — implement `GET /api/badge` (return badge JSON for QR generation — body `{"name": "...", "github": "...", "project": "..."}`)
- [ ] Add health check: `GET /api/health` returning `{"status": "ok"}`
- [ ] Add `requirements.txt` with `fastapi`, `uvicorn[standard]`, `qrcode`

## Phase 3 — Frontend Shell & Styling

- [ ] Write `frontend/css/style.css` — dark terminal theme: near-black background (`#0d1117`), monospace font stack (JetBrains Mono / Fira Code / system monospace), green/cyan accent colors, high contrast, minimal chrome, command palette overlay styles, table/card styles for schedule, badge terminal output style
- [ ] Write `frontend/index.html` — base HTML shell with command palette trigger (`Cmd+K`), navigation links (Schedule, Expo, Badge, Contacts), main content area
- [ ] Write `frontend/schedule.html` — schedule view shell with filter bar (tag chips, speaker search, date selector), talk list area
- [ ] Write `frontend/expo.html` — expo map shell with SVG map container, booth pin list, route button
- [ ] Write `frontend/badge.html` — badge view shell with QR code display area, scan button, contacts list area
- [ ] Write `frontend/contacts.html` — contacts list shell with contact cards and delete buttons
- [ ] Write `frontend/js/app.js` — shared utilities: API fetch helper, navigation router, keyboard shortcut handler (Cmd+K for palette)

## Phase 4 — Command Palette & Schedule

- [ ] Write `frontend/js/palette.js` — command palette overlay: open on `Cmd+K`/`Ctrl+K`, single input field, debounce input, call `/api/talks/search?q=...`, render results as list with talk title, speaker, time, room, highlighted matching tags, click to navigate to talk detail
- [ ] Write `frontend/js/schedule.js` — schedule view: load talks from `/api/talks`, render as cards grouped by day, implement filter bar (tag chips filter by `?tag=`, speaker search by `?speaker=`, date selector by `?date=`), click talk to show detail modal

## Phase 5 — Expo Map & Pathfinding

- [ ] Create `frontend/assets/expo-map.svg` — hand-authored minimalist vector floor plan of a conference expo hall with labeled sections (A, B, C zones), stage areas, and walkable corridors
- [ ] Write `frontend/js/expo.js` — expo map view: render SVG map, plot booths as labeled circles at their (x, y) grid positions, implement pin toggle (call `/api/booths/pins`), highlight pinned booths in distinct color, implement A* pathfinding in vanilla JS between consecutive pinned booths, draw path as SVG line overlay, "Route" button to trigger path calculation

## Phase 6 — QR Networking & Badge

- [ ] Vendor `qrcode.js` library: download `https://cdn.jsdelivr.net/npm/qrcode@1.5.4/build/qrcode.min.js` to `frontend/vendor/qrcode.min.js`
- [ ] Write `frontend/js/badge.js` — badge view: render user badge (name, GitHub, project) in terminal-style output, generate QR code from badge JSON (base64-encoded compact format: `{"n":"...","g":"...","p":"..."}`) using qrcode.js, implement scan mode using `getUserMedia` camera API to scan incoming QR codes, decode scanned JSON, call `/api/contacts/scan` to store contact, show confirmation toast
- [ ] Write `frontend/js/contacts.js` — contacts view: load contacts from `/api/contacts`, render as cards with name, GitHub link, project, scan time, delete button per contact calling `DELETE /api/contacts/<id>`

## Phase 7 — Polish & Air-Gap Verification

- [ ] Verify all API routes return correct data with curl against the running server
- [ ] Verify command palette search returns relevant results for sample queries ("rag", "local models", "agents")
- [ ] Verify QR generation produces scannable codes
- [ ] Verify QR scanning flow: scan a test QR → contact appears in contacts list
- [ ] Verify expo map renders and pins are highlighted
- [ ] Verify pathfinding draws a visible route between two pinned booths
- [ ] Test the full flow with zero network access (disconnect from internet, verify everything works on local Wi-Fi only)
- [ ] Ensure no external network calls are made from the frontend (check for any CDN references beyond the vendored qrcode.js)
- [ ] Final review: all seed data columns match schema DDL, all API responses match design.md spec
