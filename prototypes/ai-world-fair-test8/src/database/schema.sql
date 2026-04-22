-- Prototype schema. Append CREATE TABLE statements per feature.
--
-- INVARIANT: every column named in seed.py's INSERTs must appear here.
-- Adding a column to seed data? Add it to the CREATE TABLE too.
-- Removing a column from schema? Remove it from seed INSERTs too.
--

-- talks table
CREATE TABLE IF NOT EXISTS talks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    talk_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    abstract TEXT,
    speaker_id INTEGER REFERENCES speakers(id),
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    room TEXT,
    track TEXT,
    tags TEXT,
    level TEXT CHECK(level IN ('beginner','intermediate','advanced'))
);

-- speakers table
CREATE TABLE IF NOT EXISTS speakers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    speaker_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    bio TEXT,
    github TEXT,
    twitter TEXT,
    company TEXT
);

-- booths table
CREATE TABLE IF NOT EXISTS booths (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booth_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    grid_x INTEGER NOT NULL,
    grid_y INTEGER NOT NULL,
    description TEXT,
    website TEXT
);

-- user_bookmarks table
CREATE TABLE IF NOT EXISTS user_bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    talk_id INTEGER REFERENCES talks(id),
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    type TEXT CHECK(type IN ('talk','booth','speaker')) NOT NULL,
    entity_id TEXT NOT NULL
);

-- contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    github TEXT,
    topic TEXT,
    scanned_at TEXT DEFAULT CURRENT_TIMESTAMP,
    raw_json TEXT
);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS talks_fts USING fts5(
    title,
    abstract,
    tags,
    content='talks',
    content_rowid='id'
);

-- Trigger to keep FTS index in sync
CREATE TRIGGER IF NOT EXISTS talks_ai AFTER INSERT ON talks BEGIN
    INSERT INTO talks_fts(rowid, title, abstract, tags) VALUES (new.id, new.title, new.abstract, new.tags);
END;

CREATE TRIGGER IF NOT EXISTS talks_ad AFTER DELETE ON talks BEGIN
    INSERT INTO talks_fts(talks_fts, rowid, title, abstract, tags) VALUES('delete', old.rowid, old.title, old.abstract, old.tags);
END;

CREATE TRIGGER IF NOT EXISTS talks_au AFTER UPDATE ON talks BEGIN
    INSERT INTO talks_fts(talks_fts, rowid, title, abstract, tags) VALUES('delete', old.rowid, old.title, old.abstract, old.tags);
    INSERT INTO talks_fts(rowid, title, abstract, tags) VALUES (new.id, new.title, new.abstract, new.tags);
END;
