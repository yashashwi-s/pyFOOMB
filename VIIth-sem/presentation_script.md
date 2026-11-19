# Speaker notes for the revised Beamer presentation

## 1. Title

We study how the relationship between growth rate and specific product formation should influence feeding in a fed-batch reactor. We use nine literature datasets and compare five feed strategies under shared reactor assumptions.

## 2. Project roadmap

The previous semester established the fitted production relationships and batch simulations. The current work adds a fed-batch model, uses actual pyFOOMB BioprocessModel and Caretaker objects, and evaluates feeding schedules with Assimulo and SUNDIALS CVode. The optimizer varies the feed settings while keeping the fitted biology fixed. The main scientific next step is validation against experimental fed-batch measurements.

## 3. Growth and production

Specific growth rate mu measures growth per unit biomass per hour. Specific product formation qp measures product per unit biomass per hour.

A linear relationship rises with growth over the fitted range. A bell-shaped relationship peaks at an intermediate rate. A hyperbolic relationship approaches a plateau.

Feeding changes substrate availability. Substrate affects growth through Monod kinetics. Growth then affects specific production. Total product also depends on the amount of biomass and how long it remains productive.

Dilution D = F/V is not generally equal to mu in fed-batch. They are approximately equal only if biomass concentration is roughly constant, because dX/dt = (mu-D)X.

## 4. Process model

X, S and P are concentrations. V is liquid volume. Cells grow, consume substrate and form product. Feeding increases volume and changes concentrations through dilution.

Dilution does not mean cells or product leave the reactor. Product amount is P times V. Its rate of change is qp times X times V: the dilution terms cancel when concentration is converted to amount.

The model begins at X0 = 0.1 g/L, S0 = 20 g/L, P0 = 0 and V0 = 1 L. Batch operation continues until S = 0.5 g/L. The feed phase then lasts 40 hours. Feed contains 400 g/L substrate, the pump limit is 2 L/h, and working volume is limited to 4 L. These are shared modelling assumptions, not experimental operating conditions fitted for each product.

CVode integrates the equations numerically through Assimulo. Events handle the batch transition, pump switching and end of feeding. The model omits oxygen-transfer limitation, maintenance, biomass death and product degradation. Experimental validation should assess which additional mechanisms are needed.

## 5. The pyFOOMB optimization workflow

The main implementation files are pyfoomb_feed_model.py and pyfoomb_feed_optimization.py.

BioprocessModel contains the reactor equations, production relationship and feeding logic. Caretaker manages model parameters and simulations. Its Simulator constructs the Assimulo CVode solver for each simulation.

The custom ProductCaretaker subclass defines a process-design objective: minimize negative final product amount. The standard measurement-fitting objective would not optimize product yield automatically.

Caretaker.estimate runs differential evolution. For each candidate parameter vector, the loss function calls Caretaker.simulate, reads final P and V, and returns -P*V. Repeating this process searches for better feed settings.

The pygmo branch uses pyFOOMB LossCalculator, PyfoombArchipelago and Caretaker.estimate_parallel_continued. Each case has two populations with different seeds. This installed pygmo build cannot serialize algorithms to mp_island workers. A custom in-process island avoids that serialization. A lock serializes islands within a case. Independent cases run in separate processes, each with its own model and solver. Do not claim simultaneous island execution within a case or that the unchanged estimate_parallel entry point works.

The fresh Caretaker search uses seed 42, population multiplier 14, 40 generations and polishing. The additional pygmo search includes the previous best settings as one candidate, evaluated afresh with CVode. Final candidates are re-evaluated with tighter CVode tolerances before selecting the best per strategy. A finite search budget does not prove a global optimum.

## 6. Five strategies

Constant: one fixed pump flow.

Exponential: F0 exp(mu_set*t). F0 sets initial flow and mu_set sets the rate at which the feed grows. mu_set is a feed-profile parameter, not a guaranteed actual cellular growth rate. Exponential feeding is motivated by exponentially growing biomass demand.

Linear ramp: F0+k*t. k is the additional flow added per hour, with units L/h squared.

Exponential plus linear: combines the two terms. Extra flexibility can improve a fit, but a tiny score difference does not establish practical superiority.

Two-stage: use F1 until t_switch, then F2. The optimizer chooses the two flows and the switching time. The switch does not necessarily correspond to a biological phase transition.

All five strategies obey the shared pump and volume constraints.

## 7. Best strategy per dataset

The table reports the best settings found after native CVode replay. It is a numerical ranking within this model and search budget.

When two strategies differ by less than 0.1%, describe them as close in this comparison. The 0.1% threshold is a reporting convention, not a statistical significance test. Exact rankings and differences are recorded in pyfoomb_results/final/best_per_dataset.csv.

## 8. Strategy comparison

Compare bars within each product panel. All strategies share the reactor assumptions for that dataset. Product units differ across datasets, so comparing absolute bar heights across different products is not meaningful.

A taller bar means greater final product amount. It does not necessarily mean greater final concentration or a practically better laboratory strategy.

## 9. Time courses

Explain the batch phase, the start of feeding, substrate availability, biomass accumulation and product formation. The plots show actual native pyFOOMB trajectories. Product concentration has its own axis and volume appears separately.

Discuss the process dynamics that produce the endpoint, rather than only saying which line is highest.

## 10. Findings

Exponential feeding ranks first for two of the three linear products and all three bell-shaped products. The hybrid ranks first for HIP, but its lead over exponential feeding is negligible. Linear ramps rank first for all three hyperbolic products.

All nine products have another strategy within 0.1% of the winner. This is a reporting threshold, not a statistical significance test. Several feeding laws can produce almost the same endpoint, so pump simplicity and experimental performance matter when choosing between them.

At identical feed settings, total product from CVode and LSODA differs by at most 0.0052% across the 45 cases. This supports numerical agreement; it does not validate the biology. Finite search budgets do not prove a global optimum.

## 11. Web platform: two bug fixes

First, worker-pool startup called signal handling inside a FastAPI request thread and crashed. Initialising the pool at app startup on the main thread removes that startup crash. This fix alone does not resolve the separate installed pygmo build's algorithm serialization issue.

Second, error toasts used the ordinary status role. They now use the alert role, so screen readers announce errors promptly.

The frontend is Next.js and React. FastAPI handles requests. pyFOOMB and Assimulo/CVode perform simulations. Feed optimisation is currently a separate scientific workflow; adding its controls and results to the web interface is future work.

## 12. Closing

We fitted literature growth-production relationships, implemented a fed-batch reactor in pyFOOMB, and optimised five feed strategies using CVode simulations. The next step is experimental validation: measure X, S, P and the actual feed schedule, fit parameters on calibration runs, and test predictions against a separate run.
