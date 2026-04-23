# Tasks: World's Fair Companion

## Phase 1: Schema, Seed Data, and API Foundation

- [ ] Create `api/schema.sql` with DDL for all five tables: `talks`, `watchlist`, `contacts`, `expo_booths`, `pinned_booths` — include all columns exactly as specified in design.md, with PRIMARY KEYs and FOREIGN KEYs
- [ ] Create `api/database.py` with SQLite connection helper, schema initialization function, and a `get_db()` context manager
- [ ] Create `api/seed.py` that connects to the database, runs `schema.sql`, and inserts seed data for all five tables — use the exact column sets from design.md (every seed column must exist in the DDL)
- [ ] Create `api/main.py` with FastAPI app instance, `/api/health` endpoint returning `{ "status": "ok" }`, and static file serving for the frontend
- [ ] Create `requirements.txt` with `fastapi`, `uvicorn`, `aiosqlite`
- [ ] Verify: `python api/seed.py` runs without errors and `sqlite3` shows all tables populated

## Phase 2: Schedule API

- [ ] Implement `GET /api/talks/search?q=<query>&track=<track>&day=<day>` — full-text search using SQLite `LIKE` across title, speaker, description, and tags; optional `track` and `day` filters; returns JSON array
- [ ] Implement `GET /api/talks/<id>` — returns single talk object by integer ID
- [ ] Implement `GET /api/talks/watchlist` — returns user's pinned talks with full talk details joined
- [ ] Implement `POST /api/talks/watchlist` — accepts `{ "talk_id": <int> }`, inserts into `watchlist` table, returns 201
- [ ] Implement `DELETE /api/talks/watchlist/<id>` — removes entry from `watchlist` by primary key
- [ ] Verify: curl each endpoint against the running server and confirm correct JSON responses

## Phase 3: Networking API

- [ ] Implement `GET /api/contacts` — returns all scanned contacts as JSON array, ordered by `scanned_at` descending
- [ ] Implement `POST /api/contacts` — accepts `{ "name": "<str>", "github": "<str>", "project": "<str>" }`, inserts into `contacts` table, returns 201
- [ ] Verify: curl endpoints and confirm contact data persists across requests

## Phase 4: Expo API

- [ ] Implement `GET /api/expo/booths` — returns all expo booths with grid positions as JSON array
- [ ] Implement `GET /api/expo/booths/<id>` — returns single booth object by ID
- [ ] Implement `POST /api/expo/pin` — accepts `{ "booth_id": <int> }`, inserts into `pinned_booths` table, returns 201
- [ ] Implement `DELETE /api/expo/pin/<id>` — removes pinned booth entry by primary key
- [ ] Implement `GET /api/expo/route` — accepts optional `start_booth_id` query param; runs nearest-neighbor heuristic on grid coordinates of pinned booths; returns ordered list of booth objects with grid positions
- [ ] Verify: pin multiple booths, call `/api/expo/route`, confirm ordered output follows nearest-neighbor logic

## Phase 5: Frontend Shell and Styling

- [ ] Create `index.html` with single-page app structure: header with app title, tab navigation (Schedule | Networking | Expo), main content area, and script includes
- [ ] Create `css/style.css` with terminal-dark theme: dark background (`#0d1117`), monospace font stack, muted green accents (`#3fb950`), gray secondary text, white primary text
- [ ] Create `js/app.js` with tab switching logic, URL hash-based routing (`#schedule`, `#badge`, `#expo`), and API base URL configuration
- [ ] Verify: open `index.html` in a browser, confirm dark theme renders, tabs switch content areas, API calls to `/api/health` succeed

## Phase 6: Schedule UI — Command Palette

- [ ] Create `js/schedule.js` with command palette modal: triggers on `Cmd+K` / `Ctrl+K`, shows input field, Escape to close, Enter to select
- [ ] Implement debounced search: as user types, fetch `/api/talks/search?q=<query>` and render results in a scrollable list below the input
- [ ] Each result item shows: talk title (bold), speaker, time, and track
- [ ] Implement talk detail view: clicking a result shows full talk info (description, speaker bio, room) in a side panel or expanded row
- [ ] Implement watchlist toggle: pin/unpin button on each talk, calls `POST/DELETE /api/talks/watchlist`, updates UI state
- [ ] Implement watchlist tab: separate view showing all pinned talks with remove option
- [ ] Verify: open command palette, type "RAG", confirm filtered results; pin a talk, confirm it appears in watchlist

## Phase 7: Networking UI — Digital Badge and QR

- [ ] Create badge view in `index.html` under the Networking tab: terminal-style card with name, GitHub handle, and project description in monospace
- [ ] Create `js/badge.js` with QR code generation: compress badge info as JSON, encode to QR using the vendored `qrcode.min.js` library
- [ ] Implement QR code display: render QR in a `<canvas>` or `<svg>` element below the badge info
- [ ] Implement QR scanning: use browser `getUserMedia` API to access camera, decode QR codes from video stream using `qrcode.min.js` decode function
- [ ] On successful decode: extract JSON, display preview, confirm save to `/api/contacts`
- [ ] Implement contacts list view: table or list of all scanned contacts with name, GitHub, and project
- [ ] Verify: generate badge QR, scan it with the app's camera, confirm contact appears in the list

## Phase 8: Expo UI — Map and Routing

- [ ] Create expo map SVG in `index.html` or generated by `js/expo.js`: grid-based floor plan with booth rectangles positioned at their `grid_x` / `grid_y` coordinates
- [ ] Implement booth click handler: clicking a booth toggles its pinned state, calls `POST/DELETE /api/expo/pin`, updates visual highlight (e.g., green border for pinned)
- [ ] Implement route calculation: fetch `/api/expo/route`, draw polylines connecting pinned booths in visit order on the SVG map
- [ ] Add route legend: show start point, visited order numbers, and total estimated walking distance (Manhattan distance sum)
- [ ] Verify: pin 3+ booths, confirm route lines draw correctly between them in nearest-neighbor order

## Phase 9: Polish and Air-Gap Readiness

- [ ] Add loading states to all API calls (spinner or skeleton UI)
- [ ] Add error handling: network errors, empty results, invalid JSON responses
- [ ] Add keyboard shortcuts: `Cmd+K` for command palette, `Esc` to close modals, arrow keys to navigate search results
- [ ] Add responsive layout: ensure the app works on laptop screens (1366×768 minimum) and tablet sizes
- [ ] Add a "Data" section or README in the frontend explaining how to seed the database and run air-gapped
- [ ] Final verification: run the full app locally, test all three tabs end-to-end, confirm zero outbound network calls after seeding
