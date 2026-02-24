"""
In-memory store for active model sessions.
Each session holds a Caretaker, measurements, and estimation results.
"""

import uuid
from typing import Any, Dict, Optional


class ModelSession:
    """Holds all state for a single model session."""

    def __init__(self, model_id: str, caretaker: Any, metadata: dict):
        self.model_id = model_id
        self.caretaker = caretaker
        self.metadata = metadata
        self.measurements: list = []
        self.estimation_results: list = []
        self.sensitivities: Optional[list] = None
        self.last_simulation: Optional[list] = None
        self.observation_functions_code: list = []


class ModelStore:
    """Thread-safe in-memory store for model sessions."""

    def __init__(self):
        self._sessions: Dict[str, ModelSession] = {}

    def create(self, caretaker: Any, metadata: dict) -> str:
        model_id = str(uuid.uuid4())[:8]
        self._sessions[model_id] = ModelSession(model_id, caretaker, metadata)
        return model_id

    def get(self, model_id: str) -> Optional[ModelSession]:
        return self._sessions.get(model_id)

    def list_all(self) -> list:
        return [
            {
                "id": s.model_id,
                "name": s.metadata.get("model_name", "Unnamed"),
                "states": s.metadata.get("states", []),
                "parameters": list(s.metadata.get("model_parameters", {}).keys()),
                "has_observations": len(s.observation_functions_code) > 0,
                "has_measurements": len(s.measurements) > 0,
            }
            for s in self._sessions.values()
        ]

    def delete(self, model_id: str) -> bool:
        if model_id in self._sessions:
            del self._sessions[model_id]
            return True
        return False


# Singleton instance
store = ModelStore()
