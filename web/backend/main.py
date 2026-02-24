"""
pyFOOMB Web GUI — Backend API
FastAPI server wrapping pyFOOMB as REST endpoints.
"""

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
