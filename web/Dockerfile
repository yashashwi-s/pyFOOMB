# pyFOOMB Web GUI — Dockerfile
# Multi-stage build: conda backend + Node.js frontend

FROM continuumio/miniconda3:latest AS backend-base

# Install pyfoomb and dependencies via conda
RUN conda install -y -c conda-forge python=3.9 pyfoomb assimulo pygmo \
    numpy scipy pandas openpyxl joblib psutil matplotlib seaborn && \
    conda clean -afy

# Install FastAPI dependencies
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

WORKDIR /app/backend
COPY backend/ .

# Frontend build stage
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Final stage
FROM continuumio/miniconda3:latest

# Backend setup
RUN conda install -y -c conda-forge python=3.9 pyfoomb assimulo pygmo \
    numpy scipy pandas openpyxl joblib psutil matplotlib seaborn && \
    conda clean -afy
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Node.js for frontend
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy backend
COPY backend/ /app/backend/

# Copy frontend build
COPY --from=frontend-build /app/frontend/.next /app/frontend/.next
COPY --from=frontend-build /app/frontend/node_modules /app/frontend/node_modules
COPY --from=frontend-build /app/frontend/package.json /app/frontend/package.json
COPY --from=frontend-build /app/frontend/public /app/frontend/public
COPY --from=frontend-build /app/frontend/next.config.ts /app/frontend/next.config.ts

# Copy start script
COPY start-docker.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 3000 8000

CMD ["/app/start.sh"]
