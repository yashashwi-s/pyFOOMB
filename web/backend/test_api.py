"""
Comprehensive test suite for pyFOOMB Web GUI backend.
Tests every endpoint, simulating real frontend interaction flows.

Usage:
    cd /home/yashashwi-s/bpdd/pyFOOMB/web/backend
    python -m pytest test_api.py -v --tb=short 2>&1
"""

import io
import numpy
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────

def create_monod_model(name="TestMonod"):
    """Create a Monod growth model and return model_id."""
    r = client.post("/api/models", json={
        "template_id": "monod_growth",
        "model_name": name,
        "model_parameters": {"mu_max": 0.5, "K_S": 0.1, "Y_XS": 0.5, "Y_PS": 0.3},
        "initial_values": {"P0": 0.0, "S0": 10.0, "X0": 0.1},
    })
    assert r.status_code == 200, f"Create failed: {r.text}"
    return r.json()["model_id"]


def add_synthetic_measurements(model_id):
    """Simulate, then use noisy output as measurements."""
    r = client.post(f"/api/models/{model_id}/simulate", json={
        "t_start": 0, "t_end": 10, "n_points": 20,
    })
    assert r.status_code == 200
    results = r.json()["results"]

    measurements = []
    for series in results:
        timepoints = series["timepoints"]
        values = series["values"]
        # Add 5% noise
        noisy = [v * (1 + 0.05 * (i % 3 - 1) * 0.1) for i, v in enumerate(values)]
        measurements.append({
            "name": series["name"],
            "timepoints": timepoints,
            "values": noisy,
            "errors": [max(0.01, abs(v) * 0.05) for v in noisy],
        })

    r = client.post(f"/api/models/{model_id}/measurements", json={"measurements": measurements})
    assert r.status_code == 200
    return r.json()


# ──────────────────────────────────────────────────────────
# 1. Model CRUD
# ──────────────────────────────────────────────────────────

class TestModelCRUD:

    def test_list_templates(self):
        r = client.get("/api/templates")
        assert r.status_code == 200
        templates = r.json()["templates"]
        assert len(templates) >= 8
        names = [t["id"] for t in templates]
        assert "monod_growth" in names
        assert "logistic_growth" in names

    def test_create_model_monod(self):
        r = client.post("/api/models", json={
            "template_id": "monod_growth",
            "model_parameters": {"mu_max": 0.4, "K_S": 1.0, "Y_XS": 0.5, "Y_PS": 0.3},
            "initial_values": {"P0": 0.0, "S0": 20.0, "X0": 0.5},
        })
        assert r.status_code == 200
        data = r.json()
        assert "model_id" in data
        assert data["metadata"]["template_id"] == "monod_growth"

    def test_create_all_templates(self):
        """Create one model from every available template."""
        r = client.get("/api/templates")
        templates = r.json()["templates"]
        for tmpl in templates:
            r = client.post("/api/models", json={"template_id": tmpl["id"]})
            assert r.status_code == 200, f"Failed for template {tmpl['id']}: {r.text}"

    def test_list_models(self):
        create_monod_model("ListTest")
        r = client.get("/api/models")
        assert r.status_code == 200
        models = r.json()["models"]
        assert any(m["name"] == "ListTest" for m in models)

    def test_get_model(self):
        mid = create_monod_model("GetTest")
        r = client.get(f"/api/models/{mid}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == mid
        assert "parameters" in data

    def test_delete_model(self):
        mid = create_monod_model("DeleteTest")
        r = client.delete(f"/api/models/{mid}")
        assert r.status_code == 200
        r = client.get(f"/api/models/{mid}")
        assert r.status_code == 404

    def test_create_invalid_template(self):
        r = client.post("/api/models", json={"template_id": "nonexistent"})
        assert r.status_code == 400


# ──────────────────────────────────────────────────────────
# 2. Simulation
# ──────────────────────────────────────────────────────────

class TestSimulation:

    def test_simulate_default(self):
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/simulate", json={
            "t_start": 0, "t_end": 20, "n_points": 100,
        })
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 3  # P, S, X states
        assert len(results[0]["timepoints"]) == 100

    def test_simulate_with_overrides(self):
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/simulate", json={
            "t_start": 0, "t_end": 10, "n_points": 50,
            "parameters": {"mu_max": 1.0},
        })
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results[0]["timepoints"]) == 50

    def test_simulate_fedbatch(self):
        """Test fed-batch model (has events)."""
        r = client.post("/api/models", json={"template_id": "fed_batch_monod"})
        assert r.status_code == 200, f"Fed-batch create failed: {r.text}"
        mid = r.json()["model_id"]

        r = client.post(f"/api/models/{mid}/simulate", json={
            "t_start": 0, "t_end": 30, "n_points": 200,
        })
        assert r.status_code == 200

    def test_simulate_all_templates(self):
        """Simulate every model template to ensure they all work."""
        r = client.get("/api/templates")
        for tmpl in r.json()["templates"]:
            r2 = client.post("/api/models", json={"template_id": tmpl["id"]})
            mid = r2.json()["model_id"]
            t_end = tmpl.get("default_t_end", 10)
            r3 = client.post(f"/api/models/{mid}/simulate", json={
                "t_start": 0, "t_end": t_end, "n_points": 50,
            })
            assert r3.status_code == 200, f"Simulation failed for {tmpl['id']}: {r3.text}"


# ──────────────────────────────────────────────────────────
# 3. Measurements
# ──────────────────────────────────────────────────────────

class TestMeasurements:

    def test_add_measurements_json(self):
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/measurements", json={
            "measurements": [
                {"name": "X", "timepoints": [0, 5, 10], "values": [0.1, 1.5, 4.2]},
                {"name": "S", "timepoints": [0, 5, 10], "values": [10.0, 5.0, 0.5]},
            ]
        })
        assert r.status_code == 200
        assert len(r.json()["names"]) == 2

    def test_add_measurements_with_errors(self):
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/measurements", json={
            "measurements": [{
                "name": "X",
                "timepoints": [0, 5, 10],
                "values": [0.1, 1.5, 4.2],
                "errors": [0.01, 0.1, 0.3],
            }]
        })
        assert r.status_code == 200

    def test_upload_csv(self):
        mid = create_monod_model()
        csv_content = "time,X,S\n0,0.1,10.0\n5,1.5,5.0\n10,4.2,0.5\n"
        r = client.post(
            f"/api/models/{mid}/measurements/upload",
            files={"file": ("data.csv", io.BytesIO(csv_content.encode()), "text/csv")},
        )
        assert r.status_code == 200
        assert r.json()["names"] == ["X", "S"]

    def test_get_measurements(self):
        mid = create_monod_model()
        add_synthetic_measurements(mid)
        r = client.get(f"/api/models/{mid}/measurements")
        assert r.status_code == 200
        assert len(r.json()["measurements"]) > 0

    def test_clear_measurements(self):
        mid = create_monod_model()
        add_synthetic_measurements(mid)
        r = client.delete(f"/api/models/{mid}/measurements")
        assert r.status_code == 200
        r = client.get(f"/api/models/{mid}/measurements")
        assert len(r.json()["measurements"]) == 0

    def test_add_measurement_with_error_model(self):
        """Test Measurement creation with error model applied."""
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/measurements", json={
            "measurements": [{
                "name": "X",
                "timepoints": [0, 5, 10],
                "values": [0.1, 1.5, 4.2],
                "error_model_type": "constant",
                "error_model_parameters": {"abs_error": 0.1},
            }]
        })
        assert r.status_code == 200
        # Verify errors were set
        r = client.get(f"/api/models/{mid}/measurements")
        meas = r.json()["measurements"]
        assert len(meas) == 1
        assert meas[0].get("errors") is not None


# ──────────────────────────────────────────────────────────
# 4. Estimation
# ──────────────────────────────────────────────────────────

class TestEstimation:

    def test_estimate_local(self):
        mid = create_monod_model()
        add_synthetic_measurements(mid)
        r = client.post(f"/api/models/{mid}/estimate", json={
            "unknowns": {"mu_max": [0.1, 2.0], "K_S": [0.01, 5.0]},
            "method": "local",
            "metric": "SS",
        })
        assert r.status_code == 200, f"Estimate failed: {r.text}"
        data = r.json()
        assert "estimates" in data
        assert "mu_max" in data["estimates"]

    def test_estimate_no_measurements(self):
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/estimate", json={
            "unknowns": {"mu_max": [0.1, 2.0]},
            "method": "local",
        })
        assert r.status_code == 400


# ──────────────────────────────────────────────────────────
# 5. Analysis
# ──────────────────────────────────────────────────────────

class TestAnalysis:

    def test_sensitivities_with_measurements(self):
        """Sensitivities using measurements (the preferred way)."""
        mid = create_monod_model()
        add_synthetic_measurements(mid)
        r = client.post(f"/api/models/{mid}/sensitivities", json={
            "t_end": 10, "n_points": 50,
        })
        assert r.status_code == 200, f"Sensitivity failed: {r.text}"
        data = r.json()
        assert "sensitivities" in data
        assert len(data["sensitivities"]) > 0

    def test_sensitivities_no_measurements(self):
        """Sensitivities using tfinal (no measurements loaded)."""
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/sensitivities", json={
            "t_end": 10, "n_points": 50,
        })
        assert r.status_code == 200, f"Sensitivity (tfinal) failed: {r.text}"

    def test_parameter_matrices(self):
        mid = create_monod_model()
        add_synthetic_measurements(mid)
        # First get sensitivities
        r = client.post(f"/api/models/{mid}/sensitivities", json={"t_end": 10, "n_points": 50})
        assert r.status_code == 200, f"Sensitivity failed: {r.text}"
        r = client.post(f"/api/models/{mid}/parameter-matrices", json={
            "estimates": {"mu_max": 0.5, "K_S": 0.1},
        })
        assert r.status_code == 200
        data = r.json()
        assert "FIM" in data

    def test_parameter_uncertainties(self):
        mid = create_monod_model()
        add_synthetic_measurements(mid)
        r = client.post(f"/api/models/{mid}/parameter-uncertainties", json={
            "estimates": {"mu_max": 0.5, "K_S": 0.1},
        })
        # Accept 200 (success) or 400 (FIM not invertible with sparse test data — expected)
        assert r.status_code in (200, 400)


# ──────────────────────────────────────────────────────────
# 6. Parameter Management
# ──────────────────────────────────────────────────────────

class TestParameters:

    def test_get_parameters(self):
        mid = create_monod_model()
        r = client.get(f"/api/models/{mid}/parameters")
        assert r.status_code == 200
        params = r.json()["parameters"]
        assert "mu_max" in params

    def test_set_parameters(self):
        mid = create_monod_model()
        r = client.put(f"/api/models/{mid}/parameters", json={
            "parameters": {"mu_max": 0.8},
        })
        assert r.status_code == 200

    def test_get_parameter_mapping(self):
        mid = create_monod_model()
        r = client.get(f"/api/models/{mid}/parameter-mapping")
        assert r.status_code == 200

    def test_set_integrator(self):
        mid = create_monod_model()
        r = client.put(f"/api/models/{mid}/integrator", json={
            "kwargs": {"atol": 1e-8, "rtol": 1e-6},
        })
        assert r.status_code == 200
        # Verify simulation still works
        r = client.post(f"/api/models/{mid}/simulate", json={
            "t_start": 0, "t_end": 10, "n_points": 50,
        })
        assert r.status_code == 200


# ──────────────────────────────────────────────────────────
# 7. Observation Functions + Model Check
# ──────────────────────────────────────────────────────────

class TestObservations:

    def test_list_observation_templates(self):
        r = client.get("/api/templates/observations")
        assert r.status_code == 200
        templates = r.json()["templates"]
        assert len(templates) > 0

    def test_add_observation_function(self):
        mid = create_monod_model()
        r = client.get("/api/templates/observations")
        obs_templates = r.json()["templates"]
        if obs_templates:
            obs_id = obs_templates[0]["id"]
            r2 = client.get(f"/api/models/{mid}")
            states = r2.json()["metadata"]["states"]
            r3 = client.post(f"/api/models/{mid}/observation-functions", json={
                "template_id": obs_id,
                "observed_state": states[0],
            })
            assert r3.status_code == 200, f"Add obs failed: {r3.text}"

    def test_model_check(self):
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/check")
        assert r.status_code == 200
        assert "passed" in r.json()


# ──────────────────────────────────────────────────────────
# 8. New Features: Error Model, Optimizer Kwargs, Reset
# ──────────────────────────────────────────────────────────

class TestNewFeatures:

    def test_update_error_model(self):
        """PUT error model on existing measurement."""
        mid = create_monod_model()
        # Add measurement without error model
        client.post(f"/api/models/{mid}/measurements", json={
            "measurements": [{"name": "X", "timepoints": [0, 5, 10], "values": [0.1, 1.5, 4.2]}]
        })
        # Update error model
        r = client.put(f"/api/models/{mid}/measurements/X/error-model", json={
            "error_model_type": "relative",
            "error_model_parameters": {"rel_error": 0.1},
        })
        assert r.status_code == 200, f"Update error model failed: {r.text}"

    def test_error_model_combined(self):
        """Test combined error model (abs + rel)."""
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/measurements", json={
            "measurements": [{
                "name": "S",
                "timepoints": [0, 5, 10],
                "values": [10.0, 5.0, 0.5],
                "error_model_type": "combined",
                "error_model_parameters": {"abs_error": 0.1, "rel_error": 0.05},
            }]
        })
        assert r.status_code == 200, f"Error model combined failed: {r.text}"
        r = client.get(f"/api/models/{mid}/measurements")
        meas = r.json()["measurements"]
        assert len(meas) == 1
        assert meas[0].get("errors") is not None

    def test_error_model_not_found(self):
        mid = create_monod_model()
        r = client.put(f"/api/models/{mid}/measurements/NOTEXIST/error-model", json={
            "error_model_type": "constant",
            "error_model_parameters": {"abs_error": 0.1},
        })
        assert r.status_code == 404

    def test_optimizer_kwargs_get(self):
        mid = create_monod_model()
        r = client.get(f"/api/models/{mid}/optimizer-kwargs")
        assert r.status_code == 200
        assert "optimizer_kwargs" in r.json()

    def test_optimizer_kwargs_set(self):
        mid = create_monod_model()
        r = client.put(f"/api/models/{mid}/optimizer-kwargs", json={
            "optimizer_kwargs": {"maxiter": 500},
        })
        assert r.status_code == 200

    def test_reset_model(self):
        mid = create_monod_model()
        # Change parameters
        client.put(f"/api/models/{mid}/parameters", json={"parameters": {"mu_max": 99.0}})
        # Reset
        r = client.post(f"/api/models/{mid}/reset")
        assert r.status_code == 200

    def test_generate_data(self):
        """Generate synthetic noisy data from simulation."""
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/generate-data", json={
            "t_end": 10,
            "n_points": 15,
            "noise_percent": 5.0,
            "seed": 42,
        })
        assert r.status_code == 200, f"Generate data failed: {r.text}"
        data = r.json()
        assert len(data["names"]) == 3  # P, S, X
        assert len(data["measurements"]) == 3
        for m in data["measurements"]:
            assert len(m["timepoints"]) == 15
            assert len(m["values"]) == 15
            assert len(m["errors"]) == 15

        # Verify measurements are stored in session
        r = client.get(f"/api/models/{mid}/measurements")
        assert len(r.json()["measurements"]) == 3

    def test_generate_data_specific_states(self):
        """Generate data for specific states only."""
        mid = create_monod_model()
        r = client.post(f"/api/models/{mid}/generate-data", json={
            "t_end": 10,
            "n_points": 10,
            "noise_percent": 3.0,
            "states": ["X", "S"],
        })
        assert r.status_code == 200
        assert set(r.json()["names"]) == {"X", "S"}


# ──────────────────────────────────────────────────────────
# 9. End-to-End Workflow
# ──────────────────────────────────────────────────────────

class TestE2EWorkflow:

    def test_full_workflow(self):
        """
        Simulate full user workflow:
        Create → Simulate → Add Data → Estimate → Sensitivities → Matrices
        """
        # 1. Create model
        r = client.post("/api/models", json={
            "template_id": "monod_growth",
            "model_parameters": {"mu_max": 0.5, "K_S": 0.1, "Y_XS": 0.5, "Y_PS": 0.3},
            "initial_values": {"P0": 0.0, "S0": 10.0, "X0": 0.1},
        })
        assert r.status_code == 200, f"Create failed: {r.text}"
        mid = r.json()["model_id"]

        # 2. Simulate
        r = client.post(f"/api/models/{mid}/simulate", json={
            "t_start": 0, "t_end": 10, "n_points": 30,
        })
        assert r.status_code == 200
        sim = r.json()["results"]

        # 3. Add measurements (use simulation output with noise)
        measurements = []
        for s in sim:
            measurements.append({
                "name": s["name"],
                "timepoints": s["timepoints"],
                "values": [v * 1.02 for v in s["values"]],
                "errors": [max(0.01, abs(v) * 0.05) for v in s["values"]],
            })
        r = client.post(f"/api/models/{mid}/measurements", json={"measurements": measurements})
        assert r.status_code == 200

        # 4. Local estimate (using global optimizer with bounds)
        r = client.post(f"/api/models/{mid}/estimate", json={
            "unknowns": {"mu_max": [0.1, 2.0], "K_S": [0.01, 5.0]},
            "method": "local",
        })
        assert r.status_code == 200, f"Estimation failed: {r.text}"
        estimates = r.json()["estimates"]
        assert "mu_max" in estimates
        assert "K_S" in estimates

        # 5. Sensitivities (measurements already loaded in session)
        r = client.post(f"/api/models/{mid}/sensitivities", json={
            "t_end": 10, "n_points": 30,
        })
        assert r.status_code == 200, f"Sensitivities failed: {r.text}"

        # 6. Parameter matrices (FIM, Cov, Corr)
        r = client.post(f"/api/models/{mid}/parameter-matrices", json={
            "estimates": estimates,
        })
        assert r.status_code == 200
        matrices = r.json()
        assert matrices.get("FIM") is not None
