# pyFOOMB Web GUI

Web interface for the [pyFOOMB](https://doi.org/10.1002/elsc.202000088) bioprocess modelling framework.

## Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │              Browser (:3000)                  │
                    │                                              │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
                    │  │ Dashboard│ │  Model   │ │  Simulation  │ │
                    │  └──────────┘ └──────────┘ └──────────────┘ │
                    │  ┌──────────┐ ┌──────────┐ ┌──────────────┐ │
                    │  │   Data   │ │Estimation│ │   Analysis   │ │
                    │  └──────────┘ └──────────┘ └──────────────┘ │
                    │  ┌──────────┐ ┌──────────┐                  │
                    │  │Replicates│ │ Examples  │  Next.js 16     │
                    │  └──────────┘ └──────────┘  Tailwind v4     │
                    └────────────────┬─────────────────────────────┘
                                     │ fetch (JSON)
                    ┌────────────────▼─────────────────────────────┐
                    │           FastAPI Server (:8000)              │
                    │                                              │
                    │  ┌─────────────────────────────────────────┐ │
                    │  │              Routers                     │ │
                    │  │  models · simulation · data · estimation │ │
                    │  │  analysis · parameters                  │ │
                    │  └────────────────┬────────────────────────┘ │
                    │                   │                           │
                    │  ┌────────────────▼────────────────────────┐ │
                    │  │             Services                    │ │
                    │  │  model_store · model_templates          │ │
                    │  │  serializers · code_executor            │ │
                    │  └────────────────┬────────────────────────┘ │
                    │                   │                           │
                    │  ┌────────────────▼────────────────────────┐ │
                    │  │           pyfoomb Package               │ │
                    │  │  Caretaker · BioprocessModel            │ │
                    │  │  ObservationFunction · Measurement      │ │
                    │  │  assimulo (CVode) · pygmo (islands)     │ │
                    │  └────────────────────────────────────────┘ │
                    └──────────────────────────────────────────────┘
```

## Data Flow

```
 Template ──▶ Caretaker ──▶ simulate() ──▶ Chart
                │
                ├──▶ Measurements ──▶ estimate() ──▶ Fitted params
                │                         │
                │                         ├──▶ estimate_parallel()
                │                         ├──▶ estimate_repeatedly()
                │                         └──▶ estimate_MC_sampling()
                │
                ├──▶ get_sensitivities() ──▶ Sensitivity chart
                │
                ├──▶ get_parameter_matrices() ──▶ FIM / Cov / Corr
                │
                └──▶ get_optimality_criteria() ──▶ A, D, E, E_mod
```

## Quick Start

```bash
# Local (requires conda env 'bpdd' with pyfoomb installed)
./start.sh

# Docker (new setup)
docker build -t pyfoomb-web .
docker run -p 3000:3000 -p 8000:8000 pyfoomb-web
```

Frontend: http://localhost:3000  
Backend API docs: http://localhost:8000/docs

## File Structure

```
web/
├── start.sh                  # Start both servers (conda env bpdd)
├── Dockerfile                # Full containerized build
├── backend/
│   ├── main.py               # FastAPI app entry point
│   ├── requirements.txt
│   ├── routers/
│   │   ├── models.py         # Template-based model creation, model checking
│   │   ├── simulation.py     # Forward simulation
│   │   ├── data.py           # Measurement CRUD + file upload
│   │   ├── estimation.py     # 5 estimation methods
│   │   ├── analysis.py       # Sensitivity, FIM, Cov, Corr, OED
│   │   └── parameters.py     # Replicates, mappings, integrator
│   └── services/
│       ├── model_store.py    # In-memory session management
│       ├── model_templates.py # 8 pre-built bioprocess models
│       ├── serializers.py    # pyFOOMB → JSON conversion
│       └── code_executor.py  # Dynamic model class creation
└── frontend/
    ├── src/app/
    │   ├── page.tsx           # Dashboard
    │   ├── model/page.tsx     # Model template selector
    │   ├── simulation/page.tsx # Interactive simulation + charts
    │   ├── data/page.tsx      # Measurement entry + paste
    │   ├── estimation/page.tsx # Parameter estimation
    │   ├── analysis/page.tsx  # Sensitivity + uncertainty
    │   ├── replicates/page.tsx # Multi-reactor management
    │   └── examples/page.tsx  # Pre-configured scenarios
    ├── src/components/
    │   └── Sidebar.tsx
    └── src/lib/
        └── api.ts             # Typed API client
```

## API Coverage

### Implemented

| pyFOOMB Method | Endpoint | Notes |
|---|---|---|
| `Caretaker.__init__` | `POST /api/models` | Template-based |
| `Caretaker.simulate` | `POST /api/models/{id}/simulate` | — |
| `Caretaker.estimate` | `POST /api/models/{id}/estimate` | method=local |
| `Caretaker.estimate_parallel` | same | method=parallel |
| `Caretaker.estimate_repeatedly` | same | method=repeated |
| `Caretaker.estimate_MC_sampling` | same | method=mc |
| `Caretaker.estimate_parallel_MC_sampling` | same | method=parallel_mc |
| `Caretaker.get_sensitivities` | `POST /api/models/{id}/sensitivities` | — |
| `Caretaker.get_parameter_matrices` | `POST /api/models/{id}/parameter-matrices` | FIM+Cov+Corr |
| `Caretaker.get_parameter_uncertainties` | `POST /api/models/{id}/parameter-uncertainties` | — |
| `Caretaker.get_optimality_criteria` | `POST /api/models/{id}/optimality-criteria` | A,D,E,E_mod |
| `Caretaker.set_parameters` | `PUT /api/models/{id}/parameters` | — |
| `Caretaker.add_replicate` | `POST /api/models/{id}/replicates` | — |
| `Caretaker.apply_mappings` | `POST /api/models/{id}/mappings` | — |
| `Caretaker.set_integrator_kwargs` | `PUT /api/models/{id}/integrator` | — |
| `ModelChecker` | `POST /api/models/{id}/check` | — |
| `Measurement` creation | `POST /api/models/{id}/measurements` | JSON + file |
| `ObservationFunction` | `POST /api/models/{id}/observation-functions` | Template-based |
| `Visualization.compare_estimates` | Frontend charts | Recharts |
| `Visualization.show_parameter_distributions` | Frontend histograms | Recharts |

### Not Yet Implemented

| pyFOOMB Feature | Priority | Reason |
|---|---|---|
| `estimate_parallel_continued` | Medium | Requires persistent archipelago state |
| `Visualization.compare_estimates_many` | Medium | MC overlay plots |
| `Visualization.show_kinetic_data_many` | Low | Multi-replicate plotting |
| Custom model equations (non-template) | Low | Would need equation parser |
| `optimizer_kwargs` configuration | Low | Advanced tuning |
| Error model configuration per Measurement | Medium | `apply_error_model` method |
| File upload (CSV/XLSX) via drag-and-drop | Medium | Backend supports it, frontend needs form |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind v4, Recharts |
| Backend | FastAPI, Python, uvicorn |
| ODE Solver | assimulo (CVode) |
| Optimization | pygmo (generalized island model) |
| Data | numpy, pandas, scipy |
