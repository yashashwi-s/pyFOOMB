"""
Plots for the feed-flow (F(t)) strategy optimisation results.

Reads the CSV output of `feed_flow_optimization.py` and produces:
  1. feed_flow_strategy_comparison.png -- 3x3 bar chart, total product per
     strategy for every dataset, winning strategy highlighted.
  2. feed_flow_best_profiles.png -- 3x3 time-course plot (X, S, P, F, mu) of
     the winning strategy for every dataset.

Re-simulating the 9 winning trajectories is cheap (no optimisation, just a
single forward integration each), so this script does not need to re-run the
~45-minute differential_evolution sweep.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from feed_flow_optimization import (
    DATA, KINETICS, STRATEGIES, T_FEDBATCH,
    fit_qp_model, simulate_batch, simulate_fedbatch,
)

HERE = os.path.dirname(os.path.abspath(__file__))

STRATEGY_ORDER = ['constant', 'exponential', 'linear_ramp', 'two_stage', 'pulsed', 'feedback_control']
STRATEGY_LABELS = {
    'constant': 'Constant', 'exponential': 'Exponential', 'linear_ramp': 'Linear ramp',
    'two_stage': 'Two-stage', 'pulsed': 'Pulsed', 'feedback_control': 'Feedback',
}
MODEL_ORDER = ['linear', 'bell_shaped', 'hyperbolic']
MODEL_EDGE = {'linear': '#1565C0', 'bell_shaped': '#E65100', 'hyperbolic': '#2E7D32'}
MODEL_BG = {'linear': '#E3F2FD', 'bell_shaped': '#FFF3E0', 'hyperbolic': '#E8F5E9'}


def flat_dataset_list():
    """(model_type, dataset_dict) for all 9 datasets, in the same row order used elsewhere."""
    out = []
    for mtype in MODEL_ORDER:
        for ds in DATA[mtype]:
            out.append((mtype, ds))
    return out


def plot_strategy_comparison(df):
    fig, axes = plt.subplots(3, 3, figsize=(19, 13))
    fig.suptitle(
        'Total Product Formed per Feed-Flow Strategy\n'
        '(fixed 40 h fed-batch phase, shared reactor/feed constraints, best strategy starred)',
        fontsize=16, fontweight='bold', y=0.995,
    )

    datasets = flat_dataset_list()
    for col, mtype in enumerate(MODEL_ORDER):
        rows = [d for d in datasets if d[0] == mtype]
        for row, (_, ds) in enumerate(rows):
            ax = axes[row, col]
            ax.set_facecolor(MODEL_BG[mtype])
            sub = df[df['product'] == ds['product']].set_index('strategy').loc[STRATEGY_ORDER]
            values = sub['total_product'].values
            best_i = int(np.argmax(values))

            colors = [MODEL_EDGE[mtype] if i == best_i else '#B0BEC5' for i in range(len(values))]
            bars = ax.bar(range(len(values)), values, color=colors, edgecolor='white')
            bars[best_i].set_edgecolor('black')
            bars[best_i].set_linewidth(1.5)

            ax.set_xticks(range(len(values)))
            ax.set_xticklabels([STRATEGY_LABELS[s] for s in STRATEGY_ORDER], rotation=35, ha='right', fontsize=8)
            ax.set_title(f"{ds['product']}\n({ds['organism_type']})", fontsize=10, fontweight='bold', pad=6)
            ax.set_ylabel(f"Total product ({ds['qp_unit'].replace('/(g*h)', '')})", fontsize=8)
            ax.text(
                best_i, values[best_i], ' best', fontsize=8, fontweight='bold',
                ha='left', va='bottom', color='black',
            )
            ax.grid(True, axis='y', alpha=0.3)

        axes[0, col].annotate(
            {'linear': 'LINEAR', 'bell_shaped': 'BELL-SHAPED', 'hyperbolic': 'HYPERBOLIC'}[mtype],
            xy=(0.5, 1.28), xycoords='axes fraction', fontsize=14, fontweight='bold', ha='center',
            color=MODEL_EDGE[mtype],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=MODEL_BG[mtype], edgecolor=MODEL_EDGE[mtype], linewidth=2),
        )

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.subplots_adjust(hspace=0.65, wspace=0.35, top=0.84)
    out = os.path.join(HERE, 'feed_flow_strategy_comparison.png')
    fig.savefig(out, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"Saved {out}")


def resimulate_best(best_row):
    """Re-run batch + fed-batch phase for one dataset using its winning strategy's
    already-optimised parameters, returning the fed-batch solution and time series."""
    mtype = best_row['model_type']
    product = best_row['product']
    ds = next(d for d in DATA[mtype] if d['product'] == product)
    kin = KINETICS[ds['organism_type']]
    qp_fn, qp_params = fit_qp_model(mtype, ds['mu'], ds['qp'])
    mu_cap = ds['mu'].max() * 1.2

    t_feed, y_feed, batch_sol = simulate_batch(kin, qp_fn, qp_params, mu_cap)

    strat_name = best_row['strategy']
    strat = STRATEGIES[strat_name]
    params = np.array([best_row[f'param_{n}'] for n in strat['names']])

    sol = simulate_fedbatch(strat, params, kin, qp_fn, qp_params, mu_cap, y_feed, strat['max_step'])
    return ds, kin, qp_fn, qp_params, mu_cap, t_feed, batch_sol, sol, strat_name, params


def plot_best_profiles(best_df):
    fig, axes = plt.subplots(3, 3, figsize=(20, 14))
    fig.suptitle(
        'Winning Feed-Flow Strategy per Dataset -- Full Batch + Fed-Batch Time Course',
        fontsize=17, fontweight='bold', y=0.995,
    )

    datasets = flat_dataset_list()
    for col, mtype in enumerate(MODEL_ORDER):
        rows = [d for d in datasets if d[0] == mtype]
        for row, (_, ds) in enumerate(rows):
            ax = axes[row, col]
            best_row = best_df[best_df['product'] == ds['product']].iloc[0]
            (ds_, kin, qp_fn, qp_params, mu_cap, t_feed, batch_sol, sol,
             strat_name, params) = resimulate_best(best_row)

            t_batch = batch_sol.t
            t_fed = sol.t + t_feed
            t_all = np.concatenate([t_batch, t_fed])
            X_all = np.concatenate([batch_sol.y[0], sol.y[0]])
            S_all = np.concatenate([batch_sol.y[1], sol.y[1]])
            P_all = np.concatenate([batch_sol.y[2], sol.y[2]])
            V_all = np.concatenate([batch_sol.y[3], sol.y[3]])

            ax2 = ax.twinx()
            l1, = ax.plot(t_all, X_all, color='#1b5e20', lw=2, label='X [g/L]')
            l2, = ax.plot(t_all, S_all, color='#b71c1c', lw=2, ls='--', label='S [g/L]')
            l3, = ax2.plot(t_all, P_all * V_all, color=MODEL_EDGE[mtype], lw=2.2, label='Total P [unit]')
            l4, = ax2.plot(t_all, V_all * 20, color='#6a1b9a', lw=1.3, ls=':', label='V [L] (x20)')

            ax.axvline(t_feed, color='gray', lw=1, ls=':')
            ax.set_xlabel('Time (h)', fontsize=9)
            ax.set_ylabel('X, S (g/L)', fontsize=9)
            ax2.set_ylabel('Total product (right)', fontsize=9, color=MODEL_EDGE[mtype])
            ax2.tick_params(axis='y', labelcolor=MODEL_EDGE[mtype])
            ax.set_title(
                f"{ds['product']} ({ds['organism_type']})\nwinner: {STRATEGY_LABELS[strat_name]}",
                fontsize=10, fontweight='bold', pad=6,
            )
            lines = [l1, l2, l3, l4]
            ax.legend(lines, [l.get_label() for l in lines], loc='upper center',
                      bbox_to_anchor=(0.5, -0.18), ncol=2, fontsize=7.5)
            ax.grid(True, alpha=0.3)

        axes[0, col].annotate(
            {'linear': 'LINEAR', 'bell_shaped': 'BELL-SHAPED', 'hyperbolic': 'HYPERBOLIC'}[mtype],
            xy=(0.5, 1.38), xycoords='axes fraction', fontsize=14, fontweight='bold', ha='center',
            color=MODEL_EDGE[mtype],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=MODEL_BG[mtype], edgecolor=MODEL_EDGE[mtype], linewidth=2),
        )

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    plt.subplots_adjust(hspace=0.75, wspace=0.4, top=0.82)
    out = os.path.join(HERE, 'feed_flow_best_profiles.png')
    fig.savefig(out, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"Saved {out}")


def main():
    df = pd.read_csv(os.path.join(HERE, 'feed_flow_results.csv'))
    best_df = pd.read_csv(os.path.join(HERE, 'feed_flow_best_per_dataset.csv'))
    plot_strategy_comparison(df)
    plot_best_profiles(best_df)


if __name__ == '__main__':
    main()
