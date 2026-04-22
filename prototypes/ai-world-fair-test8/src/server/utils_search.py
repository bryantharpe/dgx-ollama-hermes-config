#!/usr/bin/env python3
"""Search utilities for AI World Fair prototype."""

import json
import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def search_talks(query: str):
    """Execute FTS5 search and return ranked results."""
    conn = get_db()
    try:
        cur = conn.execute(
            """
            SELECT t.id, t.talk_id, t.title, t.abstract, t.speaker_id,
                   t.start_time, t.end_time, t.room, t.track, t.tags, t.level
            FROM talks t
            WHERE t.id IN (SELECT rowid FROM talks_fts WHERE talks_fts MATCH ?)
            ORDER BY t.start_time
            """,
            (query,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def filter_talks(
    tags: list = None,
    speaker_id: int = None,
    track: str = None,
    date: str = None,
):
    """Apply WHERE clause filters to talk queries."""
    conn = get_db()
    try:
        where_clauses = []
        params = []

        if tags:
            for tag in tags:
                where_clauses.append("JSON_ARRAY_LENGTH(COALESCE(t.tags, '[]')) > 0")
                params.append(f"%{tag}%")

        if speaker_id:
            where_clauses.append("t.speaker_id = ?")
            params.append(speaker_id)

        if track:
            where_clauses.append("t.track = ?")
            params.append(track)

        if date:
            where_clauses.append("DATE(t.start_time) = ?")
            params.append(date)

        if where_clauses:
            where_clause = " WHERE " + " AND ".join(where_clauses)
        else:
            where_clause = ""

        cur = conn.execute(
            f"""
            SELECT t.id, t.talk_id, t.title, t.abstract, t.speaker_id,
                   t.start_time, t.end_time, t.room, t.track, t.tags, t.level
            FROM talks t{where_clause}
            ORDER BY t.start_time
            """,
            params,
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def sync_fts():
    """Sync FTS5 index with talks table (call after seed)."""
    conn = get_db()
    try:
        cur = conn.execute("SELECT id, title, abstract, tags FROM talks")
        rows = cur.fetchall()
        for row in rows:
            conn.execute(
                """
                INSERT INTO talks_fts (rowid, title, abstract, tags)
                VALUES (?, ?, ?, ?)
                """,
                (row["id"], row["title"], row["abstract"], row["tags"]),
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    sync_fts()
    print("FTS index synced")
