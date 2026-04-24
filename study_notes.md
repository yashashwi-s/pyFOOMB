# Study Notes — Fed-Batch Optimisation with pyFOOMB

> **Student:** Yashashwi Singhania (23014019)
> **Guide:** Dr. Sharon Mano Pappu J.
> **Lab:** BPDD, Dept. of Biochemical Engineering, IIT (BHU) Varanasi

---

## Slide 1: Title Page

- **Fed-Batch**: Fermentation where nutrients are added during the process (not all at start like batch). Lets you control growth rate.
- **Bioprocess**: Any process using living organisms to make a product.
- **pyFOOMB**: Python Framework for Object-Oriented Modelling of Bioprocesses.
- **BPDD**: __________ (fill in full form).

---

## Slide 2: Project Overview

- **Feeding strategy**: How you add substrate over time in fed-batch (constant, exponential, or pulse).
- **Recombinant protein**: Protein made by inserting foreign DNA into a host organism.
- **μ (mu)**: Specific growth rate (h⁻¹). How fast cells grow. μ = 0.1 means biomass increases 10% per hour.
- **qp**: Specific product formation rate. How fast each gram of cells produces product.
- **X, S, P**: Biomass, Substrate, Product concentrations.
- **GUI**: Graphical User Interface — a visual browser app instead of writing code.
- **Parameter estimation**: Finding best values of model constants so the model matches data.
- **Feed optimisation**: Finding the best feeding schedule to maximise product.
- **Scale-up analysis**: Checking if lab-scale results hold at industrial volumes.

---

## Slide 3: What is pyFOOMB?

**Full form**: **Py**thon **F**ramework for **O**bject-**O**riented **M**odelling of **B**ioprocesses

**Paper**: Hemmerich et al. (2021), *Eng. Life Sci.* 21(3-4):242–257

- **ODE**: Ordinary Differential Equation. Describes how something changes over time. Example: dX/dt = μ·X.
- **rhs()**: "Right-Hand Side" method. Where you write your ODEs in Python.
- **Event handling**: Detects when something happens (e.g. substrate drops to zero) and responds (e.g. start feeding).
- **Bolus**: A sudden one-time addition of substrate.
- **CVode**: A numerical ODE solver from the SUNDIALS library. Very fast and stable.
- **SUNDIALS**: Suite of Nonlinear and Differential/Algebraic equation Solvers. C library from Lawrence Livermore.
- **assimulo**: Python wrapper around SUNDIALS that pyFOOMB uses.
- **scipy**: Python library for scientific computing (optimisers, integrators, statistics).
- **scipy.optimize**: Part of scipy for finding best-fit parameters.
- **pygmo**: Python wrapper for pagmo2. Global optimisation using island model with 17 algorithms.
- **Sensitivity analysis**: How much each output changes when you tweak a parameter. Tells which parameters matter most.
- **FIM**: Fisher Information Matrix. How much information your data contains about each parameter.
- **OED**: Optimal Experimental Design. Uses FIM to figure out the best next experiment.
- **Kinetic model**: Math description of reaction rates.
- **Hardcoded**: Built into software permanently. pyFOOMB does NOT hardcode kinetics — you write your own.

---

## Slide 4: pyFOOMB Architecture

| Class | What it does |
|-------|-------------|
| **BioprocessModel** | Abstract base class. You subclass it, write `rhs()` with your ODEs, optionally `state_events()` and `change_states()` for fed-batch. |
| **ObservationFunction** | Maps model states to measurements. E.g. X → optical density. |
| **Measurements** | Your experimental data (time + values). |
| **Simulator** | Runs model forward in time using CVode. Gives X(t), S(t), P(t). |
| **ExtendedSimulator** | Simulator + calculates error between simulation and data ("loss"). |
| **Caretaker** | Main class. Manages everything: model → simulate → data → estimate → analyse. |

Three layers: User (your model/data) → Core (Simulator, Caretaker) → Solvers (CVode, pygmo, scipy).

---

## Slide 5: Our Contribution

**What existed** (pyFOOMB library): ODE framework, CVode, estimation, FIM — all code-only via Jupyter.

**What we built**:
- **Next.js**: React-based framework for web apps. React = JavaScript library for building UIs.
- **FastAPI**: Modern Python web framework for REST APIs. Auto-generates documentation.
- **REST API**: Frontend talks to backend via HTTP requests (GET, POST, DELETE) with JSON data.
- **Endpoints**: Individual URLs the API responds to (e.g. `POST /api/models`). We have 30+.
- **Model templates**: 8 pre-built kinetic models so users don't write code.
- **Recharts**: React charting library for interactive plots.
- **KaTeX**: Library for rendering math equations in the browser.
- **CSV**: Comma-Separated Values — simple text format for data.
- **39 automated API tests**: Using pytest to verify every endpoint.

---

## Slide 6: System Architecture

### Layer by layer

**Browser** (Next.js, React, Recharts, KaTeX): 6 pages in the frontend.

**FastAPI** (30+ endpoints): Python backend server.

**Routers** (actual API routes):

| Router | Handles |
|--------|---------|
| `/api/models` | Create, list, delete models. Select templates. |
| `/api/simulation` | Run forward simulation. |
| `/api/data` | Import measurements (paste, upload CSV, Google Sheets). |
| `/api/estimation` | Run parameter estimation (5 methods). |
| `/api/analysis` | Sensitivity, FIM, covariance, confidence intervals. |

**Services**:

| Service | What it does |
|---------|-------------|
| **ModelStore** | Stores active model sessions in memory. |
| **ModelTemplates** | 8 pre-built kinetic models with defaults. |
| **CodeExecutor** | Dynamically creates Python classes using `exec()`. For advanced custom models. |
| **Serializers** | Converts numpy arrays etc. to JSON for the frontend. |

**pyFOOMB** (Caretaker, Simulator, BioprocessModel, ObservationFunction): The existing library.

**Solvers**:
- **CVode (SUNDIALS)**: Integrates ODEs.
- **pygmo (17 algorithms)**: Global optimisation. Algorithms: DE, PSO, SADE, Bee Colony, CMA-ES, etc.
- **scipy.optimize**: Local optimisation. L-BFGS-B, Nelder-Mead.

---

## Slide 7: GUI Workflow

### 6 pages
1. **Model**: Pick template, set parameters.
2. **Simulate**: Run forward ODE, see plots.
3. **Data**: Import measurements.
4. **Estimate**: Fit parameters (5 methods).
5. **Analyse**: Sensitivity, FIM, confidence intervals.
6. **Replicates**: Share parameters across multiple experiments.

### 8 Model Templates

| Template | μ equation | When to use |
|----------|-----------|-------------|
| **Monod** | μ_max·S/(K_S+S) | Standard, one substrate limits growth |
| **Logistic** | μ_max·(1-X/X_max) | Carrying capacity limits growth |
| **Exponential** | μ_max (constant) | Unlimited growth (early batch) |
| **Andrews** | μ_max·S/(K_S+S+S²/K_I) | High substrate inhibits growth |
| **Contois** | μ_max·S/(K_S·X+S) | K_S depends on biomass |
| **Double Monod** | μ_max·S₁/(K₁+S₁)·S₂/(K₂+S₂) | Two substrates needed |
| **Exp. Decay** | dX/dt = -k·X | Cell death |
| **Fed-Batch Monod** | Monod + feed events | Fed-batch with volume change |

### 5 Estimation Methods

| Method | How it works |
|--------|-------------|
| **Local (scipy)** | Starts from one point, moves downhill. L-BFGS-B (gradient-based, respects bounds) or Nelder-Mead (simplex, no gradients). Fast but local minima risk. |
| **Global (pygmo)** | Multiple "islands" each run different algorithm. Exchange best solutions ("migration"). Robust, slower. |
| **Repeated local** | Local optimisation many times from random starts. Keeps best. |
| **Monte Carlo** | Randomly sample parameter space, evaluate each. |
| **Parallel MC** | Monte Carlo on multiple CPU cores. |

- **L-BFGS-B**: Limited-memory Broyden-Fletcher-Goldfarb-Shanno with Bounds. Gradient-based optimiser.
- **Nelder-Mead**: Simplex method. No gradients. Geometric shape shrinks toward minimum.
- **Island model**: Multiple populations evolving in parallel, exchanging best solutions.

---

## Slide 9: μ–qp Relationship Models

### Why it matters
μ–qp tells you: at a given growth rate, how fast does the cell make product? This dictates the optimal feeding strategy because feed rate controls μ.

### Three types

**1. Linear (Luedeking-Piret)**: qp = α·μ + β
- α = growth-associated coefficient, β = non-growth-associated
- If β ≈ 0: purely growth-coupled → maximise μ → exponential feeding
- Luedeking-Piret: scientists who proposed it (1959)

**2. Bell-Shaped (Gaussian)**: qp = qp_max · exp(-(μ-μ_opt)²/(2σ²))
- qp_max = peak height, μ_opt = peak position, σ = peak width
- Must maintain μ at μ_opt → constant feed rate or feedback control

**3. Hyperbolic (Monod-like)**: qp = qp_max · μ/(K_q + μ)
- qp_max = plateau value, K_q = half-saturation constant
- Saturates: above certain μ, more growth doesn't help
- Just need μ >> K_q → flexible feeding

**scipy.optimize.curve_fit**: Non-linear least squares fitting.

---

## Slide 10: Literature Survey

- **Chemostat / CSTR**: Continuous Stirred-Tank Reactor. Fresh medium flows in, culture flows out at same rate. At steady state D = μ.
- **Dilution rate (D)**: D = F/V. In chemostat at steady state, D = μ.
- **Steady state**: All concentrations constant. dX/dt = dS/dt = dP/dt = 0.
- **n**: Number of data points from each paper.

### The 9 products

| Product | What it is |
|---------|-----------|
| **Resveratrol** | Plant polyphenol (antioxidant, in red wine) |
| **VHH Antibody** | Small antibody fragments from camelids (nanobodies) |
| **Crl1 Lipase SCC** | Fat-breaking enzyme, single gene copy |
| **EPG** | Endopolygalacturonase, breaks down pectin |
| **Fab Fragment** | Antigen-binding part of antibody |
| **ROL Lipase** | *Rhizopus oryzae* lipase |
| **Crl1 Lipase MCC** | Same enzyme, multiple gene copies |
| **α-Galactosidase** | Breaks down galactose sugars |
| **GFP** | Green Fluorescent Protein (reporter) |

### Organisms
- ***S. cerevisiae***: Baker's yeast, μ_max ≈ 0.40 h⁻¹, GRAS, Crabtree effect
- ***P. pastoris***: μ_max ≈ 0.20 h⁻¹, two promoters: PGAP (constitutive) and PAOX1 (methanol-induced)
- **PGAP**: Always active. **PAOX1**: Only active with methanol.
- **SCC vs MCC**: Single vs Multi Copy Clone. More copies = more protein but different kinetics.

---

## Slide 11: Extracted Data

- **R²**: Coefficient of determination. 1 = perfect fit, 0 = useless model.
- **D = μ at steady state**: Why chemostat gives clean μ–qp data.

### Units
| Unit | Meaning |
|------|---------|
| h⁻¹ | Per hour (for μ) |
| mmol/(g·h) | Millimoles per gram biomass per hour |
| mg/(g·h) | Milligrams per gram biomass per hour |
| AU/(g·h) | Arbitrary Units per gram biomass per hour |
| U/(g·h) | Enzyme Units per gram biomass per hour |
| RFU/(g·h) | Relative Fluorescence Units per gram biomass per hour |

### Fitted parameters
- Linear: α, β
- Bell: qp_max, μ_opt, σ
- Hyperbolic: qp_max, K_q

---

## Slide 13: Batch XPS Simulation

### ODE System
- dX/dt = μ·X (growth)
- dS/dt = -(μ/Y_X/S)·X (substrate consumption)
- dP/dt = qp(μ)·X (product formation)
- μ = μ_max·S/(K_S+S) (Monod kinetics)

### Parameters
| Symbol | Name | S.c. | P.p. |
|--------|------|------|------|
| μ_max | Max growth rate | 0.40 h⁻¹ | 0.20 h⁻¹ |
| K_S | Half-saturation constant | 0.10 g/L | 0.05 g/L |
| Y_X/S | Yield (biomass/substrate) | 0.50 g/g | 0.45 g/g |

- **K_S**: Substrate at which μ = μ_max/2. Lower = better at scavenging.
- **Y_X/S**: Efficiency of substrate→biomass conversion.
- **solve_ivp (RK45)**: Numerically integrates ODEs. RK45 = Runge-Kutta 4th/5th order, adaptive step size.

### Why CSTR data works for batch
μ–qp is a cell property, not reactor property. Measured in CSTR (clean data), applies to any reactor mode.

---

## Slide 15: Project Roadmap

**Done**: Study pyFOOMB → Build Web GUI → Literature Survey → μ–qp Fitting → Batch Simulation

**Next**: Fed-Batch Models → Param. Estimation & Optimisation → Experimental Validation → Deploy GUI → Scale-Up Analysis

---

## Viva Q&A

1. **What is pyFOOMB?** Python framework for bioprocess modelling. Doesn't hardcode kinetics. Users write rhs().
2. **Three μ–qp models?** Linear → max μ. Bell → maintain μ_opt. Hyperbolic → flexible.
3. **How did you fit?** scipy.optimize.curve_fit on chemostat data. All R² > 0.84.
4. **How did you simulate XPS?** Fitted qp(μ) + Monod parameters → batch ODEs → solve_ivp (RK45).
5. **What does GUI do?** Wraps 100% of pyFOOMB API. 6 pages. Next.js + FastAPI.
6. **Why fed-batch?** Control μ via feed rate → control qp → maximise product.
7. **Why CSTR data for batch?** μ–qp is a cell property. Works in any reactor.
8. **Island model?** pygmo's parallel optimisation. Multiple algorithms, migration of best solutions.
9. **FIM?** Fisher Information Matrix. High = well-identifiable parameter.
10. **OED?** Optimal Experimental Design. A/D/E criteria using FIM.

---

## Abbreviation Glossary

| Abbr | Full form |
|------|-----------|
| ODE | Ordinary Differential Equation |
| CSTR | Continuous Stirred-Tank Reactor |
| CVode | C-language Variable-coefficient ODE solver |
| SUNDIALS | Suite of Nonlinear and Differential/Algebraic equation Solvers |
| FIM | Fisher Information Matrix |
| OED | Optimal Experimental Design |
| GUI | Graphical User Interface |
| REST | Representational State Transfer |
| API | Application Programming Interface |
| JSON | JavaScript Object Notation |
| CSV | Comma-Separated Values |
| RK45 | Runge-Kutta 4th/5th order |
| L-BFGS-B | Limited-memory BFGS with Bounds |
| DE | Differential Evolution |
| PSO | Particle Swarm Optimisation |
| SADE | Self-Adaptive DE |
| CMA-ES | Covariance Matrix Adaptation Evolution Strategy |
| PGAP | GAP promoter (constitutive) |
| PAOX1 | Alcohol Oxidase 1 promoter (methanol-induced) |
| SCC | Single Copy Clone |
| MCC | Multi Copy Clone |
| GFP | Green Fluorescent Protein |
| EPG | Endopolygalacturonase |
| ROL | Rhizopus oryzae Lipase |
| VHH | Variable Heavy-Heavy chain antibody domain |
| HSA | Human Serum Albumin |
| GRAS | Generally Recognised As Safe |
| SS | Sum of Squares |
| WSS | Weighted Sum of Squares |
| negLL | Negative Log-Likelihood |
| R² | Coefficient of Determination |
| XPS | X (biomass), P (product), S (substrate) profiles |
| BPDD | __________ (fill in) |

---

*Last updated: April 2026*
