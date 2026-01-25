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
)
from app.utils.validators import validate_universe, validate_date_range

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

# Validate universe using validators.py
universe_errors = validate_universe(universe, AVAILABLE_TICKERS)
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
    # Default end date is start date + 1 year
    default_end_val = start_date + timedelta(days=366)
else:
    min_end_date = date(2000, 1, 2)
    default_end_val = DEFAULT_END_DATE

end_date = col2.date_input(
    "End Date",
    value=default_end_val,
    min_value=min_end_date,
    help="Backtest end date - The last active portfolio day. Default value is 1 year after start date"
)

# Validate date range using validators.py
date_errors = validate_date_range(start_date, end_date)
if date_errors:
    for error in date_errors:
        st.sidebar.error(f"⚠️ {error}")
else:
    # Calculate trading days (approximate)
    days_diff = (end_date - start_date).days
    st.sidebar.success(f"✓ Period: {days_diff} calendar days")

st.sidebar.markdown("### ⚖️ Risk Caps")
st.sidebar.info("Risk cap controls will appear here")

st.sidebar.markdown("### 🎯 Volatility Targeting")
st.sidebar.info("Vol targeting controls will appear here")

st.sidebar.markdown("### 🔧 Allocator Settings")
st.sidebar.info("Allocator controls will appear here")

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
