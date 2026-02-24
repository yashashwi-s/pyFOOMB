"""
Serializers for converting pyFOOMB objects to JSON-serializable dicts.
"""

import numpy
from typing import Any, List


def _safe_float(v):
    """Convert numpy floats/ints and handle NaN/Inf."""
    if v is None:
        return None
    if isinstance(v, (numpy.floating, numpy.integer)):
        v = float(v)
    if isinstance(v, float):
        if numpy.isnan(v):
            return None
        if numpy.isinf(v):
            return None
    return v


def serialize_timeseries(ts) -> dict:
    """Serialize a TimeSeries (ModelState, Observation, Sensitivity) to dict."""
    result = {
        "name": ts.name,
        "replicate_id": ts.replicate_id,
        "timepoints": [_safe_float(t) for t in ts.timepoints.flatten()],
        "values": [_safe_float(v) for v in ts.values.flatten()],
    }
    if hasattr(ts, "info") and ts.info:
        result["info"] = ts.info
    return result


def serialize_measurement(m) -> dict:
    """Serialize a Measurement to dict."""
    result = serialize_timeseries(m)
    if m.errors is not None:
        result["errors"] = [_safe_float(e) for e in m.errors.flatten()]
    else:
        result["errors"] = None
    result["has_error_model"] = m.error_model is not None
    return result


def serialize_simulation_results(results: list) -> list:
    """Serialize a list of simulation results (ModelState/Observation objects)."""
    return [serialize_timeseries(r) for r in results]


def serialize_estimation_result(result: dict) -> dict:
    """Serialize estimation result dict."""
    if result is None:
        return {}
    serialized = {}
    for key, value in result.items():
        if isinstance(value, numpy.ndarray):
            serialized[key] = [_safe_float(v) for v in value.flatten()]
        elif isinstance(value, (numpy.floating, numpy.integer)):
            serialized[key] = _safe_float(value)
        elif isinstance(value, dict):
            serialized[key] = {
                k: _safe_float(v) if isinstance(v, (float, numpy.floating, numpy.integer)) else v
                for k, v in value.items()
            }
        else:
            serialized[key] = value
    return serialized


def serialize_matrix(matrix: numpy.ndarray, labels: list = None) -> dict:
    """Serialize a numpy matrix with optional row/column labels."""
    if matrix is None:
        return None
    return {
        "data": [[_safe_float(v) for v in row] for row in matrix],
        "labels": labels,
        "shape": list(matrix.shape),
    }


def serialize_parameters(params: dict) -> dict:
    """Serialize a parameter dict, handling numpy types."""
    return {k: _safe_float(v) for k, v in params.items()}
