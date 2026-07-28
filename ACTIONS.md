# ACTIONS.md — What still needs you, and why

Everything below is stuff this sandbox genuinely cannot finish end-to-end.
Reasons are sandbox-specific (no conda, no persistent hosting, no email
account, no ground-truth experimental data) — not scope I skipped.

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

**Not verified**: the pygmo-island (`estimate_parallel`) and Monte-Carlo
estimation methods — `pygmo` itself installed and imports fine via pip here,
but a full multi-island run wasn't executed to completion given time. Worth
a manual click-through once you have this running locally.

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
