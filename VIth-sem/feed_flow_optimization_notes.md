# Feed-Flow (F(t)) Strategy Optimisation — Methods & Findings

> Continuation of `mu_qp_visualization.py` (qp-mu literature fits) and
> `simulate_xps.py` (batch X/S/P validation). Code: `feed_flow_optimization.py`
> (optimisation sweep) and `feed_flow_plots.py` (figures).

## 1. Goal

The study notes established the control chain

```
F(t)  ->  D = F/V ~= mu  ->  qp(mu)  ->  P
```

and a qualitative prediction per qp(mu) shape:

| qp(mu) shape | Theoretical feeding rule |
|---|---|
| Linear (Luedeking-Piret) | push mu as high as the data supports |
| Bell-shaped (Gaussian) | hold mu at exactly mu_opt |
| Hyperbolic (saturating) | any mu comfortably above K_mu is fine |

This experiment turns that into a quantitative test: for each of the 9
literature products, six different feed-flow functions F(t) are optimised
end-to-end, and the winner is reported.

## 2. Process model

Every dataset runs in the **same generic reactor** so that only the qp(mu)
*shape* (and the organism's own mu_max/Ks/Yxs) differs between runs — this
keeps the comparison apples-to-apples, the same abstraction `simulate_xps.py`
already used for the batch X/S/P plots.

* **Batch phase** (F=0): X0=0.1 g/L, S0=20 g/L, V0=1 L, integrated with Monod
  kinetics until S depletes to 0.5 g/L — this is when a real fed-batch run
  would switch the pump on.
* **Fed-batch phase** (fixed 40 h horizon): standard four-state mass balance

  ```
  dX/dt = mu*X - (F/V)*X
  dS/dt = (F/V)*(S_in - S) - (mu/Yxs)*X
  dP/dt = qp(mu)*X - (F/V)*P
  dV/dt = F
  mu    = mu_max*S/(Ks+S)
  ```
  with a shared feed reservoir `S_in = 400 g/L`, a working-volume ceiling
  `V_max = 4 L` (4x fill), and a feed-pump cap `F_cap = 2 L/h`.
* `qp(mu)` is evaluated with `mu` capped at 1.2x the largest mu the original
  chemostat data actually covered, so the optimiser cannot exploit
  unrealistic extrapolation of a curve fitted only over a narrow range.
* Integrated with `solve_ivp(method='LSODA')` — orders of magnitude faster
  than `RK45` here because of how stiff the dynamics get once V approaches
  V_max (RK45: ~0.7 s/solve, LSODA: ~0.004 s/solve in benchmarking).

## 3. The six feed-flow strategies

| Strategy | F(t) | Free parameters |
|---|---|---|
| Constant | `F0` | F0 |
| Exponential | `F0 * exp(mu_set * t)` | F0, mu_set |
| Linear ramp | `F0 + k*t` | F0, k |
| Two-stage | `F1` until `t_switch`, then `F2` | F1, F2, t_switch |
| Pulsed | on/off square wave, period `T_cycle`, duty cycle `duty`, amplitude `F_pulse` | F_pulse, T_cycle, duty |
| Feedback control | `Kp * (S_set(mu_target) - S(t))`, clipped >= 0 | mu_target, Kp |

Exponential and feedback-control are the two "control the growth rate"
strategies (open-loop vs. closed-loop); constant/linear/two-stage/pulsed are
practical alternatives that don't require an online growth-rate estimate.

## 4. Optimisation

Each strategy's free parameters are optimised with
`scipy.optimize.differential_evolution` — the same global, derivative-free
optimiser pyFOOMB's `Caretaker.estimate()` uses for its single-machine Tier-1
global estimation (the compiled `assimulo`/`pygmo` stack pyFOOMB normally
runs on could not be installed in this sandbox, so `solve_ivp` +
`differential_evolution` stand in for CVode + pygmo/scipy — same two-tier
idea, portable dependencies).

**Objective**: maximise total product formed, `P(t_f) * V(t_f)`
(mass-balance identity: `d(P*V)/dt = qp(mu)*X*V`, so this is exactly the
time-integral of production, dilution cancels out). A quadratic penalty
applies if the volume ceiling is exceeded.

54 optimisation runs (9 datasets x 6 strategies) were executed; full results
in `feed_flow_results.csv`, one winner per dataset in
`feed_flow_best_per_dataset.csv`.

## 5. Results

### 5.1 Winner per dataset

| qp(mu) shape | Product | Winning strategy | Margin vs. runner-up | Spread best-vs-worst |
|---|---|---|---|---|
| Linear | Resveratrol | **Exponential** | 6.8% | 90.9% |
| Linear | Heterologous Protein (HIP) | **Pulsed** | 4.9% | 183.1% |
| Linear | Crl1 Lipase (SCC) | **Exponential** | 0.5% | 16.3% |
| Bell-shaped | EPG | **Exponential** | 0.1% | 13.3% |
| Bell-shaped | Fab 3H6 | **Exponential** | 6.7% | 62.7% |
| Bell-shaped | ROL | **Exponential** | 1.6% | 18.8% |
| Hyperbolic | Crl1 Lipase (MCC) | **Linear ramp** | 0.1% | 4.9% |
| Hyperbolic | HSA | **Linear ramp** | 0.3% | 5.5% |
| Hyperbolic | alpha-Galactosidase | **Linear ramp** | 0.0% | 1.2% |

(margin/spread = % more total product than the runner-up / worst strategy for
that dataset.)

### 5.2 What this confirms

* **Bell-shaped: exponential feed wins 3/3.** An exponential feed with
  `mu_set` optimised near each product's fitted `mu_opt` is exactly the
  "hold mu at the peak" strategy the theory predicted — and it is also where
  strategy choice matters *most*: bell-shaped datasets show the largest
  best-vs-worst spread (13–63%), because a Gaussian qp(mu) punishes drifting
  away from mu_opt in either direction. Getting the feed law right pays off
  more here than anywhere else.
* **Hyperbolic: linear-ramp (a gentle, near-flat feed) wins 3/3, by tiny
  margins (0–0.3%).** This matches "flexible" almost too well — once mu is
  comfortably above K_mu, qp is already close to qp_max, so *any* reasonable
  strategy is within 1–6% of optimal. This is the most forgiving qp(mu) shape
  to feed for.
* **Linear: exponential wins 2/3** (Resveratrol, Crl1 SCC), consistent with
  "push mu as high as the fitted data supports." **HIP is won by pulsed
  feeding** instead — HIP's Luedeking-Piret fit keeps rising without
  saturating across the whole literature mu-range (0.05–0.30 h⁻¹), so a
  strategy that can transiently spike mu higher than a smooth exponential
  manages (before the V_max budget is spent) captures slightly more product.
  Linear datasets show the largest spreads of all (16–183%): growth-coupled
  products are the most sensitive to *total feed delivered at high mu*, not
  just its shape.

### 5.3 An emergent result the theory didn't predict

Within any single dataset, the **time-averaged mu ends up nearly identical
across all 6 strategies** (typically within +/-0.003 h⁻¹ of one another) even
though the strategies look very different in F(t)-shape. This happens because
the shared `V_max` ceiling fixes the *total* substrate that can ever be
delivered (`(V_max - V0) * S_in`), and Monod growth self-regulates: whatever
the feed-law shape, S settles into a similar quasi-steady balance against
consumption once the system is substrate-limited. So the real lever the
optimiser pulls per dataset isn't "a wildly different average mu" — it's
*how efficiently the fixed feed budget is spent over time* relative to each
qp(mu) curve's shape, which is exactly what shows up as the (sometimes large)
differences in total product between strategies above.

## 6. Practical takeaway

* If a product's qp-mu relationship is **bell-shaped**, invest in a growth-rate
  controller (exponential feed profile, or closed-loop feedback) — the payoff
  for getting the feed law right is the largest of the three categories.
* If it's **hyperbolic**, a simple, low-maintenance feed (linear ramp,
  or even constant) is close enough to optimal — not worth the operational
  complexity of active mu control.
* If it's **linear/growth-associated**, favour exponential feeding to sustain
  the highest mu the data supports, but check whether the qp(mu) fit
  saturates within the sampled range: if it doesn't, more aggressive
  short-pulse feeding right at the start of the feed phase can outperform a
  smooth exponential under a fixed volume budget.

## 7. Reproducing this

```bash
cd VIth-sem
python3 feed_flow_optimization.py   # ~45 min: 54 differential_evolution runs
python3 feed_flow_plots.py          # seconds: re-simulates the 9 winners only
```

Outputs: `feed_flow_results.csv`, `feed_flow_best_per_dataset.csv`,
`feed_flow_strategy_comparison.png`, `feed_flow_best_profiles.png`.

## 8. Roadmap update

This closes the "Fed-Batch Models" and starts the "Parameter Estimation &
Optimisation" items from the project roadmap. Natural next steps: re-run the
sweep with the real pyFOOMB `BioprocessModel`/`Caretaker` stack (CVode +
pygmo, once `assimulo`/`pygmo` are available via conda) so the same feed
strategies can later be validated against real fed-batch experimental data
instead of a shared synthetic reactor.
