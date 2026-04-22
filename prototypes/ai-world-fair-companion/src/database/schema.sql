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
    tags TEXT NOT NULL,
    track TEXT
);

CREATE TABLE IF NOT EXISTS speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    bio TEXT,
    github TEXT,
    talks_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS expo_booths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    booth_number TEXT NOT NULL,
    description TEXT,
    tags TEXT NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    category TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    github TEXT,
    project TEXT,
    scanned_at TEXT NOT NULL,
    source_hash TEXT NOT NULL
);
