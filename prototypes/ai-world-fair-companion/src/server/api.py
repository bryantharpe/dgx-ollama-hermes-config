import base64
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter(prefix="/api", tags=["api"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "fair.db")
PINS_PATH = os.path.join(DATA_DIR, "pins.json")

os.makedirs(DATA_DIR, exist_ok=True)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def read_json(path: str, default: Any) -> Any:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default
    return default


def write_json(path: str, value: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(value, f, indent=2)


def json_response(data: Any, status: int = 200):
    return {"data": data} if not isinstance(data, dict) else data


# ─── talks ─────────────────────────────────────────────────────────────────
@router.get("/talks")
async def list_talks(
    tag: Optional[str] = Query(None),
    speaker: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
):
    conn = get_db()
    try:
        where = []
        params = []
        if tag:
            where.append("tags LIKE ?")
            params.append(f"%{tag}%")
        if speaker:
            where.append("speaker_name LIKE ?")
            params.append(f"%{speaker}%")
        if date:
            where.append("DATE(start_time) = DATE(?)")
            params.append(date)

        query = "SELECT * FROM talks"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY start_time"

        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/talks/search")
async def search_talks(q: str = Query(..., alias="q")):
    conn = get_db()
    try:
        search_term = f"%{q}%"
        query = """
            SELECT * FROM talks
            WHERE title LIKE ? OR description LIKE ? OR speaker_name LIKE ? OR tags LIKE ?
            ORDER BY start_time
        """
        cur = conn.execute(query, [search_term, search_term, search_term, search_term])
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/talks/{talk_id}")
async def get_talk(talk_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM talks WHERE id = ?", (talk_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Talk not found")
        return dict(row)
    finally:
        conn.close()


# ─── speakers ──────────────────────────────────────────────────────────────
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
        cur = conn.execute("SELECT * FROM speakers WHERE id = ?", (speaker_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Speaker not found")
        speaker = dict(row)
        cur_talks = conn.execute("SELECT * FROM talks WHERE speaker_name = ?", (speaker["name"],))
        speaker["talks"] = [dict(t) for t in cur_talks.fetchall()]
        return speaker
    finally:
        conn.close()


# ─── booths ───────────────────────────────────────────────────────────────
@router.get("/booths")
async def list_booths(
    tag: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    conn = get_db()
    try:
        where = []
        params = []
        if tag:
            where.append("tags LIKE ?")
            params.append(f"%{tag}%")
        if category:
            where.append("category = ?")
            params.append(category)

        query = "SELECT * FROM expo_booths"
        if where:
            query += " WHERE " + " AND ".join(where)
        query += " ORDER BY booth_number"

        cur = conn.execute(query, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/booths/{booth_id}")
async def get_booth(booth_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM expo_booths WHERE id = ?", (booth_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Booth not found")
        return dict(row)
    finally:
        conn.close()


@router.get("/booths/pins")
async def get_pins(request: Request):
    pins = read_json(PINS_PATH, [])
    return {"pins": pins}


@router.post("/booths/pins")
async def toggle_pin(request: Request, body: Dict[str, Any]):
    booth_id = body.get("booth_id")
    action = body.get("action", "pin")
    pins = read_json(PINS_PATH, [])
    if action == "pin":
        if booth_id not in pins:
            pins.append(booth_id)
    else:
        if booth_id in pins:
            pins.remove(booth_id)
    write_json(PINS_PATH, pins)
    return {"pins": pins}


@router.get("/route")
async def get_route(
    request: Request,
    from_id: int = Query(..., alias="from"),
    to_id: int = Query(..., alias="to"),
):
    pins = read_json(PINS_PATH, [])
    if from_id not in pins or to_id not in pins:
        raise HTTPException(status_code=400, detail="Both booths must be pinned")

    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT x, y FROM expo_booths WHERE id IN (?, ?)", (from_id, to_id)
        )
        rows = cur.fetchall()
        if len(rows) != 2:
            raise HTTPException(status_code=404, detail="Booths not found")

        from_pos = (rows[0]["x"], rows[0]["y"])
        to_pos = (rows[1]["x"], rows[1]["y"])

        path = a_star_pathfinding(from_pos, to_pos, pins)
        return {"path": path, "from": from_id, "to": to_id}
    finally:
        conn.close()


def a_star_pathfinding(
    start: tuple, goal: tuple, pinned_booths: List[int]
) -> List[Dict[str, Any]]:
    grid_size = 100
    grid = [[0] * grid_size for _ in range(grid_size)]

    blocked = set()
    conn = get_db()
    try:
        cur = conn.execute("SELECT x, y FROM expo_booths WHERE id IN ({})".format(
            ",".join("?" * len(pinned_booths))
        ), pinned_booths)
        for row in cur.fetchall():
            bx, by = int(row["x"]), int(row["y"])
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    nx, ny = bx + dx, by + dy
                    if 0 <= nx < grid_size and 0 <= ny < grid_size:
                        blocked.add((nx, ny))
    finally:
        conn.close()

    for bx, by in blocked:
        grid[bx][by] = 1

    def heuristic(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def get_neighbors(pos):
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < grid_size and 0 <= ny < grid_size and grid[nx][ny] == 0:
                neighbors.append((nx, ny))
        return neighbors

    open_set = [(heuristic(start, goal), 0, start, [start])]
    visited = set()

    while open_set:
        open_set.sort(key=lambda x: x[0])
        _, cost, current, path = open_set.pop(0)

        if current == goal:
            return [{"x": p[0], "y": p[1]} for p in path]

        if current in visited:
            continue
        visited.add(current)

        for neighbor in get_neighbors(current):
            if neighbor not in visited:
                new_cost = cost + 1
                heur = new_cost + heuristic(neighbor, goal)
                open_set.append((heur, new_cost, neighbor, path + [neighbor]))

    return [{"x": start[0], "y": start[1]}, {"x": goal[0], "y": goal[1]}]


# ─── contacts ──────────────────────────────────────────────────────────────
@router.post("/contacts/scan")
async def scan_contact(body: Dict[str, str]):
    payload = body.get("payload")
    if not payload:
        raise HTTPException(status_code=400, detail="Missing payload")

    try:
        decoded = base64.b64decode(payload).decode("utf-8")
        contact_data = json.loads(decoded)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload format")

    name = contact_data.get("n", "")
    github = contact_data.get("g", "")
    project = contact_data.get("p", "")
    source_hash = payload

    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT id FROM contacts WHERE source_hash = ?", (source_hash,)
        )
        if cur.fetchone():
            return {"message": "Contact already exists", "saved": False}

        from datetime import datetime
        scanned_at = datetime.utcnow().isoformat() + "Z"

        conn.execute(
            "INSERT INTO contacts (name, github, project, scanned_at, source_hash) VALUES (?, ?, ?, ?, ?)",
            (name, github, project, scanned_at, source_hash),
        )
        conn.commit()
        return {"message": "Contact saved", "saved": True}
    finally:
        conn.close()


@router.get("/contacts")
async def list_contacts():
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM contacts ORDER BY scanned_at DESC")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Contact not found")
        return dict(row)
    finally:
        conn.close()


@router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: int):
    conn = get_db()
    try:
        cur = conn.execute("SELECT id FROM contacts WHERE id = ?", (contact_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Contact not found")
        conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
        conn.commit()
        return {"message": "Contact deleted"}
    finally:
        conn.close()


# ─── badge ─────────────────────────────────────────────────────────────────
@router.get("/badge")
async def get_badge():
    return {
        "name": os.environ.get("USER_NAME", "Conference Attendee"),
        "github": os.environ.get("USER_GITHUB", "attendee"),
        "project": os.environ.get("USER_PROJECT", "AI Engineer"),
    }
