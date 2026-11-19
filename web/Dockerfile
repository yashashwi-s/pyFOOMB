# pyFOOMB Web GUI — Dockerfile
# Multi-stage build: conda backend + Node.js frontend
#
# Build from the REPO ROOT (not this web/ directory), since the backend needs the
# pyfoomb/ package source and its conda env spec, which live one level up:
#   docker build -f web/Dockerfile -t pyfoomb-web .
#   docker run -p 3000:3000 -p 8000:8000 pyfoomb-web
#
# NOTE: for the Vercel (frontend) + Render (backend) split deployment, the frontend
# half of this image isn't used — see web/backend/Dockerfile for a backend-only
# image, and render.yaml at the repo root.

FROM continuumio/miniconda3:latest AS backend-base

# pyfoomb is this repo's own package, not a published conda-forge package — install
# its real dependencies (assimulo needs the compiled SUNDIALS C library via conda)
# from environment.yml, then pip-install pyfoomb itself from source.
WORKDIR /app
COPY environment.yml ./environment.yml
RUN conda env create -f environment.yml && conda clean -afy

COPY pyfoomb ./pyfoomb
COPY setup.py pyproject.toml README.md MANIFEST.in ./
COPY web/backend/requirements.txt ./web/backend/requirements.txt
RUN conda run -n pyfoomb pip install --no-cache-dir -e . -r web/backend/requirements.txt

COPY web/backend ./web/backend

# Frontend build stage
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY web/frontend/package*.json ./
RUN npm ci
COPY web/frontend/ .
RUN npm run build

# Final stage: backend-base already has the conda env + backend/ source; add
# Node.js and the built frontend on top of it.
FROM backend-base

# Node.js for the frontend
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy frontend build
COPY --from=frontend-build /app/frontend/.next /app/frontend/.next
COPY --from=frontend-build /app/frontend/node_modules /app/frontend/node_modules
COPY --from=frontend-build /app/frontend/package.json /app/frontend/package.json
COPY --from=frontend-build /app/frontend/public /app/frontend/public
COPY --from=frontend-build /app/frontend/next.config.ts /app/frontend/next.config.ts

# Copy start script
COPY web/start-docker.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 3000 8000

CMD ["/app/start.sh"]
