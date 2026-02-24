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
            session.measurements.append(measurement)
            added.append(m.name)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error creating measurement '{m.name}': {str(e)}",
            )

    return {"message": f"Added {len(added)} measurements", "names": added}


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
