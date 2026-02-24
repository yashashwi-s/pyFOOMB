#!/bin/bash
# Docker entrypoint — starts both servers
set -e

cd /app/backend
uvicorn main:app --host 0.0.0.0 --port 8000 &

cd /app/frontend
npx next start -p 3000 &

wait
