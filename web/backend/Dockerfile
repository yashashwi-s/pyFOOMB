# pyFOOMB backend API — standalone image (frontend is deployed separately on Vercel).
#
# Build context must be the REPO ROOT (not web/backend/), since this needs the
# pyfoomb/ package source plus its conda env spec. On Render, set:
#   dockerfilePath: web/backend/Dockerfile
#   dockerContext:  .
# (already configured in render.yaml at the repo root).
FROM continuumio/miniconda3:latest

WORKDIR /app

# assimulo needs the compiled SUNDIALS C library, which is only reliably available
# via conda-forge — this recreates the same env pip alone cannot build.
COPY environment.yml ./environment.yml
RUN conda env create -f environment.yml && conda clean -afy

# Install the pyfoomb package itself (this repo, not a published package) plus the
# FastAPI server's own deps, into that same env.
COPY pyfoomb ./pyfoomb
COPY setup.py pyproject.toml README.md MANIFEST.in ./
COPY web/backend/requirements.txt ./web/backend/requirements.txt
RUN conda run -n pyfoomb pip install --no-cache-dir -e . -r web/backend/requirements.txt

COPY web/backend ./web/backend
WORKDIR /app/web/backend

EXPOSE 8000
CMD ["conda", "run", "--no-capture-output", "-n", "pyfoomb", "sh", "-c", \
     "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
