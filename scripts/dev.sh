#!/usr/bin/env bash
set -e

# Resolve repository root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# 1. Environment initialization
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "Notice: .env not found. Initializing from .env.example..."
        cp .env.example .env
    else
        echo "Error: Neither .env nor .env.example found."
        exit 1
    fi
fi

if [ ! -f "web/.env.local" ]; then
    cat <<EOF > web/.env.local
BACKEND_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
EOF
fi

BACKEND_ONLY=false
FRONTEND_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --backend-only) BACKEND_ONLY=true ;;
        --frontend-only) FRONTEND_ONLY=true ;;
    esac
done

if [ "$BACKEND_ONLY" = true ]; then
    echo "Starting TalentGraph Backend on http://127.0.0.1:8000..."
    exec uv run uvicorn talentgraph.api.main:app --host 127.0.0.1 --port 8000 --reload
fi

if [ "$FRONTEND_ONLY" = true ]; then
    echo "Starting TalentGraph Frontend on http://localhost:3000..."
    cd web && exec npm run dev
fi

echo "=========================================================="
echo " Starting TalentGraph (Backend :8000 + Frontend :3000)"
echo " Press Ctrl+C to terminate both services."
echo "=========================================================="

cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}
trap cleanup INT TERM EXIT

# Start backend in background
uv run uvicorn talentgraph.api.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Wait for backend health
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo "Backend is live at http://127.0.0.1:8000"
        break
    fi
    sleep 0.5
done

# Start frontend in foreground
cd web && npm run dev

