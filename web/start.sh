#!/bin/bash
# pyFOOMB Web GUI — Start Script
# Starts both backend (FastAPI) and frontend (Next.js) servers.
# Uses conda env 'bpdd' for the backend.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "═══════════════════════════════════════"
echo "  pyFOOMB Web GUI"
echo "═══════════════════════════════════════"

# Start backend
echo ""
echo "→ Starting backend (FastAPI) on port 8000..."
cd "$SCRIPT_DIR/backend"
conda run --no-banner -n bpdd uvicorn main:app --reload --port 8000 --host 0.0.0.0 &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"

# Start frontend
echo "→ Starting frontend (Next.js) on port 3000..."
cd "$SCRIPT_DIR/frontend"
npm run dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"

echo ""
echo "═══════════════════════════════════════"
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:3000"
echo "  API docs: http://localhost:8000/docs"
echo "═══════════════════════════════════════"
echo ""
echo "Press Ctrl+C to stop both servers."

# Trap SIGINT to kill both processes
trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# Wait for either process to exit
wait
