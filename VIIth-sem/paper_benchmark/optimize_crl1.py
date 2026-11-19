"""Paper-parameterised Crl1 sensitivity sweep using the existing feed laws."""

import csv
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit, differential_evolution

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import feed_flow_optimization as reference

# Nieto-Taype et al. Table 1, measured fed-batch rates, in UA/(g DCW h).
DATA = {
    "SCC": ([.048, .088, .133], [77, 149, 292]),
    "MCC": ([.023, .051, .087, .147], [374, 550, 697, 777]),
}
# Glycerol/glucose protocol cited by Nieto-Taype. The 4 L value serves as
# an assumed design bound based on the referenced Fab run's working volume.
BATCH_SUBSTRATE = 40.
INITIAL_VOLUME = 2.
FEED_SUBSTRATE = 400.
MAX_VOLUME = 4.
HARVEST_BIOMASS = 100.
HORIZON = 40.  # Study comparison window, not an experimental stopping time.
PUMP_CAP = 2.  # Retained engineering bound, not reported for this reactor.
BATCH_YIELD = .49
INOCULUM = .1  # Retained assumption. Clone-specific inoculum unavailable.
KINETICS = {"mu_max": .20, "Ks": .05, "Yxs": .50}


def production_fit(clone):
    growth, product = DATA[clone]
    if clone == "SCC":
        slope = np.dot(growth, product) / np.dot(growth, growth)
        return lambda mu: slope * mu

    def saturation(mu, maximum, half_rate):
        return maximum * mu / (half_rate + mu)

    params, _ = curve_fit(saturation, growth, product, bounds=(0, np.inf))
    return lambda mu: saturation(mu, *params)


def simulate(name, params, production, *, tight=False):
    strategy = reference.STRATEGIES[name]
    # At depletion, transfer all simulated biomass and the initial liquid
    # volume. Score fed-batch activity only because the initial activity is
    # unknown for each clone. It is a common offset within a clone.
    state = np.array([INOCULUM + BATCH_YIELD * BATCH_SUBSTRATE, 0., 0., INITIAL_VOLUME])
    edges = [0., HORIZON]
    if "t_switch" in strategy["names"]:
        edges.append(params[strategy["names"].index("t_switch")])
    if name == "pulsed":
        _, period, duty = params
        for begin in np.arange(0, HORIZON, period):
            edges.extend(t for t in (begin, begin + duty * period) if 0 < t < HORIZON)
    edges = sorted(set(edges))

    def harvest(t, y):
        return y[0] - HARVEST_BIOMASS

    def full(t, y):
        return y[3] - MAX_VOLUME

    harvest.terminal = full.terminal = True
    harvest.direction = full.direction = 1
    time, values = [0.], [state.copy()]
    for start, stop in zip(edges, edges[1:]):
        def rhs(t, y):
            x, s, p, v = y
            mu = KINETICS["mu_max"] * max(s, 0) / (KINETICS["Ks"] + max(s, 0))
            schedule_time = (start + stop) / 2 if name == "pulsed" else min(
                max(t, start), np.nextafter(stop, start)
            )
            flow = np.clip(strategy["fn"](schedule_time, y, params, KINETICS), 0., PUMP_CAP)
            dilution = flow / v
            return ((mu - dilution) * x,
                    dilution * (FEED_SUBSTRATE - s) - mu * x / KINETICS["Yxs"],
                    production(min(mu, .147)) * x - dilution * p, flow)

        sol = solve_ivp(rhs, (start, stop), state, method="LSODA", events=(harvest, full),
                        rtol=1e-8 if tight else 3e-5, atol=1e-10 if tight else 1e-7)
        if not sol.success:
            raise RuntimeError(sol.message)
        time.extend(sol.t[1:])
        values.extend(sol.y.T[1:])
        state = sol.y[:, -1]
        if sol.status == 1:
            break
    return np.asarray(time), np.asarray(values)


def main(clone):
    production = production_fit(clone)
    results = []
    for name, strategy in reference.STRATEGIES.items():
        def loss(params):
            _, states = simulate(name, params, production)
            return -states[-1, 2] * states[-1, 3]

        fit = differential_evolution(loss, strategy["bounds"](KINETICS), seed=42,
                                    maxiter=12, popsize=6, polish=False)
        time, states = simulate(name, fit.x, production, tight=True)
        biomass, substrate, titre, volume = states[-1]
        assert volume <= MAX_VOLUME + 1e-7 and biomass <= HARVEST_BIOMASS + 1e-6
        params = dict(zip(strategy["names"], map(float, fit.x)))
        results.append((name, titre * volume, titre, time[-1], biomass, volume, str(params)))
        print(clone, name, round(titre * volume), flush=True)
    with (HERE / f"crl1_{clone.lower()}_strategies.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("strategy", "activity_UA", "titre_UA_L", "feed_h",
                         "biomass_g_L", "volume_L", "parameters"))
        writer.writerows(results)


if __name__ == "__main__":
    main(sys.argv[1])
