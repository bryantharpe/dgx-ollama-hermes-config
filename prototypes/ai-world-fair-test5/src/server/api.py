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


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/talks")
async def list_talks(q: Optional[str] = None, topic: Optional[str] = None, track: Optional[str] = None, level: Optional[str] = None, speaker: Optional[str] = None):
    conn = get_db()
    try:
        where_clauses = []
        params = []
        
        if q:
            where_clauses.append("(title LIKE ? OR speaker_name LIKE ? OR topics LIKE ? OR description LIKE ?)")
            search_term = f"%{q}%"
            params.extend([search_term, search_term, search_term, search_term])
        
        if topic:
            where_clauses.append("topics LIKE ?")
            params.append(f"%{topic}%")
        
        if track:
            where_clauses.append("track = ?")
            params.append(track)
        
        if level:
            where_clauses.append("level = ?")
            params.append(level)
        
        if speaker:
            where_clauses.append("speaker_name LIKE ?")
            params.append(f"%{speaker}%")
        
        query = "SELECT * FROM talks"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY start_time"
        
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/talks/{talk_id}")
async def get_talk(talk_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM talks WHERE id = ?", (talk_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Talk not found")
        return dict(row)
    finally:
        conn.close()


@router.get("/speakers")
async def list_speakers(q: Optional[str] = None):
    conn = get_db()
    try:
        where_clauses = []
        params = []
        
        if q:
            where_clauses.append("name LIKE ?")
            params.append(f"%{q}%")
        
        query = "SELECT * FROM speakers"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY name"
        
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/speakers/{speaker_id}")
async def get_speaker(speaker_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM speakers WHERE id = ?", (speaker_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Speaker not found")
        return dict(row)
    finally:
        conn.close()


@router.get("/booths")
async def list_booths(q: Optional[str] = None, zone: Optional[str] = None):
    conn = get_db()
    try:
        where_clauses = []
        params = []
        
        if q:
            where_clauses.append("name LIKE ?")
            params.append(f"%{q}%")
        
        if zone:
            where_clauses.append("zone = ?")
            params.append(zone)
        
        query = "SELECT * FROM booths"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY zone, name"
        
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/booths/{booth_id}")
async def get_booth(booth_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM booths WHERE id = ?", (booth_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Booth not found")
        return dict(row)
    finally:
        conn.close()


@router.get("/schedule")
async def get_schedule():
    conn = get_db()
    try:
        cur = conn.execute("""
            SELECT t.*, s.pinned_at 
            FROM talks t 
            JOIN user_schedule s ON t.id = s.talk_id 
            ORDER BY t.start_time
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.post("/schedule/pin")
async def pin_talk(data: Dict[str, int]):
    talk_id = data.get("talk_id")
    if not talk_id:
        raise HTTPException(status_code=400, detail="talk_id is required")
    
    conn = get_db()
    try:
        cur = conn.execute("SELECT id FROM talks WHERE id = ?", (talk_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Talk not found")
        
        cur = conn.execute("SELECT id FROM user_schedule WHERE talk_id = ?", (talk_id,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Talk already pinned")
        
        conn.execute(
            "INSERT INTO user_schedule (talk_id, pinned_at) VALUES (?, ?)",
            (talk_id, "2026-06-29T13:55:00")
        )
        conn.commit()
        return {"status": "ok", "talk_id": talk_id}
    finally:
        conn.close()


@router.delete("/schedule/unpin/{talk_id}")
async def unpin_talk(talk_id: int):
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM user_schedule WHERE talk_id = ?", (talk_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Talk not in schedule")
        conn.commit()
        return {"status": "ok", "talk_id": talk_id}
    finally:
        conn.close()


@router.get("/contacts")
async def list_contacts(q: Optional[str] = None):
    conn = get_db()
    try:
        where_clauses = []
        params = []
        
        if q:
            where_clauses.append("(name LIKE ? OR github LIKE ? OR hacking_on LIKE ?)")
            search_term = f"%{q}%"
            params.extend([search_term, search_term, search_term])
        
        query = "SELECT * FROM contacts"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY scanned_at DESC"
        
        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.post("/contacts")
async def save_contact(data: Dict[str, str]):
    conn = get_db()
    try:
        name = data.get("name")
        github = data.get("github")
        hacking_on = data.get("hacking_on")
        badge_json = data.get("badge_json", "")
        
        if not name:
            raise HTTPException(status_code=400, detail="name is required")
        
        conn.execute(
            "INSERT OR REPLACE INTO contacts (name, github, hacking_on, scanned_at, badge_json) VALUES (?, ?, ?, ?, ?)",
            (name, github or "", hacking_on or "", "2026-06-29T16:30:00", badge_json)
        )
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()


@router.get("/badge")
async def get_badge():
    badge_path = os.path.join(DATA_DIR, "badge.json")
    return read_json(badge_path, {"name": "AI Engineer", "github": "", "hacking_on": "Exploring the conference"})


@router.post("/badge")
async def update_badge(data: Dict[str, str]):
    badge_path = os.path.join(DATA_DIR, "badge.json")
    write_json(badge_path, data)
    return data


@router.get("/expo/pins")
async def get_expo_pins():
    conn = get_db()
    try:
        cur = conn.execute("""
            SELECT b.*, p.pinned_at 
            FROM booths b 
            JOIN user_pins p ON b.id = p.booth_id 
            ORDER BY b.name
        """)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.post("/expo/pin")
async def pin_booth(data: Dict[str, int]):
    booth_id = data.get("booth_id")
    if not booth_id:
        raise HTTPException(status_code=400, detail="booth_id is required")
    
    conn = get_db()
    try:
        cur = conn.execute("SELECT id FROM booths WHERE id = ?", (booth_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Booth not found")
        
        cur = conn.execute("SELECT id FROM user_pins WHERE booth_id = ?", (booth_id,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Booth already pinned")
        
        conn.execute(
            "INSERT INTO user_pins (booth_id, pinned_at) VALUES (?, ?)",
            (booth_id, "2026-06-29T10:00:00")
        )
        conn.commit()
        return {"status": "ok", "booth_id": booth_id}
    finally:
        conn.close()


@router.delete("/expo/unpin/{booth_id}")
async def unpin_booth(booth_id: int):
    conn = get_db()
    try:
        cur = conn.execute("DELETE FROM user_pins WHERE booth_id = ?", (booth_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Booth not in pins")
        conn.commit()
        return {"status": "ok", "booth_id": booth_id}
    finally:
        conn.close()


def nearest_neighbor_path(booths):
    if not booths:
        return []
    
    remaining = list(booths)
    path = [remaining.pop(0)]
    
    while remaining:
        last = path[-1]
        last_x, last_y = last.get("grid_x", 0), last.get("grid_y", 0)
        
        nearest = None
        nearest_dist = float("inf")
        
        for booth in remaining:
            dist = abs(booth.get("grid_x", 0) - last_x) + abs(booth.get("grid_y", 0) - last_y)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest = booth
        
        if nearest:
            path.append(nearest)
            remaining.remove(nearest)
    
    return path


@router.get("/expo/route")
async def get_expo_route():
    conn = get_db()
    try:
        cur = conn.execute("SELECT id, name, zone, grid_x, grid_y FROM booths WHERE id IN (SELECT booth_id FROM user_pins)")
        booths = [dict(r) for r in cur.fetchall()]
        
        if not booths:
            return {"path": [], "booths": []}
        
        ordered = nearest_neighbor_path(booths)
        
        return {
            "path": [b["id"] for b in ordered],
            "booths": ordered
        }
    finally:
        conn.close()
