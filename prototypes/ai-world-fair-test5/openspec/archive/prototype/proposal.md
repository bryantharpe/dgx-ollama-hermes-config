# Proposal: AI Engineer World's Fair Companion

## Why

The AI Engineer World's Fair (June 29 – July 2, Moscone Center, San Francisco) is a massive conference with 100+ partner booths, dozens of concurrent talks, and significant schedule-collision risk. Attendees — primarily AI/ML engineers — need a fast, high-signal tool to navigate the event. Official conference apps tend to be bloated and cloud-dependent. This prototype delivers a lightweight, **fully airgapped** companion that works entirely offline once loaded.

## Target Audience

- AI/ML engineers attending the conference
- Developers who prefer terminal/IDE-like interfaces
- Attendees who want frictionless hallway-track networking without cloud accounts

## Goals

1. **Aggressive schedule filtering** — Find talks by tech stack, topic, or speaker with a command-palette search (Cmd+K style).
2. **Frictionless QR networking** — Exchange digital badges via QR scan, zero network calls.
3. **Offline expo map** — Pin booths, visualize routes on a vector floor map.
4. **IDE-aesthetic UI** — Dark mode default, terminal-inspired design, fast and responsive.

## Non-Goals

- Production-grade scalability or multi-device sync
- Real-time push notifications
- Social features or user accounts
- Integration with official conference APIs
- Mobile-native apps (this is a web app served from a local server)

## Primary User Journeys

### Journey 1: Schedule Discovery
1. Attendee opens the app on a laptop connected to the conference's private Wi-Fi.
2. Presses Cmd+K to open the command palette.
3. Types "RAG pipelines" or "local model orchestration".
4. App returns filtered talks with time, room, speaker, and description.
5. Attendee pins a talk to their personal schedule.

### Journey 2: Hallway Networking
1. Attendee opens their digital badge view (terminal-style card with name, GitHub handle, and current hack).
2. Two attendees scan each other's QR codes by pointing phone screens at each other's laptops.
3. The app decodes the compressed JSON badge and saves the contact locally.
4. Attendee can view all scanned contacts in a list, searchable by name or topic.

### Journey 3: Expo Navigation
1. Attendee opens the expo floor map.
2. Pins booths of interest by clicking on the vector map.
3. App calculates a walking route connecting all pinned booths.
4. Attendee follows the highlighted path from booth to booth.
