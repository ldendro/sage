"""Fixed weight meta allocator UI renderer (app-side)."""

from typing import Any, Dict, List

import streamlit as st


def render_params(key_prefix: str, selected_strategies: List[str]) -> Dict[str, Any]:
    """Render fixed-weight parameters and return params dict."""
    st.markdown("**Strategy Weights**")

    weights: Dict[str, float] = {}
    remaining = 100.0
    n_strategies = len(selected_strategies)

    for i, strategy_name in enumerate(selected_strategies):
        label = strategy_name.replace("_", " ").title()
        if i == n_strategies - 1:
            weights[strategy_name] = round(remaining / 100.0, 4)
            st.markdown(f"**{label} Weight:** {remaining:.0f}%")
        else:
            default_weight = (100.0 / n_strategies) if n_strategies else 0.0
            weight_key = f"{key_prefix}weight_{strategy_name}"
            if weight_key in st.session_state:
                if st.session_state[weight_key] > remaining:
                    st.session_state[weight_key] = remaining
                elif st.session_state[weight_key] < 0.0:
                    st.session_state[weight_key] = 0.0
            weight_pct = st.slider(
                f"**{label} Weight**",
                min_value=0.0,
                max_value=remaining,
                value=min(default_weight, remaining),
                step=1.0,
                format="%.0f%%",
                key=weight_key,
            )
            weights[strategy_name] = weight_pct / 100.0
            remaining = round(remaining - weight_pct, 2)

    return {"weights": weights}
