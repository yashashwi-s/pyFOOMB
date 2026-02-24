"""
Parameter estimation endpoints.
Supports local (scipy), parallel (pygmo), repeated, and Monte Carlo estimation.
"""

import numpy
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List

from services.model_store import store
from services.serializers import serialize_parameters, serialize_simulation_results

router = APIRouter(tags=["estimation"])


class EstimateRequest(BaseModel):
    unknowns: Dict[str, List[float]]  # {param_name: [lower, upper]}
    metric: str = "SS"  # SS, WSS, negLL
    method: str = "local"  # local, parallel, repeated, mc, parallel_mc
    # Local options
    optimizer: Optional[str] = "Nelder-Mead"
    # Parallel options
    parallel_optimizer: Optional[str] = "de1220"
    n_islands: Optional[int] = 4
    pop_size: Optional[int] = 20
    n_evolutions: Optional[int] = 50
    # Repeated options
    n_jobs: Optional[int] = 10
    # MC options
    mc_samples: Optional[int] = 100
    reuse_errors: Optional[bool] = True


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

    # Prepare unknowns
    unknowns = {k: tuple(v) for k, v in req.unknowns.items()}

    try:
        if req.method == "local":
            result = session.caretaker.estimate(
                unknowns=unknowns,
                measurements=session.measurements,
                metric=req.metric,
                optimizer=req.optimizer,
                reset_afterwards=True,
            )

            # result is a dict with parameter names as keys
            estimates = serialize_parameters(result)
            loss = _get_loss(session, result, req.metric)

            session.estimation_results.append(
                {"method": "local", "estimates": estimates, "loss": loss}
            )

            return {"estimates": estimates, "loss": loss}

        elif req.method == "parallel":
            optimizer_kwargs = {}
            if req.parallel_optimizer:
                optimizer_kwargs["optimizer_name"] = req.parallel_optimizer

            result = session.caretaker.estimate_parallel(
                unknowns=unknowns,
                measurements=session.measurements,
                metric=req.metric,
                n_islands=req.n_islands or 4,
                pop_size=req.pop_size or 20,
                n_evolutions=req.n_evolutions or 50,
                reset_afterwards=True,
                optimizer_kwargs=optimizer_kwargs if optimizer_kwargs else None,
            )

            # result is a ParallelEstimationInfo-like object
            estimates = serialize_parameters(result)
            loss = _get_loss(session, result, req.metric)

            session.estimation_results.append(
                {"method": "parallel", "estimates": estimates, "loss": loss}
            )

            return {"estimates": estimates, "loss": loss}

        elif req.method == "repeated":
            results = session.caretaker.estimate_repeatedly(
                unknowns=unknowns,
                measurements=session.measurements,
                metric=req.metric,
                jobs=req.n_jobs or 10,
                reset_afterwards=True,
            )

            # results is a dict of {param_name: numpy.array of estimates}
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
                unknowns=unknowns,
                measurements=session.measurements,
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
                unknowns=unknowns,
                measurements=session.measurements,
                metric=req.metric,
                mc_samples=req.mc_samples or 100,
                n_islands=req.n_islands or 4,
                pop_size=req.pop_size or 20,
                n_evolutions=req.n_evolutions or 50,
                reset_afterwards=True,
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


def _get_loss(session, estimates, metric):
    """Calculate loss for given estimates."""
    try:
        guess_dict = {k: v for k, v in estimates.items() if isinstance(v, (int, float))}
        loss = session.caretaker.loss_function(
            guess_dict=guess_dict,
            metric=metric,
            measurements=session.measurements,
        )
        return float(loss) if loss is not None else None
    except Exception:
        return None
