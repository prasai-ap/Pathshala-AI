#!/usr/bin/env bash
set -euo pipefail

BACKEND_INTERNAL_PORT="${BACKEND_INTERNAL_PORT:-8000}"

uvicorn backend.main:app \
  --host 127.0.0.1 \
  --port "${BACKEND_INTERNAL_PORT}" &

python -m streamlit run frontend/app.py \
  --server.address 0.0.0.0 \
  --server.port "${PORT:-10000}"
