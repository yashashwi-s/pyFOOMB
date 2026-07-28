"""Optimise one additional feed-flow strategy against all 9 datasets and merge
it into the existing feed_flow_results.csv / feed_flow_best_per_dataset.csv,
without re-running the other (already-optimised) strategies."""

import os
import sys

import numpy as np
import pandas as pd

from feed_flow_optimization import (
    DATA, KINETICS, STRATEGIES, DE_KWARGS, HERE,
    fit_qp_model, simulate_batch, simulate_fedbatch, objective, mean_mu, summarise,
)
from scipy.optimize import differential_evolution


def run_one_strategy(strat_name):
    strat = STRATEGIES[strat_name]
    rows = []
    for mtype in ['linear', 'bell_shaped', 'hyperbolic']:
        for ds in DATA[mtype]:
            kin = KINETICS[ds['organism_type']]
            qp_fn, qp_params = fit_qp_model(mtype, ds['mu'], ds['qp'])
            mu_cap = ds['mu'].max() * 1.2
            t_feed, y_feed, _ = simulate_batch(kin, qp_fn, qp_params, mu_cap)

            bounds = strat['bounds'](kin)
            res = differential_evolution(
                objective, bounds,
                args=(strat, kin, qp_fn, qp_params, mu_cap, y_feed, strat['max_step']),
                **DE_KWARGS,
            )
            sol = simulate_fedbatch(strat, res.x, kin, qp_fn, qp_params, mu_cap, y_feed, strat['max_step'])
            Xf, Sf, Pf, Vf = sol.y[:, -1]
            row = dict(
                model_type=mtype, product=ds['product'], organism=ds['organism_type'],
                reference=ds['reference'], strategy=strat_name,
                total_product=Pf * Vf, P_final=Pf, V_final=Vf, X_final=Xf, S_final=Sf,
                avg_mu=mean_mu(sol, kin), t_feed=t_feed, qp_unit=ds['qp_unit'],
            )
            for name, val in zip(strat['names'], res.x):
                row[f'param_{name}'] = val
            rows.append(row)
            print(f"{ds['product']:<38s} {strat_name:<14s} total_product={row['total_product']:.3f}")
    return pd.DataFrame(rows)


def main(strat_name):
    results_path = os.path.join(HERE, 'feed_flow_results.csv')
    df = pd.read_csv(results_path)
    df = df[df['strategy'] != strat_name]  # drop any stale run of this strategy
    new_rows = run_one_strategy(strat_name)
    df = pd.concat([df, new_rows], ignore_index=True)
    df.to_csv(results_path, index=False)
    print(f"\nMerged {len(new_rows)} rows for '{strat_name}' into {results_path} ({len(df)} total rows)")

    best = summarise(df)
    best.to_csv(os.path.join(HERE, 'feed_flow_best_per_dataset.csv'), index=False)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'exp_linear')
