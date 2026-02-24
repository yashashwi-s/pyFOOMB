"""
Dynamic code executor for creating BioprocessModel and ObservationFunction subclasses
from user-provided Python code strings.
"""

import numpy
from typing import Any, Dict, List, Optional, Type


def create_model_class(
    class_name: str,
    rhs_code: str,
    states: list,
    model_parameters: list,
    state_events_code: Optional[str] = None,
    change_states_code: Optional[str] = None,
) -> Type:
    """
    Dynamically creates a BioprocessModel subclass from user code strings.

    The user provides the body of rhs(), state_events(), and change_states() methods.
    We wrap them into a proper class definition and exec() it.
    """
    from pyfoomb import BioprocessModel

    indent = "        "

    # Build rhs method
    rhs_body = "\n".join(indent + line for line in rhs_code.strip().split("\n"))
    rhs_method = f"    def rhs(self, t, y, sw):\n{rhs_body}"

    # Build state_events method (optional)
    events_method = ""
    if state_events_code and state_events_code.strip():
        events_body = "\n".join(
            indent + line for line in state_events_code.strip().split("\n")
        )
        events_method = f"\n\n    def state_events(self, t, y, sw):\n{events_body}"

    # Build change_states method (optional)
    change_method = ""
    if change_states_code and change_states_code.strip():
        change_body = "\n".join(
            indent + line for line in change_states_code.strip().split("\n")
        )
        change_method = f"\n\n    def change_states(self, t, y, sw):\n{change_body}"

    class_code = f"""
class {class_name}(BioprocessModel):
{rhs_method}{events_method}{change_method}
"""

    namespace = {
        "BioprocessModel": BioprocessModel,
        "numpy": numpy,
    }
    exec(class_code, namespace)
    return namespace[class_name]


def create_observation_class(
    class_name: str,
    observe_code: str,
) -> Type:
    """
    Dynamically creates an ObservationFunction subclass from user code string.
    """
    from pyfoomb import ObservationFunction

    indent = "        "
    observe_body = "\n".join(indent + line for line in observe_code.strip().split("\n"))
    observe_method = f"    def observe(self, state_values):\n{observe_body}"

    class_code = f"""
class {class_name}(ObservationFunction):
{observe_method}
"""

    namespace = {
        "ObservationFunction": ObservationFunction,
        "numpy": numpy,
    }
    exec(class_code, namespace)
    return namespace[class_name]
