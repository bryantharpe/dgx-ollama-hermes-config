# Proposal: World's Fair Companion

**Change:** prototype
**Project:** World's Fair Companion
**Slug:** worlds-fair-companion-test3
**Status:** Draft
**Created:** 2026-04-20

## Why

AI Engineer World's Fair (June 29 – July 2, Moscone Center, SF) is a massive conference with 100+ expo booths, overlapping talks, and dense networking opportunities. Attendees — primarily AI/ML engineers — need a fast, signal-dense tool to navigate the event without relying on internet connectivity. Current conference apps are bloated, cloud-dependent, and slow to load in crowded venues with poor Wi-Fi.

This prototype delivers an offline-first, air-gapped companion that lets engineers filter talks by technical topic, network via QR codes, and navigate the expo floor — all running entirely on a local device with zero network calls.

## Target Audience

- AI/ML engineers attending the conference
- Developers who prefer terminal/IDE-like interfaces
- Attendees who value speed and signal over polish

## Non-Goals

- Production-grade scalability
- User accounts or authentication
- Real-time sync between devices
- Social features or feeds
- Mobile-native app (web app served locally)
- Accessibility compliance (prototype phase)

## Core User Journeys

### 1. Schedule Discovery via Command Palette
**As an** AI engineer,
**I want to** type a topic like "RAG pipelines" or "local model orchestration" into a Cmd+K command palette,
**So that** I instantly see all matching talks across the 4-day schedule, filtered by relevance and time.

### 2. QR-Based Networking
**As an** attendee,
**I want to** generate a scannable digital badge showing my name, GitHub handle, and current project,
**So that** I can exchange contacts with other attendees by scanning each other's screens — no accounts, no cloud, no friction.

### 3. Expo Floor Navigation
**As an** attendee,
**I want to** pin booths I want to visit on a vector expo map,
**So that** the app calculates a walking route connecting my pinned booths in an efficient order.

### 4. Offline-First Operation
**As an** attendee,
**I want** the entire app to work with zero internet connectivity,
**So that** I can rely on it in a crowded venue where Wi-Fi is unreliable or unavailable.

## Success Criteria

- Command palette returns search results in <200ms from local SQLite
- QR badge generation and scanning works without any network calls
- Expo map renders as a lightweight SVG with route calculation
- Entire app runs from a single laptop/mini-PC on a closed Wi-Fi network
- Zero external API dependencies after initial data seeding
