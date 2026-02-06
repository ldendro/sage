"""Execution control component (Run button and validation)."""

import streamlit as st
from typing import List

# ==================== DEFAULTS ====================
# (None for execution control)


def render(errors: List[str]) -> bool:
    """
    Render run button and handle validation state.
    
    Args:
        errors: List of validation errors from other components
        
    Returns:
        bool: True if run button was clicked and no errors exist
    """
    st.sidebar.markdown("---")
    
    has_errors = len(errors) > 0
    
    if has_errors:
        st.sidebar.button(
            "🚀 Run Backtests",
            type="primary",
            width='stretch',
            disabled=True,
            help="Fix validation errors before running",
            key="run_backtest_disabled"
        )
        st.sidebar.error(f"⚠️ {len(errors)} validation error(s)")
        return False
    else:
        run_clicked = st.sidebar.button(
            "🚀 Run Backtests",
            type="primary",
            width='stretch',
            help="Run backtests with current parameters",
            key="run_backtest"
        )
        return run_clicked

def render_advanced_settings():
    """Render advanced settings (cache management)."""
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Advanced Settings", expanded=False):
        st.markdown("**Data Cache Management**")
        
        # Import cache utilities
        from sage_core.data.cache import get_cache_size, clear_cache
        
        # Show cache stats
        cache_count, cache_size_bytes = get_cache_size()
        cache_size_mb = cache_size_bytes / (1024 * 1024)
        
        if cache_count > 0:
            st.caption(f"📊 Cache: {cache_count} file(s), {cache_size_mb:.2f} MB")
        else:
            st.caption("📊 Cache: Empty")
        
        # Clear cache button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Cache", help="Clear all cached market data", width='stretch'):
                deleted = clear_cache()
                if deleted > 0:
                    st.success(f"Deleted {deleted} cache file(s)")
                    # Rerun to update stats immediately? 
                    # st.rerun() is tricky inside a component, might loop. 
                    # But usually safe if triggered by button.
                else:
                    st.info("Cache was already empty")
        
        with col2:
            if st.button("🔄 Refresh", help="Refresh cache statistics", width='stretch'):
                st.rerun()
        
        st.markdown("---")
        st.caption("""
        **Cache Info:**
        - Historical data cached for 24 hours
        - Recent data (last 7 days) cached for 1 hour
        - Cache location: `~/.sage/cache/`
        """)
