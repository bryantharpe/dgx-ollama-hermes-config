import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["api"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "app.db")

os.makedirs(DATA_DIR, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def read_json(path: str, default: Any) -> Any:
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return default


def write_json(path: str, value: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(value, f, indent=2)


# ─── health ───
@router.get("/health")
async def health():
    return {"status": "ok"}


# ─── talks ───
class Talk(BaseModel):
    id: int
    talk_id: str
    title: str
    abstract: Optional[str]
    speaker_id: Optional[int]
    start_time: str
    end_time: str
    room: Optional[str]
    track: Optional[str]
    tags: Optional[str]
    level: Optional[str]


@router.get("/talks", response_model=List[Talk])
async def list_talks(
    q: Optional[str] = Query(None, description="Search query"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    speaker: Optional[str] = Query(None, description="Filter by speaker ID"),
    track: Optional[str] = Query(None, description="Filter by track"),
    date: Optional[str] = Query(None, description="Filter by date (YYYY-MM-DD)"),
):
    conn = get_db()
    try:
        where_clauses = []
        params = []

        if q:
            where_clauses.append(
                "t.id IN (SELECT rowid FROM talks_fts WHERE talks_fts MATCH ?)"
            )
            params.append(q)

        if tag:
            where_clauses.append("JSON_ARRAY_LENGTH(COALESCE(t.tags, '[]')) > 0")
            params.append(f"%{tag}%")

        if speaker:
            where_clauses.append("t.speaker_id = ?")
            params.append(speaker)

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
        talks = [dict(r) for r in cur.fetchall()]
        return talks
    finally:
        conn.close()


@router.get("/talks/search", response_model=List[Talk])
async def search_talks(q: str = Query(..., description="Search query")):
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
            (q,),
        )
        talks = [dict(r) for r in cur.fetchall()]
        return talks
    finally:
        conn.close()


@router.get("/talks/{talk_id}", response_model=Talk)
async def get_talk(talk_id: str):
    conn = get_db()
    try:
        cur = conn.execute(
            """
            SELECT t.id, t.talk_id, t.title, t.abstract, t.speaker_id,
                   t.start_time, t.end_time, t.room, t.track, t.tags, t.level
            FROM talks t WHERE t.talk_id = ? OR t.id = ?
            """,
            (talk_id, talk_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Talk not found")
        return dict(row)
    finally:
        conn.close()


# ─── speakers ───
@router.get("/speakers")
async def list_speakers():
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM speakers ORDER BY name"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/speakers/{speaker_id}")
async def get_speaker(speaker_id: str):
    conn = get_db()
    try:
        cur = conn.execute(
            """
            SELECT * FROM speakers WHERE speaker_id = ? OR id = ?
            """,
            (speaker_id, speaker_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Speaker not found")
        speaker = dict(row)

        cur_talks = conn.execute(
            "SELECT * FROM talks WHERE speaker_id = ? ORDER BY start_time",
            (speaker["id"],),
        )
        speaker["talks"] = [dict(r) for r in cur_talks.fetchall()]
        return speaker
    finally:
        conn.close()


# ─── booths ───
class Booth(BaseModel):
    id: int
    booth_id: str
    name: str
    category: Optional[str]
    grid_x: int
    grid_y: int
    description: Optional[str]
    website: Optional[str]


@router.get("/booths", response_model=List[Booth])
async def list_booths(category: Optional[str] = Query(None)):
    conn = get_db()
    try:
        if category:
            cur = conn.execute(
                "SELECT * FROM booths WHERE category = ? ORDER BY name",
                (category,),
            )
        else:
            cur = conn.execute(
                "SELECT * FROM booths ORDER BY grid_x, grid_y"
            )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/booths/pinned")
async def get_pinned_booths():
    conn = get_db()
    try:
        cur = conn.execute(
            """
            SELECT DISTINCT b.*
            FROM booths b
            JOIN user_bookmarks ub ON ub.entity_id = b.booth_id AND ub.type = 'booth'
            ORDER BY b.grid_x, b.grid_y
            """
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/booths/{booth_id}")
async def get_booth(booth_id: str):
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM booths WHERE booth_id = ? OR id = ?",
            (booth_id, booth_id),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Booth not found")
        return dict(row)
    finally:
        conn.close()


# ─── badges ───
@router.get("/badge")
async def get_badge():
    return {
        "name": "AI World Fair Attendee",
        "github": "aiworldfair",
        "topic": "LLMs and RAG",
    }


@router.post("/contacts/scan")
async def scan_contact(payload: Dict[str, Any]):
    conn = get_db()
    try:
        raw_json = payload.get("raw_json", "")
        try:
            data = json.loads(raw_json)
            name = data.get("name", "")
            github = data.get("github", "")
            topic = data.get("topic", "")
        except json.JSONDecodeError:
            name = ""
            github = ""
            topic = ""

        conn.execute(
            """
            INSERT INTO contacts (name, github, topic, raw_json)
            VALUES (?, ?, ?, ?)
            """,
            (name, github, topic, raw_json),
        )
        conn.commit()

        cur = conn.execute(
            "SELECT * FROM contacts ORDER BY id DESC LIMIT 1"
        )
        return dict(cur.fetchone())
    finally:
        conn.close()


@router.get("/contacts")
async def list_contacts():
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM contacts ORDER BY scanned_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: int):
    conn = get_db()
    try:
        conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
        return {"deleted": contact_id}
    finally:
        conn.close()


# ─── bookmarks ───
class BookmarkCreate(BaseModel):
    entity_id: str
    type: str


@router.get("/bookmarks")
async def list_bookmarks():
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT * FROM user_bookmarks ORDER BY created_at DESC"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.post("/bookmarks")
async def create_badge(payload: BookmarkCreate):
    conn = get_db()
    try:
        entity_id = payload.entity_id
        btype = payload.type

        conn.execute(
            """
            INSERT INTO user_bookmarks (type, entity_id)
            VALUES (?, ?)
            """,
            (btype, entity_id),
        )
        conn.commit()

        cur = conn.execute(
            "SELECT * FROM user_bookmarks ORDER BY id DESC LIMIT 1"
        )
        return dict(cur.fetchone())
    finally:
        conn.close()


@router.delete("/bookmarks/{bookmark_id}")
async def delete_badge(bookmark_id: int):
    conn = get_db()
    try:
        conn.execute("DELETE FROM user_bookmarks WHERE id = ?", (bookmark_id,))
        conn.commit()
        return {"deleted": bookmark_id}
    finally:
        conn.close()
