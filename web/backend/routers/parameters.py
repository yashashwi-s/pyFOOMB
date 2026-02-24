"""
Parameter management, replicates, mappings, and integrator settings.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List

from services.model_store import store
from services.serializers import serialize_parameters

router = APIRouter(tags=["parameters"])


class SetParametersRequest(BaseModel):
    parameters: Dict[str, float]


class AddReplicateRequest(BaseModel):
    replicate_id: str


class MappingItem(BaseModel):
    replicate_id: str
    global_name: str
    local_name: Optional[str] = None
    value: Optional[float] = None


class ApplyMappingsRequest(BaseModel):
    mappings: List[MappingItem]


class IntegratorRequest(BaseModel):
    kwargs: Dict[str, float]


@router.get("/models/{model_id}/parameters")
def get_parameters(model_id: str):
    """Get current parameter state."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        params = session.caretaker._get_all_parameters()
        return {"parameters": serialize_parameters(params)}
    except Exception:
        return {"parameters": serialize_parameters(session.metadata.get("model_parameters", {}))}


@router.put("/models/{model_id}/parameters")
def set_parameters(model_id: str, req: SetParametersRequest):
    """Set parameter values."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        session.caretaker.set_parameters(req.parameters)
        return {"message": "Parameters updated", "parameters": serialize_parameters(req.parameters)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error setting parameters: {str(e)}")


@router.get("/models/{model_id}/replicates")
def get_replicates(model_id: str):
    """Get replicate IDs."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    return {"replicate_ids": session.caretaker.replicate_ids}


@router.post("/models/{model_id}/replicates")
def add_replicate(model_id: str, req: AddReplicateRequest):
    """Add a new replicate."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        session.caretaker.add_replicate(req.replicate_id)
        return {
            "message": f"Replicate '{req.replicate_id}' added",
            "replicate_ids": session.caretaker.replicate_ids,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error adding replicate: {str(e)}")


@router.post("/models/{model_id}/mappings")
def apply_mappings(model_id: str, req: ApplyMappingsRequest):
    """Apply parameter mappings."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        from pyfoomb import ParameterMapper

        mappers = []
        for m in req.mappings:
            mapper = ParameterMapper(
                replicate_id=m.replicate_id,
                global_name=m.global_name,
                local_name=m.local_name,
                value=m.value,
            )
            mappers.append(mapper)

        session.caretaker.apply_mappings(mappers)
        return {"message": f"Applied {len(mappers)} mappings"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error applying mappings: {str(e)}")


@router.get("/models/{model_id}/parameter-mapping")
def get_parameter_mapping(model_id: str):
    """Get current parameter mapping."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        mapping = session.caretaker.parameter_mapping
        # Convert to serializable format
        if hasattr(mapping, 'to_dict'):
            return {"mapping": mapping.to_dict()}
        elif isinstance(mapping, dict):
            return {"mapping": mapping}
        else:
            return {"mapping": str(mapping)}
    except Exception:
        return {"mapping": {}}


@router.put("/models/{model_id}/integrator")
def set_integrator(model_id: str, req: IntegratorRequest):
    """Set integrator kwargs (atol, rtol, etc.)."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    try:
        session.caretaker.set_integrator_kwargs(req.kwargs)
        return {"message": "Integrator settings updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error setting integrator: {str(e)}")
