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
) -> Dict:
    """
    Render asset allocator UI.

    Returns:
        dict with keys:
            - asset_allocator: dict with 'type' and 'params'
            - vol_window: int (compatibility with current engine)
            - errors: list of validation error strings
    """
    container = container or st.sidebar
    errors = []

    if show_header:
        container.markdown("---")
        container.markdown("### Asset Allocator")
        container.caption("Controls allocation across assets")

    allocator_options = list(PORTFOLIO_ALLOCATOR_SPECS.keys())
    format_func = lambda x: get_portfolio_allocator_spec(x).display_name

    default_index = 0
    if DEFAULT_ALLOCATOR_TYPE in allocator_options:
        default_index = allocator_options.index(DEFAULT_ALLOCATOR_TYPE)

    allocator_type = container.radio(
        "Allocation Method",
        options=allocator_options,
        index=default_index,
        format_func=format_func,
        help="Method for allocating across assets",
        key=f"{key_prefix}asset_allocator_type",
    )

    expander = container.expander("Asset Allocator Parameters", expanded=expand_params)
    with expander:
        spec = get_portfolio_allocator_spec(allocator_type)
        if spec.description:
            expander.caption(spec.description)

        params = {}
        if spec.render_params is not None:
            params = spec.render_params(key_prefix=f"{key_prefix}allocator_{allocator_type}_")
        else:
            expander.caption("_No parameters_")

    vol_window = params.get("lookback")
    if vol_window is None:
        vol_window = params.get("vol_window")

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
    
