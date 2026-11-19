"""Reproduce the feed study with the volume-stop fix, in separate processes.

Uses the original DE settings and seed. Old outputs are retained in archive/.
Checkpoints permit interrupted runs to resume without repeating finished fits.
"""
import json
import hashlib
import os
import shutil
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
from scipy.optimize import differential_evolution

import feed_flow_optimization as opt

HERE = Path(__file__).resolve().parent
SOURCE_HASH = hashlib.sha256(Path(opt.__file__).read_bytes()).hexdigest()[:12]
CHECKPOINTS = HERE / 'tmp' / ('corrected_sweep_' + SOURCE_HASH)


def run_one(task):
    index, kind, dataset_index, name = task
    ds = opt.DATA[kind][dataset_index]
    kin = opt.KINETICS[ds['organism_type']]
    fn, fitted = opt.fit_qp_model(kind, ds['mu'], ds['qp'])
    cap = ds['mu'].max() * 1.2
    t_feed, y_feed, _ = opt.simulate_batch(kin, fn, fitted, cap)
    strategy = opt.STRATEGIES[name]
    result = differential_evolution(
        opt.objective, strategy['bounds'](kin),
        args=(strategy, kin, fn, fitted, cap, y_feed, strategy['max_step']),
        **opt.DE_KWARGS,
    )
    sol = opt.simulate_fedbatch(strategy, result.x, kin, fn, fitted, cap,
                                y_feed, strategy['max_step'])
    if not sol.success:
        raise RuntimeError(f'{ds["product"]}/{name}: {sol.message}')
    X, S, P, V = sol.y[:, -1]
    row = dict(model_type=kind, product=ds['product'], organism=ds['organism_type'],
               reference=ds['reference'], strategy=name, total_product=P * V,
               P_final=P, V_final=V, X_final=X, S_final=S,
               avg_mu=opt.mean_mu(sol, kin), t_feed=t_feed, qp_unit=ds['qp_unit'])
    row.update({f'param_{key}': float(value)
                for key, value in zip(strategy['names'], result.x)})
    row = {key: value.item() if hasattr(value, 'item') else value
           for key, value in row.items()}
    diagnostics = dict(source_hash=SOURCE_HASH, nfev=int(result.nfev), nit=int(result.nit),
                       converged=bool(result.success), message=str(result.message))
    (CHECKPOINTS / f'{index:02d}.json').write_text(
        json.dumps(dict(row=row, diagnostics=diagnostics), indent=2))
    return index, row


def main():
    archive = HERE / 'archive' / 'pre_volume_fix'
    archive.mkdir(parents=True, exist_ok=True)
    for name in ('feed_flow_results.csv', 'feed_flow_best_per_dataset.csv',
                 'feed_flow_strategy_comparison.png', 'feed_flow_best_profiles.png',
                 'feed_flow_linear_ramp_only.png', 'feed_flow_optimization_notes.md',
                 'presentation.tex', 'presentation.pdf'):
        source = HERE / name
        if source.exists() and not (archive / name).exists():
            shutil.copy2(source, archive / name)
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    tasks = []
    for kind, datasets in opt.DATA.items():
        for i in range(len(datasets)):
            for name in opt.STRATEGIES:
                tasks.append((len(tasks), kind, i, name))
    rows = {}
    pending = []
    for task in tasks:
        checkpoint = CHECKPOINTS / f'{task[0]:02d}.json'
        if checkpoint.exists():
            rows[task[0]] = json.loads(checkpoint.read_text())['row']
        else:
            pending.append(task)
    start = time.monotonic()
    with ProcessPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(run_one, task) for task in pending]
        for future in as_completed(futures):
            index, row = future.result()
            rows[index] = row
            print(f'{len(rows)}/{len(tasks)} {row["product"]} / {row["strategy"]}: '
                  f'V={row["V_final"]:.6f}, product={row["total_product"]:.3f}',
                  flush=True)
    frame = pd.DataFrame([rows[i] for i in range(len(tasks))])
    assert len(frame) == 63 and frame['V_final'].max() < opt.V_MAX + 0.001
    frame.to_csv(HERE / 'feed_flow_results.csv', index=False)
    best = opt.summarise(frame)
    best.to_csv(HERE / 'feed_flow_best_per_dataset.csv', index=False)
    print(f'Completed in {time.monotonic() - start:.1f}s', flush=True)


if __name__ == '__main__':
    main()
