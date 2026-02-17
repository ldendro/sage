"""Asset allocator selection component."""

from typing import Dict, Optional

import streamlit as st

from app.portfolio_allocator_ui.registry import (
    PORTFOLIO_ALLOCATOR_SPECS,
    get_portfolio_allocator_spec,
)

# ==================== DEFAULTS ====================
DEFAULT_ALLOCATOR_TYPE = "inverse_vol_v1"


def render(
    key_prefix: str = "",
    container: Optional[st.delta_generator.DeltaGenerator] = None,
    show_header: bool = True,
    expand_params: bool = False,
    current_values: Dict = None,
) -> Dict:
    """
    Render asset allocator UI.

    Args:
        current_values: Dict with 'type' and 'params' from the portfolio config.

    Returns:
        dict with keys:
            - asset_allocator: dict with 'type' and 'params'
            - vol_window: int (compatibility with current engine)
            - errors: list of validation error strings
    """
    container = container or st.sidebar
    cv = current_values or {}
    errors = []

    if show_header:
        container.markdown("---")
        container.markdown("### Asset Allocator")
        container.caption("Controls allocation across assets")

    allocator_options = list(PORTFOLIO_ALLOCATOR_SPECS.keys())
    format_func = lambda x: get_portfolio_allocator_spec(x).display_name

    current_type = cv.get("type", DEFAULT_ALLOCATOR_TYPE)
    default_index = 0
    if current_type in allocator_options:
        default_index = allocator_options.index(current_type)
    elif DEFAULT_ALLOCATOR_TYPE in allocator_options:
        default_index = allocator_options.index(DEFAULT_ALLOCATOR_TYPE)

    allocator_type = container.radio(
        "Allocation Method",
        options=allocator_options,
        index=default_index,
        format_func=format_func,
        help="Method for allocating across assets",
        key=f"{key_prefix}asset_allocator_type",
    )

    allocator_params_cv = cv.get("params", {}) if cv.get("type") == allocator_type else {}

    expander = container.expander("Asset Allocator Parameters", expanded=expand_params)
    with expander:
        spec = get_portfolio_allocator_spec(allocator_type)
        if spec.description:
            expander.caption(spec.description)

        params = {}
        if spec.render_params is not None:
            params = spec.render_params(
                key_prefix=f"{key_prefix}allocator_{allocator_type}_",
                current_values=allocator_params_cv,
            )
        else:
            expander.caption("_No parameters_")

    vol_window = params.get("lookback") or params.get("vol_window")

    if show_header:
        container.markdown("---")
    
    return {
        "asset_allocator": {
            "type": allocator_type,
            "params": params,
        },
        "vol_window": vol_window,
        "errors": errors,
    }    
