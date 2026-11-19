# Feed-flow strategy study: refreshed results

For the October 2026 comparison including four new sequential two-stage feed
families, use [the native pyFOOMB extension](pyfoomb_results/two_stage_extension/README.md).
Its 99-case results and figures are separate from the earlier seven-family
SciPy results described below. The sequential exponential → linear family is
different from the additive `F0*exp(mu*t) + k*t` family.

Updated 30 September 2026. The original outputs are retained in `archive/pre_volume_fix/`.

## Scope and procedure

Nine digitised literature datasets describe specific product rate as a function of growth rate: three linear, three Gaussian bell-shaped, and three hyperbolic fits. `curve_fit` estimates the parameters by nonlinear least squares. These are manually extracted points, with no measurement-uncertainty model.

The same generic reactor is used for each dataset, with organism-specific Monod constants. Initial conditions are X=0.1 g/L, S=20 g/L, P=0, V=1 L. The batch phase ends at S=0.5 g/L. The feed phase lasts 40 h, with 400 g/L feed, a 2 L/h pump cap, and a 4 L vessel ceiling.

The control sequence is F(t) -> substrate availability -> growth rate -> fitted product rate -> product accumulation. Volume also changes dilution. Equating F/V with growth rate is an additional steady-concentration assumption, rather than a general fed-batch identity.

## Numerical methods

LSODA solves the four-state mass balances. A terminal event detects V=4 L, then a separate no-feed integration completes the horizon. This avoids repeated solver steps around a discontinuous volume cutoff. Saved and dense-interpolated volume obey the vessel ceiling.

Differential evolution searches the parameters of seven feed families: constant, exponential, linear ramp, exponential plus linear, two-stage, pulsed, and substrate-feedback control. Each search uses seed 42, up to 40 generations, population multiplier 14, and polishing. The objective is total final product P(tf)*V(tf). This includes product accumulated in the preceding batch phase.

Completed searches from the corrected RHS cutoff and the explicit volume-event implementation were reused. All saved candidates were replayed with the final event model; the highest final product was retained for each of the 63 product-strategy cases. `optimization_run_diagnostics.csv` records the search implementation and selected candidates; `optimization_run_metadata.json` records the final model hash and checks. Duplicate searches use the same seed and budget. These are best found values, with uneven convergence across cases; they do not establish global optima or uncertainty in rankings.

## Best found strategy per dataset

Margin is relative to the runner-up; spread is relative to the weakest tested strategy in the same product. Product units differ across datasets.

| Shape | Product | Best found | Margin | Spread |
|---|---|---|---:|---:|
| linear | Resveratrol | Exponential | 0.003% | 59.3% |
| linear | Heterologous Protein (HIP) | Exponential | 0.003% | 10.6% |
| linear | Crl1 Lipase (SCC, PGAP) | Exponential | 0.002% | 10.8% |
| bell_shaped | EPG (Polygalacturonase) | Exponential | 0.000% | 20.8% |
| bell_shaped | Fab 3H6 (PGAP) | Exponential | 0.013% | 62.3% |
| bell_shaped | ROL (Rhizopus oryzae Lipase, PAOX1) | Exponential | 0.010% | 18.2% |
| hyperbolic | Crl1 Lipase (MCC, PGAP) | Linear ramp | 0.007% | 8.0% |
| hyperbolic | alpha-Galactosidase | Linear ramp | 0.000% | 8.4% |
| hyperbolic | HSA (Human Serum Albumin) | Linear ramp | 0.016% | 9.9% |

The bell-shaped and linear datasets favour exponential feeding in these saved searches; hyperbolic datasets favour linear ramps. Several leads are very small. A fitted qp peak alone does not specify the total-product optimum: the optimiser also trades biomass, feeding time, and the fixed reactor budget. Treat the shape-wise patterns as findings of this synthetic study.

## Verification and limitations

All 63 final trajectories respect V <= 4 L. The maximum relative biomass/substrate balance residual is below 0.004%. The earlier saved results had a maximum final volume of 4.344 L and are unsuitable as constrained-study rankings.

A smaller-step replay of every pulsed candidate is saved in `pulse_step_verification.csv`; halving the refined step changed product totals by less than 0.003%. Pulsed parameter searches used a coarser integration, so re-optimisation with the refined integration remains a next step. Further work is repeated seeds, larger search budgets, uncertainty and sensitivity analysis, experimental fed-batch validation, and a GUI feed-optimisation page. The present standalone study uses SciPy; porting to pyFOOMB/CVode remains a future numerical cross-check.

## Reproducing the figures and study

Run from `VIIth-sem/` using an environment with NumPy, SciPy, pandas, and matplotlib:

```bash
python rerun_corrected_sweep.py        # fresh full 63-case search; resumable checkpoints
python feed_flow_plots.py             # comprehensive study figures
python feed_flow_linear_ramp_summary.py
python build_presentation_figures.py   # six readable slide figures
```

The visual Beamer deck is `presentation.tex`; its rendered deliverable is `presentation.pdf`. `presentation_script.md` holds the fuller explanations.
