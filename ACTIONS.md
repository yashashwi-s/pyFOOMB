# ACTIONS.md — What still needs you, and why

Everything below is stuff this sandbox genuinely cannot finish end-to-end.
Reasons are sandbox-specific (no conda, no persistent hosting, no email
account, no ground-truth experimental data) — not scope I skipped.

## Update (28 Jul 2026): ran everything for real in the `bpdd` conda env

You set up `bpdd` with the actual `assimulo`/`pygmo` stack (`environment.yml`
from #1 below), so this pass verified things the original sandbox couldn't,
and fixed two real bugs found along the way:

- **`pyfoomb/` test suite runs for real**: `mamba run -n bpdd python -m
  pytest tests/` → 485 passed, 9 failed (all `estimate_parallel`/MC-sampling
  tests — see the pygmo-island finding below). CVode itself, and everything
  that doesn't touch pygmo islands, is solid.
- **Web backend boots on the real `pyfoomb`**, no shim needed:
  `web/backend/test_api.py` → 39/39 passed against the real solver.
- **Frontend `npm run lint` and `npm run build` both still pass clean**,
  confirming the #5 claim below still holds after a fresh `npm install`.
- **Bug fixed — `web/backend/main.py`**: any `method=parallel`/`parallel_mc`
  estimate request crashed instantly with `ValueError: signal only works in
  main thread of the main interpreter`. Cause: `pygmo.mp_island` lazily
  spawns its worker-process pool on first use via a call that includes
  `signal.signal(...)`, which only works on a process's main thread —
  but FastAPI/Starlette runs sync route handlers in a worker thread. Fixed
  by calling `pygmo.mp_island.init_pool()` once at app import time (main
  thread, before uvicorn starts serving); later per-request inits then
  become no-ops. Verified live via the API.
- **Found, NOT fixed — pygmo/pagmo build itself is broken in `bpdd`**: once
  the threading crash above is out of the way, every pygmo optimizer
  algorithm (`sga`, `de1220`, `pso`, `bee_colony`, `sea`,
  `simulated_annealing`, `compass_search` — tested all of them) fails
  identically on `mp_island` evolve with `RuntimeError: unregistered void
  cast ... algo_inner<X> <- algo_inner_base`. Reproduces with a bare
  `pickle.dumps((pygmo.algorithm(X), population))`, no pyfoomb or
  multiprocessing involved — it's a broken (un)pickling registry in this
  exact `pygmo=2.19.7`/`pagmo=2.19.1` conda-forge build for osx-arm64/py39
  (no other py39 build exists on conda-forge to try instead). I looked at
  swapping the archipelago's island type to `pygmo.thread_island` (which
  sidesteps pickling entirely and does work in isolation) but **rejected
  it**: `LossCalculator.get_model_loss` calls back into the *same* shared,
  mutable `Caretaker`/simulator/CVode instance for every island, so
  concurrently-evolving thread islands would race on `set_parameters()` +
  simulate and silently corrupt results instead of crashing — worse than
  the current, loud failure. This needs either an upstream pygmo/pagmo fix
  or a different pygmo build; it is not safely fixable in `pyfoomb` code.
  This resolves the "Not verified" note on the pygmo-island path in #5.
- **Bug found and fixed — `VIth-sem/feed_flow_optimization.py`**: the
  working-volume ceiling (`V <= V_MAX`) was enforced only as a soft
  quadratic penalty in the DE objective, which barely bites right at the
  boundary. Checked against the committed `feed_flow_results.csv`: **57 of
  63 optimized runs ended with `V_final > V_MAX`** (median +0.7%, worst case
  EPG/`exp_linear` at +8.6%), i.e. most "winning strategies" in
  `feed_flow_optimization_notes.md` and `email_to_prof_draft.txt` came from
  a search space that overflows the reactor it claims to model. Fixed by
  clipping the feed to zero once `V >= V_MAX` inside the ODE right-hand side
  itself (`simulate_fedbatch`) — the pump physically stops at a full vessel,
  same as a real fed-batch — instead of relying on a penalty. Re-verified
  the worst two offenders directly: `V_final` now lands at `4.0000`–`4.0001`
  L (numerical tolerance only) instead of `4.34` L.
  **I did not rerun the full 63-run sweep** (~45 min, and it would rewrite
  `feed_flow_results.csv`, the plots, `feed_flow_optimization_notes.md`,
  `presentation.tex`/`presentation_script.md`, and the professor email draft
  — all of which currently reflect the pre-fix, volume-violating numbers).
  Rerun `python VIth-sem/feed_flow_optimization.py` and regenerate the plots
  before citing/presenting any of those numbers again; margins were tight
  enough on a couple of datasets (Resveratrol ~0.4%, Crl1-SCC ~0.5%) that
  the winning strategy could change once the ceiling actually holds.
- Minor: `feed_flow_optimization.py`'s module docstring said "6 feed-flow
  strategies"/"rank the 6 strategies" even though `exp_linear` had already
  brought the count to 7 (`STRATEGIES` dict, `feed_flow_optimization_notes.md`
  correctly said 7) — fixed the docstring, no behavior change.
- Minor a11y bug fixed: `Toast.tsx` gave every toast `role="status"` (a
  polite live region) even for `type: "error"`, while the sibling
  `StatusMessage.tsx` correctly used `role="alert"` for errors. Error toasts
  now use `role="alert"` too, so screen readers announce them assertively
  like the inline error banners do.
- Noted, not changed: `feedback_control`'s DE bounds allow `mu_target` up to
  `0.97 * mu_max`, but `feed_feedback_control` internally clips at
  `0.95 * mu_max` — the `[0.95, 0.97]` slice of the search space is dead
  (always maps to the same setpoint). Harmless, just wastes a little DE
  budget; not worth touching without a full rerun anyway given the fix above.

## 1. Real pyFOOMB solvers (assimulo / pygmo) — not pip-installable here

`pyfoomb/modelling.py` hard-imports `assimulo.solvers.sundials.CVode`, which
needs the compiled SUNDIALS C library + conda. `pip install assimulo` fails
in this sandbox (no Cython/SUNDIALS headers). `pygmo` *did* install fine via
pip here, so only `assimulo` is the real blocker.

**To unblock the actual pyFOOMB package and its real notebooks/tests:**
```bash
conda env create -f environment.yml
conda activate pyfoomb
pip install -e .
```

**What I did instead, locally, to still get real work done:**
- `VIth-sem/feed_flow_optimization.py` uses `scipy.integrate.solve_ivp`
  (LSODA) + `scipy.optimize.differential_evolution` directly — the same
  two-tier idea (ODE integrator + global optimiser) pyFOOMB itself uses
  (CVode + pygmo/scipy), just with portable dependencies. This is a
  legitimate, independent implementation, not a stand-in that needs replacing
  — but if you want the feed-flow study re-validated against the *actual*
  pyFOOMB `Caretaker`/`BioprocessModel` classes (e.g. for a thesis chapter),
  that's the natural next step once you have the conda env.
- To exercise the web backend (which imports the real `pyfoomb` package) I
  wrote a **temporary, local-only shim** at `/tmp/assimulo_shim` that
  satisfies the exact `Explicit_Problem`/`CVode` surface pyFOOMB calls
  (verified against `modelling.py`/`simulation.py`), backed by
  `solve_ivp` instead of SUNDIALS. **This was never added to the repo, is
  not a dependency of anything committed, and disappears when this
  container is reclaimed.** It let me boot the FastAPI backend and click
  through the real GUI with real math (verified: Monod batch growth,
  yield-conserving mass balance, and event-driven bolus feeding all
  integrate correctly). If you want to do the same locally without conda,
  ask for the shim's source and drop it on `PYTHONPATH` ahead of `pyfoomb`
  — but for anything you'll cite or publish, use the real conda env instead.
- **This is now moot**: the `bpdd` conda env (real assimulo + pygmo) exists,
  so the shim is no longer needed — see the 28 Jul 2026 update at the top of
  this file for what running for real actually found.

## 2. Feed-flow optimisation numbers are one DE run, not a proven global optimum

`differential_evolution` ran with `maxiter=40, popsize=14` per strategy per
dataset (63 runs total, ~45 min) — good enough to rank strategies and see a
qualitative pattern, not proven to have found the exact global optimum for
each. If a number needs to go in a thesis/paper, rerun with a larger budget
and a few different seeds and check the results don't move.

## 3. Reactor assumptions are synthetic, not lab-calibrated

`V0=1L, V_max=4L, S_in=400 g/L, T_fedbatch=40h` are the same for all 9
products, chosen so the qp(mu) *shape* is the only thing varying across
comparisons (documented in `feed_flow_optimization_notes.md`). Before using
these numbers for an actual bioreactor run, swap in your lab's real working
volume, feed concentration, and pump limits.

## 4. Literature qp-mu data points are manually digitised

The 9 datasets in `mu_qp_visualization.py`/`simulate_xps.py`/
`feed_flow_optimization.py` were read off published figures/tables by eye —
no automated plot-digitisation tool was used in this session. Worth a
second pass against the original papers (or a tool like WebPlotDigitizer) if
precision matters.

## 5. Website: UI/UX overhaul done, but still needs to be run/deployed by you to demo it

Done (commit `a6ed980`): design tokens consolidated out of inline styles into
Tailwind, a real cascade bug fixed (custom CSS was silently beating
conditional Tailwind classes — the selected-template highlight and active-tab
underline never actually showed color), unicode glyph icons replaced with
`lucide-react`, loading/empty/error states added everywhere data is fetched,
the sensitivity-analysis chart fixed (was drawing 20+ series on one
categorical axis — now faceted per state with a real numeric time axis), the
sidebar made responsive (drawer below `md` instead of eating half a phone
screen), and the `eslint`/`eslint-config-next` toolchain fixed (`npm run
lint`/`npm run build` were silently never working before — both pass clean
now). Verified against a real running backend + real browser (Playwright),
screenshots before/after on disk if you want to see more than what was sent
to you.

**Update**: the pygmo-island (`estimate_parallel`) and Monte-Carlo estimation
methods are now verified, not just "worth a click-through" — see the 28 Jul
2026 update at the top of this file for what's fixed (a real FastAPI-threading
bug) versus what's genuinely blocked (a broken pygmo/pagmo build in `bpdd`).

This sandbox's frontend/backend processes still die when the container is
reclaimed — nothing here is a persistent URL. To show it to your professor:
```bash
# backend (needs the real conda env from #1 above, not the /tmp shim)
cd web/backend && pip install -r requirements.txt && uvicorn main:app --reload
# frontend, separate terminal
cd web/frontend && npm install && npm run dev
```
or use the existing `web/start.sh` / `web/start-docker.sh`.

## 6. Email to your professor — drafted, not sent

`VIth-sem/email_to_prof_draft.txt` is ready to copy-paste. No email
connector was authorized in this session, so nothing was actually sent.

## 7. Not attempted (out of scope for this session)

- Real experimental fed-batch data to validate any of this against (roadmap
  item "Experimental Validation" — needs actual lab runs).
- Scale-up analysis (roadmap item) — no pilot/production-scale data exists
  yet to scale to.
- A `Canva` MCP connector showed up as available-but-unauthenticated; not
  used since nothing here needed it. If you want a Canva-based deck instead
  of the matplotlib figures, authorize it via your claude.ai connector
  settings first.

## Future plan (from the project roadmap)

1. Port `feed_flow_optimization.py`'s ODE model + 7 feed strategies into
   real `pyfoomb.BioprocessModel` subclasses once the conda env is set up,
   and re-optimise with `Caretaker.estimate_parallel()` (pygmo islands)
   instead of `differential_evolution`, as a numerics cross-check.
2. Replace the synthetic reactor assumptions (#3) with real lab bioreactor
   constraints once you're ready to test a strategy on the bench.
3. Add a "Feed-flow optimisation" page to the web GUI (currently only in
   `VIth-sem/` as standalone scripts) once the backend runs on the real
   solver stack — turn the 7 strategies into a template families the GUI
   ranks live, the way `model_templates.py` already ranks kinetic models.
4. Validate the winning strategy per product against real fed-batch runs
   (roadmap: "Experimental Validation"), then revisit scale-up.
