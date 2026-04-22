-- Prototype schema. Append CREATE TABLE statements per feature.
--
-- INVARIANT: every column named in seed.py's INSERTs must appear here.
-- Adding a column to seed data? Add it to the CREATE TABLE too.
-- Removing a column from schema? Remove it from seed INSERTs too.
--
-- Example:
--   CREATE TABLE IF NOT EXISTS items (
--       id INTEGER PRIMARY KEY AUTOINCREMENT,
--       name TEXT NOT NULL,
--       created_at TEXT DEFAULT CURRENT_TIMESTAMP
--   );

CREATE TABLE IF NOT EXISTS talks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    speaker_name TEXT NOT NULL,
    speaker_bio TEXT,
    speaker_github TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    room TEXT NOT NULL,
    description TEXT,
    topics TEXT NOT NULL,
    track TEXT,
    level TEXT
);

CREATE TABLE IF NOT EXISTS speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    bio TEXT,
    github TEXT,
    company TEXT,
    talk_ids TEXT
);

CREATE TABLE IF NOT EXISTS booths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    zone TEXT NOT NULL,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    topics TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    github TEXT,
    hacking_on TEXT,
    scanned_at TEXT NOT NULL,
    badge_json TEXT
);

CREATE TABLE IF NOT EXISTS user_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    talk_id INTEGER NOT NULL,
    pinned_at TEXT NOT NULL,
    FOREIGN KEY (talk_id) REFERENCES talks(id)
);

CREATE TABLE IF NOT EXISTS user_pins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booth_id INTEGER NOT NULL,
    pinned_at TEXT NOT NULL,
    FOREIGN KEY (booth_id) REFERENCES booths(id)
);
