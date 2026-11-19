"""Run the feed study through real pyFOOMB/CVode and its optimizer APIs.

Examples (activate the bpdd environment first)::

    python pyfoomb_feed_optimization.py --mode compare --workers 6
    python pyfoomb_feed_optimization.py --mode optimize --engine caretaker --workers 6
    python pyfoomb_feed_optimization.py --mode optimize --engine pygmo --workers 6

The SciPy study is retained as a reference. Outputs and resumable checkpoints
are separate; no historical result or presentation is overwritten.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import threading
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/pyfoomb-feed-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/pyfoomb-feed-cache")

import numpy as np
import pandas as pd
import pygmo as pg
from assimulo.solvers.sundials import CVodeError
from pyfoomb import Caretaker
from pyfoomb.generalized_islands import (
    LossCalculator, ParallelEstimationInfo, PyfoombArchipelago,
)

import feed_flow_optimization as reference
import pyfoomb_feed_model as native

HERE = Path(__file__).resolve().parent
OUT = HERE / "pyfoomb_results"
EVOLVE_LOCK = threading.Lock()


class ProductCaretaker(Caretaker):
    """Use Caretaker's optimizer infrastructure for process design, not fitting."""

    def loss_function(self, guess_dict, metric, measurements,
                      handle_CVodeError=True, verbosity_CVodeError=False):
        self.objective_calls = getattr(self, "objective_calls", 0) + 1
        try:
            states = self.simulate(
                t=np.array([0.0, reference.T_FEDBATCH]),
                parameters=guess_dict, verbosity=50,
            )
            final = {state.name: float(state.values[-1]) for state in states}
            if (not all(np.isfinite(list(final.values()))) or
                    final["V"] > reference.V_MAX + 1e-6):
                raise ValueError("Invalid final state or volume constraint")
            return -final["P"] * final["V"]
        except CVodeError:
            self.failed_simulations = getattr(self, "failed_simulations", 0) + 1
            if not handle_CVodeError:
                raise
            return np.inf


class InProcessIsland:
    """Avoid broken C++ algorithm pickling, with no shared-model races.

    Islands within one case evolve serially under a lock. Independent cases
    run in separate worker processes, each with its own Caretaker and CVode.
    This does not claim simultaneous island execution within a case.
    """

    def run_evolve(self, algo, pop):
        with EVOLVE_LOCK:
            return algo, algo.evolve(pop)

    def get_name(self):
        return "locked in-process pygmo evolution"


def cases(strategies=None):
    tasks = []
    # Append new families after all legacy cases, preserving saved indices.
    for group in (reference.LEGACY_STRATEGIES, tuple(reference.TWO_STAGE_SHAPES)):
        for kind, datasets in reference.DATA.items():
            for dataset_index, _ in enumerate(datasets):
                for name in group:
                    tasks.append((len(tasks), kind, dataset_index, name))
    return tasks if strategies is None else [task for task in tasks if task[3] in strategies]


def json_safe(value):
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def reference_row(ds, name):
    frame = pd.read_csv(HERE / "feed_flow_results.csv")
    return frame[(frame["product"] == ds["product"]) &
                 (frame["strategy"] == name)].iloc[0]


def row_from_solution(kind, ds, name, params, runner, solution):
    X, S, P, V = solution.y[:, -1]
    kin = reference.KINETICS[ds["organism_type"]]
    row = dict(model_type=kind, product=ds["product"],
               organism=ds["organism_type"], reference=ds["reference"],
               strategy=name, total_product=P * V, P_final=P, V_final=V,
               X_final=X, S_final=S, avg_mu=reference.mean_mu(solution, kin),
               t_feed=runner.batch.t_feed, qp_unit=ds["qp_unit"])
    row.update({f"param_{key}": float(value) for key, value in params.items()})
    return json_safe(row)


def compare_one(task):
    index, kind, dataset_index, name = task
    ds = reference.DATA[kind][dataset_index]
    strategy = reference.STRATEGIES[name]
    old = reference_row(ds, name)
    params = {key: float(old[f"param_{key}"]) for key in strategy["names"]}
    runner = native.make_runner(ds, kind, name)
    result = runner.simulate(params)
    kin = reference.KINETICS[ds["organism_type"]]
    fn, fit = reference.fit_qp_model(kind, ds["mu"], ds["qp"])
    cap = float(ds["mu"].max() * 1.2)
    t_batch, y_batch_final, _ = reference.simulate_batch(kin, fn, fit, cap)
    scipy = reference.simulate_fedbatch(
        strategy, [params[key] for key in strategy["names"]],
        kin, fn, fit, cap, y_batch_final, strategy["max_step"],
    )
    if not scipy.success:
        raise RuntimeError(scipy.message)
    native_product = float(result.y[2, -1] * result.y[3, -1])
    scipy_product = float(scipy.y[2, -1] * scipy.y[3, -1])
    row = dict(case_index=index, model_type=kind, product=ds["product"],
               strategy=name, scipy_total_product=scipy_product,
               pyfoomb_total_product=native_product,
               relative_difference_percent=100 * (native_product / scipy_product - 1),
               scipy_volume=float(scipy.y[3, -1]),
               pyfoomb_volume=float(result.y[3, -1]),
               batch_switch_difference_seconds=3600 * (runner.batch.t_feed - t_batch),
               runtime_seconds=result.runtime_seconds,
               params=params)
    return index, json_safe(row)


def optimize_pygmo(caretaker, names, bounds, warm_params):
    ordered = sorted(names, key=str.lower)
    sorted_bounds = [bounds[names.index(key)] for key in ordered]
    problem = pg.problem(LossCalculator(
        unknowns=ordered, bounds=sorted_bounds, metric="total_product",
        measurements=[], caretaker_loss_fun=caretaker.loss_function,
    ))
    arch = PyfoombArchipelago(t=pg.fully_connected())
    arch.problem = LossCalculator
    arch.set_migrant_handling(pg.migrant_handling.preserve)
    size = max(5, 14 * len(names))
    for island_index in range(2):
        population = pg.population(problem, size=size, seed=42 + island_index)
        # One cold population and one warm population. The warm candidate is
        # evaluated by the real CVode objective, not copied as an old score.
        if island_index == 1:
            worst = int(np.argmax(population.get_f()[:, 0]))
            population.set_x(worst, [warm_params[key] for key in ordered])
        algo = pg.algorithm(pg.de(gen=10, F=0.8, CR=0.9, variant=2,
                                 ftol=0.0, xtol=0.0, seed=42 + island_index))
        arch.push_back(pg.island(algo=algo, pop=population, udi=InProcessIsland()))
    estimates, info = caretaker.estimate_parallel_continued(
        estimation_result=ParallelEstimationInfo(arch), evolutions=2,
        atol_islands=0.0, rtol_islands=0.0, max_memory_share=1.0,
        report_level=0,
    )
    return estimates, dict(
        nfev=sum(island.get_population().problem.get_fevals() for island in info.archipelago),
        islands=2, generations_per_island=20, population_size_per_island=size,
        island_champion_products=[-float(f[0]) for f in info.archipelago.get_champions_f()],
        initialization="one cold population; one includes the CVode-replayed SciPy candidate",
        API="Caretaker.estimate_parallel_continued / PyfoombArchipelago / LossCalculator",
        backend="in-process locked evolution; independent cases in separate processes",
    )


def optimize_one(task, engine):
    index, kind, dataset_index, name = task
    start = time.monotonic()
    ds = reference.DATA[kind][dataset_index]
    strategy = reference.STRATEGIES[name]
    names = strategy["names"]
    bounds = strategy["bounds"](reference.KINETICS[ds["organism_type"]])
    runner = native.make_runner(ds, kind, name, caretaker_class=ProductCaretaker)
    if engine == "caretaker":
        params, info = runner.caretaker.estimate(
            unknowns=names, measurements=[], bounds=bounds,
            metric="total_product", use_global_optimizer=True, report_level=0,
            optimizer_kwargs=dict(reference.DE_KWARGS),
        )
        opt = info["opt_info"]
        diagnostics = dict(nfev=int(opt.nfev), nit=int(opt.nit),
                           converged=bool(opt.success), message=str(opt.message),
                           API="Caretaker.estimate (SciPy differential evolution)",
                           initialization="fresh seeded population; no warm start")
    else:
        old = reference_row(ds, name)
        warm = {key: float(old[f"param_{key}"]) for key in names}
        params, diagnostics = optimize_pygmo(runner.caretaker, names, bounds, warm)
    solution = runner.simulate(params, timepoints=np.linspace(0, reference.T_FEDBATCH, 1001))
    row = row_from_solution(kind, ds, name, params, runner, solution)
    diagnostics.update(runtime_seconds=time.monotonic() - start,
                       failed_simulations=getattr(runner.caretaker, "failed_simulations", 0))
    return index, dict(row=row, diagnostics=json_safe(diagnostics)), solution, runner.batch


def work(task, mode, engine, checkpoint_dir, profile_dir):
    if mode == "compare":
        index, payload = compare_one(task)
    else:
        index, payload, solution, batch = optimize_one(task, engine)
        Path(profile_dir).mkdir(parents=True, exist_ok=True)
        np.savez_compressed(Path(profile_dir) / f"{index:02d}.npz",
                            t=solution.t, y=solution.y,
                            t_batch=batch.t, y_batch=batch.y, t_feed=batch.t_feed)
    target = Path(checkpoint_dir) / f"{index:02d}.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(json_safe(payload), indent=2))
    temporary.replace(target)
    return index, payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["compare", "optimize"], default="compare")
    parser.add_argument("--engine", choices=["caretaker", "pygmo"], default="caretaker")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--indices", help="Comma-separated case indices for a bounded run")
    parser.add_argument("--strategies", nargs="+", choices=list(reference.STRATEGIES),
                        default=list(reference.LEGACY_STRATEGIES))
    args = parser.parse_args()
    source_paths = [Path(__file__), Path(native.__file__), Path(reference.__file__)]
    source_hash = hashlib.sha256(b"".join(path.read_bytes() for path in source_paths)).hexdigest()
    baseline_hash = hashlib.sha256((HERE / "feed_flow_results.csv").read_bytes()).hexdigest()
    token = source_hash[:12] + "_" + baseline_hash[:8]
    run_name = args.mode if args.mode == "compare" else args.engine
    checkpoints = OUT / "checkpoints" / f"{run_name}_{token}"
    destination = OUT if args.mode == "compare" else OUT / args.engine
    checkpoints.mkdir(parents=True, exist_ok=True)
    destination.mkdir(parents=True, exist_ok=True)
    tasks = cases(args.strategies)
    if args.indices:
        selected = {int(index) for index in args.indices.split(",")}
        tasks = [task for task in tasks if task[0] in selected]
    payloads = {}
    pending = []
    for task in tasks:
        checkpoint = checkpoints / f"{task[0]:02d}.json"
        if checkpoint.exists():
            payloads[task[0]] = json.loads(checkpoint.read_text())
        else:
            pending.append(task)
    start = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(work, task, args.mode, args.engine,
                               str(checkpoints), str(destination / "profiles"))
                   for task in pending]
        for future in as_completed(futures):
            index, payload = future.result()
            payloads[index] = payload
            row = payload if args.mode == "compare" else payload["row"]
            value = (row["relative_difference_percent"] if args.mode == "compare"
                     else row["total_product"])
            print(f"{len(payloads)}/{len(tasks)} {row['product']} / {row['strategy']}: {value:.6g}", flush=True)
    ordered_payloads = [payloads[task[0]] for task in tasks]
    if args.mode == "compare":
        frame = pd.DataFrame(ordered_payloads)
        frame.drop(columns=["params"]).to_csv(destination / "solver_comparison.csv", index=False)
    else:
        frame = pd.DataFrame([payload["row"] for payload in ordered_payloads])
        frame.to_csv(destination / "feed_flow_results.csv", index=False)
        best = frame.loc[frame.groupby(["model_type", "product"])["total_product"].idxmax()]
        best.to_csv(destination / "best_per_dataset.csv", index=False)
        pd.DataFrame([dict(case_index=task[0], **payload["diagnostics"])
                      for task, payload in zip(tasks, ordered_payloads)]).to_csv(
                          destination / "optimization_diagnostics.csv", index=False)
    versions = {}
    for library in ["numpy", "scipy", "pandas", "pygmo", "assimulo"]:
        try:
            versions[library] = importlib.metadata.version(library)
        except importlib.metadata.PackageNotFoundError:
            versions[library] = "unknown"
    import pyfoomb
    versions["pyfoomb"] = pyfoomb.__version__
    metadata = dict(
        cases=len(tasks), completed=len(ordered_payloads), engine=args.engine,
        mode=args.mode, source_sha256=source_hash, baseline_sha256=baseline_hash,
        source_files=[str(path) for path in source_paths], library_versions=versions,
        elapsed_seconds=time.monotonic() - start, solver="Assimulo/SUNDIALS CVode",
        objective="minimize negative final product concentration times final volume",
        native_simulation="BioprocessModel -> Caretaker.simulate -> Simulator -> CVode",
        DE_settings=reference.DE_KWARGS if args.engine == "caretaker" else
                    dict(islands=2, generations_per_island=20, population_multiplier=14,
                         seeds=[42, 43], migration_topology="fully_connected"),
        island_note="pygmo mp_island build cannot serialize algorithms; in-process UDI avoids this. "
                    "A lock serializes islands in each case; separate processes parallelize cases.",
        ranking_note="Finite-budget searches, not proofs of global optimality. "
                     "The pygmo branch includes one warm candidate per case; the Caretaker.estimate branch is fresh.",
    )
    (destination / f"{args.mode}_metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Completed {len(tasks)} cases in {metadata['elapsed_seconds']:.1f}s: {destination}", flush=True)


if __name__ == "__main__":
    main()
