import json
import os
import sqlite3
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException

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


# ─── talks ────────────────────────────────────────────────────────────────────
@router.get("/talks")
async def list_talks(day: Optional[str] = None, q: Optional[str] = None, tag: Optional[str] = None):
    conn = get_db()
    try:
        query = "SELECT * FROM talks WHERE 1=1"
        params = []
        if day:
            query += " AND day = ?"
            params.append(day)
        if q:
            query += " AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)"
            params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
        if tag:
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")
        query += " ORDER BY day, start_time"
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/talks/search")
async def search_talks(q: str):
    conn = get_db()
    try:
        # Relevance: tag match > title match > description match
        search_term = f"%{q}%"
        cur = conn.execute(
            """
            SELECT *, 
                CASE 
                    WHEN tags LIKE ? THEN 1
                    WHEN title LIKE ? THEN 2
                    WHEN description LIKE ? THEN 3
                    ELSE 4
                END as relevance
            FROM talks
            WHERE title LIKE ? OR description LIKE ? OR tags LIKE ?
            ORDER BY relevance, day, start_time
            """,
            [search_term, search_term, search_term, search_term, search_term, search_term]
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/speakers")
async def list_speakers():
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM speakers ORDER BY name")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/speakers/{speaker_id}")
async def get_speaker(speaker_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM speakers WHERE id = ?", [speaker_id])
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Speaker not found")
        return dict(row)
    finally:
        conn.close()


# ─── expo booths ──────────────────────────────────────────────────────────────
@router.get("/booths")
async def list_booths():
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM expo_booths ORDER BY company_name")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/booths/search")
async def search_booths(q: str):
    conn = get_db()
    try:
        search_term = f"%{q}%"
        cur = conn.execute(
            """
            SELECT * FROM expo_booths
            WHERE company_name LIKE ? OR tags LIKE ? OR description LIKE ?
            ORDER BY company_name
            """,
            [search_term, search_term, search_term]
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.post("/booths/{booth_id}/pin")
async def pin_booth(booth_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT id FROM expo_booths WHERE id = ?", [booth_id])
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Booth not found")
        pinned_path = os.path.join(DATA_DIR, "pinned_booths.json")
        pinned = read_json(pinned_path, [])
        if booth_id not in pinned:
            pinned.append(booth_id)
            write_json(pinned_path, pinned)
        return {"status": "pinned", "booth_id": booth_id}
    finally:
        conn.close()


@router.get("/booths/pinned")
async def get_pinned_booths():
    pinned_path = os.path.join(DATA_DIR, "pinned_booths.json")
    pinned = read_json(pinned_path, [])
    return {"pinned": pinned}


# ─── routes ───────────────────────────────────────────────────────────────────
@router.post("/routes/calculate")
async def calculate_route(payload: Dict[str, Any]):
    pinned_booth_ids = payload.get("booth_ids", [])
    if len(pinned_booth_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 booths to calculate a route")
    
    conn = get_db()
    try:
        placeholders = ",".join("?" * len(pinned_booth_ids))
        cur = conn.execute(
            f"SELECT id, grid_x, grid_y FROM expo_booths WHERE id IN ({placeholders})",
            pinned_booth_ids
        )
        booths = {row["id"]: (row["grid_x"], row["grid_y"]) for row in cur.fetchall()}
    finally:
        conn.close()
    
    entrance = (5.0, 5.0)
    route = []
    current = entrance
    remaining = list(pinned_booth_ids)
    
    while remaining:
        nearest = None
        nearest_dist = float("inf")
        for booth_id in remaining:
            x, y = booths[booth_id]
            dist = ((x - current[0]) ** 2 + (y - current[1]) ** 2) ** 0.5
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = booth_id
        route.append(nearest)
        current = booths[nearest]
        remaining.remove(nearest)
    
    return {"route": route, "total_distance": round(nearest_dist, 2)}


# ─── expo map ─────────────────────────────────────────────────────────────────
@router.get("/expo/map")
async def get_expo_map():
    map_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "expo-map.svg")
    if os.path.exists(map_path):
        with open(map_path, "r") as f:
            svg = f.read()
        return {"svg": svg}
    return {"error": "Map not found"}


# ─── contacts / QR ────────────────────────────────────────────────────────────
@router.post("/contacts/scan")
async def scan_contact(payload: Dict[str, Any]):
    conn = get_db()
    try:
        name = payload.get("name", "")
        github = payload.get("github", "")
        project = payload.get("project", "")
        source_id = payload.get("source_id", "")
        scanned_at = payload.get("scanned_at") or "2026-04-20T00:00:00"
        
        cur = conn.execute(
            "INSERT INTO saved_contacts (name, github, project, scanned_at, source_id) VALUES (?, ?, ?, ?, ?)",
            [name, github, project, scanned_at, source_id]
        )
        return {"id": cur.lastrowid, "status": "saved"}
    finally:
        conn.close()


@router.get("/contacts")
async def list_contacts():
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM saved_contacts ORDER BY scanned_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM saved_contacts WHERE id = ?", [contact_id])
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        return dict(row)
    finally:
        conn.close()


@router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT id FROM saved_contacts WHERE id = ?", [contact_id])
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Contact not found")
        conn.execute("DELETE FROM saved_contacts WHERE id = ?", [contact_id])
        return {"status": "deleted"}
    finally:
        conn.close()


@router.get("/badge")
async def get_badge():
    badge = {
        "name": "AI Engineer",
        "github": "ai-engineer",
        "project": "Worlds Fair Companion",
        "source_id": "badge-001",
        "scanned_at": "2026-04-20T00:00:00"
    }
    return badge
