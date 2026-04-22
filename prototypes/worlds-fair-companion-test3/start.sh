#!/bin/bash
set -e

cd /app

python /app/src/database/seed.py

exec uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir /app/src/server
