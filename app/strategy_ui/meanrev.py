"""Mean reversion strategy UI renderer (app-side)."""

from typing import Any, Dict

import streamlit as st

from sage_core.strategies.meanrev import MeanRevStrategy

DEFAULTS = MeanRevStrategy.DEFAULT_PARAMS

BOUNDS = {
    "rsi_period": (2, 100, 1),
    "rsi_oversold": (0, 100, 1),
    "rsi_overbought": (0, 100, 1),
    "bb_period": (2, 200, 1),
    "bb_std": (0.5, 5.0, 0.1),
    "zscore_lookback": (10, 252, 5),
    "zscore_threshold": (0.5, 5.0, 0.1),
    "weighted_threshold": (0.0, 1.0, 0.01),
    "weight_step": 0.05,
}

COMBINATION_METHODS = [
    ("majority", "Majority vote"),
    ("all", "All agree"),
    ("weighted", "Weighted blend"),
]

def _clamp_state(key: str, min_value: float, max_value: float) -> None:
    if key not in st.session_state:
        return
    value = st.session_state[key]
    if value < min_value:
        st.session_state[key] = min_value
    elif value > max_value:
        st.session_state[key] = max_value


def render_params(key_prefix: str) -> Dict[str, Any]:
    """Render Mean Reversion strategy parameters and return params dict."""
    rsi_period = st.slider(
        "RSI period (days)",
        min_value=BOUNDS["rsi_period"][0],
        max_value=BOUNDS["rsi_period"][1],
        value=DEFAULTS["rsi_period"],
        step=BOUNDS["rsi_period"][2],
        help="Window length for RSI calculation",
        key=f"{key_prefix}rsi_period",
    )

    rsi_oversold = st.slider(
        "RSI oversold",
        min_value=BOUNDS["rsi_oversold"][0],
        max_value=BOUNDS["rsi_oversold"][1],
        value=DEFAULTS["rsi_oversold"],
        step=BOUNDS["rsi_oversold"][2],
        help="Buy signal threshold",
        key=f"{key_prefix}rsi_oversold",
    )

    rsi_overbought_min = max(BOUNDS["rsi_overbought"][0], rsi_oversold + 1)
    rsi_overbought_default = DEFAULTS["rsi_overbought"]
    if rsi_overbought_default < rsi_overbought_min:
        rsi_overbought_default = rsi_overbought_min
    _clamp_state(f"{key_prefix}rsi_overbought", rsi_overbought_min, BOUNDS["rsi_overbought"][1])

    rsi_overbought = st.slider(
        "RSI overbought",
        min_value=rsi_overbought_min,
        max_value=BOUNDS["rsi_overbought"][1],
        value=rsi_overbought_default,
        step=BOUNDS["rsi_overbought"][2],
        help="Sell signal threshold",
        key=f"{key_prefix}rsi_overbought",
    )

    bb_period = st.slider(
        "Bollinger Bands period (days)",
        min_value=BOUNDS["bb_period"][0],
        max_value=BOUNDS["bb_period"][1],
        value=DEFAULTS["bb_period"],
        step=BOUNDS["bb_period"][2],
        help="Window length for Bollinger Bands",
        key=f"{key_prefix}bb_period",
    )

    bb_std = st.slider(
        "Bollinger Bands std dev",
        min_value=BOUNDS["bb_std"][0],
        max_value=BOUNDS["bb_std"][1],
        value=DEFAULTS["bb_std"],
        step=BOUNDS["bb_std"][2],
        help="Standard deviation multiplier",
        key=f"{key_prefix}bb_std",
    )

    zscore_lookback = st.slider(
        "Z-Score lookback (days)",
        min_value=BOUNDS["zscore_lookback"][0],
        max_value=BOUNDS["zscore_lookback"][1],
        value=DEFAULTS["zscore_lookback"],
        step=BOUNDS["zscore_lookback"][2],
        help="Window length for Z-Score",
        key=f"{key_prefix}zscore_lookback",
    )

    zscore_threshold = st.slider(
        "Z-Score threshold",
        min_value=BOUNDS["zscore_threshold"][0],
        max_value=BOUNDS["zscore_threshold"][1],
        value=DEFAULTS["zscore_threshold"],
        step=BOUNDS["zscore_threshold"][2],
        help="Higher threshold = fewer trades",
        key=f"{key_prefix}zscore_threshold",
    )

    method_options = [method for method, _ in COMBINATION_METHODS]
    method_labels = {method: label for method, label in COMBINATION_METHODS}
    default_method = DEFAULTS["combination_method"]
    method_index = method_options.index(default_method) if default_method in method_options else 0

    combination_method = st.selectbox(
        "Signal combination method",
        options=method_options,
        index=method_index,
        format_func=lambda value: method_labels.get(value, value),
        help="How to combine RSI, Bollinger Bands, and Z-Score signals",
        key=f"{key_prefix}combination_method",
    )

    weights = list(DEFAULTS["weights"])
    weighted_threshold = DEFAULTS["weighted_threshold"]

    if combination_method == "weighted":
        st.markdown("**Weights (sum to 1)**")
        weight_step = BOUNDS["weight_step"]

        _clamp_state(f"{key_prefix}weight_rsi", 0.0, 1.0)
        weight_rsi = st.slider(
            "RSI weight",
            min_value=0.0,
            max_value=1.0,
            value=weights[0],
            step=weight_step,
            key=f"{key_prefix}weight_rsi",
        )

        max_bb_weight = max(0.0, 1.0 - weight_rsi)
        default_bb_weight = weights[1]
        if default_bb_weight > max_bb_weight:
            default_bb_weight = max_bb_weight

        if max_bb_weight <= 0.0:
            _clamp_state(f"{key_prefix}weight_bb", 0.0, 0.0)
            weight_bb = 0.0
            st.caption(f"Bollinger Bands weight (computed): {weight_bb:.2f}")
        else:
            _clamp_state(f"{key_prefix}weight_bb", 0.0, max_bb_weight)
            weight_bb = st.slider(
                "Bollinger Bands weight",
                min_value=0.0,
                max_value=max_bb_weight,
                value=default_bb_weight,
                step=weight_step,
                key=f"{key_prefix}weight_bb",
            )

        weight_zscore = max(0.0, 1.0 - weight_rsi - weight_bb)
        st.caption(f"Z-Score weight (computed): {weight_zscore:.2f}")

        weights = [weight_rsi, weight_bb, weight_zscore]

        weighted_threshold = st.slider(
            "Weighted threshold",
            min_value=BOUNDS["weighted_threshold"][0],
            max_value=BOUNDS["weighted_threshold"][1],
            value=DEFAULTS["weighted_threshold"],
            step=BOUNDS["weighted_threshold"][2],
            help="Lower threshold = more aggressive, higher = more conservative",
            key=f"{key_prefix}weighted_threshold",
        )

    return {
        "rsi_period": rsi_period,
        "rsi_oversold": rsi_oversold,
        "rsi_overbought": rsi_overbought,
        "bb_period": bb_period,
        "bb_std": bb_std,
        "zscore_lookback": zscore_lookback,
        "zscore_threshold": zscore_threshold,
        "combination_method": combination_method,
        "weights": weights,
        "weighted_threshold": weighted_threshold,
    }
