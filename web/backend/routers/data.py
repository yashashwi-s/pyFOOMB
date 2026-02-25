"""
Measurement data management endpoints.
"""

import io
import numpy
import pandas
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, List

from services.model_store import store
from services.serializers import serialize_measurement

router = APIRouter(tags=["data"])


class MeasurementInput(BaseModel):
    name: str
    timepoints: List[float]
    values: List[float]
    errors: Optional[List[float]] = None
    replicate_id: Optional[str] = None
    error_model_type: Optional[str] = None  # "constant", "relative", "combined"
    error_model_parameters: Optional[Dict[str, float]] = None


class MeasurementBatchInput(BaseModel):
    measurements: List[MeasurementInput]


@router.post("/models/{model_id}/measurements")
def add_measurements(model_id: str, req: MeasurementBatchInput):
    """Add measurement data to the model session."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    from pyfoomb import Measurement

    added = []
    for m in req.measurements:
        try:
            measurement = Measurement(
                name=m.name,
                timepoints=numpy.array(m.timepoints),
                values=numpy.array(m.values),
                errors=numpy.array(m.errors) if m.errors else None,
                replicate_id=m.replicate_id,
            )

            # Apply error model if specified
            if m.error_model_type and m.error_model_parameters:
                error_model = _get_error_model(m.error_model_type)
                measurement.update_error_model(error_model, m.error_model_parameters)

            session.measurements.append(measurement)
            added.append(m.name)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error creating measurement '{m.name}': {str(e)}",
            )

    return {"message": f"Added {len(added)} measurements", "names": added}


def _get_error_model(model_type: str):
    """Return error model callable by type name.
    pyFOOMB calls: error_model(values, error_model_parameters_dict)
    """
    def constant_error(values, params):
        abs_error = params.get("abs_error", 0.1)
        return numpy.full_like(values, abs_error, dtype=float)

    def relative_error(values, params):
        rel_error = params.get("rel_error", 0.05)
        return numpy.abs(values) * rel_error

    def combined_error(values, params):
        abs_error = params.get("abs_error", 0.1)
        rel_error = params.get("rel_error", 0.05)
        return abs_error + numpy.abs(values) * rel_error

    models = {
        "constant": constant_error,
        "relative": relative_error,
        "combined": combined_error,
    }
    if model_type not in models:
        raise ValueError(f"Unknown error model: {model_type}. Available: {list(models.keys())}")
    return models[model_type]


@router.post("/models/{model_id}/measurements/upload")
async def upload_measurements(model_id: str, file: UploadFile = File(...)):
    """Upload measurement data from CSV or XLSX file."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    content = await file.read()
    try:
        if file.filename.endswith(".xlsx") or file.filename.endswith(".xls"):
            df = pandas.read_excel(io.BytesIO(content))
        elif file.filename.endswith(".csv"):
            df = pandas.read_csv(io.BytesIO(content))
        else:
            raise HTTPException(
                status_code=400, detail="Unsupported file format. Use CSV or XLSX."
            )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    # Expect columns: name, time, value, error (optional)
    # Or: time column + one column per measurement
    from pyfoomb import Measurement

    added = []

    if "time" in df.columns and "name" in df.columns:
        # Long format: name, time, value, error
        for name, group in df.groupby("name"):
            timepoints = group["time"].values.astype(float)
            values = group["value"].values.astype(float)
            errors = (
                group["error"].values.astype(float) if "error" in group.columns else None
            )
            m = Measurement(
                name=str(name),
                timepoints=timepoints,
                values=values,
                errors=errors,
            )
            session.measurements.append(m)
            added.append(str(name))
    elif "time" in df.columns:
        # Wide format: time column + value columns
        time_col = df["time"].values.astype(float)
        for col in df.columns:
            if col == "time":
                continue
            values = df[col].values.astype(float)
            m = Measurement(
                name=str(col),
                timepoints=time_col,
                values=values,
            )
            session.measurements.append(m)
            added.append(str(col))
    else:
        raise HTTPException(
            status_code=400,
            detail='File must have a "time" column. Use long format (name, time, value, error) or wide format (time, col1, col2, ...).',
        )

    return {"message": f"Uploaded {len(added)} measurements", "names": added}


@router.get("/models/{model_id}/measurements")
def get_measurements(model_id: str):
    """List all measurements for a model."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    return {
        "measurements": [serialize_measurement(m) for m in session.measurements]
    }


@router.delete("/models/{model_id}/measurements")
def clear_measurements(model_id: str):
    """Clear all measurements for a model."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")
    session.measurements = []
    return {"message": "All measurements cleared"}


class ErrorModelUpdate(BaseModel):
    error_model_type: str  # "constant", "relative", "combined"
    error_model_parameters: Dict[str, float]


@router.put("/models/{model_id}/measurements/{measurement_name}/error-model")
def update_measurement_error_model(model_id: str, measurement_name: str, req: ErrorModelUpdate):
    """Update the error model on an existing measurement."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    matches = [m for m in session.measurements if m.name == measurement_name]
    if not matches:
        raise HTTPException(status_code=404, detail=f"Measurement '{measurement_name}' not found")

    try:
        error_model = _get_error_model(req.error_model_type)
        for m in matches:
            m.update_error_model(error_model, req.error_model_parameters)
        return {"message": f"Error model updated for '{measurement_name}'", "count": len(matches)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating error model: {str(e)}")
