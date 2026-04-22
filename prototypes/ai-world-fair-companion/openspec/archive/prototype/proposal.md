# Proposal: AI Engineer World's Fair Companion

## Why

The AI Engineer World's Fair (June 29 – July 2, Moscone Center, San Francisco) is a massive, multi-day conference with 100+ partner booths, overlapping talk tracks, and a dense hallway track. Attendees — primarily AI/ML engineers — need a high-signal, low-friction tool to navigate the event. Existing conference apps are bloated, cloud-dependent, and require reliable internet. This prototype delivers a **fully air-gapped, offline-first companion** that runs on a local laptop or mini-PC behind a private Wi-Fi router, with zero external network calls once initialized.

## Target Audience

- AI/ML engineers attending the conference
- Developers who prefer terminal/IDE-like interfaces
- Attendees who value speed, privacy, and offline reliability

## Core Goals

1. **Aggressive schedule filtering** — Find talks by tech stack, topic, or speaker, not just by time slot.
2. **Frictionless hallway networking** — QR-code-based contact exchange with zero network dependency.
3. **Offline expo navigation** — Pinned booth map with local pathfinding.
4. **IDE-like aesthetic** — Dark mode, command-palette search (Cmd+K), terminal-inspired UI.

## Non-Goals

- Production-grade scalability or multi-user sync
- Real-time push notifications
- Social features or public profiles
- Integration with official conference apps or APIs after initialization
- Mobile-native apps (this is a web app served locally)

## Primary User Journeys

### Journey 1: Find a Talk by Topic
1. Attendee opens the app in their browser on the private Wi-Fi.
2. Presses `Cmd+K` to open the command palette.
3. Types "RAG pipelines" or "local model orchestration."
4. App returns matching talks with time, room, speaker, and tags — queried from local SQLite.

### Journey 2: Exchange Contacts via QR
1. Attendee opens their digital badge view, which displays a QR code containing compressed JSON (name, GitHub handle, project description).
2. Two attendees scan each other's screens.
3. The app decodes the JSON, stores the contact in local storage, and shows a confirmation toast.

### Journey 3: Navigate the Expo Floor
1. Attendee browses the expo map and pins booths of interest.
2. App overlays pins on a minimalist vector map.
3. Attendee requests a route; the app calculates a path between pinned booths using local grid-based pathfinding.

### Journey 4: Browse Schedule by Filter
1. Attendee opens the schedule view.
2. Applies filters: topic tags, speaker name, time range.
3. Results update instantly from local SQLite — no network latency.
