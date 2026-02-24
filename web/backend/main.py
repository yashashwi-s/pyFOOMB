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
