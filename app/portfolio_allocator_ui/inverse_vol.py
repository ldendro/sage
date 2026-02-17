"""Inverse volatility portfolio allocator UI renderer (app-side)."""

from typing import Any, Dict

import streamlit as st

DEFAULT_LOOKBACK = 60

BOUNDS = {
    "lookback": (10, 252, 10),
}


def render_params(key_prefix: str, current_values: Dict[str, Any] = None) -> Dict[str, Any]:
    """Render inverse volatility parameters and return params dict."""
    cv = current_values or {}
    lookback = st.slider(
        "Inverse Vol Window (trading days)",
        min_value=BOUNDS["lookback"][0],
        max_value=BOUNDS["lookback"][1],
        value=cv.get("lookback", DEFAULT_LOOKBACK),
        step=BOUNDS["lookback"][2],
        help="Lookback window for inverse volatility weight calculation across assets",
        key=f"{key_prefix}lookback",
    )

    return {"lookback": lookback}
