#!/usr/bin/env bash
# OmniMarket Intelligence Terminal - launcher (macOS / Linux)
set -euo pipefail
cd "$(dirname "$0")"
echo -e "\n  OMNIMARKET  Intelligence Terminal\n"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
[ -d frontend/node_modules ] || (cd frontend && npm install --no-fund --no-audit)
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
API=$!
(cd frontend && npx vite --host 127.0.0.1 --port 5173) &
UI=$!
trap 'kill $API $UI 2>/dev/null' EXIT INT TERM
sleep 4
(command -v open >/dev/null && open http://localhost:5173) || (command -v xdg-open >/dev/null && xdg-open http://localhost:5173) || true
echo "  API http://localhost:8000/docs · UI http://localhost:5173 - Ctrl+C to stop"
wait
