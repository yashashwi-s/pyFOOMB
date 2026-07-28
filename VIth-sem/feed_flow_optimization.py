"""
Feed-Flow (F(t)) Strategy Optimisation for Fed-Batch Bioprocesses
==================================================================

This is the natural continuation of `mu_qp_visualization.py` (qp-mu literature
fits) and `simulate_xps.py` (batch X/S/P validation): now that we trust the
qp(mu) relationship for each of the 9 literature products, the open question
is *how to feed the bioreactor* to get the most product out of each one.

Recall the control chain established in the study notes:

    F(t) -> D = F/V ~= mu -> qp(mu) -> P

Different qp(mu) shapes call for (in theory) different feeding strategies:
  * Linear (Luedeking-Piret), qp = alpha*mu + beta        -> push mu as high as possible
  * Bell-shaped (Gaussian), qp peaks at mu_opt             -> hold mu at mu_opt, no more
  * Hyperbolic (Monod-like saturation)                     -> any mu comfortably above K_mu is fine

This script turns that qualitative theory into a quantitative, testable claim:

  1. For every one of the 9 datasets, run a short **batch phase** (no feed) from
     inoculation until the substrate is nearly exhausted -- this is when a real
     fed-batch would switch the feed pump on.
  2. From that point, integrate a **fed-batch phase** of fixed duration under 6
     different feed-flow functions F(t):
       - constant             F(t) = F0
       - exponential          F(t) = F0 * exp(mu_set * t)
       - linear ramp          F(t) = F0 + k*t
       - two-stage (bang)     F(t) = F1 for t < t_switch, else F2
       - pulsed (bolus-like)  F(t) alternates between F_pulse and 0 with a duty cycle
       - feedback control     F(t) = Kp * (S_set(mu_target) - S(t)), clipped >= 0
  3. Optimise the free parameters of each F(t) with `scipy.optimize.differential_evolution`
     (the same global optimiser pyFOOMB's Caretaker.estimate() uses for Tier-1
     single-machine global estimation) to **maximise total product formed**,
     P(t_f) * V(t_f), subject to a working-volume ceiling (V <= V_MAX).
  4. Rank the 6 strategies per dataset and report the winner.

Everything here runs on plain numpy/scipy so it can be executed and unit-tested
without the compiled `assimulo`/`pygmo` stack that the full pyFOOMB package
needs (those provide the same two optimisation tiers -- CVode+scipy and
CVode+pygmo -- that this script emulates with solve_ivp+differential_evolution).
"""

import os
import time

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit, differential_evolution

HERE = os.path.dirname(os.path.abspath(__file__))

# ============================================================================
# 1. qp(mu) MODEL FUNCTIONS  (identical to mu_qp_visualization.py / simulate_xps.py)
# ============================================================================

def linear_model(mu, alpha, beta):
    """Luedeking-Piret: qp = alpha * mu + beta"""
    return alpha * mu + beta


def bell_shaped_model(mu, qp_max, mu_opt, sigma):
    """Gaussian bell-shape: qp = qp_max * exp(-(mu - mu_opt)^2 / (2*sigma^2))"""
    return qp_max * np.exp(-((mu - mu_opt) ** 2) / (2 * sigma ** 2))


def hyperbolic_model(mu, qp_max, Kq):
    """Monod-like saturation: qp = qp_max * mu / (Kq + mu)"""
    return qp_max * mu / (Kq + mu)


MODEL_FNS = {
    'linear': linear_model,
    'bell_shaped': bell_shaped_model,
    'hyperbolic': hyperbolic_model,
}

FIT_P0 = {
    # initial guesses / bounds for curve_fit, mirroring simulate_xps.py
    'linear': lambda mu, qp: dict(p0=[max(qp) / max(mu), 0.0]),
    'bell_shaped': lambda mu, qp: dict(
        p0=[max(qp), mu[np.argmax(qp)], 0.04], maxfev=20000,
        bounds=([0, 0, 1e-4], [np.inf, 0.5, 0.5]),
    ),
    'hyperbolic': lambda mu, qp: dict(
        p0=[max(qp) * 1.1, 0.03], maxfev=20000,
        bounds=([0, 1e-4], [np.inf, 0.5]),
    ),
}

# ============================================================================
# 2. LITERATURE qp-mu DATA (corrected values, same as simulate_xps.py)
# ============================================================================

DATA = {
    'linear': [
        {
            'product': 'Resveratrol', 'organism_type': 'S. cerevisiae',
            'reference': 'Vos et al. (2015)',
            'mu': np.array([0.025, 0.050, 0.075, 0.10, 0.15]),
            'qp': np.array([0.001, 0.004, 0.009, 0.016, 0.025]),
            'qp_unit': 'mmol/(g*h)',
        },
        {
            'product': 'Heterologous Protein (HIP)', 'organism_type': 'S. cerevisiae',
            'reference': 'Liu et al. (2013)',
            'mu': np.array([0.05, 0.10, 0.15, 0.20, 0.25, 0.30]),
            'qp': np.array([0.5, 1.2, 2.1, 3.2, 4.5, 5.8]),
            'qp_unit': 'mg/(g*h)',
        },
        {
            'product': 'Crl1 Lipase (SCC, PGAP)', 'organism_type': 'P. pastoris',
            'reference': 'Nieto-Taype et al. (2020)',
            'mu': np.array([0.025, 0.05, 0.075, 0.10, 0.125, 0.15]),
            'qp': np.array([6.0, 13.0, 21.0, 30.0, 38.0, 47.0]),
            'qp_unit': 'AU/(g*h)',
        },
    ],
    'bell_shaped': [
        {
            'product': 'EPG (Polygalacturonase)', 'organism_type': 'S. cerevisiae',
            'reference': 'Glauche et al. (2017)',
            'mu': np.array([0.01, 0.03, 0.05, 0.07, 0.10, 0.13, 0.15, 0.20, 0.25, 0.30]),
            'qp': np.array([30, 80, 160, 280, 390, 430, 410, 340, 200, 100]),
            'qp_unit': 'U/(g*h)',
        },
        {
            'product': 'Fab 3H6 (PGAP)', 'organism_type': 'P. pastoris',
            'reference': 'Maurer et al. (2006) / Garcia-Ortega et al. (2019)',
            'mu': np.array([0.015, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15]),
            'qp': np.array([1.0, 3.0, 8.5, 12.0, 10.5, 7.5, 4.5]),
            'qp_unit': 'mg/(g*h)',
        },
        {
            'product': 'ROL (Rhizopus oryzae Lipase, PAOX1)', 'organism_type': 'P. pastoris',
            'reference': 'Garcia-Ortega et al. (2016) / Canales et al. (2015)',
            'mu': np.array([0.01, 0.02, 0.035, 0.05, 0.065, 0.08, 0.10, 0.12]),
            'qp': np.array([6.0, 16.0, 30.0, 40.0, 38.0, 28.0, 18.0, 10.0]),
            'qp_unit': 'AU/(g*h)',
        },
    ],
    'hyperbolic': [
        {
            'product': 'Crl1 Lipase (MCC, PGAP)', 'organism_type': 'P. pastoris',
            'reference': 'Nieto-Taype et al. (2020)',
            'mu': np.array([0.025, 0.05, 0.075, 0.10, 0.125, 0.15]),
            'qp': np.array([35, 70, 100, 120, 130, 135]),
            'qp_unit': 'AU/(g*h)',
        },
        {
            'product': 'alpha-Galactosidase', 'organism_type': 'S. cerevisiae',
            'reference': 'Giuseppin et al. (1993) / Hensing et al. (1995)',
            'mu': np.array([0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.25, 0.30]),
            'qp': np.array([6.0, 16.0, 25.0, 31.0, 38.0, 41.0, 42.5, 43.0]),
            'qp_unit': 'U/(g*h)',
        },
        {
            'product': 'HSA (Human Serum Albumin)', 'organism_type': 'P. pastoris',
            'reference': 'Rebnegger et al. (2014)',
            'mu': np.array([0.015, 0.025, 0.05, 0.075, 0.10, 0.125, 0.15]),
            'qp': np.array([0.8, 1.5, 4.0, 6.5, 8.5, 9.5, 10.0]),
            'qp_unit': 'mg/(g*h)',
        },
    ],
}

KINETICS = {
    'S. cerevisiae': dict(mu_max=0.40, Ks=0.10, Yxs=0.50),
    'P. pastoris': dict(mu_max=0.20, Ks=0.05, Yxs=0.45),
}

# ============================================================================
# 3. PROCESS-WIDE ASSUMPTIONS
#
# To isolate the effect of qp(mu) *shape* on the optimal feed strategy, every
# dataset is run in the same generic bioreactor (same reactor/feed limits and
# same initial conditions). Only the organism kinetics (mu_max, Ks, Yxs) and
# the fitted qp(mu) law differ between datasets -- this keeps the comparison
# apples-to-apples, exactly like the shared X0/S0/P0 used in simulate_xps.py.
# ============================================================================

X0, S0, P0, V0 = 0.1, 20.0, 0.0, 1.0     # batch inoculation (g/L, g/L, unit/L, L)
S_IN = 400.0                              # concentrated feed reservoir, g/L
V_MAX = 4.0                                # working volume ceiling, L (4x fill)
F_CAP = 2.0                                # physical feed pump ceiling, L/h
T_BATCH_MAX = 60.0                         # safety cap for the batch phase, h
S_DEPLETE = 0.5                            # g/L -- feed switches on here
T_FEDBATCH = 40.0                          # fixed fed-batch horizon, h

DE_KWARGS = dict(seed=42, tol=1e-7, polish=True, maxiter=40, popsize=14, mutation=(0.5, 1.2))


# ============================================================================
# 4. FEED-FLOW STRATEGIES  F(t, y, params, kinetics)
# ============================================================================

def feed_constant(t, y, p, kin):
    (F0,) = p
    return F0


def feed_exponential(t, y, p, kin):
    F0, mu_set = p
    return F0 * np.exp(mu_set * t)


def feed_linear_ramp(t, y, p, kin):
    F0, k = p
    return F0 + k * t


def feed_two_stage(t, y, p, kin):
    F1, F2, t_switch = p
    return F1 if t < t_switch else F2


def feed_pulsed(t, y, p, kin):
    F_pulse, T_cycle, duty = p
    phase = t % T_cycle
    return F_pulse if phase < duty * T_cycle else 0.0


def feed_exp_linear(t, y, p, kin):
    F0, mu_set, k = p
    return F0 * np.exp(mu_set * t) + k * t


def feed_feedback_control(t, y, p, kin):
    """Proportional control on S, targeting the S set-point that Monod kinetics
    maps to mu_target. Approximates a real-time specific-growth-rate controller."""
    mu_target, Kp = p
    mu_max, Ks = kin['mu_max'], kin['Ks']
    mu_t = min(mu_target, 0.95 * mu_max)
    S_set = Ks * mu_t / (mu_max - mu_t)
    S = y[1]
    return Kp * (S_set - S)


STRATEGIES = {
    'constant': dict(
        fn=feed_constant, names=['F0'],
        bounds=lambda kin: [(1e-3, 0.5)],
        max_step=1.0,
        description='Fixed feed rate for the whole fed-batch phase.',
    ),
    'exponential': dict(
        fn=feed_exponential, names=['F0', 'mu_set'],
        bounds=lambda kin: [(1e-4, 0.2), (1e-3, kin['mu_max'] * 1.05)],
        max_step=1.0,
        description='F(t)=F0*exp(mu_set*t), classic strategy to hold mu ~= mu_set.',
    ),
    'linear_ramp': dict(
        fn=feed_linear_ramp, names=['F0', 'k'],
        bounds=lambda kin: [(1e-3, 0.3), (0.0, 0.05)],
        max_step=1.0,
        description='F(t)=F0+k*t, sub-exponential ramp (mu drifts down over time).',
    ),
    'exp_linear': dict(
        fn=feed_exp_linear, names=['F0', 'mu_set', 'k'],
        bounds=lambda kin: [(1e-4, 0.2), (1e-3, kin['mu_max'] * 1.05), (0.0, 0.05)],
        max_step=1.0,
        description='F(t)=F0*exp(mu_set*t)+k*t, exponential growth-rate control plus a linear top-up.',
    ),
    'two_stage': dict(
        fn=feed_two_stage, names=['F1', 'F2', 't_switch'],
        bounds=lambda kin: [(1e-3, 0.5), (1e-3, 0.5), (1.0, T_FEDBATCH - 1.0)],
        max_step=0.5,
        description='Growth-phase feed F1 until t_switch, then production-phase feed F2.',
    ),
    'pulsed': dict(
        fn=feed_pulsed, names=['F_pulse', 'T_cycle', 'duty'],
        bounds=lambda kin: [(1e-2, 1.0), (0.5, 8.0), (0.05, 0.95)],
        max_step=0.15,
        description='Bolus-like on/off feeding with a fixed cycle length and duty cycle.',
    ),
    'feedback_control': dict(
        fn=feed_feedback_control, names=['mu_target', 'Kp'],
        bounds=lambda kin: [(1e-3, kin['mu_max'] * 0.97), (1e-2, 20.0)],
        max_step=0.5,
        description='Closed-loop proportional control of S towards the set-point for mu_target.',
    ),
}


# ============================================================================
# 5. SIMULATION: BATCH PHASE THEN FED-BATCH PHASE
# ============================================================================

def qp_eval(mu, qp_fn, qp_params, mu_cap):
    """Evaluate qp(mu), capping mu at ~1.2x the literature-observed range so the
    fitted curves are not wildly extrapolated by the optimiser searching for
    growth rates the original chemostat experiments never sampled."""
    mu_c = min(mu, mu_cap)
    return max(qp_fn(mu_c, *qp_params), 0.0)


def simulate_batch(kin, qp_fn, qp_params, mu_cap):
    def rhs(t, y):
        X, S, P, V = y
        X, S = max(X, 0.0), max(S, 0.0)
        mu = kin['mu_max'] * S / (kin['Ks'] + S) if S > 1e-9 else 0.0
        qp = qp_eval(mu, qp_fn, qp_params, mu_cap)
        return [mu * X, -(mu / kin['Yxs']) * X, qp * X, 0.0]

    def event_deplete(t, y):
        return y[1] - S_DEPLETE
    event_deplete.terminal = True
    event_deplete.direction = -1

    sol = solve_ivp(
        rhs, (0.0, T_BATCH_MAX), [X0, S0, P0, V0],
        method='LSODA', rtol=1e-6, atol=1e-9, max_step=1.0, events=event_deplete,
    )
    t_feed = sol.t[-1]
    y_feed = sol.y[:, -1]
    return t_feed, y_feed, sol


def simulate_fedbatch(strategy, params, kin, qp_fn, qp_params, mu_cap, y_feed, max_step):
    fn = strategy['fn']

    def rhs(t, y):
        X, S, P, V = y
        X, S, V = max(X, 0.0), max(S, 0.0), max(V, 1e-6)
        mu = kin['mu_max'] * S / (kin['Ks'] + S) if S > 1e-9 else 0.0
        qp = qp_eval(mu, qp_fn, qp_params, mu_cap)
        F = min(max(fn(t, y, params, kin), 0.0), F_CAP)
        dX = mu * X - (F / V) * X
        dS = (F / V) * (S_IN - S) - (mu / kin['Yxs']) * X
        dP = qp * X - (F / V) * P
        dV = F
        return [dX, dS, dP, dV]

    return solve_ivp(
        rhs, (0.0, T_FEDBATCH), y_feed,
        method='LSODA', rtol=1e-5, atol=1e-8, max_step=max_step, dense_output=True,
    )


def objective(params, strategy, kin, qp_fn, qp_params, mu_cap, y_feed, max_step):
    sol = simulate_fedbatch(strategy, params, kin, qp_fn, qp_params, mu_cap, y_feed, max_step)
    if not sol.success:
        return 1e9
    Xf, Sf, Pf, Vf = sol.y[:, -1]
    total_product = Pf * Vf
    penalty = 1e6 * max(0.0, Vf - V_MAX) ** 2
    return -total_product + penalty


def mean_mu(sol, kin):
    """Time-weighted average specific growth rate actually realised over the run."""
    t, S = sol.t, np.clip(sol.y[1], 0, None)
    mu = kin['mu_max'] * S / (kin['Ks'] + S)
    trapezoid = getattr(np, 'trapezoid', None) or np.trapz
    return trapezoid(mu, t) / (t[-1] - t[0])


# ============================================================================
# 6. MAIN OPTIMISATION SWEEP
# ============================================================================

def fit_qp_model(mtype, mu_data, qp_data):
    fn = MODEL_FNS[mtype]
    kwargs = FIT_P0[mtype](mu_data, qp_data)
    popt, _ = curve_fit(fn, mu_data, qp_data, **kwargs)
    return fn, popt


def run_sweep(verbose=True):
    rows = []
    t_start = time.time()

    for mtype in ['linear', 'bell_shaped', 'hyperbolic']:
        for ds in DATA[mtype]:
            kin = KINETICS[ds['organism_type']]
            qp_fn, qp_params = fit_qp_model(mtype, ds['mu'], ds['qp'])
            mu_cap = ds['mu'].max() * 1.2

            t_feed, y_feed, batch_sol = simulate_batch(kin, qp_fn, qp_params, mu_cap)

            if verbose:
                print(f"\n=== {ds['product']} ({ds['organism_type']}, {mtype}) ==="
                      f"  batch phase ended at t_feed={t_feed:.2f} h, "
                      f"X={y_feed[0]:.3f} g/L, S={y_feed[1]:.3f} g/L")

            for strat_name, strat in STRATEGIES.items():
                bounds = strat['bounds'](kin)
                res = differential_evolution(
                    objective, bounds,
                    args=(strat, kin, qp_fn, qp_params, mu_cap, y_feed, strat['max_step']),
                    **DE_KWARGS,
                )
                sol = simulate_fedbatch(strat, res.x, kin, qp_fn, qp_params, mu_cap, y_feed, strat['max_step'])
                Xf, Sf, Pf, Vf = sol.y[:, -1]
                total_product = Pf * Vf
                avg_mu = mean_mu(sol, kin)

                row = dict(
                    model_type=mtype, product=ds['product'], organism=ds['organism_type'],
                    reference=ds['reference'], strategy=strat_name,
                    total_product=total_product, P_final=Pf, V_final=Vf, X_final=Xf, S_final=Sf,
                    avg_mu=avg_mu, t_feed=t_feed, qp_unit=ds['qp_unit'],
                )
                for name, val in zip(strat['names'], res.x):
                    row[f'param_{name}'] = val
                rows.append(row)

                if verbose:
                    print(f"  {strat_name:<18s} total_product={total_product:10.3f}  "
                          f"avg_mu={avg_mu:.4f} h^-1  params={dict(zip(strat['names'], np.round(res.x, 4)))}")

    if verbose:
        print(f"\nTotal optimisation time: {time.time() - t_start:.1f} s")

    return pd.DataFrame(rows)


def summarise(df):
    """Pick the best strategy per dataset and print/save a ranked table."""
    best_idx = df.groupby('product')['total_product'].idxmax()
    best = df.loc[best_idx].sort_values(['model_type', 'product'])

    print("\n" + "=" * 100)
    print("BEST FEED-FLOW STRATEGY PER DATASET")
    print("=" * 100)
    print(f"{'Model type':<12} {'Product':<32} {'Best strategy':<18} {'Total product':>14} {'avg mu (h-1)':>14}")
    print("-" * 100)
    for _, r in best.iterrows():
        print(f"{r['model_type']:<12} {r['product']:<32} {r['strategy']:<18} "
              f"{r['total_product']:14.3f} {r['avg_mu']:14.4f}")
    print("=" * 100)

    return best


def main():
    df = run_sweep(verbose=True)
    df.to_csv(os.path.join(HERE, 'feed_flow_results.csv'), index=False)
    print(f"\nSaved full results to feed_flow_results.csv ({len(df)} rows)")

    best = summarise(df)
    best.to_csv(os.path.join(HERE, 'feed_flow_best_per_dataset.csv'), index=False)
    print("Saved best-per-dataset summary to feed_flow_best_per_dataset.csv")

    return df, best


if __name__ == '__main__':
    main()
