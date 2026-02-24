"""
Model definition and observation function endpoints.
Template-based — users select a pre-built model and configure via forms.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict

from services.model_store import store
from services.model_templates import (
    MODEL_TEMPLATES,
    OBSERVATION_TEMPLATES,
    get_template_list,
    get_observation_template_list,
)
from services.serializers import serialize_parameters

router = APIRouter(tags=["models"])


class CreateModelRequest(BaseModel):
    template_id: str
    model_name: Optional[str] = None
    model_parameters: Optional[Dict[str, float]] = None
    initial_values: Optional[Dict[str, float]] = None


class AddObservationRequest(BaseModel):
    template_id: str
    observed_state: str
    observation_parameters: Optional[Dict[str, float]] = None


@router.get("/templates")
def list_templates():
    """List all available model templates."""
    return {"templates": get_template_list()}


@router.get("/templates/observations")
def list_observation_templates():
    """List all available observation function templates."""
    return {"templates": get_observation_template_list()}


@router.post("/models")
def create_model(req: CreateModelRequest):
    """Create a model from a template with user-configured parameters."""
    if req.template_id not in MODEL_TEMPLATES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown template: {req.template_id}. Available: {list(MODEL_TEMPLATES.keys())}",
        )

    tmpl = MODEL_TEMPLATES[req.template_id]

    # Use template defaults, override with user values
    params = dict(tmpl["model_parameters"])
    if req.model_parameters:
        params.update(req.model_parameters)

    initial_vals = dict(tmpl["initial_values"])
    if req.initial_values:
        initial_vals.update(req.initial_values)

    model_name = req.model_name or tmpl["name"]

    try:
        from pyfoomb import Caretaker

        caretaker = Caretaker(
            bioprocess_model_class=tmpl["class"],
            model_parameters=params,
            states=tmpl["states"],
            initial_values=initial_vals,
            initial_switches=tmpl.get("initial_switches"),
            model_name=model_name,
        )
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Error creating model: {str(e)}"
        )

    metadata = {
        "template_id": req.template_id,
        "model_name": model_name,
        "states": tmpl["states"],
        "state_labels": tmpl["state_labels"],
        "model_parameters": params,
        "parameter_labels": tmpl["parameter_labels"],
        "initial_values": initial_vals,
        "initial_value_labels": tmpl["initial_value_labels"],
        "initial_switches": tmpl.get("initial_switches"),
        "equation": tmpl["equation"],
        "description": tmpl["description"],
        "category": tmpl["category"],
        "default_t_end": tmpl["default_t_end"],
    }

    model_id = store.create(caretaker, metadata)
    return {"model_id": model_id, "message": f"Model '{model_name}' created", "metadata": metadata}


@router.get("/models")
def list_models():
    """List all active model sessions."""
    return {"models": store.list_all()}


@router.get("/models/{model_id}")
def get_model(model_id: str):
    """Get details of a specific model."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    params = {}
    try:
        params = serialize_parameters(session.caretaker._get_all_parameters())
    except Exception:
        params = serialize_parameters(session.metadata.get("model_parameters", {}))

    return {
        "id": session.model_id,
        "metadata": session.metadata,
        "parameters": params,
        "has_observations": len(session.observation_functions_code) > 0,
        "has_measurements": len(session.measurements) > 0,
        "measurement_count": len(session.measurements),
        "replicate_ids": session.caretaker.replicate_ids,
    }


@router.delete("/models/{model_id}")
def delete_model(model_id: str):
    """Delete a model session."""
    if store.delete(model_id):
        return {"message": "Model deleted"}
    raise HTTPException(status_code=404, detail="Model not found")


@router.post("/models/{model_id}/observation-functions")
def add_observation_function(model_id: str, req: AddObservationRequest):
    """Add an observation function from template."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    if req.template_id not in OBSERVATION_TEMPLATES:
        raise HTTPException(status_code=400, detail=f"Unknown observation template: {req.template_id}")

    if req.observed_state not in session.metadata.get("states", []):
        raise HTTPException(status_code=400, detail=f"Unknown state: {req.observed_state}")

    obs_tmpl = OBSERVATION_TEMPLATES[req.template_id]
    obs_params = dict(obs_tmpl["parameters"])
    if req.observation_parameters:
        obs_params.update(req.observation_parameters)

    try:
        obs_info = {
            "template_id": req.template_id,
            "observed_state": req.observed_state,
            "observation_parameters": obs_params,
        }
        session.observation_functions_code.append(obs_info)

        # Rebuild caretaker with all observations
        all_obs_params = []
        for oi in session.observation_functions_code:
            ot = OBSERVATION_TEMPLATES[oi["template_id"]]
            all_obs_params.append(
                (ot["class"], oi["observed_state"], oi["observation_parameters"])
            )

        meta = session.metadata
        tmpl = MODEL_TEMPLATES[meta["template_id"]]

        from pyfoomb import Caretaker

        new_caretaker = Caretaker(
            bioprocess_model_class=tmpl["class"],
            model_parameters=meta["model_parameters"],
            states=meta["states"],
            initial_values=meta["initial_values"],
            initial_switches=meta.get("initial_switches"),
            model_name=meta["model_name"],
            observation_functions_parameters=all_obs_params,
        )
        session.caretaker = new_caretaker

    except Exception as e:
        session.observation_functions_code.pop()
        raise HTTPException(status_code=400, detail=f"Error adding observation: {str(e)}")

    return {"message": f"Observation function added for state '{req.observed_state}'"}


@router.post("/models/{model_id}/check")
def check_model(model_id: str):
    """Run model consistency checks."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    import io
    import sys

    old_stdout = sys.stdout
    sys.stdout = captured = io.StringIO()

    try:
        from pyfoomb.model_checking import ModelChecker

        checker = ModelChecker()
        rid = session.caretaker.replicate_ids[0]
        simulators = session.caretaker._Caretaker__simulators
        simulator = simulators[rid]
        result = checker.check_model_consistency(simulator, report=True)
    except Exception as e:
        sys.stdout = old_stdout
        return {"passed": False, "details": str(e)}

    sys.stdout = old_stdout
    output = captured.getvalue()

    return {
        "passed": result if isinstance(result, bool) else True,
        "details": output if output else "All checks passed.",
    }
