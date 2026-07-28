"""Single-strategy presentation figure: linear-ramp feed F(t)=F0+k*t only,
across all 9 datasets. For showing the professor one strategy in isolation,
without the other 6 competing bars/lines cluttering the picture.
"""

import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from feed_flow_optimization import DATA, KINETICS, STRATEGIES, fit_qp_model, simulate_batch, simulate_fedbatch
from feed_flow_plots import HERE, MODEL_ORDER, MODEL_EDGE, MODEL_BG, flat_dataset_list

STRAT_NAME = 'linear_ramp'


def main():
    df = pd.read_csv(os.path.join(HERE, 'feed_flow_results.csv'))
    strat = STRATEGIES[STRAT_NAME]

    fig, axes = plt.subplots(3, 3, figsize=(19, 13))
    fig.suptitle(
        'Linear-Ramp Feed Strategy  --  F(t) = F0 + k·t\n'
        'per-product optimised parameters, full batch + fed-batch time course',
        fontsize=17, fontweight='bold', y=0.995,
    )

    datasets = flat_dataset_list()
    for col, mtype in enumerate(MODEL_ORDER):
        rows = [d for d in datasets if d[0] == mtype]
        for row, (_, ds) in enumerate(rows):
            ax = axes[row, col]
            r = df[(df['product'] == ds['product']) & (df['strategy'] == STRAT_NAME)].iloc[0]

            kin = KINETICS[ds['organism_type']]
            qp_fn, qp_params = fit_qp_model(mtype, ds['mu'], ds['qp'])
            mu_cap = ds['mu'].max() * 1.2
            t_feed, y_feed, batch_sol = simulate_batch(kin, qp_fn, qp_params, mu_cap)
            params = np.array([r[f'param_{n}'] for n in strat['names']])
            sol = simulate_fedbatch(strat, params, kin, qp_fn, qp_params, mu_cap, y_feed, strat['max_step'])

            t_all = np.concatenate([batch_sol.t, sol.t + t_feed])
            X_all = np.concatenate([batch_sol.y[0], sol.y[0]])
            S_all = np.concatenate([batch_sol.y[1], sol.y[1]])
            P_all = np.concatenate([batch_sol.y[2], sol.y[2]])
            V_all = np.concatenate([batch_sol.y[3], sol.y[3]])

            ax2 = ax.twinx()
            l1, = ax.plot(t_all, X_all, color='#1b5e20', lw=2, label='Biomass X [g/L]')
            l2, = ax.plot(t_all, S_all, color='#b71c1c', lw=2, ls='--', label='Substrate S [g/L]')
            l3, = ax2.plot(t_all, P_all * V_all, color=MODEL_EDGE[mtype], lw=2.3, label='Total product')
            ax.axvline(t_feed, color='gray', lw=1, ls=':')

            ax.set_facecolor(MODEL_BG[mtype])
            ax.set_xlabel('Time (h)', fontsize=9)
            ax.set_ylabel('X, S (g/L)', fontsize=9)
            ax2.set_ylabel(f"Total product ({ds['qp_unit'].split('/')[0]})", fontsize=8.5, color=MODEL_EDGE[mtype])
            ax2.tick_params(axis='y', labelcolor=MODEL_EDGE[mtype])
            ax.set_title(
                f"{ds['product']} ({ds['organism_type']})\n"
                f"F0={r['param_F0']:.4f} L/h, k={r['param_k']:.4f} L/h²",
                fontsize=9.5, fontweight='bold', pad=6,
            )
            ax.legend([l1, l2, l3], [l.get_label() for l in [l1, l2, l3]],
                      loc='upper center', bbox_to_anchor=(0.5, -0.18), ncol=3, fontsize=7.5)
            ax.grid(True, alpha=0.3)

        axes[0, col].annotate(
            {'linear': 'LINEAR qp(μ)', 'bell_shaped': 'BELL-SHAPED qp(μ)', 'hyperbolic': 'HYPERBOLIC qp(μ)'}[mtype],
            xy=(0.5, 1.38), xycoords='axes fraction', fontsize=13, fontweight='bold', ha='center',
            color=MODEL_EDGE[mtype],
            bbox=dict(boxstyle='round,pad=0.4', facecolor=MODEL_BG[mtype], edgecolor=MODEL_EDGE[mtype], linewidth=2),
        )

    plt.tight_layout(rect=[0, 0, 1, 0.91])
    plt.subplots_adjust(hspace=0.75, wspace=0.4, top=0.83)
    out = os.path.join(HERE, 'feed_flow_linear_ramp_only.png')
    fig.savefig(out, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f"Saved {out}")


if __name__ == '__main__':
    main()
