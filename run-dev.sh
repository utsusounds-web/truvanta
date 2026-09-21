#!/usr/bin/env bash
# Starts the Django backend and Vite frontend together; Ctrl+C stops both.
# Verifies the backend actually comes up before starting the frontend —
# if it doesn't, you get a clear reason instead of a silent "can't reach
# the server" error later inside the app.
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_LOG="$(mktemp)"

cleanup() {
  echo ""
  echo "Stopping..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  rm -f "$BACKEND_LOG"
}
trap cleanup EXIT INT TERM

if [ ! -f "$ROOT_DIR/backend/.env" ]; then
  echo "backend/.env not found — copying from .env.example"
  cp "$ROOT_DIR/backend/.env.example" "$ROOT_DIR/backend/.env"
fi
if [ ! -f "$ROOT_DIR/frontend/.env" ]; then
  echo "frontend/.env not found — copying from .env.example"
  cp "$ROOT_DIR/frontend/.env.example" "$ROOT_DIR/frontend/.env"
fi

if [ ! -d "$ROOT_DIR/backend/venv" ]; then
  echo "No backend/venv found — set it up first:"
  echo "  cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "frontend/node_modules not found — installing dependencies now..."
  (cd "$ROOT_DIR/frontend" && npm install)
fi

echo "Starting backend on http://localhost:8000 ..."
(
  cd "$ROOT_DIR/backend"
  source venv/bin/activate
  python manage.py migrate --noinput
  python manage.py runserver 0.0.0.0:8000
) > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

echo -n "Waiting for backend to come up"
BACKEND_UP=false
for i in $(seq 1 20); do
  if curl -s -o /dev/null "http://localhost:8000/api/auth/me/" 2>/dev/null; then
    BACKEND_UP=true
    break
  fi
  echo -n "."
  sleep 1
done
echo ""

if [ "$BACKEND_UP" != "true" ]; then
  echo ""
  echo "The backend did not come up within 20 seconds. Its output:"
  echo "----------------------------------------------------------"
  cat "$BACKEND_LOG"
  echo "----------------------------------------------------------"
  echo "Common causes: dependencies not installed (pip install -r requirements.txt"
  echo "inside backend/venv), a migration error, or port 8000 already in use by"
  echo "something else. See RUNNING.md > Troubleshooting for more."
  exit 1
fi
echo "Backend is up."

echo "Starting frontend on http://localhost:5173 ..."
(
  cd "$ROOT_DIR/frontend"
  npm run dev
) &
FRONTEND_PID=$!

wait "$BACKEND_PID" "$FRONTEND_PID"
