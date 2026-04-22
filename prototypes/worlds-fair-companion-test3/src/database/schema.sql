-- Talks table
CREATE TABLE IF NOT EXISTS talks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    speaker_id INTEGER NOT NULL,
    day TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    room TEXT NOT NULL,
    description TEXT,
    tags TEXT NOT NULL,
    track TEXT,
    FOREIGN KEY (speaker_id) REFERENCES speakers(id)
);

-- Speakers table
CREATE TABLE IF NOT EXISTS speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    bio TEXT,
    company TEXT,
    github TEXT,
    twitter TEXT
);

-- Expo booths table
CREATE TABLE IF NOT EXISTS expo_booths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    description TEXT,
    tags TEXT,
    grid_x REAL NOT NULL,
    grid_y REAL NOT NULL,
    hall TEXT NOT NULL,
    booth_number TEXT
);

-- Saved contacts table
CREATE TABLE IF NOT EXISTS saved_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    github TEXT,
    project TEXT,
    scanned_at TEXT NOT NULL,
    source_id TEXT
);
