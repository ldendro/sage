"""Universe and date range selection component."""

import streamlit as st
from datetime import date, timedelta

from app.utils.validators import validate_universe_widget, validate_date_range_widget

# ==================== DEFAULTS ====================
AVAILABLE_TICKERS = [
    "SPY", "QQQ", "IWM",  # Equities
    "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"  # Sectors
]

DEFAULT_UNIVERSE = ["SPY", "QQQ", "IWM", "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
DEFAULT_START_DATE = date(2020, 1, 1)


def render() -> dict:
    """
    Render universe selection and date range UI.
    
    Returns:
        dict with keys:
            - universe: list of selected tickers
            - start_date: date object
            - end_date: date object
            - errors: list of validation error strings
    """
    errors = []
    
    # ==================== UNIVERSE SELECTION ====================
    st.sidebar.markdown("### Universe Selection")
    
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
        errors.extend(universe_errors)
    else:
        st.sidebar.success(f"✓ {len(universe)} asset(s) selected")
    
    # ==================== DATE RANGE ====================
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Date Range")
    
    col1, col2 = st.sidebar.columns(2)
    
    start_date = col1.date_input(
        "Start Date",
        value=DEFAULT_START_DATE,
        min_value=date(2000, 1, 1),
        max_value=date.today() - timedelta(days=1),
        help="Backtest start date - The first active portfolio day"
    )
    
    if start_date is not None:
        min_end_date = start_date + timedelta(days=1)
    else:
        min_end_date = date(2000, 1, 2)
    
    end_date = col2.date_input(
        "End Date",
        value=date.today(),
        min_value=min_end_date,
        max_value=date.today(),
        help="Backtest end date - The last active portfolio day"
    )
    
    date_errors = validate_date_range_widget(start_date, end_date)
    if date_errors:
        for error in date_errors:
            st.sidebar.error(f"⚠️ {error}")
        errors.extend(date_errors)
    else:
        days_diff = (end_date - start_date).days
        st.sidebar.success(f"✓ Period: {days_diff} calendar days")
    
    return {
        'universe': list(universe),
        'start_date': start_date.isoformat() if start_date else None,
        'end_date': end_date.isoformat() if end_date else None,
        'errors': errors,
    }
