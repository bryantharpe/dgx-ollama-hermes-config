# Prototype Template

Starter skeleton for Hermes-generated prototypes. Copy this directory, fill in the feature code, and ship.

## Stack
Python 3.12-slim · FastAPI · Uvicorn · SQLite · vanilla HTML/CSS/JS. Airgap-native (`pip install` at build time, zero runtime network).

## Boot it
```bash
PROTOTYPE_NAME=my-prototype PROTOTYPE_PORT=9001 docker compose up -d --build
curl http://localhost:9001/api/health   # {"status":"ok"}
curl -I http://localhost:9001/          # 200, text/html
```

## What each file does

| Path | Role |
|------|------|
| `Dockerfile` | Single-image build. Installs deps, copies `src/`, healthchecks `/api/health`. |
| `docker-compose.yml` | Reads `${PROTOTYPE_NAME}` and `${PROTOTYPE_PORT}` from env. Mounts `./data` for SQLite + JSON state. |
| `start.sh` | Entrypoint: seed DB then exec uvicorn with `--app-dir`. |
| `requirements.txt` | FastAPI + uvicorn. Feature-specific deps (qrcode, sqlite-utils, etc.) get appended here. |
| `src/server/main.py` | FastAPI app. `BASE_DIR`/`FRONTEND_DIR` computed absolutely. Mounts `/static`. `/` serves `index.html`. `/api/health` returns ok. |
| `src/server/api.py` | Empty `APIRouter(prefix="/api")` — add feature routes here. |
| `src/database/schema.sql` | Empty. Add `CREATE TABLE` statements per feature. |
| `src/database/seed.py` | Reads schema, creates `data/app.db` via `SCRIPT_DIR`-absolute paths. Add seed data. |
| `src/frontend/index.html` | Shell. Loads `/static/css/app.css` and `/static/js/app.js`. |
| `src/frontend/css/app.css` | Base styles. Replace per prototype. |
| `src/frontend/js/app.js` | Base JS. Fetches `/api/health` on load as a smoke check. |
| `data/` | Runtime volume mount. SQLite DB and any server-side JSON live here. |

## What to add per prototype

1. **Tables** → `src/database/schema.sql`
2. **Seed data** → `src/database/seed.py`
3. **API routes** → `src/server/api.py`
4. **UI** → `src/frontend/index.html` + per-feature `.js`/`.css` in `src/frontend/js/`, `src/frontend/css/`
5. **Feature deps** → append to `requirements.txt`

## Patterns that are already correct — don't change them

- Absolute paths via `BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` in `main.py` / `api.py`
- `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` + `from api import router` in `main.py`
- DB path computed from `SCRIPT_DIR` in `seed.py`
- `uvicorn main:app --app-dir /app/src/server` in `start.sh` (avoids needing an `__init__.py` hierarchy)
- Healthcheck hits `/api/health`
- Port comes from `${PROTOTYPE_PORT}`, never hardcoded

Every one of these patterns exists because a previous prototype broke without it.

## Verify the template itself
```bash
cd /home/admin/code/hermes-config/prototypes
cp -r _template _smoke_test
cd _smoke_test
PROTOTYPE_NAME=smoke PROTOTYPE_PORT=9999 docker compose up -d --build
sleep 3 && curl -fsS http://localhost:9999/api/health
docker compose down -v && cd .. && rm -rf _smoke_test
```
