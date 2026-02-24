"""
Sensitivity analysis, Fisher information, uncertainty, and OED endpoints.
"""

import numpy
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List

from services.model_store import store
from services.serializers import (
    serialize_timeseries,
    serialize_matrix,
    serialize_parameters,
)

router = APIRouter(tags=["analysis"])


class SensitivityRequest(BaseModel):
    parameters: Optional[List[str]] = None
    responses: Optional[List[str]] = None
    t_end: float = 10.0
    n_points: int = 100
    rel_h: float = 1e-3
    abs_h: Optional[float] = None


class UncertaintyRequest(BaseModel):
    estimates: Dict[str, float]


class OptimalityRequest(BaseModel):
    cov_matrix: List[List[float]]


@router.post("/models/{model_id}/sensitivities")
def get_sensitivities(model_id: str, req: SensitivityRequest):
    """Calculate parameter sensitivities."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    t = numpy.linspace(0, req.t_end, req.n_points)

    try:
        kwargs = {"t": t, "rel_h": req.rel_h}
        if req.parameters:
            kwargs["parameters"] = req.parameters
        if req.responses:
            kwargs["responses"] = req.responses
        if req.abs_h is not None:
            kwargs["abs_h"] = req.abs_h

        sensitivities = session.caretaker.get_sensitivities(**kwargs)
        session.sensitivities = sensitivities

        return {
            "sensitivities": [serialize_timeseries(s) for s in sensitivities]
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Sensitivity error: {str(e)}"
        )


@router.post("/models/{model_id}/parameter-matrices")
def get_parameter_matrices(model_id: str, req: UncertaintyRequest):
    """Calculate FIM, Cov, and Corr matrices."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    if not session.measurements:
        raise HTTPException(
            status_code=400, detail="No measurements available."
        )

    try:
        result = session.caretaker.get_parameter_matrices(
            estimates=req.estimates,
            measurements=session.measurements,
            sensitivities=session.sensitivities,
        )

        labels = list(req.estimates.keys())

        return {
            "FIM": serialize_matrix(result.get("FIM"), labels) if "FIM" in result else None,
            "Cov": serialize_matrix(result.get("Cov"), labels) if "Cov" in result else None,
            "Corr": serialize_matrix(result.get("Corr"), labels) if "Corr" in result else None,
        }
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Matrix calculation error: {str(e)}"
        )


@router.post("/models/{model_id}/parameter-uncertainties")
def get_parameter_uncertainties(model_id: str, req: UncertaintyRequest):
    """Calculate parameter uncertainties from FIM."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    if not session.measurements:
        raise HTTPException(
            status_code=400, detail="No measurements available."
        )

    try:
        result = session.caretaker.get_parameter_uncertainties(
            estimates=req.estimates,
            measurements=session.measurements,
        )

        serialized = {}
        for k, v in result.items():
            if isinstance(v, numpy.ndarray):
                serialized[k] = serialize_matrix(v, list(req.estimates.keys()))
            elif isinstance(v, dict):
                serialized[k] = serialize_parameters(v)
            else:
                serialized[k] = v

        return serialized
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Uncertainty calculation error: {str(e)}"
        )


@router.post("/models/{model_id}/optimality-criteria")
def get_optimality_criteria(model_id: str, req: OptimalityRequest):
    """Calculate OED optimality criteria from covariance matrix."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        cov = numpy.array(req.cov_matrix)
        result = session.caretaker.get_optimality_criteria(Cov=cov)
        return {"criteria": serialize_parameters(result)}
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Optimality error: {str(e)}"
        )
