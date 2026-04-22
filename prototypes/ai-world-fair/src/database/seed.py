#!/usr/bin/env python3
"""Idempotent database bootstrap. Runs at container startup via start.sh.

DO NOT REMOVE the os.makedirs(DATA_DIR) call — sqlite3.connect() fails
with "unable to open database file" if DATA_DIR doesn't exist on first
boot, and the container falls into a restart loop.

SCHEMA / SEED CONSISTENCY INVARIANT:
    Every column name in any INSERT below MUST be declared in schema.sql
    for the same table. If you add a column to seed data, add it to the
    CREATE TABLE. Drift crashes the container at startup with
    `sqlite3.OperationalError: table X has no column named Y`.
"""

import os
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")
SCHEMA_PATH = os.path.join(SCRIPT_DIR, "schema.sql")

os.makedirs(DATA_DIR, exist_ok=True)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

with open(SCHEMA_PATH, "r") as f:
    schema = f.read()
if schema.strip():
    cursor.executescript(schema)

# ─── add seed data below ─────────────────────────────────────────────────────
# Use INSERT OR IGNORE / INSERT OR REPLACE so re-running is safe.
#
# Example:
# cursor.executemany(
#     "INSERT OR IGNORE INTO items (id, name) VALUES (?, ?)",
#     [(1, "alpha"), (2, "beta")],
# )

conn.commit()
conn.close()

print(f"seeded {DB_PATH}")
