# World's Fair Companion - Prototype Technical Specifications

## Overview

This document outlines the technical specifications for the "World's Fair Companion" application, a prototype designed to operate in a completely air-gapped environment at the AI Engineer World’s Fair (June 29–July 2 at Moscone Center, SF). The app provides local-first event navigation with features including schedule filtering, QR-based networking, and expo floor navigation—all without network connectivity after initial setup.

## Requirements

### Core Features

- **Schedule Filter & Search**:  
  Users can search and filter events by technical stacks (e.g., "local model orchestration", "RAG pipelines") via a command palette interface (`Cmd + K`). No dependency on external APIs; search operates entirely against a local SQLite database.

- **QR-Based Networking**:  
  Each user generates a QR code containing JSON-encoded profile data (name, GitHub handle, project interests). Scanning QR codes locally allows saving contact information to device storage without network access.

- **Expo Floor Map**:  
  Interactive SVG map of the expo floor with booth locations. Users can "pin" booths of interest; the app calculates a walking path between pinned points using local pathfinding.

### Constraints

- All components run completely offline post-setup (no cloud services, no internet access).
- Prototype must be deployable on a single laptop or mini-PC serving as a local HTTP server.
- UI design mimics IDE aesthetics with dark mode by default and command palette interactions.

## Technical Specifications

### Architecture & Stack

- **Backend**:  
  FastAPI application serving static assets and providing API endpoints for schedule data. SQLite database to store event schedules, user profiles, and expo booth data.

- **Frontend**:  
  Plain HTML, CSS, and JavaScript with Tailwind CSS for styling (lightweight, no heavy frameworks). SVG-based expo floor map with JavaScript-driven pathfinding and interaction.

- **Data Storage**:  
  All data stored locally; database is a single `.sqlite` file initialized before event deployment.

### Data Models

- **Events** (SQLite table):  
  `id`, `title`, `description`, `start_time`, `end_time`, `track`, `tags` (JSON array), `speakers` (JSON array).

- **Users** (SQLite table):  
  `id`, `name`, `github_handle`, `projects` (JSON array), `pinned_booths` (JSON list of booth IDs).

- **Expo Booths** (SQLite table):  
  `id`, `name`, `x`, `y`, `description`, `tags` (JSON array).

### Implementation Tasks

1. **Project Structure Setup**  
   Create directory structure: `/app/backend` (FastAPI), `/app/frontend` (HTML/CSS/JS), and `/app/db` (SQLite initialization). Initialize FastAPI server with basic routing for static files.

2. **Schedule Data Parser**  
   Write Python script to import conference schedules from provided public data into SQLite database. Ensure database schema matches `Events` model; include fields for tags and tracks.

3. **FastAPI Backend Implementation**  
   Create API endpoints:  
   - `GET /api/events` — returns filtered events by query parameters (e.g., `stacks=rag`).  
   - `PUT /api/user` — saves user profile data to SQLite with POST body.

4. **Frontend Command Palette**  
   Implement keyboard shortcut handling (`Cmd + K`) for search input. Display filtered events dynamically within the UI based on search terms.

5. **QR Code Generation**  
   Integrate client-side QR code generation using a local library (e.g., `qrcode.js`). Display profile JSON as QR code; provide download option for saving QR as image.

6. **Expo Floor Map Implementation**  
   Create SVG floor plan of Moscone Center with booths positioned by coordinates. Implement JavaScript pathfinding (Dijkstra’s algorithm) for shortest paths between pinned booths. Allow user interaction to pin/unpin booths and update path calculations.

7. **Database Initialization & Data Population**  
   Run database setup script to populate from collected conference data. Ensure SQLite file is self-contained and readable by FastAPI.

8. **Testing & Verification**  
   Validate all components operate correctly in air-gapped mode:  
   - Start server on localhost, access frontend without internet.  
   - Test QR code generation/scanning locally.  
   - Verify pathfinding works without external dependencies.

## Deployment Instructions

- **Setup**:  
  Clone repository and run `./setup.sh` to install dependencies. Populate SQLite database using `python db_initializer.py`. Start FastAPI server: `uvicorn backend.main:app --reload`.

- **Air-Gapped Deployment**:  
  Copy the entire `/app` directory to a USB drive or portable device. On-site, launch server directly from the device (no internet required after setup).

- **Security Note**:  
  All data remains on local device; no external data transmissions occur after initial setup.