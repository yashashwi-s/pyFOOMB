"""Render the expanded native study from saved result rows and trajectories."""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/pyfoomb-feed-matplotlib')
os.environ.setdefault('XDG_CACHE_HOME', '/tmp/pyfoomb-feed-cache')

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import feed_flow_optimization as reference
from plot_pyfoomb_results import (
    STRATEGY_ORDER, STRATEGY_LABELS, MODEL_BG, MODEL_LABELS,
    _dataset_grid, _case_index, _profile, _unit_for_row,
    plot_strategy_comparison, plot_profiles,
)

OUT = Path(__file__).resolve().parent / 'pyfoomb_results/two_stage_extension/final'
NEW = tuple(reference.TWO_STAGE_SHAPES)
COLORS = dict(zip(NEW, ('#1877B8', '#D1495B', '#149C95', '#8B5DA8')))
COLORS.update(two_stage='#DA9A00', previous_best='#37474F')


def save(fig, filename):
    fig.savefig(OUT / filename, dpi=180, bbox_inches='tight', facecolor='white')
    plt.close(fig)


def schematics():
    fig, axes = plt.subplots(1, 5, figsize=(18, 3.7), sharex=True, sharey=True)
    common = dict(F1=.035, F2=.04, k1=.003, k2=.0015, mu1=.07, mu2=.05, t_switch=18.)
    t = np.unique(np.r_[np.linspace(0, 40, 801), 17.999, 18])
    for ax, name in zip(axes, ('two_stage', *NEW)):
        strategy = reference.STRATEGIES[name]
        parameters = [common[key] for key in strategy['names']]
        F = [strategy['fn'](value, None, parameters, None) for value in t]
        ax.plot(t, F, color=COLORS[name], lw=2.6)
        ax.axvline(18, color='#78909C', ls='--', lw=1)
        ax.axvspan(18, 40, color='#E8F1F5', alpha=.6)
        ax.set_title(STRATEGY_LABELS[name], fontsize=12, fontweight='bold')
        ax.set_xlabel('Time since feed start (h)', fontsize=9)
        ax.grid(alpha=.25)
    axes[0].set_ylabel('Feed rate (L/h)', fontsize=10)
    fig.suptitle('Two-stage feed families | illustrative settings', fontweight='bold', fontsize=15)
    fig.text(.5, -.01, 'Stage 2 uses its own start rate and local time; the switch can change the feed rate.',
             ha='center', fontsize=10)
    fig.tight_layout()
    save(fig, 'two_stage_schematics.png')


def heatmap(results):
    products = [reference.DATA[kind][i]['product'] for kind in reference.DATA for i in range(3)]
    values = results.pivot(index='product', columns='strategy', values='total_product').reindex(
        index=products, columns=STRATEGY_ORDER)
    relative = values.div(values.max(axis=1), axis=0)*100
    fig, ax = plt.subplots(figsize=(16.5, 7.0))
    im = ax.imshow(relative, vmin=50, vmax=100, cmap='YlGnBu', aspect='auto')
    ax.set_xticks(range(len(STRATEGY_ORDER)), [STRATEGY_LABELS[s] for s in STRATEGY_ORDER], rotation=35, ha='right')
    ax.set_yticks(range(len(products)), products)
    for i in range(len(products)):
        for j in range(len(STRATEGY_ORDER)):
            value = relative.iloc[i, j]
            ax.text(j, i, f'{value:.1f}', ha='center', va='center', fontsize=8,
                    color='white' if value > 85 else '#102A43')
    ax.axvline(6.5, color='white', lw=3)
    ax.set_title('Total product relative to the best found for each dataset (%)', fontweight='bold', pad=15)
    fig.colorbar(im, ax=ax, label='Within-dataset performance (%)', shrink=.85)
    fig.tight_layout()
    save(fig, 'relative_performance_heatmap.png')


def compare_to_previous(results):
    products = [reference.DATA[kind][i]['product'] for kind in reference.DATA for i in range(3)]
    legacy = results[results.strategy.isin(reference.LEGACY_STRATEGIES)].groupby('product').total_product.max()
    values = results[results.strategy.isin(NEW)].pivot(index='product', columns='strategy', values='total_product')
    gain = (values.div(legacy, axis=0)-1)*100
    gain = gain.reindex(index=products, columns=NEW)
    fig, ax = plt.subplots(figsize=(10.7, 6.7))
    limit = max(float(np.abs(gain.to_numpy()).max()), .01)
    im = ax.imshow(gain, cmap='RdBu', vmin=-limit, vmax=limit, aspect='auto')
    ax.set_xticks(range(4), [STRATEGY_LABELS[s] for s in NEW], rotation=20, ha='right')
    ax.set_yticks(range(9), products)
    for i in range(9):
        for j in range(4):
            value = gain.iloc[i, j]
            ax.text(j, i, f'{value:+.3f}%', ha='center', va='center', fontsize=9,
                    color='white' if abs(value) > .6*limit else '#102A43')
    ax.set_title('New two-stage strategies versus the earlier best\nchange in total product at the same reactor limits',
                 fontweight='bold', pad=15)
    fig.colorbar(im, ax=ax, label='Change versus earlier best (%)', shrink=.85)
    fig.tight_layout()
    save(fig, 'two_stage_vs_previous.png')


def trajectory_comparison(results, quantity):
    grid = _dataset_grid(results)
    fig, axes = plt.subplots(3, 3, figsize=(18.5, 12.3))
    for ax, pair in zip(axes.flat, [pair for row in grid for pair in row]):
        kind, product = pair
        sub = results[(results.model_type == kind) & (results['product'] == product)]
        previous = sub[sub.strategy.isin(reference.LEGACY_STRATEGIES)].sort_values('total_product', ascending=False).iloc[0]
        ax.set_facecolor(MODEL_BG[kind])
        series = [(name, name) for name in NEW] + [('two_stage', 'two_stage'), (previous.strategy, 'previous_best')]
        for name, label in series:
            index = _case_index(results, kind, product, name)
            path = OUT/'profiles'/f'{index:02d}.npz'
            with np.load(path) as profile:
                t, y = profile['t'], profile['y']
                if quantity == 'feed':
                    if 'F_actual' in profile.files:
                        values = profile['F_actual']
                    else:
                        row = sub[sub.strategy == name].iloc[0]
                        strategy = reference.STRATEGIES[name]
                        params = [float(row[f'param_{key}']) for key in strategy['names']]
                        kin = reference.KINETICS[row.organism]
                        scheduled = np.array([strategy['fn'](value, state, params, kin) for value, state in zip(t, y.T)])
                        values = np.where(y[3] < reference.V_MAX-1e-8, np.clip(scheduled, 0, reference.F_CAP), 0)
                else:
                    values = y[2]*y[3]
            ax.plot(t, values, color=COLORS[label], lw=1.8 if label in NEW else 1.5,
                    ls='--' if label == 'previous_best' else ':' if label == 'two_stage' else '-',
                    alpha=.95)
        ax.set_title(f'{product}\n{MODEL_LABELS[kind]}', fontsize=10, fontweight='bold')
        ax.set_xlabel('Time since feed start (h)', fontsize=9)
        ax.set_ylabel('Actual feed rate (L/h)' if quantity == 'feed' else f'Total product ({_unit_for_row(sub.iloc[0])})', fontsize=9)
        ax.grid(alpha=.25)
    from matplotlib.lines import Line2D
    labels = [*NEW, 'two_stage', 'previous_best']
    handles = [Line2D([], [], color=COLORS[name], lw=2,
                      ls='--' if name == 'previous_best' else ':' if name == 'two_stage' else '-') for name in labels]
    names = [STRATEGY_LABELS.get(name, 'Earlier best') for name in labels]
    fig.legend(handles, names, loc='lower center', ncol=6, bbox_to_anchor=(.5, -.005), fontsize=11, frameon=False)
    fig.suptitle('Optimized actual feed profiles' if quantity == 'feed' else 'Product accumulation: two-stage strategies and earlier best',
                 fontsize=16, fontweight='bold', y=.995)
    fig.text(.5, .958, 'The pump stops when the vessel reaches 4 L; curves use the saved native trajectories.',
             ha='center', fontsize=10, color='#455A64')
    fig.tight_layout(rect=[0, .035, 1, .945], h_pad=2.0, w_pad=2.0)
    save(fig, f'two_stage_{quantity}_profiles.png')


def volumes(results):
    fig, ax = plt.subplots(figsize=(12, 4.2))
    for name in STRATEGY_ORDER:
        rows = results[results.strategy == name]
        ax.scatter(rows.case_index, rows.V_final, s=25, label=STRATEGY_LABELS[name], alpha=.85)
    ax.axhline(4, color='#D1495B', lw=1.8, ls='--', label='4 L ceiling')
    ax.axvline(62.5, color='#78909C', ls=':', lw=1)
    ax.set_ylim(min(3.5, results.V_final.min()-.05), 4.08)
    ax.set_xlabel('Case index | earlier cases 0–62, new cases 63–98')
    ax.set_ylabel('Final vessel volume (L)')
    ax.set_title('Working-volume check for all 99 native trajectories', fontweight='bold')
    ax.grid(axis='y', alpha=.25)
    ax.legend(ncol=4, loc='upper center', bbox_to_anchor=(.5, -.25), frameon=False, fontsize=8)
    fig.tight_layout()
    save(fig, 'volume_validation.png')


def main():
    results = pd.read_csv(OUT/'feed_flow_results.csv')
    best = pd.read_csv(OUT/'best_per_dataset.csv')
    if len(results) != 99:
        raise ValueError('Expected a complete 99-case expanded study')
    plot_strategy_comparison(OUT, results)
    plot_profiles(OUT, results, best, None, 'best_profiles.png', 'Best found strategy per dataset | 11 feed families')
    for name in NEW:
        plot_profiles(OUT, results, best, name, f'{name}_profiles.png', f'{STRATEGY_LABELS[name]} | batch and fed-batch trajectories')
    schematics()
    heatmap(results)
    compare_to_previous(results)
    trajectory_comparison(results, 'feed')
    trajectory_comparison(results, 'product')
    volumes(results)
    print(f'Saved 12 figures in {OUT}')


if __name__ == '__main__':
    main()
