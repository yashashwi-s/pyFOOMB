"""
pyFOOMB Web GUI — Backend API
FastAPI server wrapping pyFOOMB as REST endpoints.
"""

# Suppress assimulo warnings about optional solvers (dopri5, rodas, etc.)
# pyFOOMB only uses CVode which is always available.
import warnings
import os
os.environ["ASSIMULO_SUPPRESS_WARNINGS"] = "1"
warnings.filterwarnings("ignore", message=".*cannot import name.*from 'assimulo.*")
warnings.filterwarnings("ignore", message=".*Could not find.*")

import sys
import io
_stderr = sys.stderr
sys.stderr = io.StringIO()
try:
    import assimulo  # noqa: F401
except Exception:
    pass
sys.stderr = _stderr

# pygmo.mp_island lazily creates its worker-process pool on first use, which involves a
# signal.signal() call that only works on the main thread. FastAPI/Starlette runs sync
# route handlers (like the "parallel"/"parallel_mc" estimation methods) in a worker
# thread, so without this the pool init crashes on the very first request with
# "ValueError: signal only works in main thread of the main interpreter". Warming the
# pool here, at import time on the main thread, makes later per-request inits no-ops.
try:
    import pygmo
    pygmo.mp_island.init_pool()
except Exception as ex:
    warnings.warn(f"Could not pre-warm pygmo.mp_island pool: {ex}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import models, simulation, data, estimation, analysis, parameters

app = FastAPI(
    title="pyFOOMB Web API",
    version="1.0.0",
    description="REST API for pyFOOMB bioprocess modelling framework",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router, prefix="/api")
app.include_router(simulation.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(estimation.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(parameters.router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
