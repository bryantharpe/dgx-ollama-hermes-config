# Tasks: World's Fair Companion

## Phase 1 — Schema & Seed Data

- [ ] Create `schema.sql` with tables: `talks`, `speakers`, `booths`, `contacts` (matching design.md column definitions exactly)
- [ ] Create `seed.py` that populates SQLite with realistic sample data:
  - [ ] 20+ talks across 4 days with varied tags (rag, local-models, llm, mlops, vector-db, etc.)
  - [ ] 10+ speakers with names, bios, GitHub handles
  - [ ] 30+ expo booths with company names, descriptions, grid positions
  - [ ] Verify seed data by running `seed.py` and querying the resulting database
- [ ] Create `src/backend/database.py` — SQLite connection helper with a single `get_db()` function that opens the database file and returns a connection

## Phase 2 — Backend API Routes

- [ ] Create `src/backend/routes/talks.py`:
  - [ ] `GET /api/talks` with query params: `q`, `day`, `track`, `speaker`
  - [ ] Full-text search across talk title, description, tags, and speaker name
  - [ ] `GET /api/talks/<id>` with speaker details joined
- [ ] Create `src/backend/routes/speakers.py`:
  - [ ] `GET /api/speakers` — list all speakers
  - [ ] `GET /api/speakers/<id>` — single speaker
- [ ] Create `src/backend/routes/booths.py`:
  - [ ] `GET /api/booths` — list all booths
  - [ ] `GET /api/booths/<id>` — single booth
- [ ] Create `src/backend/routes/contacts.py`:
  - [ ] `POST /api/contacts` — save a contact from QR scan
  - [ ] `GET /api/contacts` — list all saved contacts
  - [ ] `DELETE /api/contacts/<id>` — remove a contact
  - [ ] `POST /api/badge` — set user's own badge data
  - [ ] `GET /api/badge` — return user's badge data as JSON
- [ ] Wire all routes into `main.py` under the FastAPI app instance
- [ ] Add `GET /api/health` health check endpoint

## Phase 3 — Frontend Base & Dark Theme

- [ ] Create `src/frontend/index.html` — base HTML with navigation links to all pages
- [ ] Create `src/frontend/css/main.css` — dark mode global styles:
  - [ ] Dark background (#0d1117 or similar)
  - [ ] Monospace font family for terminal aesthetic
  - [ ] Accent color (green or cyan for highlights)
  - [ ] Navigation bar with links: Schedule, Badge, Expo, Contacts
- [ ] Create `src/frontend/js/schedule.js` — command palette logic:
  - [ ] Listen for `Cmd+K` / `Ctrl+K` keydown
  - [ ] Toggle a full-screen overlay with a text input
  - [ ] Debounced input handler that calls `GET /api/talks?q=<query>`
  - [ ] Render results as clickable list items
  - [ ] Clicking a result expands to show full talk details
- [ ] Create filter bar below the command palette:
  - [ ] Day dropdown (day1–day4)
  - [ ] Track dropdown (populated from API)
  - [ ] Speaker search input

## Phase 4 — Digital Badge & QR Networking

- [ ] Create `src/frontend/badge.html` — badge page layout
- [ ] Create `src/frontend/css/badge.css` — terminal-style badge styling:
  - [ ] Monospace font, green-on-black text
  - [ ] Badge info displayed as formatted JSON block
  - [ ] Large QR code area
- [ ] Create `src/frontend/js/badge.js`:
  - [ ] Fetch badge data from `GET /api/badge` on page load
  - [ ] Render badge info as JSON in a `<pre>` block
  - [ ] Render QR code using qrcode.js library from the badge JSON
  - [ ] Edit form to update name, GitHub, project
  - [ ] On save, POST updated data to `POST /api/badge`
- [ ] Vendor `qrcode.min.js` into `src/frontend/libs/qrcode.min.js`

## Phase 5 — Expo Map & Route Planning

- [ ] Create `src/frontend/expo.html` — expo map page layout
- [ ] Create `src/frontend/css/expo.css` — expo map styling:
  - [ ] SVG container for the floor plan
  - [ ] Booth rectangles styled with company colors
  - [ ] Pinned booths highlighted with a distinct border/glow
  - [ ] Route path drawn as a thick colored polyline
- [ ] Create `src/frontend/js/expo.js`:
  - [ ] Fetch booths from `GET /api/booths` on page load
  - [ ] Render booths as SVG `<rect>` elements positioned by `grid_x`, `grid_y`, `grid_w`, `grid_h`
  - [ ] Click handler on each booth to toggle "pinned" state
  - [ ] "Calculate Route" button triggers nearest-neighbor TSP:
    - [ ] Start at entrance (0, 0)
    - [ ] Greedily visit nearest unvisited pinned booth
    - [ ] Draw SVG polyline connecting all visited booths
    - [ ] Return to entrance
  - [ ] "Clear Route" button to remove the path overlay
- [ ] Add a simple SVG floor outline (rectangular hall with entrance marker)

## Phase 6 — Saved Contacts View

- [ ] Create `src/frontend/contacts.html` — contacts list page
- [ ] Create `src/frontend/css/contacts.css` — contacts list styling
- [ ] Create `src/frontend/js/contacts.js`:
  - [ ] Fetch contacts from `GET /api/contacts` on page load
  - [ ] Render each contact as a card with name, GitHub, project
  - [ ] GitHub handle is a clickable link (opens in new tab)
  - [ ] Delete button per contact calls `DELETE /api/contacts/<id>`
  - [ ] Empty state message when no contacts saved

## Phase 7 — Polish & Integration

- [ ] Ensure all pages share consistent navigation and dark theme
- [ ] Test command palette search with sample data — verify <200ms response
- [ ] Test QR code generation and verify it's scannable on both desktop and phone screens
- [ ] Test expo route calculation with 5+ pinned booths
- [ ] Verify all API endpoints return correct JSON and handle edge cases (empty results, missing IDs)
- [ ] Test the full flow: open app → search talks → view badge → scan QR → view contacts → navigate expo
- [ ] Verify zero outbound network calls (all data is local SQLite)
