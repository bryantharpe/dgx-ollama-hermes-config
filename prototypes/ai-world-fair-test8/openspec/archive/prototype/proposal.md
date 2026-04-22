# Proposal: AI World's Fair Companion

**Change:** prototype
**Status:** draft
**Slug:** ai-world-fair-test8

## Why

The AI Engineer World's Fair (June 29 – July 2, Moscone Center, San Francisco) is a massive conference with hundreds of talks, 100+ expo booths, and dense networking opportunities. Attendees — primarily AI/ML engineers — struggle to navigate the event because:

- Official schedules are overwhelming and lack topic-level filtering.
- Networking requires friction (business cards, manual contact entry).
- Expo floor exploration is chaotic with no personal routing.
- Conference Wi-Fi is unreliable; an offline-first tool is essential.

This prototype delivers a local-first, airgapped companion web app that gives attendees a high-signal, fast, developer-tailored navigation experience — no cloud, no internet required after initial data load.

## Target Audience

- AI/ML engineers, researchers, and practitioners attending the AI Engineer World's Fair.
- Developers who prefer terminal/IDE-like interfaces and keyboard-driven workflows.
- Attendees who want to maximize signal-to-noise ratio across 3.5 days of content.

## Goals

1. **Schedule search & filtering** — Instantly find talks by topic, speaker, or time using a command-palette interface.
2. **QR-based networking** — Frictionless contact exchange via scannable digital badges, zero network calls.
3. **Offline expo map** — Visual floor map with pinned booths and local route optimization.
4. **IDE-like aesthetic** — Dark mode default, keyboard-first navigation, terminal-inspired UI.

## Non-Goals

- Production-grade scalability or multi-user sync.
- Integration with official conference apps or APIs.
- Real-time updates during the event (data is static after initial load).
- Mobile-native apps (web-only, responsive for tablets/laptops).
- Payment, ticketing, or registration features.

## Primary User Journeys

### Journey 1: Find a Talk by Topic

1. Attendee opens the app on a laptop connected to the event's private Wi-Fi.
2. Presses `Cmd+K` to open the command palette.
3. Types "RAG pipelines" — the app queries the local SQLite database and returns matching talks with time, room, and speaker.
4. Attendee selects a talk to see full details (abstract, speaker bio, related talks).
5. The talk is bookmarked to their personal schedule.

### Journey 2: Exchange Contacts at the Expo

1. Attendee opens their digital badge view (terminal-style JSON card).
2. Meets another attendee at an expo booth.
3. Each scans the other's screen QR code with their device camera.
4. The app decodes the compressed JSON, extracts name/GitHub/topic, and saves it to local storage.
5. Both attendees now have each other's contact info without typing anything.

### Journey 3: Navigate the Expo Floor

1. Attendee opens the expo map view.
2. Pins 5–8 booths they want to visit by clicking on them.
3. Clicks "Optimize Route" — the app calculates an efficient walking path connecting all pinned booths using a local grid-based pathfinding algorithm.
4. The route is highlighted on the map with turn-by-turn visual cues.

### Journey 4: Build a Personal Schedule

1. Attendee browses the full schedule or filters by topic tags.
2. Adds talks to their personal schedule by clicking a bookmark icon.
3. Views their personalized schedule as a timeline with conflict detection (overlapping times flagged).
4. Exports their schedule as a local HTML file for offline reference.

### Journey 5: Speaker Discovery

1. Attendee searches for a known speaker by name.
2. Views all talks by that speaker across the conference.
3. Sees speaker bio, social links (GitHub, Twitter), and related topics.
4. Can bookmark the speaker for follow-up.
