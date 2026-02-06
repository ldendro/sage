"""Strategy selection component."""

import streamlit as st
from sage_core.strategies import STRATEGY_REGISTRY

from app.strategy_ui.registry import get_strategy_spec

# ==================== DEFAULTS ====================
DEFAULT_STRATEGIES = ['passthrough']


def render() -> dict:
    """
    Render strategy selection UI.
    
    Returns:
        dict with keys:
            - strategies: dict mapping strategy name to config {'params': {...}}
            - errors: list of validation error strings
    """
    errors = []
    
    # ==================== STRATEGY SELECTION ====================
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Strategy Selection")
    
    # Get display names for multiselect
    strategy_options = list(STRATEGY_REGISTRY.keys())
    format_func = lambda x: get_strategy_spec(x).display_name
    
    selected_strategies = st.sidebar.multiselect(
        "Select Strategies",
        options=strategy_options,
        default=DEFAULT_STRATEGIES,
        format_func=format_func,
        help="Choose one or more strategies. Multiple strategies will be combined using a meta allocator."
    )
    
    # Validate at least one strategy selected
    if not selected_strategies:
        st.sidebar.error("⚠️ Select at least one strategy")
        errors.append("At least one strategy must be selected")
    
    # ==================== STRATEGY PARAMETERS ====================
    strategies_config = {}

    if selected_strategies:
        st.sidebar.markdown("#### Strategy Parameters")

    for strategy_name in selected_strategies:
        spec = get_strategy_spec(strategy_name)

        with st.sidebar.expander(f"{spec.display_name} Parameters", expanded=False):
            if spec.description:
                st.caption(spec.description)
            params = spec.render_params(key_prefix=f"{strategy_name}_")
        strategies_config[strategy_name] = {'params': params}

    if selected_strategies:
        if len(selected_strategies) == 1:
            st.sidebar.info(f"ℹ️ Single strategy: **{format_func(selected_strategies[0])}**")
        else:
            if 'passthrough' in selected_strategies:
                st.sidebar.error("⚠️ Passthrough strategy cannot be combined with other strategies")
                errors.append("Passthrough strategy cannot be combined with other strategies")
            else:
                st.sidebar.info(f"ℹ️ {len(selected_strategies)} strategies selected - meta allocator will combine them")

    
    return {
        'strategies': strategies_config,
        'selected_strategies': selected_strategies,
        'errors': errors,
    }
