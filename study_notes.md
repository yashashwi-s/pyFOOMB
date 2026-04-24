# Detailed Study Notes — Fed-Batch Optimisation with pyFOOMB

> **Student:** Yashashwi Singhania (23014019)  
> **Guide:** Dr. Sharon Mano Pappu J.  
> **Lab:** BPDD, Dept. of Biochemical Engineering, IIT (BHU) Varanasi

---

## 1. What is pyFOOMB?

**pyFOOMB** = **Py**thon **F**ramework for **O**bject-**O**riented **M**odelling of **B**ioprocesses

- **Paper:** Hemmerich, Tenhaef, Wiechert & Noack (2021). *Engineering in Life Sciences*, 21(3-4):242–257. DOI: [10.1002/elsc.202000088](https://doi.org/10.1002/elsc.202000088)
- **License:** MIT (open-source)
- **Language:** Python (3.7–3.9)

### 1.1 Core Purpose

pyFOOMB provides a structured way to:

1. **Define** bioprocess models as ODE systems (user writes `rhs()` method)
2. **Simulate** forward dynamics using CVode (SUNDIALS) via assimulo
3. **Estimate** parameters from experimental data (local via scipy, global via pygmo)
4. **Analyse** parameter identifiability (sensitivity, FIM, covariance, OED)

### 1.2 Key Difference from Other Tools

Unlike COPASI, Berkeley Madonna, or gPROMS, pyFOOMB **does not hardcode any kinetic models**. Users implement *any* kinetic relationship in Python code inside the `rhs()` method. The framework only handles:
- ODE integration (with event handling for fed-batch)
- Parameter estimation infrastructure
- Statistical analysis

This makes it extremely flexible — you can implement Monod, Luedeking-Piret, bell-shaped, or any custom kinetics.

### 1.3 Architecture

```
User Layer:
  BioprocessModel (abstract) → user subclass with rhs()
  ObservationFunction → maps states to measurements
  Measurement data → experimental values

Core Layer:
  Simulator → wraps CVode, runs forward simulation
  ExtendedSimulator → adds loss calculation
  Caretaker → main API (simulate + estimate)

Solver Layer:
  assimulo/CVode (SUNDIALS) → ODE integration
  pygmo (pagmo2) → global optimization via island model
  scipy.optimize → local optimization
```

### 1.4 Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `BioprocessModel` | `modelling.py` | Abstract base; user implements `rhs()`, `state_events()`, `change_states()` |
| `ObservationFunction` | `modelling.py` | Maps model states to observable quantities |
| `Simulator` | `simulation.py` | Forward simulation wrapper for CVode |
| `ExtendedSimulator` | `simulation.py` | Adds loss function calculation |
| `Caretaker` | `caretaker.py` | Main entry point — simulate, estimate, analyse |
| `LossCalculator` | `generalized_islands.py` | pygmo problem wrapper for parallel estimation |

---

## 2. Fed-Batch Modelling in pyFOOMB

### 2.1 What is Fed-Batch?

In **batch** fermentation, all nutrients are added at the start. In **fed-batch**, additional substrate is fed during the process — either continuously or as pulses. This allows:
- Avoiding substrate inhibition
- Maintaining growth rate at a desired level
- Maximising product formation

### 2.2 ODE Mass Balances

For a fed-batch with volume change:

| Variable | ODE | Description |
|----------|-----|-------------|
| Biomass (X) | dX/dt = μ·X − (F/V)·X | Growth minus dilution |
| Substrate (S) | dS/dt = (F/V)·(S_in − S) − q_s·X | Feed input minus consumption |
| Product (P) | dP/dt = q_p·X − (F/V)·P | Formation minus dilution |
| Volume (V) | dV/dt = F | Feed flow rate |

Where:
- **μ** = specific growth rate (h⁻¹)
- **F** = feed flow rate (L/h)
- **V** = culture volume (L)
- **S_in** = feed substrate concentration (g/L)
- **q_s** = specific substrate consumption rate (g/(g·h))
- **q_p** = specific product formation rate (units/(g·h))

### 2.3 Event Handling

pyFOOMB handles feed events via assimulo's event system:

1. **`state_events(t, y, sw)`** — defines zero-crossing conditions (e.g., `S - 0.1` triggers when substrate drops below 0.1 g/L)
2. **`change_states(t, y, sw)`** — modifies state variables when event fires (e.g., add substrate bolus)
3. **`handle_event(solver, event_info)`** — orchestrates the response (toggle switches, restart solver)

### 2.4 Fed-Batch Implementation Example

```python
class FedBatchModel(BioprocessModel):
    def __init__(self):
        super().__init__(
            model_parameters=['mu_max', 'K_S', 'Y_XS', 'alpha', 'beta', 'F', 'S_in'],
            states=['P', 'S', 'V', 'X'],
            initial_switches=[False],  # Feed starts when event triggers
        )

    def rhs(self, t, y, sw):
        P, S, V, X = y
        p = self.model_parameters
        mu = p['mu_max'] * S / (p['K_S'] + S)
        qp = p['alpha'] * mu + p['beta']  # Luedeking-Piret
        qs = mu / p['Y_XS']
        F = p['F'] if sw[0] else 0.0
        
        dP = qp * X - (F/V) * P
        dS = (F/V) * (p['S_in'] - S) - qs * X
        dV = F
        dX = mu * X - (F/V) * X
        return [dP, dS, dV, dX]  # alphabetical order!

    def state_events(self, t, y, sw):
        P, S, V, X = y
        return [S - 0.1]  # feed starts when S < 0.1 g/L
```

---

## 3. The μ–qp Relationship

### 3.1 Why It Matters

The specific product formation rate (qp) depends on the specific growth rate (μ). This relationship **dictates the optimal feeding strategy**:

- If qp increases linearly with μ → **maximise growth rate** (exponential feed)
- If qp peaks at intermediate μ → **maintain μ at the optimum** (constant or feedback-controlled feed)
- If qp saturates → **any μ above the saturation point works** (flexible feeding)

### 3.2 Three Model Types

#### 3.2.1 Linear (Luedeking-Piret)

$$q_p = \alpha \cdot \mu + \beta$$

- **α** = growth-associated coefficient
- **β** = non-growth-associated coefficient (usually ≈ 0 for growth-coupled)
- **Implication:** Feed to maximise μ → exponential feeding
- **Examples:** Resveratrol (Vos 2015), Heterologous protein (Liu 2013), Crl1 lipase SCC (Nieto-Taype 2020)

#### 3.2.2 Bell-Shaped (Gaussian)

$$q_p = q_p^{max} \cdot \exp\left(-\frac{(\mu - \mu_{opt})^2}{2\sigma^2}\right)$$

- **qp_max** = maximum specific product formation rate
- **μ_opt** = optimal growth rate for production
- **σ** = width of the bell
- **Implication:** Must maintain μ at μ_opt → **constant feed rate** that gives μ = μ_opt
- **Examples:** EPG (Glauche 2017), Fab 3H6 (Maurer 2006 / Garcia-Ortega 2019), ROL (Garcia-Ortega 2016)

#### 3.2.3 Hyperbolic (Monod-like Saturation)

$$q_p = \frac{q_p^{max} \cdot \mu}{K_q + \mu}$$

- **qp_max** = maximum (saturated) product formation rate
- **Kq** = half-saturation constant for production
- **Implication:** Just need μ >> Kq → **any reasonable feed rate** works
- **Examples:** Crl1 MCC (Nieto-Taype 2020), α-Galactosidase (Giuseppin 1993), HSA (Rebnegger 2014)

---

## 4. Literature Data — What We Studied

### 4.1 Data Sources

We extracted μ–qp data from **9 published chemostat studies** across two organisms:

| # | Product | Organism | Model | Reference | DOI |
|---|---------|----------|-------|-----------|-----|
| 1 | Resveratrol | *S. cerevisiae* | Linear | Vos et al. (2015) | 10.1186/s12934-015-0321-6 |
| 2 | Heterologous Protein (HIP) | *S. cerevisiae* | Linear | Liu et al. (2013) | 10.1007/s00253-013-5100-y |
| 3 | Crl1 Lipase (SCC, PGAP) | *P. pastoris* | Linear | Nieto-Taype et al. (2020) | 10.1111/1751-7915.13498 |
| 4 | EPG (Polygalacturonase) | *S. cerevisiae* | Bell | Glauche et al. (2017) | PMC6999230 |
| 5 | Fab 3H6 (PGAP) | *P. pastoris* | Bell | Maurer (2006) / Garcia-Ortega (2019) | 10.1016/j.nbt.2019.06.002 |
| 6 | ROL Lipase (PAOX1) | *P. pastoris* | Bell | Garcia-Ortega et al. (2016) | 10.1016/j.nbt.2016.04.002 |
| 7 | Crl1 Lipase (MCC, PGAP) | *P. pastoris* | Hyperbolic | Nieto-Taype et al. (2020) | 10.1111/1751-7915.13498 |
| 8 | α-Galactosidase | *S. cerevisiae* | Hyperbolic | Giuseppin (1993) / Hensing (1995) | 10.1007/BF00872189 |
| 9 | HSA | *P. pastoris* | Hyperbolic | Rebnegger et al. (2014) | 10.1002/biot.201300334 |

### 4.2 How We Fitted the Models

**Tool:** `scipy.optimize.curve_fit` (non-linear least squares)

**Process:**
1. Extracted μ and qp data points from published figures/tables
2. For each product, chose the appropriate model (linear / bell / hyperbolic)
3. Set initial guesses:
   - Linear: `p0 = [max(qp)/max(mu), 0.0]`
   - Bell: `p0 = [max(qp), mu_at_max_qp, 0.04]`
   - Hyperbolic: `p0 = [max(qp)*1.1, 0.03]`
4. Fitted parameters using `curve_fit` with appropriate bounds
5. Calculated R² = 1 − SS_res / SS_tot

**Results:** All fits achieved R² > 0.84, with most > 0.95.

### 4.3 Key Equations Used

**R² (Coefficient of Determination):**
$$R^2 = 1 - \frac{\sum_i (y_i - \hat{y}_i)^2}{\sum_i (y_i - \bar{y})^2}$$

**Monod growth kinetics (for batch simulation):**
$$\mu = \mu_{max} \cdot \frac{S}{K_S + S}$$

---

## 5. XPS Profile Simulation

### 5.1 What Are XPS Profiles?

XPS = **X** (biomass), **P** (product), **S** (substrate) concentration profiles over time in a batch culture. They show:
- Exponential biomass growth → stationary phase
- Substrate depletion
- Product accumulation

### 5.2 How We Generated Them

**Step-by-step:**

1. **Fitted qp(μ) parameters** from literature data (Section 4.2)
2. **Used organism-specific Monod parameters:**

   | Parameter | *S. cerevisiae* | *P. pastoris* |
   |-----------|----------------|---------------|
   | μ_max (h⁻¹) | 0.40 | 0.20 |
   | K_S (g/L) | 0.10 | 0.05 |
   | Y_X/S (g/g) | 0.50 | 0.45 |

3. **Set initial conditions:** X₀ = 0.1 g/L, S₀ = 20 g/L, P₀ = 0
4. **Defined the ODE system:**
   ```
   dX/dt = μ · X
   dS/dt = -(μ / Y_XS) · X
   dP/dt = qp(μ) · X
   ```
   where μ = μ_max · S/(K_S + S) and qp(μ) uses the fitted model
5. **Integrated** using `scipy.integrate.solve_ivp` with RK45 method
6. **Time horizon:** estimated from substrate exhaustion time + 8h stationary tail

### 5.3 What the Plots Show

- **3×3 grid**: 3 model types × 3 products each = 9 panels
- Each panel has:
  - Green line: Biomass X (g/L) — exponential growth then plateau
  - Red dashed: Substrate S (g/L) — depletion curve
  - Coloured line: Product P (product-specific units/L) — accumulation
- Different organisms show different growth dynamics (S. cerevisiae faster than P. pastoris)

---

## 6. The Web GUI We Built

### 6.1 Why?

pyFOOMB is a Python library used through Jupyter notebooks and scripts. This means:
- Requires programming knowledge
- No visual interface for model selection
- Manual plotting and data handling

We built a **full-stack web application** to make pyFOOMB accessible through a browser.

### 6.2 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 16, React 19 | UI framework |
| Styling | Tailwind CSS v4 | Responsive design |
| Charts | Recharts | Interactive plots |
| Math | KaTeX | Equation rendering |
| Backend | FastAPI (Python) | REST API |
| Server | uvicorn | ASGI server |

### 6.3 Features (6 Pages)

1. **Model Page** — Select from 8 pre-built templates (Monod, Exponential, Logistic, Contois, Double Monod, Substrate Inhibition, Exponential Decay, Fed-Batch Monod). Set parameters with sliders.

2. **Simulation Page** — Run forward simulation, see interactive X/S/P plots. Overlay experimental data if loaded.

3. **Data Page** — Import measurements via:
   - Paste CSV/tab text (smart column parsing)
   - Upload .csv/.xlsx files
   - Public Google Sheets URL

4. **Estimation Page** — 5 methods:
   - Local (scipy L-BFGS-B, Nelder-Mead)
   - Parallel global (pygmo, 17 algorithms via island model)
   - Repeated local from random starting points
   - Monte Carlo sampling
   - Parallelised Monte Carlo

5. **Analysis Page** — Parameter identifiability:
   - Sensitivity analysis (which parameters affect which states)
   - Fisher Information Matrix
   - Covariance and correlation matrices
   - Confidence intervals
   - Optimal Experimental Design (A/D/E criteria)

6. **Replicates Page** — Multi-reactor parameter mapping: share kinetic parameters across experiments with different initial conditions

### 6.4 API Coverage

We implemented **100% of the core pyFOOMB API** as REST endpoints:
- 30+ API endpoints
- 39 automated tests (pytest)
- Full CRUD for models, measurements, estimation, analysis

---

## 7. Parameter Estimation in pyFOOMB

### 7.1 Local Estimation (scipy)

Uses `scipy.optimize.minimize` with methods like L-BFGS-B or Nelder-Mead. Fast but may get stuck in local minima.

### 7.2 Global Estimation (pygmo)

Uses the **Generalized Island Model**:
- Multiple "islands" each run a different optimizer
- Islands exchange best solutions via migration
- 17 available algorithms (DE, PSO, Bee Colony, SADE, etc.)
- Runs in parallel — robust against local minima

**Stopping criteria:**
- std(losses) < atol + rtol × mean (convergence)
- Max runtime exceeded
- Memory > 95%

### 7.3 Loss Metrics

| Metric | Formula | When to Use |
|--------|---------|-------------|
| SS | Σ(y_measured − y_predicted)² | No error bars |
| WSS | Σ[(y_measured − y_predicted)/σ]² | With error bars |
| negLL | -Σ log P(y_measured | y_predicted, σ) | Maximum likelihood |

---

## 8. Organisms Studied

### 8.1 *Saccharomyces cerevisiae*

- Baker's yeast, model eukaryote
- μ_max ≈ 0.40 h⁻¹ on glucose (aerobic)
- Well-characterised; Crabtree effect at high glucose
- Products studied: Resveratrol, HIP, EPG, α-Galactosidase

### 8.2 *Pichia pastoris* (*Komagataella phaffii*)

- Methylotrophic yeast, major recombinant protein host
- μ_max ≈ 0.20 h⁻¹ on glucose (aerobic)
- Two promoter systems: PGAP (constitutive) and PAOX1 (methanol-induced)
- Products studied: Crl1 SCC/MCC, Fab 3H6, ROL, HSA

---

## 9. Future Work — What's Next

### Phase 1: Fed-Batch Implementation
- Implement fed-batch ODE models in pyFOOMB with event handling
- Test constant, exponential, and pulse feed profiles
- Add volume tracking (dilution effects)

### Phase 2: Parameter Estimation from Real Data
- Obtain experimental fed-batch data (from lab or literature)
- Estimate kinetic parameters using the GUI (parallel pygmo)
- Compare local vs global estimation performance

### Phase 3: Feed Optimisation
- For each μ–qp model type, determine the optimal feed strategy:
  - **Linear qp(μ):** exponential feed to maximise μ
  - **Bell-shaped qp(μ):** constant feed to maintain μ at μ_opt
  - **Hyperbolic qp(μ):** any feed that keeps μ above K_q
- Implement feed profile optimisation as an outer loop around pyFOOMB simulation

### Phase 4: Validation
- Compare optimised feed profiles with literature results
- Validate with experimental fed-batch data
- Scale-up considerations

---

## 10. Key Concepts to Know for Viva

1. **What is pyFOOMB and how is it different from other tools?** → It doesn't hardcode models. Users write rhs() in Python.

2. **What are the three μ–qp models?** → Linear (Luedeking-Piret), Bell-shaped (Gaussian), Hyperbolic (Monod-like). Each implies a different optimal feed.

3. **How did you fit the models?** → scipy.optimize.curve_fit (non-linear least squares) on literature chemostat data. Initial guesses from data, bounds on parameters.

4. **How did you simulate XPS profiles?** → Monod batch ODE with organism-specific parameters + fitted qp(μ) → scipy.integrate.solve_ivp.

5. **What does the GUI do?** → Wraps pyFOOMB API in a web interface: Model → Simulate → Data → Estimate → Analyse → Replicates.

6. **Why fed-batch?** → Control growth rate to exploit μ–qp relationship. Can't do this in batch (μ determined by substrate). Fed-batch feed rate controls μ.

7. **What is the island model?** → pygmo's parallel optimization. Multiple islands (each with different algorithm) evolve populations and exchange best solutions via migration.

8. **What is OED?** → Optimal Experimental Design. Uses FIM to determine which experiments give the most information about parameters (A/D/E criteria).

---

*Last updated: April 2026*
