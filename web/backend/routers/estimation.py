"""
Parameter estimation endpoints.
Supports local (scipy), parallel (pygmo), repeated, and Monte Carlo estimation.

Caretaker API notes:
- estimate(unknowns=dict_of_guesses, measurements=, metric=, bounds=, optimizer_kwargs=) -> (estimations, estimation_info)
  - For global optimizer: unknowns=list, bounds=list of tuples
  - For local optimizer: unknowns=dict (param: initial_guess)
- estimate_parallel(unknowns=list, measurements=, bounds=list_of_tuples, metric=) -> (best_estimates, ParallelEstimationInfo)
- estimate_parallel_continued(estimation_result=ParallelEstimationInfo, evolutions=) -> (best_estimates, ParallelEstimationInfo)
- estimate_repeatedly(unknowns=dict_or_list, measurements=, bounds=, metric=, jobs=) -> dict
- estimate_MC_sampling(unknowns=dict_or_list, measurements=, bounds=, metric=, mc_samples=) -> dict
"""

import numpy
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Any, Tuple

from services.model_store import store
from services.serializers import serialize_parameters, serialize_simulation_results

router = APIRouter(tags=["estimation"])


class EstimateRequest(BaseModel):
    unknowns: Dict[str, List[float]]  # {param_name: [lower, upper]}
    metric: str = "SS"  # SS, WSS, negLL
    method: str = "local"  # local, parallel, repeated, mc, parallel_mc
    # Parallel options
    parallel_optimizer: Optional[str] = "de1220"
    n_evolutions: Optional[int] = 50
    rel_pop_size: Optional[float] = 10.0
    # Repeated options
    n_jobs: Optional[int] = 10
    # MC options
    mc_samples: Optional[int] = 100
    reuse_errors: Optional[bool] = True
    optimizer_kwargs: Optional[Dict[str, Any]] = None


@router.post("/models/{model_id}/estimate")
def estimate(model_id: str, req: EstimateRequest):
    """Run parameter estimation."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    if not session.measurements:
        raise HTTPException(
            status_code=400, detail="No measurements available. Upload data first."
        )

    # unknowns from frontend: {param_name: [lower, upper]}
    # Convert to bounds list and unknowns dict/list for pyFOOMB
    param_names = list(req.unknowns.keys())
    bounds = [tuple(v) for v in req.unknowns.values()]

    # For local: unknowns = dict(param: midpoint_guess), bounds = list of tuples
    # For global/parallel: unknowns = list of names, bounds = list of tuples
    unknowns_dict = {k: (v[0] + v[1]) / 2.0 for k, v in req.unknowns.items()}
    unknowns_list = param_names

    try:
        if req.method == "local":
            # estimate(unknowns=dict, measurements=, metric=, bounds=, optimizer_kwargs=) -> (dict, dict)
            estimations, estimation_info = session.caretaker.estimate(
                unknowns=unknowns_dict,
                measurements=session.measurements,
                metric=req.metric,
                bounds=bounds,
                reset_afterwards=True,
                use_global_optimizer=True,
                optimizer_kwargs=req.optimizer_kwargs,
            )

            estimates = serialize_parameters(estimations)
            loss = float(estimation_info.get("loss", 0)) if isinstance(estimation_info, dict) else None

            session.estimation_results.append(
                {"method": "local", "estimates": estimates, "loss": loss}
            )

            return {"estimates": estimates, "loss": loss}

        elif req.method == "parallel":
            # estimate_parallel(unknowns=list, measurements=, bounds=list, metric=) -> (dict, ParallelEstimationInfo)
            best_estimates, parallel_info = session.caretaker.estimate_parallel(
                unknowns=unknowns_list,
                measurements=session.measurements,
                bounds=bounds,
                metric=req.metric,
                optimizers=[req.parallel_optimizer or "de1220"],
                rel_pop_size=req.rel_pop_size or 10.0,
                evolutions=req.n_evolutions or 50,
            )

            session.parallel_info = parallel_info
            estimates = serialize_parameters(best_estimates)

            session.estimation_results.append(
                {"method": "parallel", "estimates": estimates}
            )

            return {"estimates": estimates}

        elif req.method == "repeated":
            results = session.caretaker.estimate_repeatedly(
                unknowns=unknowns_list,
                measurements=session.measurements,
                bounds=bounds,
                metric=req.metric,
                jobs=req.n_jobs or 10,
                reset_afterwards=True,
            )

            serialized = {}
            for k, v in results.items():
                if isinstance(v, numpy.ndarray):
                    serialized[k] = [float(x) for x in v]
                else:
                    serialized[k] = v

            session.estimation_results.append(
                {"method": "repeated", "distributions": serialized}
            )

            return {"distributions": serialized}

        elif req.method == "mc":
            results = session.caretaker.estimate_MC_sampling(
                unknowns=unknowns_list,
                measurements=session.measurements,
                bounds=bounds,
                metric=req.metric,
                mc_samples=req.mc_samples or 100,
                reuse_errors_as_weights=req.reuse_errors if req.reuse_errors is not None else True,
                reset_afterwards=True,
            )

            serialized = {}
            for k, v in results.items():
                if isinstance(v, numpy.ndarray):
                    serialized[k] = [float(x) for x in v]
                else:
                    serialized[k] = v

            session.estimation_results.append(
                {"method": "mc", "distributions": serialized}
            )

            return {"distributions": serialized}

        elif req.method == "parallel_mc":
            results = session.caretaker.estimate_parallel_MC_sampling(
                unknowns=unknowns_list,
                measurements=session.measurements,
                bounds=bounds,
                metric=req.metric,
                mc_samples=req.mc_samples or 100,
                optimizers=[req.parallel_optimizer or "de1220"],
                rel_pop_size=req.rel_pop_size or 10.0,
                evolutions=req.n_evolutions or 50,
            )

            serialized = {}
            for k, v in results.items():
                if isinstance(v, numpy.ndarray):
                    serialized[k] = [float(x) for x in v]
                else:
                    serialized[k] = v

            session.estimation_results.append(
                {"method": "parallel_mc", "distributions": serialized}
            )

            return {"distributions": serialized}

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown estimation method: {req.method}",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400, detail=f"Estimation error: {str(e)}"
        )


class ContinueEstimationRequest(BaseModel):
    n_evolutions: int = 10


@router.post("/models/{model_id}/estimate/continue")
def continue_estimation(model_id: str, req: ContinueEstimationRequest):
    """Continue a previous parallel estimation by running more evolutions."""
    session = store.get(model_id)
    if not session:
        raise HTTPException(status_code=404, detail="Model not found")

    if session.parallel_info is None:
        raise HTTPException(status_code=400, detail="No previous parallel estimation to continue. Run estimate_parallel first.")

    try:
        best_estimates, estimation_result = session.caretaker.estimate_parallel_continued(
            estimation_result=session.parallel_info,
            evolutions=req.n_evolutions,
        )
        session.parallel_info = estimation_result
        estimates = serialize_parameters(best_estimates)

        session.estimation_results.append(
            {"method": "parallel_continued", "estimates": estimates}
        )

        return {"estimates": estimates}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Continue estimation error: {str(e)}")
