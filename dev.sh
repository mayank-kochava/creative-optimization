#!/usr/bin/env bash
# Run the full Creative Intelligence Platform stack locally.
# Usage:
#   ./dev.sh          — start everything
#   ./dev.sh seed     — (re)seed demo data after DB is up
#   ./dev.sh stop     — stop all services
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

case "${1:-}" in
  stop)
    echo "Stopping..."
    docker compose -f "$ROOT/docker-compose.yml" down
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
    echo "Done."
    exit 0
    ;;
  seed)
    echo "Seeding demo data..."
    cd "$BACKEND" && python3.11 scripts/seed_data.py
    exit 0
    ;;
esac

# 1. Postgres
echo "▶ Starting Postgres..."
docker compose -f "$ROOT/docker-compose.yml" up -d postgres
echo "  Waiting for Postgres to be ready..."
until docker compose -f "$ROOT/docker-compose.yml" exec -T postgres pg_isready -U appuser -d creative_opt -q; do
  sleep 1
done
echo "  Postgres ready."

# 2. Run migration
echo "▶ Running Alembic migration..."
cd "$BACKEND" && python3.11 -m alembic upgrade head

# 3. Seed data (idempotent — truncates and re-seeds each run)
echo "▶ Seeding demo data..."
cd "$BACKEND" && python3.11 scripts/seed_data.py

# 4. Backend
echo "▶ Starting FastAPI backend on http://localhost:8000 ..."
cd "$BACKEND" && python3.11 -m uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# 5. Frontend
echo "▶ Starting Next.js frontend on http://localhost:3000 ..."
cd "$FRONTEND" && npm run dev &
FRONTEND_PID=$!

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Frontend : http://localhost:3000"
echo "  Backend  : http://localhost:8000"
echo "  API docs : http://localhost:8000/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Press Ctrl+C to stop."

# Forward Ctrl+C to children
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker compose -f \"$ROOT/docker-compose.yml\" stop postgres; exit 0" INT TERM
wait
