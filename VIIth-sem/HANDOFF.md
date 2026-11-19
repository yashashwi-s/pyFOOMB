# Semester VII handoff

The current 99-case comparison uses shared synthetic reactor conditions. Its plots and saved trajectories are in `pyfoomb_results/two_stage_extension/final/`. Keep these as the common-condition comparison when producing the paper-specific runs. The September 63-case native baseline is in `pyfoomb_results/final/`.

## Source conditions

For every case record the primary paper and exact figure/run, organism and product, operating mode, initial biomass/substrate/product/volume, substrate identity, feed formulation, feed trigger, and stopping criterion. Mark unreported values explicitly. A steady-state chemostat supplies kinetics at a particular dilution rate. A corresponding batch-to-fed-batch replay requires a separate experimental reference or an explicitly identified scenario.

- **Fab 2F5 benchmark:** García-Ortega et al. (2013), [Figure 2A and Table 3](https://doi.org/10.1016/j.bej.2013.07.013). Initial working volume 2 L, nominal initial glycerol 40 g/L, exponential glucose feed (400 g/L glucose) following glycerol depletion. Nominal growth targets 0.05, 0.10 and 0.15 h⁻¹. The experiments stopped at about 100 g/L dry biomass. Start with Figure 2A at 0.10 h⁻¹. Initial biomass and exact pump time series still need sourcing or an explicit estimate. Digitise the measured curves and retain the separate glycerol and glucose identities. The repo Fab entry is labeled 3H6. Resolve its kinetic-data provenance separately.
- **HSA:** Rebnegger et al. (2014), [primary paper](https://doi.org/10.1002/biot.201300334). The growth-rate series comes from glucose-limited chemostats. A matching fed-batch run still needs sourcing.
- **Resveratrol, HIP, Crl1 SCC, EPG, ROL, Crl1 MCC, and α-galactosidase:** source leads are in `../VIth-sem/simulate_xps.py` and the active dataset definitions in `feed_flow_optimization.py`. Verify figure/run identity and conditions before changing any defaults.

## Resume

1. Parameterise the reactor conditions per experimental case and pass them through both batch and fed-batch models, including the volume event, replay and plot labels.
2. Compare Fab 2F5 trajectories against Figure 2A. Account for any estimated values when interpreting disagreement. Continue with Table 3 once the baseline works.
3. Run new optimisations into a separate output directory and preserve checkpoint provenance. See `pyfoomb_results/two_stage_extension/README.md` for existing replay and plotting commands.
4. Build the presentation from this directory with `xelatex ugp-semester-vii.tex` twice. The deck presents the completed generic comparison and marks the paper-based benchmarks as pending.
