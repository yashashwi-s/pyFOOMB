"""Reconstruct the García-Ortega et al. (2013) Fab 2F5 runs from reported rates."""

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
# Table 3A: nominal and measured growth, substrate uptake, Fab formation,
# terminal biomass, measured terminal Fab titre and reported titre uncertainty.
RUNS = (
    (0.05, 0.050, 0.111, 7.7, 100.5, 15.1, 0.5),
    (0.10, 0.101, 0.225, 25.7, 97.0, 24.7, 0.9),
    (0.15, 0.146, 0.312, 35.2, 98.7, 24.1, 0.8),
)


def reconstruct(run):
    nominal, mu, qs, qp_ug, biomass_end, measured, uncertainty = run
    batch_hours = 15.0  # Approximate Figure 2A transition.
    initial_glycerol, batch_volume, feed_glucose = 40.0, 2.0, 400.0
    batch_mu, batch_yield, fab_yield = 0.197, 0.49, 0.17  # Table 1.
    initial_biomass = batch_yield * initial_glycerol / np.expm1(batch_mu * batch_hours)
    batch_time = np.linspace(0, batch_hours, 151)
    batch_biomass = initial_biomass * np.exp(batch_mu * batch_time)
    glycerol = initial_glycerol - (batch_biomass - initial_biomass) / batch_yield
    batch_fab = fab_yield * (batch_biomass - initial_biomass)
    mass_at_feed = batch_biomass[-1] * batch_volume

    # Carbon-limited feed. The paper reports mean specific rates rather than a
    # pump trace. Integrate those rates against the reconstructed biomass mass.
    volume_per_biomass = qs / (mu * feed_glucose)
    mass_end = biomass_end * (batch_volume - volume_per_biomass * mass_at_feed)
    mass_end /= 1 - biomass_end * volume_per_biomass
    feed_hours = np.log(mass_end / mass_at_feed) / mu
    feed_time = np.linspace(0, feed_hours, 241)
    mass = mass_at_feed * np.exp(mu * feed_time)
    exposure = (mass - mass_at_feed) / mu
    volume = batch_volume + qs * exposure / feed_glucose
    fab = batch_fab[-1] * batch_volume + (qp_ug / 1000) * exposure
    assert np.isclose(glycerol[-1], 0) and np.isclose(mass[-1] / volume[-1], biomass_end)
    return (
        np.r_[batch_time, batch_hours + feed_time[1:]],
        np.r_[batch_biomass, (mass / volume)[1:]],
        np.r_[np.maximum(glycerol, 0), np.zeros(len(feed_time) - 1)],
        np.r_[batch_fab, (fab / volume)[1:]],
    )


def main():
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.3), layout="constrained")
    output = []
    for run in RUNS:
        nominal, _, _, _, biomass_end, measured, uncertainty = run
        time, biomass, glycerol, fab = reconstruct(run)
        output.append((nominal, time[-1], biomass_end, fab[-1], measured, fab[-1] - measured))
        axes[0].plot(time, biomass, label=f"{nominal:.2f} h⁻¹")
        axes[1].plot(time, glycerol)
        line, = axes[2].plot(time, fab)
        axes[2].errorbar(time[-1], measured, yerr=uncertainty, fmt="o",
                         color=line.get_color(), capsize=3)
    for ax, label in zip(axes, ("Biomass (g/L)", "Residual glycerol (g/L)", "Fab 2F5 titre (mg/L)")):
        ax.axvline(15, color="0.45", linestyle=":", linewidth=1)
        ax.set(xlabel="Elapsed time (h)", ylabel=label)
        ax.grid(alpha=.2)
    axes[0].legend(title="Nominal growth")
    fig.suptitle("Fab 2F5 mass-balance reconstruction | dots show Table 3 titres at model end times")
    fig.savefig(HERE / "fab_2f5_reconstruction.png", dpi=200)
    with (HERE / "fab_2f5_endpoints.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("nominal_mu_h-1", "model_end_h", "imposed_biomass_g_L",
                         "model_fab_mg_L", "reported_fab_mg_L", "titre_difference_mg_L"))
        writer.writerows(output)


if __name__ == "__main__":
    main()
