# Two-stage feed study: expanded native comparison

Completed 5 October 2026. All four new sequences were optimized for each of the nine literature datasets. The comparison contains 11 feed families and 99 product–strategy cases. Earlier outputs remain in `../final/`.

## Stage definitions

The original two-stage family switches between two constant rates. The four additions switch between these laws:

| Family | Stage 1, before the switch | Stage 2, after the switch |
|---|---|---|
| Linear → exponential | F1 + k1*t | F2*exp(mu2*(t-ts)) |
| Exponential → linear | F1*exp(mu1*t) | F2 + k2*(t-ts) |
| Exponential → exponential | F1*exp(mu1*t) | F2*exp(mu2*(t-ts)) |
| Linear → linear | F1 + k1*t | F2 + k2*(t-ts) |

`t` is hours since feed start and `ts` is the optimized switch time, restricted to 1–39 h. F1/F2 are independently optimized stage-start rates; a feed jump at the switch is allowed, as in constant → constant. Stage two starts its own clock. Linear slopes and exponential growth rates are nonnegative; zero is an allowed constant-feed limit. The older exponential + linear strategy adds both terms simultaneously and remains a separate family.

Linear start rates use 0.001–0.3 L/h and slopes 0–0.05 L/h². Exponential start rates use 0.0001–0.2 L/h and growth rates 0–1.05 times organism mu_max. The pump cap is 2 L/h.

## Best found results versus the earlier best

The earlier seven families retain their completed native searches. Each new family has two completed Caretaker differential-evolution searches: a fresh population with seed 42, and a population informed by adapted earlier profiles with seed 43. Both use 40 generations, population multiplier 14, polishing, and the same negative final P*V objective. Every search and adapted candidate is replayed at CVode rtol 1e-8 / atol 1e-11 before selection.

| Dataset | Earlier best | Expanded best found | Gain over earlier best |
|---|---|---|---:|
| EPG (Polygalacturonase) | Exponential | Linear → exponential | +0.486675% |
| Fab 3H6 (PGAP) | Exponential | Linear → exponential | +0.402369% |
| ROL (Rhizopus oryzae Lipase, PAOX1) | Exponential | Exponential → exponential | +1.279458% |
| Crl1 Lipase (MCC, PGAP) | Linear ramp | Linear → linear | +0.100662% |
| HSA (Human Serum Albumin) | Linear ramp | Linear → linear | +0.003947% |
| alpha-Galactosidase | Linear ramp | Exponential → linear | +0.009018% |
| Crl1 Lipase (SCC, PGAP) | Exponential | Linear → exponential | +0.000968% |
| Heterologous Protein (HIP) | Exponential + linear (additive) | Exponential → exponential | +0.000634% |
| Resveratrol | Exponential | Exponential → exponential | +0.000453% |

The largest gain is for ROL (about 1.28%). EPG and Fab improve by about 0.49% and 0.40%. Several other differences are under 0.01% and should be treated as near ties. Search budgets differ between the retained baseline and new families; these are best found settings, with no proof of global optimality or statistical significance. The synthetic reactor assumptions and digitised literature fits are unchanged.

## Verification

- 72 completed new searches; 972 tightly replayed candidates.
- All 99 exported final volumes are at most 4 L. Raw new CVode volume is checked before any exported-array clipping; its largest value is 4 L plus roundoff below 3e-13 L.
- Maximum relative biomass/substrate balance residual across the expanded study: 1.580e-07.
- Maximum absolute LSODA/CVode product discrepancy for the 36 new selected profiles: 0.00003227%. These replays share the native batch endpoint and use tight tolerances.
- Five scientific checks pass, covering stage-clock reset, preserved historical indices, independent solver agreement and conservation, constant-feed equivalence, and the event/output sampling regression.
- CVode can reject an output request coinciding exactly with a stage root. The affected replay samples 1e-6 h after the switch. The physical event and parameters are unchanged. Thirty-five already validated cases were retained from before that sampling-only fix; per-case source hashes are recorded.
- The second stage is physically active in 32 of 36 selected new profiles. In four cases the vessel fills before the scheduled switch, so that second stage never feeds. The CSV records this explicitly.

## Figures and data

- [All 11 strategies: product comparison](final/strategy_comparison.png)
- [Relative performance across datasets](final/relative_performance_heatmap.png)
- [New families versus the earlier best](final/two_stage_vs_previous.png)
- [Actual optimized feed-rate profiles](final/two_stage_feed_profiles.png)
- [Product accumulation curves](final/two_stage_product_profiles.png)
- [Best X/S/P/V trajectories](final/best_profiles.png)
- [Linear → exponential X/S/P/V](final/two_stage_linear_exp_profiles.png)
- [Exponential → linear X/S/P/V](final/two_stage_exp_linear_profiles.png)
- [Exponential → exponential X/S/P/V](final/two_stage_exp_exp_profiles.png)
- [Linear → linear X/S/P/V](final/two_stage_linear_linear_profiles.png)
- [Illustrative two-stage laws](final/two_stage_schematics.png)
- [All-case working-volume check](final/volume_validation.png)

`final/feed_flow_results.csv` contains all 99 rows and feed parameters. `two_stage_vs_previous.csv` contains exact gains. `best_per_dataset.csv` includes nearest alternatives. The 72 optimizer records, candidate audit, solver checks, metadata and saved native trajectories are also in `final/`. Plots read saved trajectories and do not rerun optimizations.

## Reproduce

From `VIIth-sem/`, with the existing native solver environment active:

```bash
python -m unittest test_two_stage_feeds -v
python extend_two_stage_study.py --workers 4
python plot_two_stage_extension.py
```

The search resumes validated checkpoints for the matching code/baseline revision. A clean run performs both searches for all 36 cases. To regenerate only figures, run the last command. The original presentation continues to use the earlier 63-case figures.
