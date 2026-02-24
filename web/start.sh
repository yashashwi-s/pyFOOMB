#!/bin/bash
# pyFOOMB Web GUI — Start Script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Initialize Conda (Required for 'conda activate' to work inside a script)
CONDA_PATH=$(conda info --base)/etc/profile.d/conda.sh
if [ -f "$CONDA_PATH" ]; then
    source "$CONDA_PATH"
else
    echo "Error: Conda initialization script not found at $CONDA_PATH"
    exit 1
fi

echo "═══════════════════════════════════════"
echo "  pyFOOMB Web GUI"
echo "═══════════════════════════════════════"

# Start backend
echo ""
echo "→ Starting backend (FastAPI) on port 8000..."
cd "$SCRIPT_DIR/backend"

conda activate bpdd

# DEBUG: Verify we are using the correct Python (Should be 3.9 in the bpdd env)
echo "  Using Python: $(which python)"
python --version

# Use 'python -m' to ensure we use the environment's uvicorn
python -m uvicorn main:app --reload --port 8000 --host 0.0.0.0 &
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

trap "echo ''; echo 'Shutting down...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM

wait