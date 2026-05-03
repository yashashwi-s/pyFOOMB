"""
Pre-built bioprocess model templates.
Users select a template and configure parameters via the GUI — no code editing.
"""

import numpy as np
from pyfoomb import BioprocessModel, ObservationFunction


# ──────────────────────────────────────────────
# GROWTH MODELS
# ──────────────────────────────────────────────

class MonodGrowth(BioprocessModel):
    """Classic Monod growth model with substrate consumption and product formation.
    States: X (biomass), S (substrate), P (product)
    Parameters: mu_max, K_S, Y_XS, Y_PS
    """
    def rhs(self, t, y, sw=None):
        P, S, X = y
        mu_max = self.model_parameters['mu_max']
        K_S = self.model_parameters['K_S']
        Y_XS = self.model_parameters['Y_XS']
        Y_PS = self.model_parameters['Y_PS']

        mu = mu_max * S / (K_S + S)

        dPdt = Y_PS * mu * X
        dSdt = -1.0 / Y_XS * mu * X
        dXdt = mu * X

        return np.array([dPdt, dSdt, dXdt])


class ExponentialGrowth(BioprocessModel):
    """Simple exponential growth model.
    States: X (biomass)
    Parameters: mu (specific growth rate)
    """
    def rhs(self, t, y, sw=None):
        X = y[0]
        mu = self.model_parameters['mu']
        dXdt = mu * X
        return np.array([dXdt])


class LogisticGrowth(BioprocessModel):
    """Logistic growth with carrying capacity.
    States: X (biomass)
    Parameters: mu_max, K (carrying capacity)
    """
    def rhs(self, t, y, sw=None):
        X = y[0]
        K = self.model_parameters['K']
        mu_max = self.model_parameters['mu_max']
        dXdt = mu_max * X * (1 - X / K)
        return np.array([dXdt])


class ExponentialDecay(BioprocessModel):
    """First-order exponential decay.
    States: C (concentration)
    Parameters: k (decay rate)
    """
    def rhs(self, t, y, sw=None):
        C = y[0]
        k = self.model_parameters['k']
        dCdt = -k * C
        return np.array([dCdt])


class MonodGrowthInhibition(BioprocessModel):
    """Monod growth with substrate inhibition (Andrews/Haldane).
    States: X (biomass), S (substrate), P (product)
    Parameters: mu_max, K_S, K_I, Y_XS, Y_PS
    """
    def rhs(self, t, y, sw=None):
        P, S, X = y
        K_I = self.model_parameters['K_I']
        K_S = self.model_parameters['K_S']
        Y_PS = self.model_parameters['Y_PS']
        Y_XS = self.model_parameters['Y_XS']
        mu_max = self.model_parameters['mu_max']

        mu = mu_max * S / (K_S + S + S**2 / K_I)

        dPdt = Y_PS * mu * X
        dSdt = -1.0 / Y_XS * mu * X
        dXdt = mu * X

        return np.array([dPdt, dSdt, dXdt])


class ContoisGrowth(BioprocessModel):
    """Contois growth model (density-dependent saturation).
    States: X (biomass), S (substrate)
    Parameters: mu_max, K_SX, Y_XS
    """
    def rhs(self, t, y, sw=None):
        S, X = y
        K_SX = self.model_parameters['K_SX']
        Y_XS = self.model_parameters['Y_XS']
        mu_max = self.model_parameters['mu_max']

        mu = mu_max * S / (K_SX * X + S)

        dSdt = -1.0 / Y_XS * mu * X
        dXdt = mu * X

        return np.array([dSdt, dXdt])


class DoubleMonod(BioprocessModel):
    """Double Monod: growth limited by two substrates.
    States: X (biomass), S1 (substrate 1), S2 (substrate 2)
    Parameters: mu_max, K_S1, K_S2, Y_XS1, Y_XS2
    """
    def rhs(self, t, y, sw=None):
        S1, S2, X = y
        K_S1 = self.model_parameters['K_S1']
        K_S2 = self.model_parameters['K_S2']
        Y_XS1 = self.model_parameters['Y_XS1']
        Y_XS2 = self.model_parameters['Y_XS2']
        mu_max = self.model_parameters['mu_max']

        mu = mu_max * S1 / (K_S1 + S1) * S2 / (K_S2 + S2)

        dS1dt = -1.0 / Y_XS1 * mu * X
        dS2dt = -1.0 / Y_XS2 * mu * X
        dXdt = mu * X

        return np.array([dS1dt, dS2dt, dXdt])


# ──────────────────────────────────────────────
# FED-BATCH MODELS (with event handling)
# ──────────────────────────────────────────────

class FedBatchMonod(BioprocessModel):
    """Monod growth with a pulse feed event.
    States: S (substrate), V (volume), X (biomass)
    Parameters: mu_max, K_S, Y_XS, S_feed, V_feed, t_feed
    Events: feeding at t = t_feed
    """
    def rhs(self, t, y, sw):
        S, V, X = y
        K_S = self.model_parameters['K_S']
        Y_XS = self.model_parameters['Y_XS']
        mu_max = self.model_parameters['mu_max']

        mu = mu_max * S / (K_S + S)

        dSdt = -1.0 / Y_XS * mu * X
        dVdt = 0.0
        dXdt = mu * X

        return np.array([dSdt, dVdt, dXdt])

    def state_events(self, t, y, sw):
        t_feed = self.model_parameters['t_feed']
        event_feed = t - t_feed
        return np.array([event_feed])

    def change_states(self, t, y, sw):
        S, V, X = y
        if sw[0]:
            S_feed = self.model_parameters['S_feed']
            V_feed = self.model_parameters['V_feed']
            S = (S * V + S_feed * V_feed) / (V + V_feed)
            X = X * V / (V + V_feed)
            V = V + V_feed
        return [S, V, X]


# ──────────────────────────────────────────────
# OBSERVATION FUNCTIONS
# ──────────────────────────────────────────────

class LinearObservation(ObservationFunction):
    """Linear observation: y_obs = slope * state + offset"""
    def observe(self, state_values):
        offset = self.observation_parameters['offset']
        slope = self.observation_parameters['slope']
        return state_values * slope + offset


class LogObservation(ObservationFunction):
    """Logarithmic observation: y_obs = scale * log(state + epsilon)"""
    def observe(self, state_values):
        epsilon = self.observation_parameters['epsilon']
        scale = self.observation_parameters['scale']
        return scale * np.log(state_values + epsilon)


# ──────────────────────────────────────────────
# TEMPLATE REGISTRY
# ──────────────────────────────────────────────

MODEL_TEMPLATES = {
    "monod_growth": {
        "class": MonodGrowth,
        "name": "Monod Growth",
        "category": "Growth Models",
        "description": "Classic Monod growth kinetics with substrate limitation. Widely used for microbial growth modeling.",
        "equation": "\\mu = \\frac{\\mu_{max} \\cdot S}{K_S + S}",
        "states": ["P", "S", "X"],
        "state_labels": {"P": "Product", "S": "Substrate", "X": "Biomass"},
        "model_parameters": {"mu_max": 0.5, "K_S": 0.1, "Y_XS": 0.5, "Y_PS": 0.3},
        "parameter_labels": {
            "mu_max": "Max. specific growth rate [1/h]",
            "K_S": "Substrate saturation constant [g/L]",
            "Y_XS": "Biomass yield on substrate [g/g]",
            "Y_PS": "Product yield on substrate [g/g]",
        },
        "initial_values": {"P0": 0.0, "S0": 10.0, "X0": 0.1},
        "initial_value_labels": {"P0": "Initial product [g/L]", "S0": "Initial substrate [g/L]", "X0": "Initial biomass [g/L]"},
        "initial_switches": None,
        "default_t_end": 20.0,
    },
    "exponential_growth": {
        "class": ExponentialGrowth,
        "name": "Exponential Growth",
        "category": "Growth Models",
        "description": "Unlimited exponential growth. Simplest growth model, applicable to early-phase batch cultures.",
        "equation": "\\frac{dX}{dt} = \\mu \\cdot X",
        "states": ["X"],
        "state_labels": {"X": "Biomass"},
        "model_parameters": {"mu": 0.3},
        "parameter_labels": {"mu": "Specific growth rate [1/h]"},
        "initial_values": {"X0": 0.1},
        "initial_value_labels": {"X0": "Initial biomass [g/L]"},
        "initial_switches": None,
        "default_t_end": 24.0,
    },
    "logistic_growth": {
        "class": LogisticGrowth,
        "name": "Logistic Growth",
        "category": "Growth Models",
        "description": "Growth with carrying capacity. Biomass approaches a maximum value K.",
        "equation": "\\frac{dX}{dt} = \\mu_{max} \\cdot X \\cdot \\left(1 - \\frac{X}{K}\\right)",
        "states": ["X"],
        "state_labels": {"X": "Biomass"},
        "model_parameters": {"mu_max": 0.5, "K": 10.0},
        "parameter_labels": {"mu_max": "Max. growth rate [1/h]", "K": "Carrying capacity [g/L]"},
        "initial_values": {"X0": 0.1},
        "initial_value_labels": {"X0": "Initial biomass [g/L]"},
        "initial_switches": None,
        "default_t_end": 30.0,
    },
    "exponential_decay": {
        "class": ExponentialDecay,
        "name": "Exponential Decay",
        "category": "Decay Models",
        "description": "First-order decay kinetics. Applies to substrate degradation, cell death, or protein denaturation.",
        "equation": "\\frac{dC}{dt} = -k \\cdot C",
        "states": ["C"],
        "state_labels": {"C": "Concentration"},
        "model_parameters": {"k": 0.1},
        "parameter_labels": {"k": "Decay rate constant [1/h]"},
        "initial_values": {"C0": 100.0},
        "initial_value_labels": {"C0": "Initial concentration [g/L]"},
        "initial_switches": None,
        "default_t_end": 50.0,
    },
    "monod_inhibition": {
        "class": MonodGrowthInhibition,
        "name": "Monod + Substrate Inhibition",
        "category": "Growth Models",
        "description": "Andrews/Haldane model: Monod growth with substrate inhibition at high concentrations.",
        "equation": "\\mu = \\frac{\\mu_{max} \\cdot S}{K_S + S + S^2 / K_I}",
        "states": ["P", "S", "X"],
        "state_labels": {"P": "Product", "S": "Substrate", "X": "Biomass"},
        "model_parameters": {"mu_max": 0.5, "K_S": 0.5, "K_I": 50.0, "Y_XS": 0.4, "Y_PS": 0.2},
        "parameter_labels": {
            "mu_max": "Max. specific growth rate [1/h]",
            "K_S": "Substrate saturation constant [g/L]",
            "K_I": "Substrate inhibition constant [g/L]",
            "Y_XS": "Biomass yield on substrate [g/g]",
            "Y_PS": "Product yield on substrate [g/g]",
        },
        "initial_values": {"P0": 0.0, "S0": 20.0, "X0": 0.1},
        "initial_value_labels": {"P0": "Initial product [g/L]", "S0": "Initial substrate [g/L]", "X0": "Initial biomass [g/L]"},
        "initial_switches": None,
        "default_t_end": 40.0,
    },
    "contois_growth": {
        "class": ContoisGrowth,
        "name": "Contois Growth",
        "category": "Growth Models",
        "description": "Density-dependent saturation. The half-saturation depends on biomass concentration.",
        "equation": "\\mu = \\frac{\\mu_{max} \\cdot S}{K_{SX} \\cdot X + S}",
        "states": ["S", "X"],
        "state_labels": {"S": "Substrate", "X": "Biomass"},
        "model_parameters": {"mu_max": 0.5, "K_SX": 0.5, "Y_XS": 0.5},
        "parameter_labels": {
            "mu_max": "Max. specific growth rate [1/h]",
            "K_SX": "Contois saturation constant [g/g]",
            "Y_XS": "Biomass yield on substrate [g/g]",
        },
        "initial_values": {"S0": 10.0, "X0": 0.1},
        "initial_value_labels": {"S0": "Initial substrate [g/L]", "X0": "Initial biomass [g/L]"},
        "initial_switches": None,
        "default_t_end": 30.0,
    },
    "double_monod": {
        "class": DoubleMonod,
        "name": "Double Monod",
        "category": "Growth Models",
        "description": "Growth limited by two substrates simultaneously. Common in co-metabolism scenarios.",
        "equation": "\\mu = \\mu_{max} \\cdot \\frac{S_1}{K_{S1} + S_1} \\cdot \\frac{S_2}{K_{S2} + S_2}",
        "states": ["S1", "S2", "X"],
        "state_labels": {"S1": "Substrate 1", "S2": "Substrate 2", "X": "Biomass"},
        "model_parameters": {"mu_max": 0.4, "K_S1": 0.5, "K_S2": 1.0, "Y_XS1": 0.5, "Y_XS2": 0.3},
        "parameter_labels": {
            "mu_max": "Max. specific growth rate [1/h]",
            "K_S1": "Saturation constant S₁ [g/L]",
            "K_S2": "Saturation constant S₂ [g/L]",
            "Y_XS1": "Yield on S₁ [g/g]",
            "Y_XS2": "Yield on S₂ [g/g]",
        },
        "initial_values": {"S10": 10.0, "S20": 5.0, "X0": 0.1},
        "initial_value_labels": {"S10": "Initial S₁ [g/L]", "S20": "Initial S₂ [g/L]", "X0": "Initial biomass [g/L]"},
        "initial_switches": None,
        "default_t_end": 30.0,
    },
    "fed_batch_monod": {
        "class": FedBatchMonod,
        "name": "Fed-Batch Monod",
        "category": "Fed-Batch Models",
        "description": "Monod growth with a pulse feed event at a specified time. Substrate and volume are adjusted upon feeding.",
        "equation": "\\mu = \\frac{\\mu_{max} \\cdot S}{K_S + S}, \\quad \\text{feed at } t = t_{feed}",
        "states": ["S", "V", "X"],
        "state_labels": {"S": "Substrate", "V": "Volume", "X": "Biomass"},
        "model_parameters": {
            "mu_max": 0.5, "K_S": 0.1, "Y_XS": 0.5,
            "S_feed": 100.0, "V_feed": 0.1, "t_feed": 10.0,
        },
        "parameter_labels": {
            "mu_max": "Max. growth rate [1/h]",
            "K_S": "Saturation constant [g/L]",
            "Y_XS": "Biomass yield [g/g]",
            "S_feed": "Feed substrate conc. [g/L]",
            "V_feed": "Feed volume [L]",
            "t_feed": "Feed time [h]",
        },
        "initial_values": {"S0": 10.0, "V0": 1.0, "X0": 0.5},
        "initial_value_labels": {"S0": "Initial substrate [g/L]", "V0": "Initial volume [L]", "X0": "Initial biomass [g/L]"},
        "initial_switches": [False],
        "default_t_end": 24.0,
    },
}

OBSERVATION_TEMPLATES = {
    "linear": {
        "class": LinearObservation,
        "name": "Linear",
        "description": "y_obs = slope × state + offset",
        "parameters": {"slope": 1.0, "offset": 0.0},
        "parameter_labels": {"slope": "Slope", "offset": "Offset"},
    },
    "logarithmic": {
        "class": LogObservation,
        "name": "Logarithmic",
        "description": "y_obs = scale × ln(state + ε)",
        "parameters": {"scale": 1.0, "epsilon": 1e-10},
        "parameter_labels": {"scale": "Scale factor", "epsilon": "Small offset to avoid log(0)"},
    },
}


def get_template_list():
    """Return summary info of all available templates for the frontend."""
    templates = []
    for key, tmpl in MODEL_TEMPLATES.items():
        templates.append({
            "id": key,
            "name": tmpl["name"],
            "category": tmpl["category"],
            "description": tmpl["description"],
            "equation": tmpl["equation"],
            "states": tmpl["states"],
            "state_labels": tmpl["state_labels"],
            "parameters": tmpl["model_parameters"],
            "parameter_labels": tmpl["parameter_labels"],
            "initial_values": tmpl["initial_values"],
            "initial_value_labels": tmpl["initial_value_labels"],
            "default_t_end": tmpl["default_t_end"],
        })
    return templates


def get_observation_template_list():
    """Return summary info of all observation function templates."""
    return [
        {
            "id": key,
            "name": tmpl["name"],
            "description": tmpl["description"],
            "parameters": tmpl["parameters"],
            "parameter_labels": tmpl["parameter_labels"],
        }
        for key, tmpl in OBSERVATION_TEMPLATES.items()
    ]
