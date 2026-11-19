"""Plot saved native pyFOOMB feed-flow results.

This module only reads result files.  In particular, profile plots use the
saved ``profiles/*.npz`` trajectories and never rerun a model or optimiser.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


STRATEGY_ORDER = [
    "constant", "exponential", "linear_ramp", "exp_linear",
    "two_stage", "pulsed", "feedback_control",
    "two_stage_linear_exp", "two_stage_exp_linear",
    "two_stage_exp_exp", "two_stage_linear_linear",
]
STRATEGY_LABELS = {
    "constant": "Constant", "exponential": "Exponential",
    "linear_ramp": "Linear ramp", "exp_linear": "Exp + linear",
    "two_stage": "Const → const", "pulsed": "Pulsed",
    "feedback_control": "Feedback",
    "two_stage_linear_exp": "Linear → exp",
    "two_stage_exp_linear": "Exp → linear",
    "two_stage_exp_exp": "Exp → exp",
    "two_stage_linear_linear": "Linear → linear",
}
MODEL_ORDER = ["linear", "bell_shaped", "hyperbolic"]
MODEL_LABELS = {"linear": "LINEAR", "bell_shaped": "BELL-SHAPED", "hyperbolic": "HYPERBOLIC"}
MODEL_EDGE = {"linear": "#1565C0", "bell_shaped": "#E65100", "hyperbolic": "#2E7D32"}
MODEL_BG = {"linear": "#E3F2FD", "bell_shaped": "#FFF3E0", "hyperbolic": "#E8F5E9"}


def _ordered_datasets(df: pd.DataFrame):
    """Return model/product pairs in the saved study order."""
    seen = set()
    result = []
    for row in df[["model_type", "product"]].itertuples(index=False):
        key = (row.model_type, row.product)
        if key not in seen:
            seen.add(key)
            result.append(key)
    return result


def _dataset_grid(df: pd.DataFrame):
    """Return a row-major grid with model families in columns."""
    grouped = {model: [pair for pair in _ordered_datasets(df) if pair[0] == model] for model in MODEL_ORDER}
    grouped.update({model: [pair for pair in _ordered_datasets(df) if pair[0] == model]
                    for model in set(df.model_type) if model not in grouped})
    models = [model for model in MODEL_ORDER if grouped.get(model)] + [model for model in grouped if model not in MODEL_ORDER and grouped[model]]
    nrows = max((len(grouped[model]) for model in models), default=0)
    return [[grouped[model][row] if row < len(grouped[model]) else None for model in models]
            for row in range(nrows)]


def _unit_for_row(row) -> str:
    for name in ("product_unit", "qp_unit", "unit"):
        if name in row.index and pd.notna(row[name]):
            value = str(row[name])
            return value.replace("/(g*h)", "").strip()
    return "product units"


def _case_index(results: pd.DataFrame, model_type: str, product: str, strategy: str) -> int:
    matches = results.index[
        (results.model_type == model_type)
        & (results["product"] == product)
        & (results.strategy == strategy)
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one saved row for {model_type}/{product}/{strategy}; found {len(matches)}")
    return int(results.loc[matches[0], "case_index"]) if "case_index" in results else int(matches[0])


def _profile(results_dir: Path, case_index: int):
    path = results_dir / "profiles" / f"{case_index:02d}.npz"
    if not path.exists():
        raise FileNotFoundError(f"Missing required native pyFOOMB profile: {path}")
    with np.load(path) as data:
        required = {"t", "y", "t_batch", "y_batch", "t_feed"}
        missing = required.difference(data.files)
        if missing:
            raise ValueError(f"{path} is missing arrays: {sorted(missing)}")
        return {name: data[name] for name in required}


def _series(profile):
    """Join batch and feed phases, accepting either (4, n) or (n, 4) y arrays."""
    def orient(y):
        y = np.asarray(y)
        return y if y.shape[0] == 4 else y.T

    t_batch = np.asarray(profile["t_batch"], dtype=float)
    t_feed = float(np.asarray(profile["t_feed"]).reshape(-1)[0])
    t_fed = np.asarray(profile["t"], dtype=float)
    y_batch = orient(profile["y_batch"])
    y_fed = orient(profile["y"])
    return (np.concatenate([t_batch, t_fed + t_feed]),
            np.concatenate([y_batch, y_fed], axis=1), t_feed)


def _style_panel(ax, model_type):
    ax.set_facecolor(MODEL_BG.get(model_type, "#F5F5F5"))
    ax.grid(True, axis="y", alpha=0.3)


def plot_strategy_comparison(results_dir: Path, results: pd.DataFrame):
    grid = _dataset_grid(results)
    nrows, ncols = max(1, len(grid)), max(1, len(grid[0]) if grid else 1)
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.2 * ncols, 4.1 * nrows), squeeze=False)
    fig.suptitle("Total product by feed strategy | native pyFOOMB/CVode",
                 fontsize=16, fontweight="bold", y=0.995)
    for i, dataset in enumerate([item for row in grid for item in row]):
        if dataset is None:
            continue
        model, product = dataset
        ax = axes.flat[i]
        _style_panel(ax, model)
        sub = results[(results.model_type == model) & (results["product"] == product)].set_index("strategy")
        order = [s for s in STRATEGY_ORDER if s in sub.index] + [s for s in sub.index if s not in STRATEGY_ORDER]
        values = sub.loc[order, "total_product"].to_numpy(float)
        unit = _unit_for_row(sub.iloc[0])
        best = int(np.argmax(values))
        bars = ax.bar(range(len(order)), values,
                      color=[MODEL_EDGE.get(model, "#455A64") if j == best else "#B0BEC5" for j in range(len(order))],
                      edgecolor="white")
        bars[best].set_edgecolor("black")
        bars[best].set_linewidth(1.4)
        ax.set_xticks(range(len(order)))
        ax.set_xticklabels([STRATEGY_LABELS.get(s, s) for s in order], rotation=35, ha="right", fontsize=8)
        ax.set_title(f"{product}\n{MODEL_LABELS.get(model, model)}", fontsize=10, fontweight="bold")
        ax.set_ylabel(f"Total product ({unit})", fontsize=8)
        
    for ax, dataset in zip(axes.flat, [item for row in grid for item in row]):
        if dataset is None:
            ax.remove()
    fig.tight_layout()
    fig.savefig(results_dir / "strategy_comparison.png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_profiles(results_dir: Path, results: pd.DataFrame, best: pd.DataFrame, strategy: str | None, filename: str, title: str):
    grid = _dataset_grid(results)
    nrows, ncols = max(1, len(grid)), max(1, len(grid[0]) if grid else 1)
    fig, axes = plt.subplots(nrows, ncols, figsize=(6.2 * ncols, 4.3 * nrows), squeeze=False)
    fig.suptitle(title,
                 fontsize=16, fontweight="bold", y=0.995)
    for i, dataset in enumerate([item for row in grid for item in row]):
        if dataset is None:
            continue
        model, product = dataset
        ax = axes.flat[i]
        row = best[(best.model_type == model) & (best["product"] == product)]
        if strategy is None:
            chosen = str(row.iloc[0].strategy)
        else:
            chosen = strategy
        index = _case_index(results, model, product, chosen)
        profile = _profile(results_dir, index)
        _style_panel(ax, model)
        t, y, t_feed = _series(profile)
        ax2 = ax.twinx()
        l1, = ax.plot(t, y[0], color="#1B5E20", lw=1.9, label="X [g/L]")
        l2, = ax.plot(t, y[1], color="#B71C1C", lw=1.9, ls="--", label="S [g/L]")
        row_unit = _unit_for_row(row.iloc[0])
        l3, = ax2.plot(t, y[2], color=MODEL_EDGE.get(model, "#455A64"), lw=2.1,
                       label=f"P [{row_unit}/L]")
        # Volume has its own small inset because it is not commensurate with P.
        inset = ax.inset_axes([.68, .13, .27, .25])
        inset.plot(t, y[3], color="#6A1B9A", lw=1.1)
        inset.set_ylim(1, 4.05)
        inset.set_title("V [L]", fontsize=6, pad=1)
        inset.tick_params(labelsize=5)
        inset.grid(True, alpha=.2)
        ax.axvline(t_feed, color="gray", lw=1, ls=":")
        selected_row = results.loc[results.index[
            (results.model_type == model) & (results['product'] == product) & (results.strategy == chosen)][0]]
        if 'param_t_switch' in selected_row and pd.notna(selected_row.param_t_switch):
            switch_time = t_feed + float(selected_row.param_t_switch)
            ax.axvline(switch_time, color="#6A1B9A", lw=1.0, ls="--", alpha=.7)
            ax.text(switch_time, .97, "stage 2", transform=ax.get_xaxis_transform(),
                    fontsize=6, rotation=90, va="top", ha="right", color="#6A1B9A")
        ax2.set_ylabel(f"P ({row_unit}/L)", fontsize=8, color=MODEL_EDGE.get(model, "#455A64"))
        ax2.tick_params(axis="y", labelcolor=MODEL_EDGE.get(model, "#455A64"))
        ax.set_xlabel("Time (h)", fontsize=8)
        ax.set_ylabel("X, S (g/L)", fontsize=8)
        ax.set_title(f"{product}\n{STRATEGY_LABELS.get(chosen, chosen)}", fontsize=10, fontweight="bold")
        ax.legend([l1, l2, l3], [l.get_label() for l in (l1, l2, l3)],
                  loc="upper center", bbox_to_anchor=(.5, -.2), ncol=2, fontsize=7)
    for ax, dataset in zip(axes.flat, [item for row in grid for item in row]):
        if dataset is None:
            ax.remove()
    fig.tight_layout()
    fig.savefig(results_dir / filename, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def plot_solver_comparison(results_dir: Path, comparison: pd.DataFrame):
    comparison = comparison.copy()
    comparison["dataset"] = comparison.model_type.astype(str) + " / " + comparison["product"].astype(str)
    datasets = list(dict.fromkeys(comparison.dataset))
    strategies = [s for s in STRATEGY_ORDER if s in set(comparison.strategy)]
    strategies += [s for s in comparison.strategy if s not in strategies]
    values = comparison.pivot_table(index="dataset", columns="strategy", values="relative_difference_percent", aggfunc="first")
    values = values.reindex(index=datasets, columns=strategies)
    fig, ax = plt.subplots(figsize=(max(11, 1.1 * len(strategies)), max(7, .42 * len(datasets))))
    limit = max(1.0, float(np.nanmax(np.abs(values.to_numpy(float)))))
    image = ax.imshow(values.to_numpy(float), cmap="RdBu_r", vmin=-limit, vmax=limit, aspect="auto")
    ax.set_xticks(range(len(strategies)), [STRATEGY_LABELS.get(s, s) for s in strategies], rotation=35, ha="right")
    ax.set_yticks(range(len(datasets)), datasets)
    for r in range(values.shape[0]):
        for c in range(values.shape[1]):
            value = values.iloc[r, c]
            if pd.notna(value):
                ax.text(c, r, f"{value:+.2f}%", ha="center", va="center", fontsize=7)
    fig.colorbar(image, ax=ax, label="Relative difference: (pyFOOMB − SciPy) / SciPy (%)")
    ax.set_title("Solver relative difference by dataset and strategy\nidentical feed settings; zero means agreement", fontweight="bold")
    ax.set_xlabel("Feed-flow strategy")
    ax.set_ylabel("Dataset")
    fig.tight_layout()
    fig.savefig(results_dir / "solver_comparison.png", dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path(__file__).with_name("pyfoomb_results"))
    parser.add_argument("--strategies", nargs="+", choices=STRATEGY_ORDER,
                        help="Restrict plotted comparisons to these feed strategies.")
    args = parser.parse_args()
    results_dir = args.results_dir
    results = pd.read_csv(results_dir / "feed_flow_results.csv")
    best = pd.read_csv(results_dir / "best_per_dataset.csv")
    if args.strategies:
        results = results[results.strategy.isin(args.strategies)]
        winner_indices = results.groupby(["model_type", "product"]).total_product.idxmax()
        best = results.loc[winner_indices]
    plot_strategy_comparison(results_dir, results)
    plot_profiles(results_dir, results, best, None, "best_profiles.png", "Best strategy per dataset")
    plot_profiles(results_dir, results, best, "linear_ramp", "linear_ramp_profiles.png", "Linear ramp profiles")
    comparison = pd.read_csv(results_dir / "solver_comparison.csv")
    if args.strategies:
        comparison = comparison[comparison.strategy.isin(args.strategies)]
    plot_solver_comparison(results_dir, comparison)


if __name__ == "__main__":
    main()
