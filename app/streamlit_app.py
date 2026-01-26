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

# Placeholder run button
st.sidebar.markdown("---")
st.sidebar.button(
    "🚀 Run Backtest",
    type="primary",
    use_container_width=True,
    disabled=True,
    help="Configure parameters first"
)

# Main content area
st.info("👈 Configure parameters in the sidebar and click 'Run Backtest' to begin")

# Footer
st.markdown("---")
st.caption("Sage Backtesting Engine v2.0 | Phase 2: Streamlit App")
