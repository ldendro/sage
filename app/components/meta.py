"""Meta allocator selection component."""

import streamlit as st
from typing import List, Optional
from sage_core.meta import META_ALLOCATOR_REGISTRY

from app.meta_allocator_ui.registry import get_meta_allocator_spec

# ==================== DEFAULTS ====================
DEFAULT_META_ALLOCATOR_TYPE = 'fixed_weight'


def render(
    selected_strategies: List[str],
    key_prefix: str = "",
    container: Optional[st.delta_generator.DeltaGenerator] = None,
    show_header: bool = True,
) -> dict:
    """
    Render meta allocator UI.
    
    Only shown when multiple strategies are selected.
    
    Args:
        selected_strategies: List of selected strategy names
        
    Returns:
        dict with keys:
            - meta_allocator: dict with 'type' and 'params', or None for single strategy
            - errors: list of validation error strings
    """
    container = container or st.sidebar
    errors = []
    
    # Single strategy - no meta allocator needed
    if len(selected_strategies) <= 1:
        return {
            'meta_allocator': None,
            'errors': [],
        }
    
    # ==================== META ALLOCATOR ====================

    # Allocator type selector
    allocator_options = list(META_ALLOCATOR_REGISTRY.keys())
    format_func = lambda x: get_meta_allocator_spec(x).display_name

    default_index = 0
    if DEFAULT_META_ALLOCATOR_TYPE in allocator_options:
        default_index = allocator_options.index(DEFAULT_META_ALLOCATOR_TYPE)
    
    allocator_type = container.radio(
        "Allocation Method",
        options=allocator_options,
        index=default_index,
        format_func=format_func,
        help="Method for combining strategy returns",
        key=f"{key_prefix}meta_allocator_type",
    )
    
    # ==================== ALLOCATOR PARAMETERS ====================
    meta_allocator_config = None
    
    expander = container.expander("Meta Allocator Parameters", expanded=True)
    with expander:
        spec = get_meta_allocator_spec(allocator_type)
        if spec.description:
            expander.caption(spec.description)

        params = {}
        if spec.render_params is not None:
            params = spec.render_params(
                key_prefix=f"{key_prefix}meta_{allocator_type}_",
                selected_strategies=selected_strategies,
            )
        else:
            expander.caption("_No parameters_")

        if allocator_type == 'fixed_weight':
            weights = params.get('weights', {})
            total = sum(weights.values())
            if abs(total - 1.0) > 0.01:
                expander.error(f"⚠️ Weights must sum to 100% (currently {total:.0%})")
                errors.append(f"Strategy weights must sum to 100% (currently {total:.0%})")

        meta_allocator_config = {
            'type': allocator_type,
            'params': params,
        }
    
    return {
        'meta_allocator': meta_allocator_config,
        'errors': errors,
    }
