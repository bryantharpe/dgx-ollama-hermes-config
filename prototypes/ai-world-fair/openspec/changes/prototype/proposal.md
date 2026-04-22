# Proposal: World's Fair Companion

**Slug:** ai-world-fair
**Status:** Draft
**Created:** 2026-04-21
**Target Event:** AI Engineer World's Fair, June 29 – July 2, Moscone Center, San Francisco

## Why

AI Engineer World's Fair is a massive, multi-day conference with 100+ expo booths, dozens of parallel talks, and dense networking. Attendees — primarily AI/ML engineers — need a fast, high-signal tool to navigate the chaos. Existing conference apps are bloated, cloud-dependent, and slow. This prototype delivers an offline-first, IDE-aesthetic companion that lets developers find relevant talks, exchange contacts via QR, and navigate the expo floor — all without a network connection.

## Target Audience

- AI/ML engineers attending the conference
- Developers who prefer keyboard-driven, terminal-like interfaces
- Attendees who want to maximize signal and minimize noise across 3.5 days of content

## Non-Goals

- Production-grade scalability or multi-user sync
- Official partnership with the conference organizers
- Real-time push notifications or live updates
- Payment, ticketing, or registration
- Social media integration or cloud sharing

## Primary User Journeys

### 1. Find Relevant Talks (Cmd+K Search)

1. User opens the app on their laptop or mini-PC connected to the private conference Wi-Fi.
2. User presses `Cmd+K` to open the command palette.
3. User types a query like "RAG pipelines" or "local model orchestration."
4. The app returns matching talks with title, speaker, time, and room — queried against a local SQLite database.
5. User can further filter by day, track, or speaker.

### 2. Exchange Contacts via QR (Hallway Track)

1. User opens their digital badge view, which displays a QR code containing compressed JSON (name, GitHub handle, current project).
2. User meets another attendee and they scan each other's screens.
3. The app decodes the QR payload and saves the contact to local storage.
4. User can view their collected contacts list at any time.

### 3. Navigate the Expo Floor

1. User opens the expo map view — a minimalist vector map of the floor plan.
2. User pins booths they want to visit by clicking on them.
3. The app calculates a walking route connecting all pinned booths using a local pathfinding algorithm.
4. User follows the highlighted route from booth to booth.

## Success Criteria

- All core features work with zero network connectivity after initial data load.
- Command palette search returns results in under 200ms.
- QR code generation and scanning works reliably on mobile and desktop screens.
- Expo route calculation produces a reasonable path through pinned booths.
