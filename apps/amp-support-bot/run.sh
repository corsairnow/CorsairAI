#!/usr/bin/env bash
set -euo pipefail
export PYTHONUNBUFFERED=1
export APP_PORT="${APP_PORT:-1060}"
print("Hwllow world")
uvicorn app.main:app --host 0.0.0.0 --port "$APP_PORT"
# uvicorn app.main:app --host 192.168.1.71 --port "$APP_PORT" --reload

