# Native pyFOOMB feed study

The October 2026 extension adds linear → exponential, exponential → linear,
exponential → exponential, and linear → linear feeding. The expanded comparison
is saved separately in [two_stage_extension/](two_stage_extension/README.md),
with all 11 families across nine datasets (99 cases). The `final/` files below
remain the earlier 63-case baseline; use the extension for the new comparisons.

All 63 product/strategy cases have at least one completed optimization using a real pyFOOMB model and CVode simulations. Completed searches: 60 fresh Caretaker differential-evolution runs and 61 pygmo runs. Seven unfinished duplicate searches were stopped after every case was covered, following the request to finish faster. Completed checkpoints remain resumable.

## Scientific workflow

1. Fit literature qp(mu) points with the same SciPy curve_fit models as the reference study.
2. Implement batch and fed-batch equations as pyfoomb.BioprocessModel subclasses.
3. Run actual Caretaker.simulate calls through Simulator, Assimulo and SUNDIALS CVode.
4. Override Caretaker.loss_function for process design: minimize negative final P times V. This differs from fitting measurements.
5. Use Caretaker.estimate for fresh differential evolution and Caretaker.estimate_parallel_continued for the pygmo archipelago.
6. Replay completed candidates and reference settings at CVode rtol 1e-8 and atol 1e-11. Select the best evaluated candidate per case.

The installed pygmo multiprocessing serialization is broken. Custom locked in-process islands avoid serializing C++ algorithms. Islands within one case evolve serially. Independent cases run in separate processes with independent Caretakers. This does not claim that unchanged estimate_parallel or parallel island execution works in this environment.

## Results and comparison

The same-settings LSODA/CVode comparison covers all 63 cases. The maximum absolute product difference is 0.01094%. Final selection uses 184 tightly evaluated native candidates. All final volumes are 4 L or less, with maximum relative biomass/substrate balance error 1.58e-7.

Best found patterns: exponential for the three bell-shaped datasets and two linear datasets, exponential plus linear for HIP, and linear ramps for the three hyperbolic datasets. The HIP hybrid/exponential margin is only 0.000011%. All nine winning strategies have at least one alternative within 0.1%, which is a reporting convention rather than a significance test.

The largest improvement for a particular strategy over its replayed reference settings is about 6.19%. Similar numerical solvers do not imply identical optimization results. These are finite-budget, model-based rankings. Experimental validation is the next scientific step.

## Files

- `solver_comparison.csv`: same settings, two solvers.
- `caretaker/` and `pygmo/`: completed search records and diagnostics.
- `checkpoints/`: completed per-case records for resumption.
- `final/feed_flow_results.csv`: final 63-case native results.
- `final/best_per_dataset.csv`: winner, margin and near alternatives.
- `final/candidate_audit.csv`: every tight native replay and original search score.
- `final/optimization_comparison.csv`: changes caused by searching feed settings.
- `final/run_metadata.json`: methods, counts, solver tolerances and code hashes.
- `final/profiles/`: actual native trajectories used for the figures.

The 12-slide Beamer source uses the original IIT BHU logo and plots of the native pyFOOMB results. Compile with XeLaTeX from `VIIth-sem`; the exported `presentation.pdf` includes these assets. The desktop editor's single-file compiler cannot resolve the companion images. Earlier source and PDF versions are preserved under `archive/`.
