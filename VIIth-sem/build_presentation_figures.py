#!/usr/bin/env python3
"""Build large, slide-ready scientific figures for the optimisation recap.

Run ``python build_presentation_figures.py --recap-only`` for the three figures
that depend only on the model code.  A full run also reads the latest result
CSVs and re-simulates the winning Fab 3H6 trajectory.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/pyfoomb-matplotlib")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/pyfoomb-cache")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
import pandas as pd

from feed_flow_optimization import (
    DATA, F_CAP, KINETICS, MODEL_FNS, STRATEGIES, T_FEDBATCH, V_MAX,
    fit_qp_model, simulate_batch, simulate_fedbatch,
)


HERE = Path(__file__).resolve().parent
FIGURES = HERE / "figures"
RESULTS = HERE / "feed_flow_results.csv"
ARCHIVE_RESULTS = HERE / "archive" / "pre_volume_fix" / "feed_flow_results.csv"

NAVY = "#102A43"
BLUE = "#1877B8"
TEAL = "#149C95"
ORANGE = "#F28E2B"
RED = "#D1495B"
GREY = "#718096"
LIGHT = "#E8F1F5"

STRATEGY_ORDER = [
    "constant", "exponential", "linear_ramp", "exp_linear",
    "two_stage", "pulsed", "feedback_control",
]
STRATEGY_LABELS = {
    "constant": "Constant", "exponential": "Exponential",
    "linear_ramp": "Linear ramp", "exp_linear": "Exp + linear",
    "two_stage": "Two stage", "pulsed": "Pulsed",
    "feedback_control": "Feedback",
}


def set_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 16,
        "axes.titlesize": 20, "axes.labelsize": 17,
        "xtick.labelsize": 14, "ytick.labelsize": 14,
        "legend.fontsize": 14, "axes.titleweight": "bold",
        "axes.edgecolor": "#A7B6C2", "axes.linewidth": 1.0,
        "axes.spines.top": False, "axes.spines.right": False,
        "grid.color": "#D8E2E8", "grid.linewidth": 0.8,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white",
    })


def save(fig: plt.Figure, name: str) -> Path:
    FIGURES.mkdir(exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, dpi=220, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print(path)
    return path


def r_squared(y: np.ndarray, yhat: np.ndarray) -> float:
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    return 1.0 - ss_res / ss_tot


def representative(model_type: str, product_fragment: str):
    return next(d for d in DATA[model_type] if product_fragment in d["product"])


def recap_qp_fits() -> Path:
    choices = [
        ("linear", representative("linear", "HIP"), BLUE, "Linear"),
        ("bell_shaped", representative("bell_shaped", "Fab 3H6"), ORANGE, "Bell shaped"),
        ("hyperbolic", representative("hyperbolic", "MCC"), TEAL, "Hyperbolic"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.25))
    for ax, (mtype, ds, color, title) in zip(axes, choices):
        fn, pars = fit_qp_model(mtype, ds["mu"], ds["qp"])
        xx = np.linspace(ds["mu"].min(), ds["mu"].max(), 240)
        yy = fn(xx, *pars)
        fit = fn(ds["mu"], *pars)
        ax.plot(xx, yy, color=color, lw=4, zorder=2)
        ax.scatter(ds["mu"], ds["qp"], s=70, color="white", edgecolor=color,
                   linewidth=2.5, zorder=3)
        ax.set_title(f"{title}\n{ds['product'].split(' (')[0]}")
        ax.set_xlabel(r"Specific growth rate, $\mu$ (h$^{-1}$)")
        ax.set_ylabel(rf"$q_p$ ({ds['qp_unit']})")
        ax.text(0.04, 0.92, rf"$R^2$ = {r_squared(ds['qp'], fit):.3f}",
                transform=ax.transAxes, color=NAVY, weight="bold", va="top")
        ax.text(0.04, 0.04, ds["reference"], transform=ax.transAxes,
                color=GREY, fontsize=9, va="bottom")
        ax.grid(True, alpha=0.8)
    fig.tight_layout(w_pad=2.0)
    return save(fig, "recap_qp_fits.png")


def recap_batch_fab() -> Path:
    ds = representative("bell_shaped", "Fab 3H6")
    kin = KINETICS[ds["organism_type"]]
    fn, pars = fit_qp_model("bell_shaped", ds["mu"], ds["qp"])
    t_feed, _, sol = simulate_batch(kin, fn, pars, ds["mu"].max() * 1.2)
    t = sol.t
    X, S, P = sol.y[0], sol.y[1], sol.y[2]
    p_norm = P / max(P[-1], 1e-12)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.3), gridspec_kw={"width_ratios": [1.15, 0.85]})
    axes[0].plot(t, X, color=BLUE, lw=4, label="Biomass X")
    axes[0].plot(t, S, color=ORANGE, lw=4, label="Substrate S")
    axes[0].set_title("Batch growth and substrate use")
    axes[0].set_xlabel("Batch time (h)")
    axes[0].set_ylabel("Concentration (g/L)")
    axes[0].legend(frameon=False, loc="center left")
    axes[0].grid(True)
    axes[1].plot(t, p_norm, color=TEAL, lw=5)
    axes[1].fill_between(t, 0, p_norm, color=TEAL, alpha=0.14)
    axes[1].set_title("Normalized product")
    axes[1].set_xlabel("Batch time (h)")
    axes[1].set_ylabel(r"$P/P_{final}$")
    axes[1].set_ylim(0, 1.05)
    axes[1].grid(True)
    fig.suptitle(f"Fab 3H6 batch simulation  |  feed starts at {t_feed:.1f} h", color=NAVY,
                 fontsize=22, fontweight="bold", y=1.02)
    fig.tight_layout(w_pad=3)
    return save(fig, "recap_batch.png")


def recap_feed_laws() -> Path:
    t = np.linspace(0, 40, 800)
    curves = {
        "constant": np.full_like(t, 0.30),
        "exponential": 0.035 * np.exp(0.065 * t),
        "linear_ramp": 0.025 + 0.012 * t,
        "exp_linear": 0.02 * np.exp(0.055 * t) + 0.005 * t,
        "two_stage": np.where(t < 17, 0.12, 0.42),
        "pulsed": np.where((t % 7.0) < 2.2, 0.55, 0.0),
        "feedback_control": 0.24 + 0.08 * np.sin(t / 4.8) * np.exp(-t / 32),
    }
    fig, axes = plt.subplots(2, 4, figsize=(14, 5.5), sharex=True, sharey=True)
    colors = [NAVY, BLUE, TEAL, ORANGE, "#6B5CA5", RED, "#2A9D4B"]
    for ax, name, color in zip(axes.flat, STRATEGY_ORDER, colors):
        ax.plot(t, curves[name], color=color, lw=4)
        ax.fill_between(t, 0, curves[name], color=color, alpha=0.10)
        ax.set_title(STRATEGY_LABELS[name], fontsize=18)
        ax.set_xlim(0, 40)
        ax.set_ylim(0, 0.62)
        ax.grid(True)
    axes.flat[-1].axis("off")
    for ax in axes[1, :3]:
        ax.set_xlabel("Time")
    for ax in axes[:, 0]:
        ax.set_ylabel("Feed rate")
    fig.suptitle("Seven candidate feed laws  |  illustrative shapes", color=NAVY,
                 fontsize=23, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94], h_pad=2.0, w_pad=1.2)
    return save(fig, "feed_strategy_schematics.png")


def validate_results(df: pd.DataFrame) -> None:
    missing = {"product", "strategy", "total_product", "V_final"} - set(df.columns)
    if missing:
        raise ValueError(f"Results CSV is missing columns: {sorted(missing)}")
    duplicates = df.duplicated(["product", "strategy"])
    if duplicates.any():
        raise ValueError("Results CSV contains duplicate product-strategy rows")


def strategy_heatmap(df: pd.DataFrame) -> Path:
    validate_results(df)
    score = df.copy()
    score["relative"] = score["total_product"] / score.groupby("product")["total_product"].transform("max") * 100
    product_order = [d["product"] for m in ["linear", "bell_shaped", "hyperbolic"] for d in DATA[m]]
    matrix = score.pivot(index="product", columns="strategy", values="relative").reindex(
        index=product_order, columns=STRATEGY_ORDER)
    cmap = LinearSegmentedColormap.from_list("slide", ["#EEF4F7", "#9DDED8", TEAL, NAVY])
    fig, ax = plt.subplots(figsize=(14, 5.5))
    im = ax.imshow(matrix, aspect="auto", vmin=50, vmax=100, cmap=cmap)
    ax.set_xticks(range(len(STRATEGY_ORDER)), [STRATEGY_LABELS[s] for s in STRATEGY_ORDER], rotation=24, ha="right")
    labels = [p.replace("Heterologous Protein (HIP)", "HIP").replace(" (Human Serum Albumin)", "") for p in product_order]
    ax.set_yticks(range(len(labels)), labels)
    for i in range(matrix.shape[0]):
        vals = matrix.iloc[i].to_numpy(float)
        for j, value in enumerate(vals):
            if np.isfinite(value):
                ax.text(j, i, f"{value:.0f}", ha="center", va="center",
                        color="white" if value >= 88 else NAVY, fontsize=14,
                        fontweight="bold" if value >= 99.95 else "normal")
    cb = fig.colorbar(im, ax=ax, fraction=0.027, pad=0.025)
    cb.set_label("Relative product (% of best found)")
    ax.set_title("Feed strategy performance within each dataset", color=NAVY, pad=10)
    fig.tight_layout()
    return save(fig, "strategy_heatmap.png")


def effective_feed(t: np.ndarray, y: np.ndarray, strategy: dict, params: np.ndarray, kin: dict) -> np.ndarray:
    out = []
    for ti, yi in zip(t, y.T):
        requested = float(np.clip(strategy["fn"](ti, yi, params, kin), 0.0, F_CAP))
        out.append(0.0 if yi[3] >= V_MAX else requested)
    return np.asarray(out)


def detailed_fab(df: pd.DataFrame) -> Path:
    validate_results(df)
    rows = df[df["product"].str.contains("Fab 3H6", regex=False)]
    if rows.empty:
        raise ValueError("No Fab 3H6 rows in results CSV")
    best = rows.loc[rows["total_product"].idxmax()]
    ds = representative("bell_shaped", "Fab 3H6")
    kin = KINETICS[ds["organism_type"]]
    qp_fn, qp_pars = fit_qp_model("bell_shaped", ds["mu"], ds["qp"])
    _, y_feed, _ = simulate_batch(kin, qp_fn, qp_pars, ds["mu"].max() * 1.2)
    name = best["strategy"]
    strategy = STRATEGIES[name]
    params = np.asarray([best[f"param_{n}"] for n in strategy["names"]], dtype=float)
    sol = simulate_fedbatch(strategy, params, kin, qp_fn, qp_pars,
                            ds["mu"].max() * 1.2, y_feed, strategy["max_step"])
    t = np.linspace(0, T_FEDBATCH, 600)
    y = sol.sol(t)
    X, S, P, V = y
    mu = kin["mu_max"] * np.maximum(S, 0) / (kin["Ks"] + np.maximum(S, 0))
    feed = effective_feed(t, y, strategy, params, kin)
    total_p = P * V
    mu_peak = float(qp_pars[1])

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.3))
    axes[0].plot(t, feed, color=BLUE, lw=4)
    axes[0].fill_between(t, 0, feed, color=BLUE, alpha=0.12)
    axes[0].set_title("Effective feed")
    axes[0].set_ylabel("F(t) (L/h)")
    axes[1].plot(t, mu, color=ORANGE, lw=4, label="Realized μ")
    axes[1].axhline(mu_peak, color=NAVY, lw=2.5, ls="--", label=rf"Fitted peak {mu_peak:.3f}")
    axes[1].set_title("Growth rate and qp peak")
    axes[1].set_ylabel(r"$\mu$ (h$^{-1}$)")
    axes[1].legend(frameon=False, fontsize=12)
    axes[2].plot(t, total_p / 1000, color=TEAL, lw=4, label="Total product")
    axv = axes[2].twinx()
    axv.plot(t, V, color=GREY, lw=2.5, ls="--", label="Volume")
    axv.axhline(V_MAX, color=RED, lw=1.8, ls=":")
    axes[2].set_title("Product accumulation")
    axes[2].set_ylabel("Total product (g)")
    axv.set_ylabel("Volume (L)", color=GREY)
    axv.tick_params(axis="y", colors=GREY)
    for ax in axes:
        ax.set_xlabel("Fed batch time (h)")
        ax.grid(True)
    fig.suptitle(f"Fab 3H6 optimized trajectory  |  {STRATEGY_LABELS.get(name, name)}",
                 color=NAVY, fontsize=23, fontweight="bold", y=1.02)
    fig.tight_layout(w_pad=2.0)
    return save(fig, "fab_optimized_trajectory.png")


def volume_validation(before: pd.DataFrame, after: pd.DataFrame) -> Path:
    validate_results(before)
    validate_results(after)
    products = [d["product"] for m in ["linear", "bell_shaped", "hyperbolic"] for d in DATA[m]]
    old = before.groupby("product")["V_final"].max().reindex(products)
    new = after.groupby("product")["V_final"].max().reindex(products)
    y = np.arange(len(products))
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1.3, 0.7]})
    axes[0].hlines(y, old, new, color="#BCCAD3", lw=3)
    axes[0].scatter(old, y, s=90, color=RED, label="Before fix", zorder=3)
    axes[0].scatter(new, y, s=90, color=TEAL, label="Corrected", zorder=3)
    axes[0].axvspan(V_MAX - 0.001, V_MAX + 0.001, color=NAVY, alpha=0.12,
                    label="4 L ceiling ±1 mL tolerance")
    axes[0].set_yticks(y, [p.split(" (")[0] for p in products])
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Maximum saved final volume (L)")
    axes[0].set_title("Dataset level validation")
    axes[0].legend(frameon=False)
    axes[0].grid(True, axis="x")
    # Ignore sub-millilitre solver/event-location noise when showing violations.
    excess_old = np.maximum(old.to_numpy() - (V_MAX + 0.001), 0) * 1000
    excess_new = np.maximum(new.to_numpy() - (V_MAX + 0.001), 0) * 1000
    axes[1].bar([0, 1], [np.nanmax(excess_old), np.nanmax(excess_new)], color=[RED, TEAL], width=0.62)
    heights = [np.nanmax(excess_old), np.nanmax(excess_new)]
    top = max(max(heights), 1.0)
    axes[1].set_ylim(0, top * 1.2)
    for i, height in enumerate(heights):
        axes[1].text(i, height + top * 0.025, f"{height:.0f} mL",
                     ha="center", fontsize=18, color=NAVY)
    axes[1].set_xticks([0, 1], ["Before", "Corrected"])
    axes[1].set_ylabel("Largest excess beyond tolerance (mL)")
    axes[1].set_title("Worst saved violation")
    axes[1].grid(True, axis="y")
    fig.suptitle("Working volume ceiling check", color=NAVY, fontsize=23, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.94], w_pad=3)
    return save(fig, "volume_validation.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recap-only", action="store_true")
    args = parser.parse_args()
    set_style()
    recap_qp_fits()
    recap_batch_fab()
    recap_feed_laws()
    if args.recap_only:
        return
    current = pd.read_csv(RESULTS)
    strategy_heatmap(current)
    detailed_fab(current)
    if ARCHIVE_RESULTS.exists():
        volume_validation(pd.read_csv(ARCHIVE_RESULTS), current)
    else:
        print(f"Skipped volume validation: missing {ARCHIVE_RESULTS}")


if __name__ == "__main__":
    main()
