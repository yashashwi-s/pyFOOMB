"""pyFOOMB/CVode adapter for the feed-flow optimisation study.

The original study in :mod:`feed_flow_optimization` deliberately uses
``scipy.integrate.solve_ivp``.  This module implements the same physical model
with real pyFOOMB ``BioprocessModel`` and ``Caretaker`` objects.  It is kept
separate so the saved SciPy study remains reproducible.

pyFOOMB sorts state names alphabetically.  Consequently the model classes
below unpack their internal state vectors as ``[P, S, V, X]`` (and
``[feed_time, P, S, V, X]`` for the batch model).  Public trajectory arrays
are returned in the study's conventional ``[X, S, P, V]`` order.
"""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Mapping, Sequence, Type

import numpy as np
from scipy.optimize import curve_fit

from pyfoomb import BioprocessModel, Caretaker
from feed_flow_optimization import TWO_STAGE_SHAPES, STRATEGIES, staged_feed_rate


# These values intentionally mirror feed_flow_optimization.py.
X0, S0, P0, V0 = 0.1, 20.0, 0.0, 1.0
S_IN = 400.0
V_MAX = 4.0
F_CAP = 2.0
T_BATCH_MAX = 60.0
S_DEPLETE = 0.5
T_FEDBATCH = 40.0

STATE_ORDER = ("X", "S", "P", "V")
PYFOOMB_STATE_ORDER = ("P", "S", "V", "X")
BATCH_STATE_ORDER = ("feed_time", "P", "S", "V", "X")

KINETICS = {
    "S. cerevisiae": {"mu_max": 0.40, "Ks": 0.10, "Yxs": 0.50},
    "P. pastoris": {"mu_max": 0.20, "Ks": 0.05, "Yxs": 0.45},
}

MODEL_CODES = {"linear": 0, "bell_shaped": 1, "hyperbolic": 2}
STRATEGY_CODES = {
    "constant": 0,
    "exponential": 1,
    "linear_ramp": 2,
    "exp_linear": 3,
    "two_stage": 4,
    "pulsed": 5,
    "feedback_control": 6,
    "two_stage_linear_exp": 7,
    "two_stage_exp_linear": 8,
    "two_stage_exp_exp": 9,
    "two_stage_linear_linear": 10,
}
STAGED_CODE_SHAPES = {STRATEGY_CODES[name]: shapes for name, shapes in TWO_STAGE_SHAPES.items()}

STRATEGY_PARAMETER_NAMES = {
    "constant": ("F0",),
    "exponential": ("F0", "mu_set"),
    "linear_ramp": ("F0", "k"),
    "exp_linear": ("F0", "mu_set", "k"),
    "two_stage": ("F1", "F2", "t_switch"),
    "pulsed": ("F_pulse", "T_cycle", "duty"),
    "feedback_control": ("mu_target", "Kp"),
}
STRATEGY_PARAMETER_NAMES.update({name: tuple(STRATEGIES[name]['names']) for name in TWO_STAGE_SHAPES})

# The shortest allowed pulse period in the study is 0.5 h.  Each cycle has an
# off and on edge.  Giving every edge its own root function makes CVode land on
# every discontinuity without forcing a 0.01 h maximum step.
MIN_PULSE_PERIOD = 0.5
MAX_PULSE_CYCLES = int(np.ceil(T_FEDBATCH / MIN_PULSE_PERIOD))
N_PULSE_EVENTS = 2 * MAX_PULSE_CYCLES
VOLUME_EVENT_INDEX = 0
STAGE_EVENT_INDEX = 1
PULSE_EVENT_START = 2
N_EVENTS = PULSE_EVENT_START + N_PULSE_EVENTS


@dataclass(frozen=True)
class FittedDataset:
    """Kinetics and fitted qp(mu) coefficients needed by the ODE model."""

    product: str
    model_type: str
    organism_type: str
    mu_max: float
    Ks: float
    Yxs: float
    qp0: float
    qp1: float
    qp2: float
    mu_cap: float


@dataclass(frozen=True)
class BatchResult:
    """Batch endpoint and optional trajectory, with y in X/S/P/V order."""

    t_feed: float
    y_feed: np.ndarray
    t: np.ndarray
    y: np.ndarray
    runtime_seconds: float


@dataclass(frozen=True)
class FeedSimulation:
    """One 40 h fed-batch trajectory produced by Caretaker.simulate()."""

    t: np.ndarray
    y: np.ndarray
    y_feed: np.ndarray
    runtime_seconds: float
    state_order: tuple[str, ...] = STATE_ORDER

    @property
    def total_product(self) -> float:
        return float(self.y[2, -1] * self.y[3, -1])


def _linear_model(mu: np.ndarray, alpha: float, beta: float) -> np.ndarray:
    return alpha * mu + beta


def _bell_shaped_model(
    mu: np.ndarray, qp_max: float, mu_opt: float, sigma: float
) -> np.ndarray:
    return qp_max * np.exp(-((mu - mu_opt) ** 2) / (2.0 * sigma**2))


def _hyperbolic_model(mu: np.ndarray, qp_max: float, Kq: float) -> np.ndarray:
    return qp_max * mu / (Kq + mu)


def fit_dataset(dataset: Mapping[str, Any], model_type: str) -> FittedDataset:
    """Fit qp(mu) exactly as the SciPy reference study does.

    ``dataset`` is one entry from ``feed_flow_optimization.DATA``.  The
    extrapolation cap is likewise identical: 1.2 times the largest measured
    specific growth rate.
    """

    if model_type not in MODEL_CODES:
        raise KeyError(f"Unknown qp model type: {model_type!r}")
    organism_type = str(dataset["organism_type"])
    if organism_type not in KINETICS:
        raise KeyError(f"Unknown organism type: {organism_type!r}")

    mu = np.asarray(dataset["mu"], dtype=float)
    qp = np.asarray(dataset["qp"], dtype=float)
    if model_type == "linear":
        popt, _ = curve_fit(_linear_model, mu, qp, p0=[max(qp) / max(mu), 0.0])
    elif model_type == "bell_shaped":
        popt, _ = curve_fit(
            _bell_shaped_model,
            mu,
            qp,
            p0=[max(qp), mu[np.argmax(qp)], 0.04],
            maxfev=20000,
            bounds=([0.0, 0.0, 1e-4], [np.inf, 0.5, 0.5]),
        )
    else:
        popt, _ = curve_fit(
            _hyperbolic_model,
            mu,
            qp,
            p0=[max(qp) * 1.1, 0.03],
            maxfev=20000,
            bounds=([0.0, 1e-4], [np.inf, 0.5]),
        )

    coeffs = np.zeros(3, dtype=float)
    coeffs[: len(popt)] = popt
    kin = KINETICS[organism_type]
    return FittedDataset(
        product=str(dataset.get("product", "unnamed")),
        model_type=model_type,
        organism_type=organism_type,
        mu_max=float(kin["mu_max"]),
        Ks=float(kin["Ks"]),
        Yxs=float(kin["Yxs"]),
        qp0=float(coeffs[0]),
        qp1=float(coeffs[1]),
        qp2=float(coeffs[2]),
        mu_cap=float(1.2 * np.max(mu)),
    )


def _qp_eval(mu: float, parameters: Mapping[str, float]) -> float:
    """Evaluate the fitted qp law with the study's cap and nonnegative floor."""

    mu_c = min(float(mu), float(parameters["mu_cap"]))
    qp_model = int(round(float(parameters["qp_model"])))
    q0 = float(parameters["qp0"])
    q1 = float(parameters["qp1"])
    q2 = float(parameters["qp2"])
    if qp_model == MODEL_CODES["linear"]:
        qp = q0 * mu_c + q1
    elif qp_model == MODEL_CODES["bell_shaped"]:
        qp = q0 * np.exp(-((mu_c - q1) ** 2) / (2.0 * q2**2))
    elif qp_model == MODEL_CODES["hyperbolic"]:
        qp = q0 * mu_c / (q1 + mu_c)
    else:
        raise ValueError(f"Unsupported qp_model code: {qp_model}")
    return max(float(qp), 0.0)


class BatchBioprocessModel(BioprocessModel):
    """Batch phase which freezes exactly at the substrate depletion event."""

    def rhs(self, t, y, sw):
        # pyFOOMB alphabetic state order: feed_time, P, S, V, X.
        feed_time, P, S, V, X = y
        if sw[0]:
            return np.zeros(5)

        p = self.model_parameters
        X_eff = max(float(X), 0.0)
        S_eff = max(float(S), 0.0)
        mu = (
            float(p["mu_max"]) * S_eff / (float(p["Ks"]) + S_eff)
            if S_eff > 1e-9
            else 0.0
        )
        qp = _qp_eval(mu, p)
        return np.array(
            [
                1.0,
                qp * X_eff,
                -(mu / float(p["Yxs"])) * X_eff,
                0.0,
                mu * X_eff,
            ]
        )

    def state_events(self, t, y, sw):
        if sw[0]:
            return np.array([1.0])
        return np.array([float(y[2]) - float(self.model_parameters["S_deplete"])])

    def change_states(self, t, y, sw):
        if sw[0]:
            y[2] = float(self.model_parameters["S_deplete"])
        return y

    # Assimulo 3.7 discovers event callbacks on the concrete problem class.
    # Keep this explicit forwarding method for compatibility with that release.
    def handle_event(self, solver, event_info):
        return super().handle_event(solver, event_info)


class FedBatchBioprocessModel(BioprocessModel):
    """Fed-batch phase supporting every strategy in the reference study."""

    def rhs(self, t, y, sw):
        # pyFOOMB alphabetic state order: P, S, V, X.
        P, S, V, X = y
        p = self.model_parameters
        X_eff = max(float(X), 0.0)
        S_eff = max(float(S), 0.0)
        V_eff = max(float(V), 1e-6)
        mu = (
            float(p["mu_max"]) * S_eff / (float(p["Ks"]) + S_eff)
            if S_eff > 1e-9
            else 0.0
        )
        qp = _qp_eval(mu, p)
        feed = self._feed_rate(t, y, sw)
        dilution = feed / V_eff
        return np.array(
            [
                qp * X_eff - dilution * float(P),
                dilution * (float(p["S_in"]) - S_eff)
                - (mu / float(p["Yxs"])) * X_eff,
                feed,
                mu * X_eff - dilution * X_eff,
            ]
        )

    def _feed_rate(self, t, y, sw) -> float:
        p = self.model_parameters
        if sw[VOLUME_EVENT_INDEX]:
            return 0.0

        strategy = int(round(float(p["strategy"])))
        if strategy == STRATEGY_CODES["constant"]:
            feed = float(p["F0"])
        elif strategy == STRATEGY_CODES["exponential"]:
            feed = float(p["F0"]) * np.exp(float(p["mu_set"]) * float(t))
        elif strategy == STRATEGY_CODES["linear_ramp"]:
            feed = float(p["F0"]) + float(p["k"]) * float(t)
        elif strategy == STRATEGY_CODES["exp_linear"]:
            feed = (
                float(p["F0"]) * np.exp(float(p["mu_set"]) * float(t))
                + float(p["k"]) * float(t)
            )
        elif strategy == STRATEGY_CODES["two_stage"]:
            feed = float(p["F2"] if sw[STAGE_EVENT_INDEX] else p["F1"])
        elif strategy in STAGED_CODE_SHAPES:
            feed = staged_feed_rate(t, p, STAGED_CODE_SHAPES[strategy],
                                    second_stage=sw[STAGE_EVENT_INDEX])
        elif strategy == STRATEGY_CODES["pulsed"]:
            # Pulse starts on; each scheduled edge changes the parity.
            fired_edges = sum(bool(value) for value in sw[PULSE_EVENT_START:])
            feed = float(p["F_pulse"]) if fired_edges % 2 == 0 else 0.0
        elif strategy == STRATEGY_CODES["feedback_control"]:
            mu_max = float(p["mu_max"])
            mu_target = min(float(p["mu_target"]), 0.95 * mu_max)
            substrate_setpoint = float(p["Ks"]) * mu_target / (mu_max - mu_target)
            feed = float(p["Kp"]) * (substrate_setpoint - float(y[1]))
        else:
            raise ValueError(f"Unsupported strategy code: {strategy}")
        return min(max(float(feed), 0.0), float(p["F_cap"]))

    def state_events(self, t, y, sw):
        p = self.model_parameters
        strategy = int(round(float(p["strategy"])))
        events = np.ones(N_EVENTS, dtype=float)
        if not sw[VOLUME_EVENT_INDEX]:
            events[VOLUME_EVENT_INDEX] = float(p["V_max"]) - float(y[2])

        if (strategy == STRATEGY_CODES["two_stage"] or strategy in STAGED_CODE_SHAPES) and not sw[STAGE_EVENT_INDEX]:
            events[STAGE_EVENT_INDEX] = float(t) - float(p["t_switch"])
        if strategy == STRATEGY_CODES["pulsed"]:
            period = max(float(p["T_cycle"]), np.finfo(float).eps)
            duty = min(max(float(p["duty"]), 0.0), 1.0)
            for cycle in range(MAX_PULSE_CYCLES):
                edge_index = PULSE_EVENT_START + 2 * cycle
                if not sw[edge_index]:
                    events[edge_index] = float(t) - (cycle + duty) * period
                if not sw[edge_index + 1]:
                    events[edge_index + 1] = float(t) - (cycle + 1.0) * period
        return events

    def change_states(self, t, y, sw):
        if sw[VOLUME_EVENT_INDEX]:
            # Eliminate tiny root-location overshoots and hold V exactly at 4 L.
            y[2] = float(self.model_parameters["V_max"])
        return y

    # See BatchBioprocessModel.handle_event for Assimulo compatibility.
    def handle_event(self, solver, event_info):
        return super().handle_event(solver, event_info)


def _base_parameters(fitted: FittedDataset) -> dict[str, float]:
    return {
        "mu_max": fitted.mu_max,
        "Ks": fitted.Ks,
        "Yxs": fitted.Yxs,
        "qp_model": float(MODEL_CODES[fitted.model_type]),
        "qp0": fitted.qp0,
        "qp1": fitted.qp1,
        "qp2": fitted.qp2,
        "mu_cap": fitted.mu_cap,
        "S_in": S_IN,
        "V_max": V_MAX,
        "F_cap": F_CAP,
        "S_deplete": S_DEPLETE,
    }


def _fedbatch_parameters(fitted: FittedDataset, strategy: str) -> dict[str, float]:
    if strategy not in STRATEGY_CODES:
        raise KeyError(f"Unknown feed strategy: {strategy!r}")
    parameters = _base_parameters(fitted)
    parameters.update(
        {
            "strategy": float(STRATEGY_CODES[strategy]),
            # Every strategy knob is exposed so Caretaker estimate methods can
            # select the relevant subset as unknowns without rebuilding a model.
            "F0": 0.1,
            "mu_set": 0.1,
            "k": 0.001,
            "F1": 0.1,
            "F2": 0.05,
            "k1": 0.001,
            "k2": 0.001,
            "mu1": 0.1,
            "mu2": 0.1,
            "t_switch": 20.0,
            "F_pulse": 0.4,
            "T_cycle": 2.0,
            "duty": 0.5,
            "mu_target": min(0.1, 0.9 * fitted.mu_max),
            "Kp": 1.0,
        }
    )
    return parameters


def _set_integrator_options(
    caretaker: Caretaker,
    *,
    maxh: float,
    rtol: float = 1e-5,
    atol: float = 1e-8,
) -> None:
    for simulator in caretaker.simulators.values():
        simulator.integrator_kwargs = {
            "rtol": float(rtol),
            "atol": float(atol),
            "maxh": float(maxh),
        }


def _series_by_name(simulations: Sequence[Any]) -> dict[str, Any]:
    return {series.name: series for series in simulations}


def simulate_batch(
    dataset: Mapping[str, Any],
    model_type: str,
    *,
    fitted: FittedDataset | None = None,
    caretaker_class: Type[Caretaker] = Caretaker,
) -> BatchResult:
    """Run the batch phase with Caretaker/CVode and return its exact event state."""

    fitted = fitted or fit_dataset(dataset, model_type)
    caretaker = caretaker_class(
        bioprocess_model_class=BatchBioprocessModel,
        model_parameters=_base_parameters(fitted),
        states=list(BATCH_STATE_ORDER),
        initial_values={
            "feed_time0": 0.0,
            "P0": P0,
            "S0": S0,
            "V0": V0,
            "X0": X0,
        },
        initial_switches=[False],
        model_name=f"{fitted.product} batch",
        model_checking_assistance=False,
    )
    _set_integrator_options(caretaker, maxh=1.0, rtol=1e-6, atol=1e-9)
    started = perf_counter()
    simulations = caretaker.simulate(
        t=np.array([T_BATCH_MAX]), verbosity=50, suppress_stdout=True
    )
    runtime = perf_counter() - started
    series = _series_by_name(simulations)
    t = np.asarray(series["X"].timepoints, dtype=float)
    y = np.vstack([np.asarray(series[name].values, dtype=float) for name in STATE_ORDER])
    y_feed = y[:, -1].copy()
    t_feed = float(series["feed_time"].values[-1])
    # The switch freezes the model at depletion and CVode then continues to the
    # 60 h safety horizon.  Keep only the physical batch trajectory and append
    # the exact event state when the event point was not part of ncp output.
    keep = t < t_feed
    t = np.concatenate((t[keep], np.array([t_feed])))
    y = np.concatenate((y[:, keep], y_feed[:, None]), axis=1)
    return BatchResult(t_feed=t_feed, y_feed=y_feed, t=t, y=y, runtime_seconds=runtime)


def make_caretaker(
    dataset: Mapping[str, Any],
    model_type: str,
    strategy: str,
    *,
    y_feed: Sequence[float] | None = None,
    batch_result: BatchResult | None = None,
    fitted: FittedDataset | None = None,
    caretaker_class: Type[Caretaker] = Caretaker,
) -> Caretaker:
    """Build a reusable fed-batch Caretaker initialized at feed start.

    Supply a cached ``batch_result`` (or ``y_feed`` in X/S/P/V order) when
    repeatedly building strategy-specific caretakers for the same dataset.
    ``caretaker_class`` may be a custom Caretaker subclass implementing an
    optimisation loss.
    """

    fitted = fitted or fit_dataset(dataset, model_type)
    if batch_result is not None:
        if y_feed is not None:
            raise ValueError("Provide either batch_result or y_feed, not both")
        y_feed = batch_result.y_feed
    if y_feed is None:
        y_feed = simulate_batch(
            dataset,
            model_type,
            fitted=fitted,
            caretaker_class=Caretaker,
        ).y_feed
    y_feed_array = np.asarray(y_feed, dtype=float)
    if y_feed_array.shape != (4,):
        raise ValueError("y_feed must contain [X, S, P, V]")
    X, S, P, V = y_feed_array

    caretaker = caretaker_class(
        bioprocess_model_class=FedBatchBioprocessModel,
        model_parameters=_fedbatch_parameters(fitted, strategy),
        states=list(PYFOOMB_STATE_ORDER),
        initial_values={"P0": P, "S0": S, "V0": V, "X0": X},
        initial_switches=[False] * N_EVENTS,
        model_name=f"{fitted.product} {strategy} fed-batch",
        model_checking_assistance=False,
    )
    # Time events resolve feed discontinuities, so a one-hour maximum step is
    # sufficient for the smooth intervals and much cheaper than the SciPy
    # reference's pulse-specific 0.01 h maximum step.
    _set_integrator_options(caretaker, maxh=1.0)
    return caretaker


class FedBatchRunner:
    """Reusable adapter containing a cached batch endpoint and Caretaker."""

    def __init__(
        self,
        dataset: Mapping[str, Any],
        model_type: str,
        strategy: str,
        fitted: FittedDataset,
        batch: BatchResult,
        caretaker: Caretaker,
        default_timepoints: np.ndarray,
    ):
        self.dataset = dataset
        self.model_type = model_type
        self.strategy = strategy
        self.fitted = fitted
        self.batch = batch
        self.caretaker = caretaker
        self.default_timepoints = default_timepoints

    @property
    def parameter_names(self) -> tuple[str, ...]:
        return STRATEGY_PARAMETER_NAMES[self.strategy]

    def simulate(
        self,
        parameters: Mapping[str, float] | Sequence[float],
        timepoints: Sequence[float] | None = None,
    ) -> FeedSimulation:
        """Run ``Caretaker.simulate(parameters=...)`` for the 40 h feed phase."""

        if isinstance(parameters, Mapping):
            parameter_values = dict(parameters)
        else:
            values = tuple(float(value) for value in parameters)
            names = self.parameter_names
            if len(values) != len(names):
                raise ValueError(f"{self.strategy} expects parameters {names}")
            parameter_values = dict(zip(names, values))

        t_eval = np.asarray(
            self.default_timepoints if timepoints is None else timepoints, dtype=float
        ).reshape(-1)
        if t_eval.size < 2 or np.any(np.diff(t_eval) <= 0.0):
            raise ValueError("timepoints must be a strictly increasing sequence")
        if t_eval[0] != 0.0 or t_eval[-1] != T_FEDBATCH:
            raise ValueError("timepoints must start at 0 and end at 40 h")

        started = perf_counter()
        simulations = self.caretaker.simulate(
            t=t_eval,
            parameters=parameter_values,
            verbosity=50,
            reset_afterwards=False,
            suppress_stdout=True,
        )
        runtime = perf_counter() - started
        series = _series_by_name(simulations)
        t = np.asarray(series["X"].timepoints, dtype=float)
        y = np.vstack(
            [np.asarray(series[name].values, dtype=float) for name in STATE_ORDER]
        )
        # Root location may leave sub-ulp noise.  The physical event is exact.
        y[3] = np.minimum(y[3], V_MAX)
        return FeedSimulation(
            t=t,
            y=y,
            y_feed=self.batch.y_feed.copy(),
            runtime_seconds=runtime,
        )


def make_runner(
    dataset: Mapping[str, Any],
    model_type: str,
    strategy: str,
    *,
    batch_result: BatchResult | None = None,
    timepoints: Sequence[float] | None = None,
    caretaker_class: Type[Caretaker] = Caretaker,
) -> FedBatchRunner:
    """Fit the dataset, cache its batch phase, and return a reusable runner."""

    fitted = fit_dataset(dataset, model_type)
    batch = batch_result or simulate_batch(dataset, model_type, fitted=fitted)
    caretaker = make_caretaker(
        dataset,
        model_type,
        strategy,
        batch_result=batch,
        fitted=fitted,
        caretaker_class=caretaker_class,
    )
    default_timepoints = np.asarray(
        np.linspace(0.0, T_FEDBATCH, 401) if timepoints is None else timepoints,
        dtype=float,
    )
    return FedBatchRunner(
        dataset=dataset,
        model_type=model_type,
        strategy=strategy,
        fitted=fitted,
        batch=batch,
        caretaker=caretaker,
        default_timepoints=default_timepoints,
    )


def simulate_fedbatch(
    dataset: Mapping[str, Any],
    model_type: str,
    strategy: str,
    parameters: Mapping[str, float] | Sequence[float],
    *,
    batch_result: BatchResult | None = None,
    timepoints: Sequence[float] | None = None,
    caretaker_class: Type[Caretaker] = Caretaker,
) -> FeedSimulation:
    """Convenience one-shot wrapper around :func:`make_runner`."""

    runner = make_runner(
        dataset,
        model_type,
        strategy,
        batch_result=batch_result,
        timepoints=timepoints,
        caretaker_class=caretaker_class,
    )
    return runner.simulate(parameters)


__all__ = [
    "BatchBioprocessModel",
    "BatchResult",
    "FeedSimulation",
    "FedBatchBioprocessModel",
    "FedBatchRunner",
    "FittedDataset",
    "STATE_ORDER",
    "STRATEGY_PARAMETER_NAMES",
    "fit_dataset",
    "make_caretaker",
    "make_runner",
    "simulate_batch",
    "simulate_fedbatch",
]
