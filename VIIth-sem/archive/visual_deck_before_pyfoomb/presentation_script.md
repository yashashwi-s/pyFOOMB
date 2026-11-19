# Speaker notes for the visual progress deck

Suggested pace: about 8 minutes. The slides hold the figures; these notes carry the explanation.

## 1. Title
The project asks how a fed-batch feed schedule can increase total product. The workflow starts with literature product-formation kinetics, puts them into a process model, and searches for feed parameters. This deck recaps the earlier work and shows the refreshed feed-strategy study.

## 2. Recap: web interface
Last semester I built a browser interface around pyFOOMB. A user can define a model, simulate it, import measurements, estimate parameters, and analyse the fit. The screenshot is from that earlier interface. Feed-strategy optimisation currently runs in separate study scripts; adding it to this interface is a next step.

## 3. Recap: fitted product rates
The nine datasets cover three fitted forms: linear, bell-shaped, and hyperbolic. Here are representative products. The points were manually digitised from literature and the curves were fitted by nonlinear least squares. R-squared describes how closely the curve follows these points. It does not establish that the relationship transfers unchanged to a real fed-batch run.

## 4. Recap: batch simulation
The fitted product rate is coupled to a Monod growth model. Biomass grows, substrate is consumed, and product accumulates. This example runs until substrate falls to 0.5 g/L. That becomes the starting state for the feed phase. These are illustrative model predictions using generic organism kinetics, with no experimental validation implied.

## 5. Fed-batch model
The new state is volume. Feed brings in substrate and increases volume, so biomass and product concentrations also experience dilution. The same reactor assumptions are used for all products: 1 L initially, a 4 L ceiling, 400 g/L feed, a 2 L/h pump cap, and a 40-hour feed phase. Feed affects substrate, substrate affects growth, and growth enters the fitted product-rate relationship.

## 6. Seven feed laws
I compared constant, exponential, linear ramp, exponential plus linear, two-stage, pulsed, and feedback feeds. The curves on this slide illustrate the families, rather than fitted operating schedules. Each has its own adjustable parameters. Feedback uses the current substrate concentration; the other families follow a schedule.

## 7. Analytical methods
There are three numerical steps. First, nonlinear least squares estimates the product-rate parameters. Second, LSODA integrates the batch and fed-batch mass balances. Third, differential evolution proposes feed parameters, simulates the process, scores the outcome, and evolves better candidates. The objective is final concentration times final volume, which is total product. The study has 63 cases and a single seed (42), using up to 40 generations and population multiplier 14. It balances biomass growth and specific production under the reactor constraints; repeat searches are needed to judge robustness.

## 8. Volume-limit correction
The earlier objective penalised overflow but still allowed some runs to exceed 4 L. The corrected model stops the pump at the volume ceiling. All 63 product-strategy cases were searched with a volume-constrained model. Saved candidates were replayed with the final terminal-event model and the highest verified product retained. The figure compares saved final volumes before and after. A 1 mL band accounts for solver tolerance; exact ties finer than numerical tolerance should not be overinterpreted.

## 9. Strategy comparison
Every row shows one product. Its best found result is scaled to 100 percent, so the matrix compares strategies within that product. Absolute totals across rows have different physical units. Closely coloured cells indicate similar outcomes; a tiny lead does not establish a universally superior strategy. The comparison helps identify promising feeds and simpler alternatives worth validating.

## 10. Fab example
This example links the actual feed schedule, realised growth rate, and accumulated product. The dashed line marks the peak of the fitted product-rate curve. The optimiser seeks total product over the process, so growth rate can move around that peak while biomass and available feed change. Volume rises until the vessel limit stops feeding.

## 11. Takeaways and next steps
Across these cases, the best found feed gives 8–62% more product than the weakest tested feed. The Fab exponential and hybrid feeds differ by less than 0.02%. The contribution is a repeatable, constrained comparison of seven feed families across nine datasets. The results are model-based and use synthetic reactor assumptions. Next I will repeat searches across seeds, test sensitivity to reactor and kinetic assumptions, validate against real fed-batch data, and add a ranked feed-optimisation workflow to the GUI.
