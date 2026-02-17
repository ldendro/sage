"""Risk parity meta allocator UI renderer (app-side)."""

from typing import Any, Dict, List

import streamlit as st

from sage_core.meta.risk_parity import RiskParityAllocator

DEFAULTS = RiskParityAllocator.DEFAULT_PARAMS

BOUNDS = {
    "vol_lookback": (10, 252, 10),
}


def render_params(key_prefix: str, selected_strategies: List[str], current_values: Dict[str, Any] = None) -> Dict[str, Any]:
    """Render risk parity parameters and return params dict."""
    del selected_strategies
    cv = current_values or {}

    vol_lookback = st.slider(
        "Volatility Lookback (days)",
        min_value=BOUNDS["vol_lookback"][0],
        max_value=BOUNDS["vol_lookback"][1],
        value=cv.get("vol_lookback", DEFAULTS["vol_lookback"]),
        step=BOUNDS["vol_lookback"][2],
        help="Lookback period for strategy volatility calculation",
        key=f"{key_prefix}vol_lookback",
    )

    return {"vol_lookback": vol_lookback}
