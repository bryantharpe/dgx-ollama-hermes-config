# Proposal: World's Fair Companion

**Slug:** `worlds-fair-companion`
**Status:** Draft
**Created:** 2026-04-22
**Author:** Nemo (via meeting-transcript-to-specs)

## Why

The AI Engineer World's Fair (Moscone Center, SF — June 29 – July 2) is a massive, multi-track conference. Attendees face three acute pain points:

1. **Schedule collision** — hundreds of talks across parallel tracks; filtering by specific tech stacks (RAG pipelines, local model orchestration, etc.) is essential but hard in official apps.
2. **Networking friction** — exchanging contact info at a crowded expo floor requires apps, logins, or paper.
3. **Expo overwhelm** — 100+ partner booths across 3.5 days with no offline navigation aid.

This prototype gives AI engineers a single, offline-first tool that works entirely without internet — once the initial data is loaded, the device goes dark to the network and everything runs locally.

## Target Audience

- AI/ML engineers attending the World's Fair who want high-signal, stack-specific talk discovery.
- Developers who value terminal/IDE aesthetics and keyboard-driven workflows.
- Conference attendees who want frictionless, privacy-preserving networking.

## Non-Goals

- Production-grade scalability or multi-user sync.
- Real-time schedule updates during the event.
- Integration with official conference apps or APIs.
- Mobile-native apps (web-only, runs on a laptop/mini-PC on a private Wi-Fi).

## User Journeys

### 1. Schedule Search & Filter
1. User opens the app in a browser on the private Wi-Fi.
2. Presses `Cmd+K` to open the command palette.
3. Types "RAG" or "local orchestration" — results filter instantly from local SQLite.
4. Clicks a talk to see title, speaker, time, track, and description.
5. Can pin talks to a personal "watchlist" stored in localStorage.

### 2. QR Networking
1. User opens their digital badge view — shows name, GitHub handle, and what they're working on in a terminal-style layout.
2. A QR code on the badge encodes their info as compressed JSON.
3. User scans another attendee's badge QR with the app's camera.
4. The decoded contact is saved to localStorage — zero network calls.
5. User can view their collected contacts in a simple list.

### 3. Expo Map & Booth Routing
1. User opens the expo floor map — a minimalist vector (SVG) layout of all booths.
2. User pins booths they want to visit by clicking them.
3. App calculates a walking route connecting pinned booths using a grid-based pathfinding algorithm running locally in the browser.
4. Route is drawn as an overlay on the map.

## Stack Choice

- **Backend:** Python 3.12-slim, FastAPI, Uvicorn
- **Database:** SQLite (single file, seeded once before air-gap)
- **Frontend:** Vanilla HTML/CSS/JS, terminal/IDE dark theme
- **Deployment:** Single container serving both API and static files, run on a laptop or mini-PC on a private Wi-Fi router
