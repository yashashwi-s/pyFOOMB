"""
Forward simulation endpoint.
"""

import numpy
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List

from services.model_store import store
from services.serializers import serialize_simulation_results

router = APIRouter(tags=["simulation"])


class SimulateRequest(BaseModel):
    t_start: float = 0.0
    t_end: float = 10.0
    n_points: int = 100
    timepoints: Optional[List[float]] = None
    parameters: Optional[Dict[str, float]] = None


@router.post("/models/{model_id}/simulate")
def simulate(model_id: str, req: SimulateRequest):
    """Run forward simulation."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    # Build time vector
    if req.timepoints:
        t = numpy.array(req.timepoints)
    else:
        t = numpy.linspace(req.t_start, req.t_end, req.n_points)

    try:
        results = session.caretaker.simulate(
            t=t,
            parameters=req.parameters,
            verbosity=40,
            reset_afterwards=True,
        )
        session.last_simulation = results
        return {"results": serialize_simulation_results(results)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Simulation error: {str(e)}")
