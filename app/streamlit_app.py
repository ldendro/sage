"""Streamlit Backtesting App - Main Entry Point."""

import streamlit as st
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.defaults import (
    AVAILABLE_TICKERS,
    DEFAULT_UNIVERSE,
    DEFAULT_START_DATE,
    DEFAULT_END_DATE,
    DEFAULT_MAX_WEIGHT_PER_ASSET,
    DEFAULT_MAX_SECTOR_WEIGHT,
    DEFAULT_MIN_ASSETS_HELD,
    DEFAULT_TARGET_VOL,
    DEFAULT_VOL_LOOKBACK,
    DEFAULT_MIN_LEVERAGE,
    DEFAULT_MAX_LEVERAGE,
    DEFAULT_VOL_WINDOW,
    BOUNDS,
)
from app.utils.validators import (
    validate_date_range_widget,
    validate_risk_caps_widget,
    validate_universe_widget,
    validate_volatility_targeting_widget,
)

# Page configuration
st.set_page_config(
    page_title="Sage Backtesting Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Header
st.title("📈 Sage Backtesting Engine")
st.markdown("Interactive backtesting dashboard for quantitative strategies")

# Sidebar
st.sidebar.header("⚙️ Configuration")
st.sidebar.info("""
💡 **Quick Start**
1. Select assets from the universe
2. Choose date range
3. Adjust parameters (optional)
4. Click 'Run Backtest'
""")

# Sidebar - Universe Selection
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Universe Selection")

universe = st.sidebar.multiselect(
    "Select Assets",
    options=AVAILABLE_TICKERS,
    default=DEFAULT_UNIVERSE,
    help="Choose assets to include in the backtest"
)
universe_errors = validate_universe_widget(universe, AVAILABLE_TICKERS)
if universe_errors:
    for error in universe_errors:
        st.sidebar.error(f"⚠️ {error}")
else:
    st.sidebar.success(f"✓ {len(universe)} asset(s) selected")

# Sidebar - Date Range
st.sidebar.markdown("### 📅 Date Range")

col1, col2 = st.sidebar.columns(2)

start_date = col1.date_input(
    "Start Date",
    value=DEFAULT_START_DATE,
    min_value=date(2000, 1, 1),
    max_value=date.today() - timedelta(days=1),
    help="Backtest start date - The first active portfolio day"
)

# Calculate dynamic end date defaults
if start_date is not None:
    min_end_date = start_date + timedelta(days=1)
else:
    min_end_date = date(2000, 1, 2)

end_date = col2.date_input(
    "End Date",
    value=DEFAULT_END_DATE,
    min_value=min_end_date,
    max_value=date.today(),
    help="Backtest end date - The last active portfolio day"
)
date_errors = validate_date_range_widget(start_date, end_date)
if date_errors:
    for error in date_errors:
        st.sidebar.error(f"⚠️ {error}")
else:
    days_diff = (end_date - start_date).days
    st.sidebar.success(f"✓ Period: {days_diff} calendar days")

# Sidebar - Allocator Settings (Expandable)
with st.sidebar.expander("🔧 Allocator Settings", expanded=False):
    vol_window = st.slider(
        "Inverse Vol Window (trading days)",
        min_value=BOUNDS["vol_window"][0],
        max_value=BOUNDS["vol_window"][1],
        value=DEFAULT_VOL_WINDOW,
        step=10,
        help="Lookback window for inverse volatility weight calculation in trading days"
    )

# Sidebar - Risk Caps (Expandable)
with st.sidebar.expander("⚖️ Risk Caps", expanded=False):
    max_weight_per_asset = st.slider(
        "Max Weight per Asset",
        min_value=BOUNDS["max_weight_per_asset"][0],
        max_value=BOUNDS["max_weight_per_asset"][1],
        value=DEFAULT_MAX_WEIGHT_PER_ASSET,
        step=0.05,
        format="%.2f",
        help="Maximum allocation to any single asset (e.g., 0.25 = 25%)"
    )
    
    use_sector_cap = st.checkbox(
        "Enable Sector Weight Cap",
        value=False,
        help="Limit total exposure to any sector"
    )
    
    if use_sector_cap:
        max_sector_weight = st.slider(
            "Max Sector Weight",
            min_value=BOUNDS["max_sector_weight"][0],
            max_value=BOUNDS["max_sector_weight"][1],
            value=DEFAULT_MAX_SECTOR_WEIGHT,
            step=0.05,
            format="%.2f",
            help="Maximum allocation to any sector (e.g., 0.6 = 60%)"
        )
    else:
        max_sector_weight = None
    
    min_assets_held = st.number_input(
        "Min Assets Held",
        min_value=BOUNDS["min_assets_held"][0],
        max_value=BOUNDS["min_assets_held"][1],
        value=DEFAULT_MIN_ASSETS_HELD,
        step=1,
        help="Minimum number of assets to hold in the portfolio"
    )
    risk_caps_errors = validate_risk_caps_widget(
        min_assets_held=min_assets_held,
        universe=universe,
        max_weight_per_asset=max_weight_per_asset,
        max_sector_weight=max_sector_weight,
    )
    if risk_caps_errors:
        for error in risk_caps_errors:
            st.error(f"⚠️ {error}")

# Sidebar - Volatility Targeting (Expandable)
with st.sidebar.expander("🎯 Volatility Targeting", expanded=False):
    target_vol = st.slider(
        "Target Volatility",
        min_value=BOUNDS["target_vol"][0],
        max_value=BOUNDS["target_vol"][1],
        value=DEFAULT_TARGET_VOL,
        step=0.01,
        format="%.2f",
        help="Target annual volatility (e.g., 0.10 = 10% annualized)"
    )
    
    vol_lookback = st.slider(
        "Vol Lookback (trading days)",
        min_value=BOUNDS["vol_lookback"][0],
        max_value=BOUNDS["vol_lookback"][1],
        value=DEFAULT_VOL_LOOKBACK,
        step=10,
        help="Rolling window for volatility calculation in trading days"
    )
    
    col1, col2 = st.columns(2)
    
    min_leverage = col1.number_input(
        "Min Leverage",
        min_value=BOUNDS["min_leverage"][0],
        max_value=BOUNDS["min_leverage"][1],
        value=DEFAULT_MIN_LEVERAGE,
        step=0.1,
        format="%.1f",
        help="Minimum portfolio leverage"
    )
    
    max_leverage = col2.number_input(
        "Max Leverage",
        min_value=BOUNDS["max_leverage"][0],
        max_value=BOUNDS["max_leverage"][1],
        value=DEFAULT_MAX_LEVERAGE,
        step=0.1,
        format="%.1f",
        help="Maximum portfolio leverage"
    )
    volatility_errors = validate_volatility_targeting_widget(min_leverage, max_leverage)
    if volatility_errors:
        for error in volatility_errors:
            st.error(f"⚠️ {error}")

# Aggregate all validation errors
all_errors = universe_errors + date_errors + risk_caps_errors + volatility_errors
has_errors = len(all_errors) > 0

# Run Backtest Button
st.sidebar.markdown("---")

if has_errors:
    st.sidebar.button(
        "🚀 Run Backtest",
        type="primary",
        use_container_width=True,
        disabled=True,
        help="Fix validation errors before running"
    )
    st.sidebar.error(f"⚠️ {len(all_errors)} validation error(s)")
else:
    run_clicked = st.sidebar.button(
        "🚀 Run Backtest",
        type="primary",
        use_container_width=True,
        help="Run backtest with current parameters"
    )

# Initialize session state for results
if "backtest_results" not in st.session_state:
    st.session_state.backtest_results = None
if "backtest_params" not in st.session_state:
    st.session_state.backtest_params = None
if "backtest_error" not in st.session_state:
    st.session_state.backtest_error = None

# Execute backtest when button is clicked
if not has_errors and run_clicked:
    # Build current parameters dict for caching comparison
    current_params = {
        "universe": tuple(sorted(universe)),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "max_weight_per_asset": max_weight_per_asset,
        "max_sector_weight": max_sector_weight,
        "min_assets_held": min_assets_held,
        "target_vol": target_vol,
        "vol_lookback": vol_lookback,
        "min_leverage": min_leverage,
        "max_leverage": max_leverage,
        "vol_window": vol_window,
    }
    
    # Import engine here to avoid circular imports
    from sage_core.walkforward.engine import run_system_walkforward
    
    with st.spinner("🔄 Running backtest... This may take a moment."):
        try:
            results = run_system_walkforward(
                universe=list(universe),
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                max_weight_per_asset=max_weight_per_asset,
                max_sector_weight=max_sector_weight,
                min_assets_held=min_assets_held,
                target_vol=target_vol,
                vol_lookback=vol_lookback,
                min_leverage=min_leverage,
                max_leverage=max_leverage,
                vol_window=vol_window,
            )
            
            # Store results in session state
            st.session_state.backtest_results = results
            st.session_state.backtest_params = current_params
            st.session_state.backtest_error = None
            
        except Exception as e:
            st.session_state.backtest_results = None
            st.session_state.backtest_params = None
            st.session_state.backtest_error = str(e)

# Main content area
if st.session_state.backtest_error:
    st.error(f"❌ **Backtest Failed**\n\n{st.session_state.backtest_error}")
    
    with st.expander("🔍 Error Details", expanded=False):
        st.code(st.session_state.backtest_error)
    
    st.info("👈 Adjust parameters in the sidebar and try again")

elif st.session_state.backtest_results is not None:
    results = st.session_state.backtest_results
    metrics = results["metrics"]
    
    st.success("✅ Backtest completed successfully!")
    
    # Display key metrics in columns
    st.markdown("### 📊 Key Performance Metrics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_return = metrics.get("total_return", 0) * 100
        st.metric("Total Return", f"{total_return:.2f}%")
    
    with col2:
        cagr = metrics.get("cagr", 0) * 100
        st.metric("CAGR", f"{cagr:.2f}%")
    
    with col3:
        sharpe = metrics.get("sharpe_ratio", 0)
        st.metric("Sharpe Ratio", f"{sharpe:.2f}")
    
    with col4:
        max_dd = metrics.get("max_drawdown", 0) * 100
        st.metric("Max Drawdown", f"{max_dd:.2f}%")
    
    with col5:
        volatility = metrics.get("volatility", 0) * 100
        st.metric("Volatility", f"{volatility:.2f}%")
    
    # Placeholder for charts (will be implemented in Steps 2.6-2.8)
    st.markdown("---")
    st.info("📈 Charts and detailed analysis will be added in upcoming steps.")
    
    # Show cached parameters
    with st.expander("🔧 Backtest Parameters", expanded=False):
        params = st.session_state.backtest_params
        if params:
            param_col1, param_col2 = st.columns(2)
            with param_col1:
                st.write("**Universe:**", ", ".join(params["universe"]))
                st.write("**Date Range:**", f"{params['start_date']} to {params['end_date']}")
                st.write("**Max Weight/Asset:**", f"{params['max_weight_per_asset']:.2%}")
                st.write("**Max Sector Weight:**", f"{params['max_sector_weight']:.2%}" if params['max_sector_weight'] else "None")
            with param_col2:
                st.write("**Target Vol:**", f"{params['target_vol']:.2%}")
                st.write("**Vol Lookback:**", f"{params['vol_lookback']} days")
                st.write("**Leverage Range:**", f"{params['min_leverage']:.1f}x - {params['max_leverage']:.1f}x")
                st.write("**Vol Window:**", f"{params['vol_window']} days")

else:
    st.info("👈 Configure parameters in the sidebar and click 'Run Backtest' to begin")

# Footer
st.markdown("---")
st.caption("Sage Backtesting Engine v2.0 | Phase 2: Streamlit App")
