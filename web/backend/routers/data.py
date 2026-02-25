"""
Measurement data management endpoints.

Supports:
- JSON measurement input
- CSV/XLSX file upload (wide or long format, flexible column names)
- Raw text paste parsing (tab/comma separated)
- Google Sheets public URL import
- Error model configuration
- Synthetic data generation
"""

import io
import re
import numpy
import pandas
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, List

from services.model_store import store
from services.serializers import serialize_measurement

router = APIRouter(tags=["data"])


# ──────────────────────────────────────────────────────────
# Column name parsing — extract state names from headers
# ──────────────────────────────────────────────────────────

# Known time column aliases (case-insensitive)
_TIME_ALIASES = {"time", "time (h)", "time(h)", "t", "t (h)", "t(h)", "hours", "hour", "h"}

# Known state name patterns: "Biomass (X) [g/L]" → "X", "Substrate (S)" → "S"
_STATE_PATTERN = re.compile(r"\(([A-Za-z]\w*)\)")


def _normalize_column(col: str) -> Optional[str]:
    """Parse a column header and return the state name, or None if it's a time column."""
    col_clean = col.strip()
    col_lower = col_clean.lower()

    # Check if it's a time column
    if col_lower in _TIME_ALIASES:
        return None

    # Try to extract state from parentheses: "Biomass (X) [g/L]" → "X"
    m = _STATE_PATTERN.search(col_clean)
    if m:
        return m.group(1)

    # If no parentheses, use the column name directly (strip units)
    # "X [g/L]" → "X", "Product [g/L]" → "Product"
    name = re.split(r"\s*[\[\(]", col_clean)[0].strip()
    return name if name else col_clean


def _find_time_column(df: pandas.DataFrame) -> Optional[str]:
    """Find the time column in a dataframe, case-insensitive."""
    for col in df.columns:
        if col.strip().lower() in _TIME_ALIASES:
            return col
    # Fall back: first column if it looks numeric and ascending
    first = df.columns[0]
    try:
        vals = pandas.to_numeric(df[first], errors="coerce")
        if vals.is_monotonic_increasing and not vals.isna().all():
            return first
    except Exception:
        pass
    return None


def _parse_dataframe(df: pandas.DataFrame) -> List[dict]:
    """Parse a wide-format DataFrame into measurement dicts.

    Handles:
    - Flexible column names: "Time (h)", "Biomass (X) [g/L]", etc.
    - Annotations in values like "2.1 (Feed starts)" → strips text
    - Columns in any order
    """
    time_col = _find_time_column(df)
    if time_col is None:
        raise ValueError(
            'Could not find a time column. Expected "Time", "Time (h)", "t", "hours", etc.'
        )

    # Parse time values (strip annotations like "(Feed starts)")
    time_vals = df[time_col].apply(lambda v: _extract_number(v)).values.astype(float)

    results = []
    for col in df.columns:
        if col == time_col:
            continue
        state_name = _normalize_column(col)
        if not state_name:
            continue
        values = df[col].apply(lambda v: _extract_number(v)).values.astype(float)
        # Skip columns that are all NaN
        if numpy.all(numpy.isnan(values)):
            continue
        # Drop NaN rows (mismatched lengths)
        mask = ~numpy.isnan(values) & ~numpy.isnan(time_vals)
        results.append({
            "name": state_name,
            "timepoints": time_vals[mask].tolist(),
            "values": values[mask].tolist(),
        })

    return results


def _extract_number(val) -> float:
    """Extract numeric value from a cell that might have annotations.
    E.g. "2.1 (Feed starts)" → 2.1, "0.5" → 0.5
    """
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val = val.strip()
        # Try to extract leading number
        m = re.match(r"^([+-]?\d*\.?\d+(?:[eE][+-]?\d+)?)", val)
        if m:
            return float(m.group(1))
    return float("nan")


# ──────────────────────────────────────────────────────────
# JSON measurement input
# ──────────────────────────────────────────────────────────

class MeasurementInput(BaseModel):
    name: str
    timepoints: List[float]
    values: List[float]
    errors: Optional[List[float]] = None
    replicate_id: Optional[str] = None
    error_model_type: Optional[str] = None
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


# ──────────────────────────────────────────────────────────
# File upload (CSV / XLSX)
# ──────────────────────────────────────────────────────────

@router.post("/models/{model_id}/measurements/upload")
async def upload_measurements(model_id: str, file: UploadFile = File(...)):
    """Upload measurement data from CSV or XLSX file.

    Supports:
    - Wide format: Time (h), Biomass (X) [g/L], Substrate (S) [g/L], ...
    - Flexible column names with automatic state extraction
    - Annotated values like "2.1 (Feed starts)"
    """
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    content = await file.read()
    try:
        if file.filename and (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
            df = pandas.read_excel(io.BytesIO(content))
        elif file.filename and file.filename.endswith(".csv"):
            df = pandas.read_csv(io.BytesIO(content))
        else:
            # Try CSV first, then Excel
            try:
                df = pandas.read_csv(io.BytesIO(content))
            except Exception:
                df = pandas.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")

    try:
        parsed = _parse_dataframe(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    from pyfoomb import Measurement

    added = []
    for p in parsed:
        m = Measurement(
            name=p["name"],
            timepoints=numpy.array(p["timepoints"]),
            values=numpy.array(p["values"]),
        )
        session.measurements.append(m)
        added.append(p["name"])

    return {
        "message": f"Uploaded {len(added)} measurements",
        "names": added,
        "parsed": parsed,
    }


# ──────────────────────────────────────────────────────────
# Paste raw text (tab/comma separated)
# ──────────────────────────────────────────────────────────

class PasteInput(BaseModel):
    text: str


@router.post("/models/{model_id}/measurements/paste")
def paste_measurements(model_id: str, req: PasteInput):
    """Parse pasted tabular text (CSV or TSV) and add as measurements.

    Accepts wide format with flexible headers:
        Time (h), Biomass (X) [g/L], Substrate (S) [g/L], Product (P) [g/L]
        0, 0.5, 10.0, 0.0
        4, 2.8, 1.2, 0.1
    """
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")

    # Detect delimiter
    first_line = text.split("\n")[0]
    if "\t" in first_line:
        sep = "\t"
    else:
        sep = ","

    try:
        df = pandas.read_csv(io.StringIO(text), sep=sep, skipinitialspace=True)
        parsed = _parse_dataframe(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing pasted data: {str(e)}")

    from pyfoomb import Measurement

    added = []
    for p in parsed:
        m = Measurement(
            name=p["name"],
            timepoints=numpy.array(p["timepoints"]),
            values=numpy.array(p["values"]),
        )
        session.measurements.append(m)
        added.append(p["name"])

    return {
        "message": f"Parsed {len(added)} measurement series from pasted data",
        "names": added,
        "parsed": parsed,
    }


# ──────────────────────────────────────────────────────────
# Google Sheets import
# ──────────────────────────────────────────────────────────

class SheetsImportInput(BaseModel):
    url: str


@router.post("/models/{model_id}/measurements/sheets")
def import_google_sheets(model_id: str, req: SheetsImportInput):
    """Import data from a public Google Sheets URL.

    Accepts:
    - https://docs.google.com/spreadsheets/d/{SHEET_ID}/...
    - Converts to CSV export URL and fetches
    """
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    url = req.url.strip()

    # Extract sheet ID
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9_-]+)", url)
    if not m:
        raise HTTPException(status_code=400, detail="Invalid Google Sheets URL. Expected: https://docs.google.com/spreadsheets/d/{ID}/...")

    sheet_id = m.group(1)

    # Extract gid (sheet tab) if present
    gid_match = re.search(r"[?&]gid=(\d+)", url)
    gid = gid_match.group(1) if gid_match else "0"

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    import urllib.request
    try:
        with urllib.request.urlopen(csv_url, timeout=15) as response:
            csv_text = response.read().decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch Google Sheet. Make sure the sheet is publicly accessible (Share → Anyone with the link). Error: {str(e)}")

    try:
        df = pandas.read_csv(io.StringIO(csv_text))
        parsed = _parse_dataframe(df)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing sheet data: {str(e)}")

    from pyfoomb import Measurement

    added = []
    for p in parsed:
        m_obj = Measurement(
            name=p["name"],
            timepoints=numpy.array(p["timepoints"]),
            values=numpy.array(p["values"]),
        )
        session.measurements.append(m_obj)
        added.append(p["name"])

    return {
        "message": f"Imported {len(added)} measurement series from Google Sheets",
        "names": added,
        "parsed": parsed,
    }


# ──────────────────────────────────────────────────────────
# Error models
# ──────────────────────────────────────────────────────────

def _get_error_model(model_type: str):
    """Return error model callable by type name."""
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


# ──────────────────────────────────────────────────────────
# CRUD
# ──────────────────────────────────────────────────────────

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
    error_model_type: str
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


# ──────────────────────────────────────────────────────────
# Synthetic data generation
# ──────────────────────────────────────────────────────────

class GenerateDataRequest(BaseModel):
    t_end: float = 10.0
    n_points: int = 15
    noise_percent: float = 5.0
    abs_noise: float = 0.01
    states: Optional[List[str]] = None
    seed: Optional[int] = None


@router.post("/models/{model_id}/generate-data")
def generate_synthetic_data(model_id: str, req: GenerateDataRequest):
    """Simulate the model and add Gaussian noise to generate fake measurement data."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    from pyfoomb import Measurement

    try:
        t = numpy.linspace(0, req.t_end, req.n_points)
        simulations = session.caretaker.simulate(t=t, suppress_stdout=True)

        rng = numpy.random.default_rng(req.seed)
        added = []

        for sim in simulations:
            if req.states and sim.name not in req.states:
                continue

            clean = sim.values.copy()
            noise_std = (req.noise_percent / 100.0) * numpy.abs(clean) + req.abs_noise
            noisy = clean + rng.normal(0, noise_std)
            errors = noise_std

            m = Measurement(
                name=sim.name,
                timepoints=sim.timepoints.copy(),
                values=noisy,
                errors=errors,
            )
            session.measurements.append(m)
            added.append({
                "name": sim.name,
                "timepoints": [float(x) for x in sim.timepoints],
                "values": [float(x) for x in noisy],
                "errors": [float(x) for x in errors],
            })

        return {
            "message": f"Generated {len(added)} synthetic measurement series",
            "names": [a["name"] for a in added],
            "measurements": added,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating data: {str(e)}")
