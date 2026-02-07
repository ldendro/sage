"""Passthrough strategy UI (no parameters)."""

from typing import Any, Dict


def render_params(key_prefix: str) -> Dict[str, Any]:
    del key_prefix
    return {}
