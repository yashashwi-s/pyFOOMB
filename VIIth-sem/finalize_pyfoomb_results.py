"""Re-evaluate all searched candidates with tighter CVode tolerances.

Keeps both optimizer runs, the reference replay, and the final selection
explicit. All final profiles are actual Caretaker/CVode outputs.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil

os.environ.setdefault("MPLCONFIGDIR", "/tmp/pyfoomb-feed-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/pyfoomb-feed-cache")

import numpy as np
import pandas as pd
import feed_flow_optimization as reference
import pyfoomb_feed_model as native
from pyfoomb_feed_optimization import cases, row_from_solution

HERE = Path(__file__).resolve().parent
OUT = HERE / "pyfoomb_results"


def main():
    inputs = {
        "caretaker_fresh": pd.read_csv(OUT / "caretaker/feed_flow_results.csv"),
        "pygmo_warm": pd.read_csv(OUT / "pygmo/feed_flow_results.csv"),
        "reference_replay": pd.read_csv(HERE / "feed_flow_results.csv"),
    }
    optimized_cases = set()
    for key, frame in inputs.items():
        if frame.duplicated(["product", "strategy"]).any():
            raise ValueError(f"{key}: duplicate cases")
        if key != "reference_replay":
            optimized_cases.update(zip(frame["product"], frame["strategy"]))
    if len(optimized_cases) != 63:
        raise ValueError(f"Only {len(optimized_cases)} cases have completed native optimization")
    destination = OUT / "final"
    (destination / "profiles").mkdir(parents=True, exist_ok=True)
    selected, audits, comparisons = [], [], []
    maximum_balance_error = 0.0
    for index, kind, dataset_index, name in cases(reference.LEGACY_STRATEGIES):
        ds = reference.DATA[kind][dataset_index]
        runner = native.make_runner(ds, kind, name)
        for simulator in runner.caretaker.simulators.values():
            simulator.integrator_kwargs.update(rtol=1e-8, atol=1e-11)
        options = []
        old = None
        for source, frame in inputs.items():
            matches = frame[(frame["product"] == ds["product"]) & (frame["strategy"] == name)]
            if matches.empty:
                continue
            row = matches.iloc[0]
            params = {key: float(row[f"param_{key}"]) for key in reference.STRATEGIES[name]["names"]}
            solution = runner.simulate(params, timepoints=np.linspace(0, reference.T_FEDBATCH, 1001))
            # Check unmodified Caretaker values: clipping exported arrays is not
            # accepted as evidence that the actual ODE obeys the volume limit.
            raw = {state.name: state.values for state in runner.caretaker.simulate(
                t=np.array([0.0, reference.T_FEDBATCH]), parameters=params, verbosity=50)}
            if np.max(raw["V"]) > reference.V_MAX + 1e-7:
                raise ValueError(f"Raw CVode volume overflow in {ds['product']}/{name}")
            X, S, P, V = solution.y
            X0, S0, _, V0 = runner.batch.y_feed
            Y = reference.KINETICS[ds["organism_type"]]["Yxs"]
            balance = X*V-X0*V0 + Y*(S*V-S0*V0-reference.S_IN*(V-V0))
            relative_error = float(np.max(np.abs(balance)) / max(float(np.max(X*V)), 1.0))
            maximum_balance_error = max(maximum_balance_error, relative_error)
            if relative_error > 1e-5:
                raise ValueError(f"Mass balance error {relative_error} in {ds['product']}/{name}")
            result = row_from_solution(kind, ds, name, params, runner, solution)
            result["candidate_source"] = source
            audits.append(dict(case_index=index, source=source, **result,
                               relative_mass_balance_error=relative_error,
                               search_score=float(row["total_product"])))
            options.append((result["total_product"], result, solution))
            if source == "reference_replay":
                old = result
        _, best, solution = max(options, key=lambda option: option[0])
        selected.append(best)
        baseline = inputs["reference_replay"]
        baseline = baseline[(baseline["product"] == ds["product"]) & (baseline["strategy"] == name)].iloc[0]
        comparisons.append(dict(case_index=index, model_type=kind, product=ds["product"], strategy=name,
                                scipy_saved_product=float(baseline["total_product"]),
                                pyfoomb_same_settings_product=old["total_product"],
                                pyfoomb_reoptimized_product=best["total_product"],
                                optimization_change_percent=100*(best["total_product"]/old["total_product"]-1),
                                candidate_source=best["candidate_source"]))
        np.savez_compressed(destination / "profiles" / f"{index:02d}.npz",
                            t=solution.t, y=solution.y, t_batch=runner.batch.t,
                            y_batch=runner.batch.y, t_feed=runner.batch.t_feed)
        print(f"{index+1}/63 {ds['product']} / {name}: {best['candidate_source']}", flush=True)
    results = pd.DataFrame(selected)
    results.to_csv(destination / "feed_flow_results.csv", index=False)
    best = results.loc[results.groupby(["model_type", "product"])["total_product"].idxmax()].copy()
    for index, row in best.iterrows():
        group = results[results["product"] == row["product"]].sort_values("total_product", ascending=False)
        best.loc[index, "margin_percent"] = 100*(group.iloc[0].total_product/group.iloc[1].total_product-1)
        best.loc[index, "spread_percent"] = 100*(group.iloc[0].total_product/group.iloc[-1].total_product-1)
        equivalent = group[group.total_product >= group.iloc[0].total_product*0.999]
        best.loc[index, "within_0_1_percent"] = ", ".join(equivalent.strategy)
    best.to_csv(destination / "best_per_dataset.csv", index=False)
    pd.DataFrame(audits).to_csv(destination / "candidate_audit.csv", index=False)
    pd.DataFrame(comparisons).to_csv(destination / "optimization_comparison.csv", index=False)
    shutil.copy2(OUT / "solver_comparison.csv", destination / "solver_comparison.csv")
    metadata = dict(
        cases=63, candidate_evaluations=len(audits), solver="pyFOOMB / Assimulo / SUNDIALS CVode",
        completed_searches={key: len(frame) for key, frame in inputs.items() if key != "reference_replay"},
        final_rtol=1e-8, final_atol=1e-11,
        maximum_final_volume=float(results.V_final.max()),
        maximum_relative_mass_balance_error=maximum_balance_error,
        selection="Every case has a completed native optimization. Best per case after tight CVode replay "
                  "of available completed fresh Caretaker DE and warm pygmo searches, plus reference settings. "
                  "Incomplete duplicate searches were stopped at the user's request to finish faster.",
        fitting="Identical literature qp(mu) fits; kinetic parameters fixed during feed design",
        optimizer_note="Fresh Caretaker.estimate uses original seed42/popsize14/maxiter40/polish settings. "
                       "Pygmo uses two populations, 20 generations per island, seeds42/43, with one warm candidate. "
                       "Native estimate_parallel_continued coordinates the archipelago. "
                       "In-process UDI serializes islands; independent cases run in separate processes.",
        uncertainty="Finite budgets and close strategy scores do not establish global optimality or experimental validity",
        source_sha256={str(path.name): hashlib.sha256(path.read_bytes()).hexdigest() for path in
                       [HERE / "pyfoomb_feed_model.py", HERE / "pyfoomb_feed_optimization.py", Path(__file__)]},
    )
    (destination / "run_metadata.json").write_text(json.dumps(metadata, indent=2))
    print(best[["product", "strategy", "margin_percent", "within_0_1_percent"]].to_string(index=False))


if __name__ == "__main__":
    main()
