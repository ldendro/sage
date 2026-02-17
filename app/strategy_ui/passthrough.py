"""Passthrough strategy UI (no parameters)."""

from typing import Any, Dict


def render_params(key_prefix: str, current_values: Dict[str, Any] = None) -> Dict[str, Any]:
    del key_prefix
    del current_values
    return {}
