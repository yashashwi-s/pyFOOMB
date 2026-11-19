"""Optimize four sequential feed families, then compare all 99 native cases.

Uses the completed 63-case study as an immutable baseline. Each new case has
one fresh Caretaker DE search and one search seeded with adapted earlier laws.
Checkpoints are scoped to code and baseline hashes and can resume safely.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import time

os.environ.setdefault('MPLCONFIGDIR', '/tmp/pyfoomb-feed-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/pyfoomb-feed-cache')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')

import numpy as np
import pandas as pd
from scipy.stats import qmc

import feed_flow_optimization as reference
import pyfoomb_feed_model as native
from pyfoomb_feed_optimization import ProductCaretaker, cases, json_safe, row_from_solution

HERE = Path(__file__).resolve().parent
BASELINE = HERE / 'pyfoomb_results/final'
OUT = HERE / 'pyfoomb_results/two_stage_extension'
NEW_STRATEGIES = tuple(reference.TWO_STAGE_SHAPES)


def seed_candidates(baseline, name, kin):
    """Adapt earlier laws into stage-local rate and slope/growth settings."""
    strategy = reference.STRATEGIES[name]
    shapes = reference.TWO_STAGE_SHAPES[name]
    bounds = dict(zip(strategy['names'], strategy['bounds'](kin)))
    seeds = []
    for old in baseline.itertuples(index=False):
        if old.strategy not in ('constant', 'exponential', 'linear_ramp', 'exp_linear', 'two_stage'):
            continue
        switches = [1.0, 5.0, 10.0, 20.0, 30.0, 38.0]
        if old.strategy == 'two_stage':
            switches = [float(old.param_t_switch)]
        for switch in switches:
            parameters = dict(t_switch=switch)
            for stage, elapsed in ((1, 0.0), (2, switch)):
                if old.strategy == 'two_stage':
                    rate = old.param_F1 if stage == 1 else old.param_F2
                    slope = 0.0
                elif old.strategy == 'constant':
                    rate, slope = old.param_F0, 0.0
                elif old.strategy == 'linear_ramp':
                    rate, slope = old.param_F0 + old.param_k*elapsed, old.param_k
                else:
                    exp_rate = old.param_F0*np.exp(old.param_mu_set*elapsed)
                    extra = old.param_k if old.strategy == 'exp_linear' else 0.0
                    rate = exp_rate + extra*elapsed
                    slope = old.param_mu_set*exp_rate + extra
                parameters[f'F{stage}'] = float(rate)
                if shapes[stage-1] == 'linear':
                    parameters[f'k{stage}'] = float(slope)
                else:
                    parameters[f'mu{stage}'] = float(slope/max(rate, 1e-12))
            # Adaptation can require clipping to this family's allowed bounds.
            parameters = {key: float(np.clip(value, *bounds[key])) for key, value in parameters.items()}
            seeds.append((f'adapted_{old.strategy}_switch_{switch:g}', parameters))
    return seeds


def validate_solution(runner, parameters, solution):
    if not np.isfinite(solution.y).all():
        raise ValueError('Non-finite native trajectory')
    raw = runner.caretaker.simulate(t=np.array([0.0, 40.0]), parameters=parameters, verbosity=50)
    raw_volume = next(state.values for state in raw if state.name == 'V')
    maximum_volume = float(np.max(raw_volume))
    if maximum_volume > reference.V_MAX + 1e-7:
        raise ValueError(f'Raw CVode volume overflow: {maximum_volume}')
    X, S, _, V = solution.y
    X0, S0, _, V0 = runner.batch.y_feed
    Y = runner.fitted.Yxs
    residual = X*V-X0*V0 + Y*(S*V-S0*V0-reference.S_IN*(V-V0))
    error = float(np.max(np.abs(residual))/max(float(np.max(X*V)), 1.0))
    if error > 1e-5:
        raise ValueError(f'Mass balance residual: {error}')
    if min(np.min(X), np.min(S), np.min(solution.y[2])) < -1e-6:
        raise ValueError('Negative physical state beyond numerical tolerance')
    return error, maximum_volume


def replay_timepoints(switch):
    """Avoid CVode restarting onto an output point at the identical root time.

    Only the requested output sample moves (by 1e-6 h); the physical event,
    feed parameters and final 40 h state are unchanged.
    """
    grid = np.linspace(0, 40, 1001)
    grid = grid[np.abs(grid-switch) > 1e-6]
    return np.unique(np.r_[grid, switch+1e-6])


def optimize_case(task, checkpoint_dir, profile_dir, source_hashes):
    index, kind, dataset_index, name = task
    started = time.monotonic()
    ds = reference.DATA[kind][dataset_index]
    strategy = reference.STRATEGIES[name]
    names = strategy['names']
    kin = reference.KINETICS[ds['organism_type']]
    bounds = strategy['bounds'](kin)
    old = pd.read_csv(BASELINE / 'feed_flow_results.csv')
    old = old[(old.model_type == kind) & (old['product'] == ds['product'])]
    seeds = seed_candidates(old, name, kin)
    runner = native.make_runner(ds, kind, name, caretaker_class=ProductCaretaker)
    candidates, searches = list(seeds), []
    for source, seed in (('caretaker_fresh', 42), ('caretaker_seeded', 43)):
        settings = dict(reference.DE_KWARGS, seed=seed)
        if source == 'caretaker_seeded':
            ordered = sorted(names, key=str.lower)
            sorted_bounds = np.array([bounds[names.index(key)] for key in ordered])
            population = qmc.scale(qmc.LatinHypercube(d=len(names), seed=seed).random(14*len(names)),
                                   sorted_bounds[:, 0], sorted_bounds[:, 1])
            informed = [parameters for _, parameters in seeds] + [candidates[-1][1]]
            for i, parameters in enumerate(informed):
                population[i] = [parameters[key] for key in ordered]
            settings['init'] = population
        params, info = runner.caretaker.estimate(unknowns=names, measurements=[], bounds=bounds,
            metric='total_product', use_global_optimizer=True, report_level=0, optimizer_kwargs=settings)
        opt = info['opt_info']
        candidates.append((source, params))
        searches.append(dict(source=source, seed=seed, nfev=int(opt.nfev), nit=int(opt.nit),
                             converged=bool(opt.success), message=str(opt.message),
                             search_total_product=-float(opt.fun)))

    for simulator in runner.caretaker.simulators.values():
        simulator.integrator_kwargs.update(rtol=1e-8, atol=1e-11)
    replay, best = [], None
    for source, parameters in candidates:
        points = replay_timepoints(parameters['t_switch'])
        solution = runner.simulate(parameters, timepoints=points)
        row = row_from_solution(kind, ds, name, parameters, runner, solution)
        replay.append(dict(case_index=index, source=source, **row))
        if best is None or row['total_product'] > best[0]['total_product']:
            best = (dict(row, case_index=index, candidate_source=source), parameters, solution)
    row, parameters, solution = best
    balance_error, raw_volume = validate_solution(runner, parameters, solution)

    # Independent LSODA/CVode check at identical settings and initial state.
    qp, fit = reference.fit_qp_model(kind, ds['mu'], ds['qp'])
    scipy = reference.simulate_fedbatch(strategy, [parameters[key] for key in names], kin, qp,
        fit, float(ds['mu'].max()*1.2), runner.batch.y_feed, 0.25, rtol=1e-8, atol=1e-11)
    if not scipy.success:
        raise RuntimeError(scipy.message)
    scipy_product = float(scipy.y[2, -1]*scipy.y[3, -1])
    difference = 100*(row['total_product']/scipy_product-1)
    if abs(difference) > 0.01:
        raise ValueError(f'Independent solver mismatch: {difference}%')
    solver = dict(case_index=index, model_type=kind, product=ds['product'], strategy=name,
                  scipy_total_product=scipy_product, pyfoomb_total_product=row['total_product'],
                  relative_difference_percent=difference, scipy_volume=float(scipy.y[3, -1]),
                  pyfoomb_volume=row['V_final'], initial_state='shared native batch endpoint',
                  rtol=1e-8, atol=1e-11)

    full_indices = np.flatnonzero(solution.y[3] >= reference.V_MAX - 1e-8)
    t_full_sample = float(solution.t[full_indices[0]]) if full_indices.size else None
    switch = parameters['t_switch']
    stage_volume = float(solution.y[3, np.argmin(np.abs(solution.t-switch))])
    row.update(second_stage_active=stage_volume < reference.V_MAX-1e-8,
               t_full_first_saved_sample=t_full_sample)
    scheduled = np.array([strategy['fn'](t, y, [parameters[key] for key in names], kin)
                          for t, y in zip(solution.t, solution.y.T)])
    scheduled = np.clip(scheduled, 0, reference.F_CAP)
    actual = np.where(solution.y[3] < reference.V_MAX-1e-8, scheduled, 0.0)
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    np.savez_compressed(Path(profile_dir) / f'{index:02d}.npz', t=solution.t, y=solution.y,
        t_batch=runner.batch.t, y_batch=runner.batch.y, t_feed=runner.batch.t_feed,
        F_scheduled=scheduled, F_actual=actual, t_switch=switch)
    diagnostics = dict(case_index=index, model_type=kind, product=ds['product'], strategy=name,
        runtime_seconds=time.monotonic()-started, objective_calls=runner.caretaker.objective_calls,
        failed_simulations=getattr(runner.caretaker, 'failed_simulations', 0),
        relative_mass_balance_error=balance_error, maximum_raw_volume=raw_volume,
        candidate_evaluations=len(replay), selected_source=row['candidate_source'])
    payload = json_safe(dict(row=row, searches=searches, diagnostics=diagnostics,
                             source_sha256=source_hashes,
                             audit=replay, solver_comparison=solver))
    target = Path(checkpoint_dir) / f'{index:02d}.json'
    temporary = target.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2))
    temporary.replace(target)
    return index, payload


def assemble(payloads, destination, provenance):
    original = pd.read_csv(BASELINE / 'feed_flow_results.csv')
    original.insert(0, 'case_index', np.arange(len(original)))
    if len(original) != 63 or original.duplicated(['model_type', 'product', 'strategy']).any():
        raise ValueError('Baseline must have 63 unique cases')
    ordered = [payloads[index] for index in sorted(payloads)]
    results = pd.concat([original, pd.DataFrame([p['row'] for p in ordered])], ignore_index=True)
    expected = {(kind, reference.DATA[kind][i]['product'], name) for _, kind, i, name in cases()}
    if len(results) != 99 or set(zip(results.model_type, results['product'], results.strategy)) != expected:
        raise ValueError('Expanded study must contain every one of the 99 unique cases')
    destination.mkdir(parents=True, exist_ok=True)
    profiles = destination / 'profiles'
    profiles.mkdir(exist_ok=True)
    for path in (BASELINE / 'profiles').glob('*.npz'):
        shutil.copy2(path, profiles / path.name)
    results.to_csv(destination / 'feed_flow_results.csv', index=False)
    best = results.loc[results.groupby(['model_type', 'product']).total_product.idxmax()].copy()
    comparison = []
    for i, winner in best.iterrows():
        group = results[results['product'] == winner['product']].sort_values('total_product', ascending=False)
        old = group[group.strategy.isin(reference.LEGACY_STRATEGIES)].iloc[0]
        new = group[group.strategy.isin(NEW_STRATEGIES)].iloc[0]
        best.loc[i, 'margin_percent'] = 100*(winner.total_product/group.iloc[1].total_product-1)
        best.loc[i, 'within_0_1_percent'] = ', '.join(group[group.total_product >= winner.total_product*0.999].strategy)
        comparison.append(dict(model_type=winner.model_type, product=winner['product'],
            previous_best_strategy=old.strategy, previous_best_product=old.total_product,
            best_new_strategy=new.strategy, best_new_product=new.total_product,
            new_vs_previous_percent=100*(new.total_product/old.total_product-1),
            overall_best_strategy=winner.strategy, overall_best_product=winner.total_product,
            overall_gain_percent=100*(winner.total_product/old.total_product-1),
            qp_unit=winner.qp_unit))
    best.to_csv(destination / 'best_per_dataset.csv', index=False)
    pd.DataFrame(comparison).to_csv(destination / 'two_stage_vs_previous.csv', index=False)
    pd.DataFrame([p['diagnostics'] for p in ordered]).to_csv(destination / 'optimization_diagnostics.csv', index=False)
    pd.DataFrame([dict(case_index=p['row']['case_index'], product=p['row']['product'],
                           strategy=p['row']['strategy'], **search) for p in ordered for search in p['searches']
                 ]).to_csv(destination / 'completed_searches.csv', index=False)
    pd.DataFrame([a for p in ordered for a in p['audit']]).to_csv(destination / 'new_candidate_audit.csv', index=False)
    pd.concat([pd.read_csv(BASELINE / 'solver_comparison.csv'),
               pd.DataFrame([p['solver_comparison'] for p in ordered])], ignore_index=True
              ).to_csv(destination / 'solver_comparison.csv', index=False)
    baseline_metadata = json.loads((BASELINE / 'run_metadata.json').read_text())
    versions = {}
    for name in ('numpy', 'scipy', 'pandas', 'matplotlib', 'assimulo'):
        versions[name] = importlib.metadata.version(name)
    metadata = dict(provenance, cases=99, retained_baseline_cases=63, new_cases=36,
        completed_new_searches=72, solver='pyFOOMB / Caretaker / Assimulo / SUNDIALS CVode',
        DE_settings=reference.DE_KWARGS, new_searches='fresh seed42 and adapted-population seed43 per case',
        final_rtol=1e-8, final_atol=1e-11, library_versions=versions,
        new_candidate_evaluations=sum(len(p['audit']) for p in ordered),
        reused_new_cases=sum('reused_checkpoint_directory' in p for p in ordered),
        new_case_code_provenance={str(p['row']['case_index']): p.get('source_sha256') for p in ordered},
        output_sampling_note='Avoid sampling exactly at a stage root; the replacement sample is 1e-6 h later. '
                             'Validated completed cases from before this sampling-only change can be retained.',
        maximum_final_volume=float(results.V_final.max()),
        maximum_raw_new_volume=max(p['diagnostics']['maximum_raw_volume'] for p in ordered),
        maximum_relative_mass_balance_error=max(baseline_metadata['maximum_relative_mass_balance_error'],
            max(p['diagnostics']['relative_mass_balance_error'] for p in ordered)),
        maximum_new_solver_difference_percent=max(abs(p['solver_comparison']['relative_difference_percent']) for p in ordered),
        stage_definition='Independent stage-start rates; stage two uses t-t_switch. Feed jumps allowed. '
                         'Nonnegative slopes/growth rates; switch time in [1,39] h. Pump stops at 4 L.',
        retained_baseline_metadata=baseline_metadata,
        comparison_note='Earlier cases retain their completed searches. New cases have two Caretaker searches '
                        'and adapted baseline candidates. Search budgets differ; scores are best found values.',
        uncertainty='Finite-budget synthetic-model study. Small margins are not evidence of statistical significance '
                    'or proven global optimality. Zero stage growth is an allowed constant-feed limit.')
    (destination / 'run_metadata.json').write_text(json.dumps(json_safe(metadata), indent=2))
    return results, best, pd.DataFrame(comparison)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--indices', help='Optional comma-separated new-case indices for a bounded run')
    parser.add_argument('--reuse-checkpoints', type=Path,
                        help='Explicitly retain validated cases from an earlier sampling-only revision')
    args = parser.parse_args()
    source_paths = [Path(__file__), Path(reference.__file__), Path(native.__file__), HERE/'pyfoomb_feed_optimization.py']
    source_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}
    baseline_hash = hashlib.sha256((BASELINE/'feed_flow_results.csv').read_bytes()).hexdigest()
    token = hashlib.sha256(json.dumps(dict(source_hashes, baseline=baseline_hash), sort_keys=True).encode()).hexdigest()[:16]
    checkpoints = OUT / 'checkpoints' / token
    checkpoints.mkdir(parents=True, exist_ok=True)
    manifest = dict(source_sha256=source_hashes, baseline_csv_sha256=baseline_hash)
    (checkpoints/'run_manifest.json').write_text(json.dumps(manifest, indent=2))
    old_manifest = None
    if args.reuse_checkpoints:
        old_manifest = json.loads((args.reuse_checkpoints/'run_manifest.json').read_text())
        if old_manifest['baseline_csv_sha256'] != baseline_hash or any(
            old_manifest['source_sha256'][name] != source_hashes[name]
            for name in ('feed_flow_optimization.py', 'pyfoomb_feed_model.py', 'pyfoomb_feed_optimization.py')):
            raise ValueError('Reused checkpoints require identical model, baseline and optimizer infrastructure')
    destination = OUT / 'final'
    profile_dir = destination / 'profiles'
    tasks = cases(NEW_STRATEGIES)
    selected = {int(index) for index in args.indices.split(',')} if args.indices else {task[0] for task in tasks}
    payloads = {}
    pending = []
    for task in tasks:
        path = checkpoints / f'{task[0]:02d}.json'
        profile = profile_dir / f'{task[0]:02d}.npz'
        if path.exists() and profile.exists():
            payloads[task[0]] = json.loads(path.read_text())
        elif args.reuse_checkpoints and (args.reuse_checkpoints/path.name).exists() and profile.exists():
            payload = json.loads((args.reuse_checkpoints/path.name).read_text())
            payload['source_sha256'] = old_manifest['source_sha256']
            payload['reused_checkpoint_directory'] = str(args.reuse_checkpoints)
            path.write_text(json.dumps(payload, indent=2))
            payloads[task[0]] = payload
        elif task[0] in selected:
            pending.append(task)
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(optimize_case, task, str(checkpoints), str(profile_dir), source_hashes) for task in pending]
        for future in as_completed(futures):
            index, payload = future.result()
            payloads[index] = payload
            row = payload['row']
            print(f"{len(payloads)}/36 {row['product']} / {row['strategy']}: {row['total_product']:.8g}", flush=True)
    if len(payloads) != 36:
        print(f'Saved {len(payloads)}/36 new-case checkpoints; resume without --indices to complete the comparison.')
        return
    provenance = dict(date='2026-10-05', baseline_directory=str(BASELINE),
                      baseline_csv_sha256=baseline_hash, source_sha256=source_hashes,
                      checkpoint_directory=str(checkpoints), elapsed_this_invocation_seconds=time.monotonic()-started)
    _, _, comparison = assemble(payloads, destination, provenance)
    print(comparison[['product', 'overall_best_strategy', 'overall_gain_percent']].to_string(index=False))
    print(f'Completed expanded study: {destination}', flush=True)


if __name__ == '__main__':
    main()
