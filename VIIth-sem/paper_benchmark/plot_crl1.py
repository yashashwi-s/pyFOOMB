"""Compare the two paper-parameterised Crl1 sweeps."""
import ast
import csv

import matplotlib.pyplot as plt
import numpy as np

from optimize_crl1 import HERE, production_fit, reference, simulate


def main():
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), layout="constrained")
    profiles, profile_axes = plt.subplots(2, 4, figsize=(12, 5.5), layout="constrained")
    for index, (ax, clone) in enumerate(zip(axes, ("SCC", "MCC"))):
        with (HERE / f"crl1_{clone.lower()}_strategies.csv").open() as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == len(reference.STRATEGIES)
        winner = max(rows, key=lambda row: float(row["activity_UA"]))
        name = winner["strategy"]
        labels = [row["strategy"].replace("two_stage_", "").replace("_", " ") for row in rows]
        labels[4] = "const const"
        scores = [float(row["activity_UA"]) / 1e6 for row in rows]
        ax.barh(labels, scores, color=["#2980B9" if row is winner else "#BDC3C7" for row in rows])
        ax.invert_yaxis()
        ax.set(title=clone, xlabel="Fed-batch activity at harvest (million UA)")
        params = ast.literal_eval(winner["parameters"])
        time, states = simulate(name, list(params.values()), production_fit(clone), tight=True)
        assert np.isclose(states[-1, 2] * states[-1, 3], float(winner["activity_UA"]))
        for panel, values, label in zip(profile_axes[index], states.T,
                                        ("Biomass (g/L)", "Glucose (g/L)", "Activity (UA/L)", "Volume (L)")):
            panel.plot(time, values, color="#2980B9")
            panel.set(xlabel="Hours from feed start", ylabel=label)
            panel.grid(alpha=.2)
        profile_axes[index, 0].set_title(f"{clone} · {name.replace('_', ' ')}")
        print(clone, name, winner["activity_UA"], winner["feed_h"])
    fig.savefig(HERE / "crl1_strategy_comparison.png", dpi=200)
    profiles.savefig(HERE / "crl1_best_profiles.png", dpi=200)


if __name__ == "__main__":
    main()
