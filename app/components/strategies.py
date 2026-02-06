"""Strategy selection component."""

import streamlit as st
from sage_core.strategies import STRATEGY_REGISTRY
from typing import Optional

from app.strategy_ui.registry import get_strategy_spec

# ==================== DEFAULTS ====================
DEFAULT_STRATEGIES = ['passthrough']


def render(
    key_prefix: str = "",
    container: Optional[st.delta_generator.DeltaGenerator] = None,
    show_header: bool = True,
) -> dict:
    """
    Render strategy selection UI.
    
    Returns:
        dict with keys:
            - strategies: dict mapping strategy name to config {'params': {...}}
            - errors: list of validation error strings
    """
    container = container or st.sidebar
    errors = []
    
    # ==================== STRATEGY SELECTION ====================
    if show_header:
        container.markdown("---")
        container.markdown("### Strategy Selection")
    
    # Get display names for multiselect
    strategy_options = list(STRATEGY_REGISTRY.keys())
    format_func = lambda x: get_strategy_spec(x).display_name
    
    selected_strategies = container.multiselect(
        "Select Strategies",
        options=strategy_options,
        default=DEFAULT_STRATEGIES,
        format_func=format_func,
        help="Choose one or more strategies. Multiple strategies will be combined using a meta allocator.",
        key=f"{key_prefix}strategies",
    )
    
    # Validate at least one strategy selected
    if not selected_strategies:
        container.error("⚠️ Select at least one strategy")
        errors.append("At least one strategy must be selected")
    
    # ==================== STRATEGY PARAMETERS ====================
    strategies_config = {}

    if selected_strategies:
        container.markdown("#### Strategy Parameters")

    for strategy_name in selected_strategies:
        spec = get_strategy_spec(strategy_name)

        expander = container.expander(f"{spec.display_name} Parameters", expanded=False)
        with expander:
            if spec.description:
                expander.caption(spec.description)
            if spec.render_params is not None:
                params = spec.render_params(key_prefix=f"{key_prefix}{strategy_name}_")
            else:
                expander.caption("_No parameters_")
                params = {}
        strategies_config[strategy_name] = {'params': params}

    if selected_strategies:
        if len(selected_strategies) == 1:
            container.info(f"ℹ️ Single strategy: **{format_func(selected_strategies[0])}**")
        else:
            if 'passthrough' in selected_strategies:
                container.error("⚠️ Passthrough strategy cannot be combined with other strategies")
                errors.append("Passthrough strategy cannot be combined with other strategies")
            else:
                container.info(f"ℹ️ {len(selected_strategies)} strategies selected - meta allocator will combine them")

    
    return {
        'strategies': strategies_config,
        'selected_strategies': selected_strategies,
        'errors': errors,
    }
