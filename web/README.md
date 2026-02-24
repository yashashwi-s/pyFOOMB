# pyFOOMB Web GUI

Web interface for the [pyFOOMB](https://doi.org/10.1002/elsc.202000088) bioprocess modelling framework.

## Architecture

```mermaid
graph TB
    subgraph Browser["🌐 Browser — localhost:3000"]
        direction LR
        D[Dashboard]
        M[Model]
        S[Simulation]
        Da[Data]
        E[Estimation]
        A[Analysis]
        R[Replicates]
        Ex[Examples]
    end

    subgraph Backend["⚙️ FastAPI — localhost:8000"]
        direction TB
        subgraph Routers
            R1[models]
            R2[simulation]
            R3[data]
            R4[estimation]
            R5[analysis]
            R6[parameters]
        end
        subgraph Services
            S1[model_templates]
            S2[model_store]
            S3[serializers]
        end
    end

    subgraph Core["🧬 pyfoomb"]
        C[Caretaker]
        BM[BioprocessModel]
        OF[ObservationFunction]
        MS[Measurement]
    end

    subgraph Solvers["🔧 Solvers"]
        CV[assimulo — CVode]
        PG[pygmo — Islands]
        SC[scipy — minimize]
    end

    Browser -- "REST / JSON" --> Backend
    Routers --> Services
    Services --> Core
    Core --> Solvers
```

## Workflow

```mermaid
flowchart LR
    A["① Model\nSelect template\nSet parameters"] --> B["② Simulate\nForward integration\nVisualize dynamics"]
    B --> C["③ Data\nAdd measurements\nManual or file"]
    C --> D["④ Estimate\nFit parameters\n5 methods"]
    D --> E["⑤ Analyse\nSensitivity\nFIM · Cov · Corr"]
    E --> F["⑥ Replicates\nMulti-reactor\nParameter mapping"]

    style A fill:#1e3a5f,stroke:#3b82f6,color:#e4e4e7
    style B fill:#1e3a5f,stroke:#3b82f6,color:#e4e4e7
    style C fill:#1e3a5f,stroke:#3b82f6,color:#e4e4e7
    style D fill:#1e3a5f,stroke:#3b82f6,color:#e4e4e7
    style E fill:#1e3a5f,stroke:#3b82f6,color:#e4e4e7
    style F fill:#1e3a5f,stroke:#3b82f6,color:#e4e4e7
```

## Data Flow

```mermaid
flowchart TD
    T["Model Template"] --> CT["Caretaker"]
    CT --> SIM["simulate()"]
    SIM --> CHART["📈 Interactive Chart"]

    CT --> MEAS["Measurements"]
    MEAS --> EST["estimate()"]
    EST --> FIT["Fitted Parameters"]

    EST --> |"method"| LOCAL["local — scipy"]
    EST --> |"method"| PAR["parallel — pygmo"]
    EST --> |"method"| REP["repeated — N jobs"]
    EST --> |"method"| MC["MC sampling"]
    EST --> |"method"| PMC["parallel MC"]

    FIT --> SENS["get_sensitivities()"]
    SENS --> SC["Sensitivity Charts"]

    FIT --> MAT["get_parameter_matrices()"]
    MAT --> FIM["FIM"]
    MAT --> COV["Covariance"]
    MAT --> CORR["Correlation"]

    FIT --> OPT["get_optimality_criteria()"]
    OPT --> CRIT["A · D · E · E_mod"]

    style T fill:#27272a,stroke:#3b82f6,color:#e4e4e7
    style CT fill:#27272a,stroke:#22c55e,color:#e4e4e7
    style FIT fill:#27272a,stroke:#f59e0b,color:#e4e4e7
    style CHART fill:#18181b,stroke:#3b82f6,color:#a1a1aa
    style SC fill:#18181b,stroke:#3b82f6,color:#a1a1aa
```

## Quick Start

```bash
# Local (requires conda env 'bpdd' with pyfoomb installed)
./start.sh

# Docker
docker build -t pyfoomb-web .
docker run -p 3000:3000 -p 8000:8000 pyfoomb-web
```

| | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API docs | http://localhost:8000/docs |

## File Structure

```
web/
├── start.sh                     # Launch both servers
├── Dockerfile
├── backend/
│   ├── main.py                  # FastAPI entry point
│   ├── routers/
│   │   ├── models.py            # Template-based model CRUD
│   │   ├── simulation.py        # Forward simulation
│   │   ├── data.py              # Measurement CRUD + file upload
│   │   ├── estimation.py        # 5 estimation methods
│   │   ├── analysis.py          # Sensitivity, FIM, Cov, Corr, OED
│   │   └── parameters.py        # Replicates, mappings, integrator
│   └── services/
│       ├── model_store.py       # In-memory session store
│       ├── model_templates.py   # 8 pre-built ODE models
│       └── serializers.py       # pyFOOMB → JSON
└── frontend/
    ├── src/app/                  # 8 Next.js pages
    ├── src/components/           # Sidebar, Math (KaTeX)
    └── src/lib/                  # API client, paramToTex
```

## API Coverage

### ✅ Implemented

| pyFOOMB Method | Endpoint |
|---|---|
| `Caretaker.__init__` | `POST /api/models` |
| `Caretaker.simulate` | `POST /api/models/{id}/simulate` |
| `Caretaker.estimate` | `POST /api/models/{id}/estimate` |
| `Caretaker.estimate_parallel` | ↑ `method=parallel` |
| `Caretaker.estimate_repeatedly` | ↑ `method=repeated` |
| `Caretaker.estimate_MC_sampling` | ↑ `method=mc` |
| `Caretaker.estimate_parallel_MC_sampling` | ↑ `method=parallel_mc` |
| `Caretaker.get_sensitivities` | `POST /api/models/{id}/sensitivities` |
| `Caretaker.get_parameter_matrices` | `POST /api/models/{id}/parameter-matrices` |
| `Caretaker.get_parameter_uncertainties` | `POST /api/models/{id}/parameter-uncertainties` |
| `Caretaker.get_optimality_criteria` | `POST /api/models/{id}/optimality-criteria` |
| `Caretaker.set_parameters` | `PUT /api/models/{id}/parameters` |
| `Caretaker.add_replicate` | `POST /api/models/{id}/replicates` |
| `Caretaker.apply_mappings` | `POST /api/models/{id}/mappings` |
| `Caretaker.set_integrator_kwargs` | `PUT /api/models/{id}/integrator` |
| `ModelChecker` | `POST /api/models/{id}/check` |
| `Measurement` | `POST /api/models/{id}/measurements` |
| `ObservationFunction` | `POST /api/models/{id}/observation-functions` |

### 🔲 Not Yet Implemented

| Feature | Priority |
|---|---|
| `estimate_parallel_continued` | Medium |
| `compare_estimates_many` (MC overlay) | Medium |
| Error model per Measurement | Medium |
| CSV/XLSX drag-and-drop upload | Medium |
| Custom model equations (non-template) | Low |
| `optimizer_kwargs` configuration | Low |

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 · React 19 · Tailwind v4 · Recharts · KaTeX |
| Backend | FastAPI · Python 3.9 · uvicorn |
| ODE Solver | assimulo (CVode / SUNDIALS) |
| Optimization | pygmo (generalized island model) |
| Data | numpy · pandas · scipy |
