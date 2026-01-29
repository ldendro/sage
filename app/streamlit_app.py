"""Streamlit Backtesting App - Main Entry Point."""

import streamlit as st
import sys
import json
import pandas as pd
from datetime import date, timedelta, datetime
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config.defaults import (
    AVAILABLE_TICKERS,
    DEFAULT_UNIVERSE,
    DEFAULT_START_DATE,
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
from app.components import render_header

st.set_page_config(
    page_title="Sage Backtesting Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== HEADER ====================
render_header(
    "Sage Backtesting Engine",
    "Interactive backtesting dashboard for quantitative strategies",
    icon_path=Path(__file__).parent / "images" / "SAGEICON.png",
)

# ==================== CONFIGURATION ====================
st.sidebar.header("Configuration")
st.sidebar.info("""
💡 **Quick Start**
1. Select assets from the universe
2. Choose date range
3. Adjust parameters (optional)
4. Click 'Run Backtest'
""")

# ==================== UNIVERSE SELECTION ====================
st.sidebar.markdown("---")
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
else:
    st.sidebar.success(f"✓ {len(universe)} asset(s) selected")

# ==================== DATE RANGE ====================
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
else:
    days_diff = (end_date - start_date).days
    st.sidebar.success(f"✓ Period: {days_diff} calendar days")

# ==================== ALLOCATOR SETTINGS ====================
with st.sidebar.expander("Allocator Settings", expanded=False):
    vol_window = st.slider(
        "Inverse Vol Window (trading days)",
        min_value=BOUNDS["vol_window"][0],
        max_value=BOUNDS["vol_window"][1],
        value=DEFAULT_VOL_WINDOW,
        step=10,
        help="Lookback window for inverse volatility weight calculation in trading days"
    )

# ==================== RISK CAPS ====================
with st.sidebar.expander("Risk Caps", expanded=False):
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

# ==================== VOLATILITY TARGETING ====================
with st.sidebar.expander("Volatility Targeting", expanded=False):
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

# ==================== RUN BACKTEST BUTTON ====================
all_errors = universe_errors + date_errors + risk_caps_errors + volatility_errors
has_errors = len(all_errors) > 0

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

# ==================== ABOUT SECTION ====================

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info("""
**Sage Backtesting Engine v2.0**

A comprehensive backtesting platform for portfolio strategies featuring:
- Inverse volatility weighting
- Risk caps & sector constraints  
- Volatility targeting
- Detailed performance analytics

Built with Streamlit & Plotly
""")

# ==================== SESSION STATE INITIALIZATION ====================
if "backtest_results" not in st.session_state:
    st.session_state.backtest_results = None
if "backtest_params" not in st.session_state:
    st.session_state.backtest_params = None
if "backtest_error" not in st.session_state:
    st.session_state.backtest_error = None

# ==================== BACKTEST EXECUTION ====================
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

# ==================== MAIN CONTENT AREA ====================
if st.session_state.backtest_error:
    st.error(f"❌ **Backtest Failed**\n\n{st.session_state.backtest_error}")
    
    with st.expander("🔍 Error Details", expanded=False):
        st.code(st.session_state.backtest_error)
    
    st.info("👈 Adjust parameters in the sidebar and try again")

elif st.session_state.backtest_results is not None:
    results = st.session_state.backtest_results
    metrics = results["metrics"]
    
    # Import formatters
    from app.utils.formatters import (
        format_percentage,
        format_ratio,
        format_days,
        format_date,
    )
    
    st.success("✅ Backtest completed successfully!")
    
    # Import chart utilities
    from app.utils.charts import (
        create_equity_curve_chart,
        create_drawdown_chart,
        create_weight_allocation_chart,
    )
    
    # Create tabbed interface
    tab1, tab2, tab3, tab4 = st.tabs([
        "Key Performance",
        "Drawdown Analysis", 
        "Portfolio Allocation",
        "Yearly Performance"
    ])
    
    # ==================== TAB 1: KEY PERFORMANCE ====================
    with tab1:
        # Primary Metrics Row (5 cards)
        st.markdown("### Key Performance Metrics")
        st.caption("Overview of primary performance metrics and equity curve visualization")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            total_return = metrics.get("total_return", 0)
            st.metric(
                "Total Return",
                format_percentage(total_return),
                help="Total cumulative return over the backtest period"
            )
        
        with col2:
            cagr = metrics.get("cagr", 0)
            st.metric(
                "CAGR",
                format_percentage(cagr),
                help="Compound Annual Growth Rate"
            )
        
        with col3:
            sharpe = metrics.get("sharpe_ratio", 0)
            st.metric(
                "Sharpe Ratio",
                format_ratio(sharpe),
                help="Risk-adjusted return (annualized)"
            )
        
        with col4:
            max_dd = metrics.get("max_drawdown_pct", metrics.get("max_drawdown", 0))
            st.metric(
                "Max Drawdown",
                format_percentage(max_dd),
                help="Maximum peak-to-trough decline"
            )
        
        with col5:
            volatility = metrics.get("volatility", 0)
            st.metric(
                "Volatility",
                format_percentage(volatility),
                help="Annualized standard deviation of returns"
            )
        
        # Secondary Metrics Row (5 cards)
        st.markdown("### Additional Metrics")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            calmar = metrics.get("calmar_ratio", 0)
            st.metric(
                "Calmar Ratio",
                format_ratio(calmar),
                help="CAGR / Max Drawdown (risk-adjusted)"
            )
        
        with col2:
            avg_turnover = metrics.get("avg_daily_turnover", 0)
            st.metric(
                "Avg Daily Turnover",
                format_percentage(avg_turnover),
                help="Average daily portfolio turnover"
            )
        
        with col3:
            total_turnover = metrics.get("total_turnover", 0)
            st.metric(
                "Total Turnover",
                format_ratio(total_turnover, decimals=1) + "x",
                help="Total portfolio turnover over the period"
            )
        
        with col4:
            trading_days = metrics.get("trading_days", 0)
            st.metric(
                "Trading Days",
                f"{trading_days:,}",
                help="Number of trading days in backtest"
            )
        
        with col5:
            n_assets = metrics.get("n_assets", 0)
            st.metric(
                "Assets",
                f"{n_assets}",
                help="Number of assets in the portfolio"
            )
        
        # Create metrics DataFrame for export
        metrics_export_data = {
            "Metric": [
                "Total Return", "CAGR", "Sharpe Ratio", "Max Drawdown", "Volatility",
                "Calmar Ratio", "Avg Daily Turnover", "Total Turnover", "Trading Days", "Assets"
            ],
            "Value": [
                format_percentage(metrics.get("total_return", 0)),
                format_percentage(metrics.get("cagr", 0)),
                format_ratio(metrics.get("sharpe_ratio", 0)),
                format_percentage(metrics.get("max_drawdown_pct", 0)),
                format_percentage(metrics.get("volatility", 0)),
                format_ratio(metrics.get("calmar_ratio", 0)),
                format_percentage(metrics.get("avg_daily_turnover", 0)),
                format_ratio(metrics.get("total_turnover", 0), decimals=1) + "x",
                f"{metrics.get('trading_days', 0):,}",
                str(metrics.get("n_assets", 0))
            ]
        }
        metrics_df = pd.DataFrame(metrics_export_data)
        csv = metrics_df.to_csv(index=False)
        
        st.download_button(
            label="📥 Download Metrics (CSV)",
            data=csv,
            file_name=f"sage_backtest_metrics_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
            mime="text/csv",
            help="Download all performance metrics as CSV"
        )
        
        # Equity Curve Chart
        st.markdown("---")
        equity_curve = results.get("equity_curve")
        if equity_curve is not None and len(equity_curve) > 0:
            fig_equity = create_equity_curve_chart(equity_curve)
            st.plotly_chart(fig_equity, width='stretch')
            st.caption("💡 *Tip: Use the camera icon (📷) in the chart toolbar to download as PNG*")
        else:
            st.warning("No equity curve data available.")

    # ==================== TAB 2: DRAWDOWN ANALYSIS ====================
    with tab2:
        st.markdown("### Drawdown Metrics")
        st.caption("Overview of drawdown metrics and underwater chart visualization")

        # Drawdown metrics in columns
        dd_col1, dd_col2, dd_col3 = st.columns(3)
        
        with dd_col1:
            st.metric(
                "Max Drawdown",
                format_percentage(max_dd),
                help="Maximum peak-to-trough decline"
            )
            
            peak_date = metrics.get("peak_date")
            st.metric(
                "Peak Date",
                format_date(peak_date),
                help="Date of portfolio peak before maximum drawdown"
            )
        
        with dd_col2:
            dd_duration = metrics.get("drawdown_duration_days", 0)
            st.metric(
                "Drawdown Duration",
                format_days(dd_duration),
                help="Days from peak to trough"
            )
            
            trough_date = metrics.get("trough_date")
            st.metric(
                "Trough Date",
                format_date(trough_date),
                help="Date of maximum drawdown"
            )
        
        with dd_col3:
            recovery_date = metrics.get("recovery_date")
            recovery_days = metrics.get("recovery_duration_days")
            
            if recovery_date is not None:
                st.metric(
                    "Recovery Date",
                    format_date(recovery_date),
                    help="Date when portfolio recovered to peak"
                )
                st.metric(
                    "Recovery Duration",
                    format_days(recovery_days),
                    help="Days from trough to recovery"
                )
            else:
                st.metric(
                    "Recovery Status",
                    "Not Recovered",
                    help="Portfolio has not recovered to peak"
                )
                st.metric(
                    "Recovery Duration",
                    "N/A",
                    help="Not applicable - portfolio not recovered"
                )
        
        # Drawdown Chart
        st.markdown("---")
        drawdown_series = results.get("drawdown_series")
        if drawdown_series is not None and len(drawdown_series) > 0:
            fig_drawdown = create_drawdown_chart(drawdown_series)
            st.plotly_chart(fig_drawdown, width='stretch')
            st.caption("💡 *Tip: Use the camera icon (📷) in the chart toolbar to download as PNG*")
        else:
            st.warning("No drawdown data available.")
    
    # ==================== TAB 3: PORTFOLIO ALLOCATION ====================
    with tab3:
        st.markdown("### Weight Allocation Over Time")
        st.caption("Visualization of asset weights over the backtest period")
        
        st.markdown("---")
        weights = results.get("weights")
        if weights is not None and not weights.empty:
            fig_weights = create_weight_allocation_chart(weights)
            st.plotly_chart(fig_weights, width='stretch')
            st.caption("💡 *Tip: Use the camera icon (📷) in the chart toolbar to download as PNG*")
        else:
            st.warning("No weight allocation data available.")
        
        # Placeholder for future enhancements
        st.markdown("---")
        st.info("""
        **🔮 Future Enhancements**
        
        This tab will be expanded to include:
        - Risk contribution analysis
        - Sector exposure breakdown
        - Asset correlation heatmap
        - Additional portfolio analytics
        """)
    
    # ==================== TAB 4: YEARLY PERFORMANCE ====================
    with tab4:
        yearly_summary = metrics.get("yearly_summary")
        
        st.markdown("### Yearly Performance Summary")
        
        if yearly_summary is not None and not yearly_summary.empty:
            st.caption(f"Performance breakdown across {len(yearly_summary)} years")
            # Format the yearly summary DataFrame for display
            display_df = yearly_summary.copy()
            display_df = display_df.sort_values("year", ascending=False)  # Most recent first
            
            # Format columns for display
            display_df["Year"] = display_df["year"].astype(int)
            display_df["Total Return"] = display_df["total_return"].apply(lambda x: format_percentage(x))
            display_df["Sharpe Ratio"] = display_df["sharpe"].apply(lambda x: format_ratio(x))
            display_df["Max Drawdown"] = display_df["max_drawdown"].apply(lambda x: format_percentage(x))
            display_df["Volatility"] = display_df["volatility"].apply(lambda x: format_percentage(x))
            
            # Select and reorder columns for display
            display_df = display_df[["Year", "Total Return", "Sharpe Ratio", "Max Drawdown", "Volatility"]]
            
            # Display as interactive table
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True,
            )
                        
            # Export yearly summary
            csv_yearly = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Yearly Summary (CSV)",
                data=csv_yearly,
                file_name=f"sage_backtest_yearly_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
                mime="text/csv",
                help="Download yearly performance summary as CSV"
            )
        else:
            st.info("No yearly summary data available.")
    
    # ==================== BACKTEST PARAMETERS ====================
    st.markdown("---")
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
            
            # Export configuration
            config_json = json.dumps(params, indent=2, default=str)
            st.download_button(
                label="📥 Download Configuration (JSON)",
                data=config_json,
                file_name=f"sage_backtest_config_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.json",
                mime="application/json",
                help="Download backtest configuration for reproducibility"
            )

else:
    st.info("👈 Configure parameters in the sidebar and click 'Run Backtest' to begin")

# ==================== FOOTER ====================
st.caption("Sage Backtesting Engine v2.0 | Phase 2: Streamlit App")
