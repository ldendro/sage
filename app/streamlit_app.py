"""Streamlit Backtesting App - Main Entry Point."""

import streamlit as st
import sys
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

# Placeholder for parameter controls
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Universe Selection")
st.sidebar.info("Universe controls will appear here")

st.sidebar.markdown("### 📅 Date Range")
st.sidebar.info("Date controls will appear here")

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
