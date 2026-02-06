"""Trend strategy UI renderer (app-side)."""

from typing import Any, Dict

import streamlit as st

from sage_core.strategies.trend import TrendStrategy

DEFAULTS = TrendStrategy.DEFAULT_PARAMS

BOUNDS = {
    "momentum_lookback": (20, 504, 10),
    "sma_short": (5, 200, 5),
    "sma_long": (20, 400, 10),
    "breakout_period": (20, 504, 10),
    "weighted_threshold": (0.0, 1.0, 0.01),
    "weight_step": 0.05,
}

COMBINATION_METHODS = [
    ("majority", "Majority vote"),
    ("all", "All agree"),
    ("weighted", "Weighted blend"),
]


def render_params(key_prefix: str) -> Dict[str, Any]:
    """Render Trend strategy parameters and return params dict."""
    momentum_lookback = st.slider(
        "Momentum lookback (days)",
        min_value=BOUNDS["momentum_lookback"][0],
        max_value=BOUNDS["momentum_lookback"][1],
        value=DEFAULTS["momentum_lookback"],
        step=BOUNDS["momentum_lookback"][2],
        help="Days for momentum calculation",
        key=f"{key_prefix}momentum_lookback",
    )

    sma_short = st.slider(
        "Short SMA (days)",
        min_value=BOUNDS["sma_short"][0],
        max_value=BOUNDS["sma_short"][1],
        value=DEFAULTS["sma_short"],
        step=BOUNDS["sma_short"][2],
        help="Short moving average window",
        key=f"{key_prefix}sma_short",
    )

    sma_long_min = max(BOUNDS["sma_long"][0], sma_short + 1)
    sma_long_max = BOUNDS["sma_long"][1]
    sma_long_default = DEFAULTS["sma_long"]
    if sma_long_default < sma_long_min:
        sma_long_default = sma_long_min
    if sma_long_default > sma_long_max:
        sma_long_default = sma_long_max

    sma_long = st.slider(
        "Long SMA (days)",
        min_value=sma_long_min,
        max_value=sma_long_max,
        value=sma_long_default,
        step=BOUNDS["sma_long"][2],
        help="Long moving average window (must be > short SMA)",
        key=f"{key_prefix}sma_long",
    )

    breakout_period = st.slider(
        "Breakout period (days)",
        min_value=BOUNDS["breakout_period"][0],
        max_value=BOUNDS["breakout_period"][1],
        value=DEFAULTS["breakout_period"],
        step=BOUNDS["breakout_period"][2],
        help="Lookback window for 52-week high/low breakout",
        key=f"{key_prefix}breakout_period",
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
        help="How to combine momentum, MA crossover, and breakout signals",
        key=f"{key_prefix}combination_method",
    )

    weights = list(DEFAULTS["weights"])
    weighted_threshold = DEFAULTS["weighted_threshold"]

    if combination_method == "weighted":
        st.markdown("**Weights (sum to 1)**")
        weight_step = BOUNDS["weight_step"]

        weight_momentum = st.slider(
            "Momentum weight",
            min_value=0.0,
            max_value=1.0,
            value=weights[0],
            step=weight_step,
            key=f"{key_prefix}weight_momentum",
        )

        max_ma_weight = max(0.0, 1.0 - weight_momentum)
        default_ma_weight = weights[1]
        if default_ma_weight > max_ma_weight:
            default_ma_weight = max_ma_weight

        weight_ma = st.slider(
            "MA weight",
            min_value=0.0,
            max_value=max_ma_weight,
            value=default_ma_weight,
            step=weight_step,
            key=f"{key_prefix}weight_ma",
        )

        weight_breakout = max(0.0, 1.0 - weight_momentum - weight_ma)
        st.caption(f"Breakout weight (computed): {weight_breakout:.2f}")

        weights = [weight_momentum, weight_ma, weight_breakout]

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
        "momentum_lookback": momentum_lookback,
        "sma_short": sma_short,
        "sma_long": sma_long,
        "breakout_period": breakout_period,
        "combination_method": combination_method,
        "weights": weights,
        "weighted_threshold": weighted_threshold,
    }
