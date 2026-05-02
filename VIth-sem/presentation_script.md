# Presentation Script — 12 Minutes
## Optimising Fed-Batch Bioprocesses using pyFOOMB

> **Time budget**: ~12 min talk + 3 min Q&A = 15 min total
> **Rule of thumb**: ~45 sec per slide for data/plot slides, ~1 min for concept slides, ~30 sec for image-only slides.

---

## Slide 1 — Title (15 sec)

> "Good morning. I'm Yashashwi Singhania, working under Dr. Sharon Mano Pappu at the BPDD Lab. My UG project is on **optimising fed-batch bioprocesses using pyFOOMB**."

*Don't linger. Move on.*

---

## Slide 2 — Project Overview (1 min)

> "The core **objective** is to optimise the fed-batch feeding strategy for recombinant protein production.
>
> The central idea is simple: in recombinant organisms, the **rate at which cells produce product** — called qp — depends on **how fast they grow** — that's μ. So if we can control μ, we can maximise qp and therefore maximise product.
>
> This semester I completed four major tasks:
> 1. I studied the pyFOOMB framework — the modelling engine we're building on top of.
> 2. I built a complete **web GUI** so that non-programmers can use pyFOOMB from a browser.
> 3. I surveyed the **qp–μ literature** across 9 products and 2 organisms.
> 4. I **simulated batch X, S, P profiles** for all 9 products.
>
> Next semester I'll move to actual **fed-batch models, parameter estimation, and experimental validation**."

---

## Slide 3 — Why Optimise Fed-Batch Using qp vs μ? (1.5 min) ⭐

> "Before diving into tools, let me explain **why** this problem matters.
>
> In recombinant organisms, you've inserted a foreign gene. The cell's own growth machinery and your recombinant protein expression are **competing for the same resources** — ribosomes, ATP, amino acids. So **faster growth doesn't mean more product**. In fact, at very high μ, overexpression can stress the cell and production drops.
>
> The relationship between qp and μ is **specific to each product and organism** — there's no universal rule. That's why we need to study it case by case.
>
> So the **goal** is: find the μ that maximises qp, and then hold the cells at that μ.
>
> **How do you control μ?** That's where fed-batch comes in. In fed-batch, you're adding substrate at a controlled rate F. At quasi-steady state, the dilution rate D equals F over V, and D approximately equals μ. So by choosing your feed rate, you **directly set μ**, and therefore control qp.
>
> The control chain is: F → D ≈ μ → qp(μ) → P. That's the whole strategy."

*This is the most important conceptual slide. Make sure the audience gets the F→μ→qp chain.*

---

## Slide 4 — What is pyFOOMB? (45 sec)

> "**pyFOOMB** stands for Python Framework for Object-Oriented Modelling of Bioprocesses. It was published by Hemmerich et al. in 2021.
>
> Key capabilities: you define your ODE model by writing a `rhs()` method. pyFOOMB handles everything else — integration using CVode from SUNDIALS, event handling for fed-batch like feed start/stop, parameter estimation using both scipy and pygmo, and even sensitivity analysis and optimal experimental design.
>
> The **key differentiator** is that pyFOOMB does **not hardcode** any kinetic model. You write whatever kinetics you want. The framework is model-agnostic."

---

## Slide 5 — pyFOOMB Architecture (30 sec)

> "Architecturally, it's three layers. At the **top**, the user defines a BioprocessModel, an ObservationFunction, and provides Measurements. In the **middle**, the Simulator integrates ODEs, and the Caretaker orchestrates estimation. At the **bottom**, it uses CVode for solving, pygmo for global optimisation with 17 algorithms, and scipy for local optimisation."

*Point at the diagram as you speak. Don't read every box.*

---

## Slide 6 — Our Contribution (1 min)

> "Now, what did I actually build? pyFOOMB as a library is powerful, but it's **code-only** — you need to write Python in Jupyter notebooks. There's no visual interface at all.
>
> So I built a complete **web platform** from scratch:
> - A **Next.js** frontend with 6 pages
> - A **FastAPI** backend with over 30 REST API endpoints
> - **8 pre-built kinetic model templates** so users can start modelling without writing any code
> - Interactive plots using Recharts, math rendering using KaTeX
> - Data import from CSV, paste, or Google Sheets
> - And 39 automated API tests for quality assurance
>
> The result is a **browser-based GUI that wraps 100% of the pyFOOMB API**."

---

## Slide 7 — System Architecture (45 sec)

> "Here's the full system architecture. The browser layer uses React and Next.js. It talks to the FastAPI backend through REST endpoints — routes for models, simulation, data, estimation, and analysis. Behind the API are services like ModelStore for session management and ModelTemplates for the 8 pre-built models. Everything flows down to the pyFOOMB core and finally to the solvers — CVode, pygmo, and scipy."

*Point at layers as you describe. Top-down flow.*

---

## Slide 8 — GUI Workflow (45 sec)

> "The GUI workflow follows a natural pipeline: you **select and configure a model**, **run a forward simulation** to see predicted profiles, **import your experimental data**, **fit parameters** using one of 5 estimation methods — from simple local scipy to parallel pygmo — then **analyse** the fit with sensitivity analysis and Fisher Information Matrix, and finally handle **replicates** for multi-experiment estimation.
>
> On the left you can see the 8 substrate kinetic templates covering common bioprocess scenarios from simple Monod to fed-batch with volume change."

---

## Slide 9 — Substrate Kinetic Model Equations (30 sec)

> "Here are the actual equations for all 8 templates. These all model **how growth rate μ depends on substrate S** or on biomass and time. The most common is Monod — saturation kinetics. Andrews adds substrate inhibition. The Fed-Batch Monod adds volume change from feeding.
>
> Important: these define μ. Then μ feeds into the qp–μ relationship which I'll show next."

*Just point at the table. Don't read every equation — the audience can see them.*

---

## Slide 10 — GUI Screenshot (15 sec)

> "And here's what the actual interface looks like in the browser. You can see the model configuration panel, parameter inputs, and interactive plots."

*Quick pause for the audience to absorb the screenshot, then move on.*

---

## Slide 11 — qp–μ Relationship Models (1 min) ⭐

> "Now the second layer of modelling: qp as a function of μ. This determines the feeding strategy.
>
> We identified **three patterns** from the literature:
>
> **Linear** — qp = α·μ + β. Product is growth-associated. Strategy: maximise μ, feed aggressively.
>
> **Bell-shaped** — Gaussian peak at μ_opt. Product formation drops at both high and low μ. Strategy: hold μ at exactly μ_opt. This is the trickiest to operate.
>
> **Hyperbolic** — Monod-like saturation. qp plateaus above a certain μ. Strategy: flexible — just keep μ reasonably high.
>
> We fitted each of our 9 literature products to one of these using `curve_fit` from scipy."

---

## Slide 12 — Literature Survey Table (45 sec)

> "We surveyed **9 recombinant products** across two organisms — *S. cerevisiae* and *P. pastoris*. Data was extracted from chemostat experiments where D equals μ at steady state, so we get clean qp–μ points.
>
> The products range from small molecules like resveratrol to enzymes like lipase to antibody fragments. Three fit the linear model, three are bell-shaped, and three are hyperbolic. The table shows the reference, organism, and number of data points for each."

*Don't read every row. Highlight the spread: 3 linear, 3 bell, 3 hyperbolic.*

---

## Slide 13 — Extracted Data Ranges (30 sec)

> "This table shows the actual μ and qp ranges from the digitised data. All R² values are above 0.84, with most above 0.97, indicating good fits. Notice the wide variety of units — millimoles, milligrams, arbitrary units, enzyme units — reflecting the diversity of products."

*Quick scan. Don't read every number.*

---

## Slide 14 — qp–μ Fitting Results Plot (45 sec)

> "Here's the visual result. Each column is a model type — linear, bell-shaped, hyperbolic. Each subplot shows one product with experimental data points and the fitted curve.
>
> You can see that the linear models are very clean — R² around 0.99. The bell-shaped models show a clear peak — for example EPG peaks around μ = 0.2 h⁻¹. The hyperbolic models saturate at high μ.
>
> The key takeaway: **the same organism** — say *P. pastoris* — can show **different qp–μ shapes** for different products. It depends on the gene, the promoter, and the copy number."

---

## Slide 15 — Batch XPS Simulation Equations (45 sec)

> "To validate our fitted qp–μ parameters, I simulated full batch dynamics. The ODE system is standard: biomass grows at rate μ·X, substrate is consumed proportional to growth with yield Y_X/S, and product is formed at rate qp(μ)·X.
>
> μ itself follows Monod kinetics. I used organism-specific parameters — μ_max of 0.4 for *S. cerevisiae* and 0.2 for *P. pastoris*. Initial conditions: 0.1 g/L biomass, 20 g/L glucose, zero product.
>
> Note: the qp–μ relationship was measured in chemostats but it's a **cell property**, not a reactor property — so it applies to batch too."

---

## Slide 16 — XPS Simulation Results Plot (30 sec)

> "And here are the results. Nine batch profiles — one per product. In every case you see the classic batch behavior: biomass rises, substrate depletes, product accumulates. The differences are in the **product curves** — linear qp gives steadily accumulating product, bell-shaped gives product only during the optimal growth window, and hyperbolic gives a saturating accumulation pattern."

---

## Slide 17 — Project Roadmap (45 sec)

> "To summarise the project timeline: this semester, all five blocks in green are complete — studying pyFOOMB, building the GUI, literature survey, qp–μ fitting, and batch simulation.
>
> Next semester, I'll implement **fed-batch ODE models** with feed events in pyFOOMB, run **parameter estimation** to fit real data, **validate** against published experimental profiles, **deploy** the GUI for lab use, and explore **scale-up** analysis.
>
> The goal is to go from simulation to a tool that can actually **design optimal feed profiles** for real fermentations in our lab."

---

## Slide 18 — Thank You (10 sec)

> "Thank you. I'm happy to take questions."

---

## Timing Summary

| Slide | Topic | Time |
|-------|-------|------|
| 1 | Title | 0:15 |
| 2 | Project Overview | 1:00 |
| 3 | Why Fed-Batch + qp vs μ ⭐ | 1:30 |
| 4 | What is pyFOOMB | 0:45 |
| 5 | Architecture diagram | 0:30 |
| 6 | Our Contribution ⭐ | 1:00 |
| 7 | System Architecture | 0:45 |
| 8 | GUI Workflow | 0:45 |
| 9 | Substrate Equations | 0:30 |
| 10 | GUI Screenshot | 0:15 |
| 11 | qp–μ Relationship Models ⭐ | 1:00 |
| 12 | Literature Survey Table | 0:45 |
| 13 | Extracted Data | 0:30 |
| 14 | qp–μ Plot | 0:45 |
| 15 | Batch XPS Equations | 0:45 |
| 16 | XPS Plot | 0:30 |
| 17 | Roadmap | 0:45 |
| 18 | Thank You | 0:10 |
| | **Total** | **~12 min** |

> ⭐ = slides where you should spend the most energy. These are where you demonstrate understanding, not just facts.

---

## Tips

1. **Don't read slides.** You know the content — explain it conversationally.
2. **Point at visuals.** When showing architecture, plots, or tables — physically point.
3. **The F→D≈μ→qp→P chain** on slide 3 is your money slide. If the examiner remembers one thing, make it this.
4. **Anticipate "why"** questions: Why fed-batch? Why not just batch? Why 3 models? Why these organisms?
5. **Pace yourself.** The temptation is to rush through the GUI slides. Don't — that's your main engineering contribution.
6. **Plot slides are rest stops.** Let the audience absorb the figure for 2-3 seconds of silence before you explain.
