"""Results display component."""

import streamlit as st
import pandas as pd
import json
from datetime import datetime

from app.utils.formatters import (
    format_percentage,
    format_ratio,
    format_days,
    format_date,
)
from app.utils.charts import (
    create_equity_curve_chart,
    create_drawdown_chart,
    create_weight_allocation_chart,
)


def render_error(error_msg: str) -> None:
    """Render error message with suggestions."""
    if "No data returned" in error_msg or "possibly delisted" in error_msg:
        st.error("❌ **Invalid Ticker Symbol**")
        st.markdown(f"**Error:** {error_msg}")
        st.info("""
        💡 **Suggestions:**
        - Verify ticker symbols are correct (e.g., 'SPY', 'QQQ', 'AAPL')
        - Check that tickers are listed on major exchanges
        - Try using different ticker symbols
        """)
    
    elif "Failed to load data" in error_msg:
        st.error("❌ **Data Loading Failed**")
        st.markdown(f"**Error:** {error_msg}")
        st.info("""
        💡 **Suggestions:**
        - Check your internet connection
        - Verify ticker symbols are valid
        - Try clearing the cache (Advanced Settings)
        - Try a different date range
        """)
    
    elif "No data" in error_msg and "date range" in error_msg:
        st.error("❌ **No Data Available for Date Range**")
        st.markdown(f"**Error:** {error_msg}")
        st.info("""
        💡 **Suggestions:**
        - Try a more recent date range (e.g., 2020-2024)
        - Some tickers may not have historical data before their IPO
        - Check the available date range for your tickers
        """)
    
    elif "must be before" in error_msg:
        st.error("❌ **Invalid Date Range**")
        st.markdown(f"**Error:** {error_msg}")
        st.info("""
        💡 **Suggestion:**
        - Ensure Start Date is before End Date
        """)
    
    else:
        # Generic error
        st.error(f"❌ **Backtest Failed**\n\n{error_msg}")
        st.info("👈 Adjust parameters in the sidebar and try again")
    
    with st.expander("🔍 Full Error Details", expanded=False):
        st.code(error_msg)


def render_success(results: dict) -> None:
    """Render success message and warmup info."""
    warmup_info = results.get("warmup_info", {})
    st.success(f"✅ Backtest completed successfully! (Warmup: {warmup_info.get('total_trading_days', 0)} trading days)")
    
    with st.expander("ℹ️ About Warmup Period", expanded=False):
        total_trading = warmup_info.get("total_trading_days", 0)
        
        st.markdown(f"""
        **Warmup Period:** {total_trading} trading days
        
        {warmup_info.get("description", "N/A")}
        
        **Sequential Breakdown:**
        1. **Strategy Warmup:** {warmup_info.get('strategy_warmup', 0)} days
        2. **Meta Allocator Warmup:** {warmup_info.get('meta_allocator_warmup', 0)} days
        3. **Inverse Vol Warmup:** {warmup_info.get('asset_allocator_warmup', 0)} days
           - Needed to calculate first weights
        4. **First Portfolio Return:** {warmup_info.get('first_return', 1)} day
           - Day when first weights are applied
        5. **Vol Targeting Warmup:** {warmup_info.get('vol_targeting_warmup', 0)} days  
           - Needed to accumulate portfolio returns for vol targeting
        
        **Total:** {total_trading} trading days (system fully active after this)
        
        **During warmup:**
        - Data is loaded but not included in final results
        - Portfolio uses 1.0x leverage (no vol targeting)
        - Equity curve starts exactly at your specified start date
        """)


def render_performance_tab(metrics: dict, results: dict):
    """Render Key Performance tab."""
    # Primary Metrics Row
    st.markdown("### Key Performance Metrics")
    st.caption("Overview of primary performance metrics and equity curve visualization")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Return", format_percentage(metrics.get("total_return", 0)), help="Total cumulative return")
    with col2:
        st.metric("CAGR", format_percentage(metrics.get("cagr", 0)), help="Compound Annual Growth Rate")
    with col3:
        st.metric("Sharpe Ratio", format_ratio(metrics.get("sharpe_ratio", 0)), help="Risk-adjusted return (annualized)")
    with col4:
        max_dd = metrics.get("max_drawdown_pct", metrics.get("max_drawdown", 0))
        st.metric("Max Drawdown", format_percentage(max_dd), help="Maximum peak-to-trough decline")
    with col5:
        st.metric("Volatility", format_percentage(metrics.get("volatility", 0)), help="Annualized standard deviation")
    
    # Secondary Metrics Row
    st.markdown("### Additional Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Calmar Ratio", format_ratio(metrics.get("calmar_ratio", 0)), help="CAGR / Max Drawdown")
    with col2:
        st.metric("Avg Daily Turnover", format_percentage(metrics.get("avg_daily_turnover", 0)), help="Average daily turnover")
    with col3:
        total_turnover = metrics.get("total_turnover", 0)
        st.metric("Total Turnover", format_ratio(total_turnover, decimals=1) + "x", help="Total portfolio turnover")
    with col4:
        st.metric("Trading Days", f"{metrics.get('trading_days', 0):,}", help="Number of trading days")
    with col5:
        st.metric("Assets", str(metrics.get("n_assets", 0)), help="Number of assets")
    
    # Export Metrics CSV
    metrics_export_data = {
        "Metric": ["Total Return", "CAGR", "Sharpe Ratio", "Max Drawdown", "Volatility", "Calmar Ratio", "Avg Daily Turnover", "Total Turnover", "Trading Days", "Assets"],
        "Value": [
            format_percentage(metrics.get("total_return", 0)),
            format_percentage(metrics.get("cagr", 0)),
            format_ratio(metrics.get("sharpe_ratio", 0)),
            format_percentage(max_dd),
            format_percentage(metrics.get("volatility", 0)),
            format_ratio(metrics.get("calmar_ratio", 0)),
            format_percentage(metrics.get("avg_daily_turnover", 0)),
            format_ratio(total_turnover, decimals=1) + "x",
            f"{metrics.get('trading_days', 0):,}",
            str(metrics.get("n_assets", 0))
        ]
    }
    metrics_df = pd.DataFrame(metrics_export_data)
    
    st.download_button(
        label="📥 Download Metrics (CSV)",
        data=metrics_df.to_csv(index=False),
        file_name=f"sage_backtest_metrics_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
        mime="text/csv"
    )
    
    # Equity Curve
    st.markdown("---")
    equity_curve = results.get("equity_curve")
    if equity_curve is not None and len(equity_curve) > 0:
        fig_equity = create_equity_curve_chart(equity_curve)
        st.plotly_chart(fig_equity, width='stretch')
        st.caption("💡 *Tip: Use the camera icon (📷) in the chart toolbar to download as PNG*")
    else:
        st.warning("No equity curve data available.")


def render_drawdown_tab(metrics: dict, results: dict):
    """Render Drawdown Analysis tab."""
    st.markdown("### Drawdown Metrics")
    col1, col2, col3 = st.columns(3)
    
    max_dd = metrics.get("max_drawdown_pct", metrics.get("max_drawdown", 0))
    
    with col1:
        st.metric("Max Drawdown", format_percentage(max_dd))
        st.metric("Peak Date", format_date(metrics.get("peak_date")))
    
    with col2:
        st.metric("Drawdown Duration", format_days(metrics.get("drawdown_duration_days", 0)))
        st.metric("Trough Date", format_date(metrics.get("trough_date")))
    
    with col3:
        if metrics.get("recovery_date"):
            st.metric("Recovery Date", format_date(metrics.get("recovery_date")))
            st.metric("Recovery Duration", format_days(metrics.get("recovery_duration_days")))
        else:
            st.metric("Recovery Status", "Not Recovered")
            st.metric("Recovery Duration", "N/A")
    
    st.markdown("---")
    drawdown_series = results.get("drawdown_series")
    if drawdown_series is not None and len(drawdown_series) > 0:
        fig_drawdown = create_drawdown_chart(drawdown_series)
        st.plotly_chart(fig_drawdown, width='stretch')
        st.caption("💡 *Tip: Use the camera icon (📷) in the chart toolbar to download as PNG*")
    else:
        st.warning("No drawdown data available.")


def render_allocation_tab(results: dict):
    """Render Portfolio Allocation tab."""
    st.markdown("### Weight Allocation Over Time")
    st.markdown("---")
    weights = results.get("weights")
    if weights is not None and not weights.empty:
        fig_weights = create_weight_allocation_chart(weights)
        st.plotly_chart(fig_weights, width='stretch')
        st.caption("💡 *Tip: Use the camera icon (📷) in the chart toolbar to download as PNG*")
    else:
        st.warning("No weight allocation data available.")
    
    st.markdown("---")
    st.info("""
    **🔮 Future Enhancements**
    This tab will include risk contribution analysis, sector exposure, and rolling correlations.
    """)


def render_yearly_tab(metrics: dict):
    """Render Yearly Performance tab."""
    yearly_summary = metrics.get("yearly_summary")
    st.markdown("### Yearly Performance Summary")
    
    if yearly_summary is not None and not yearly_summary.empty:
        display_df = yearly_summary.copy().sort_values("year", ascending=False)
        display_df["Year"] = display_df["year"].astype(int)
        display_df["Total Return"] = display_df["total_return"].apply(lambda x: format_percentage(x))
        display_df["Sharpe Ratio"] = display_df["sharpe"].apply(lambda x: format_ratio(x))
        display_df["Max Drawdown"] = display_df["max_drawdown"].apply(lambda x: format_percentage(x))
        display_df["Volatility"] = display_df["volatility"].apply(lambda x: format_percentage(x))
        
        display_df = display_df[["Year", "Total Return", "Sharpe Ratio", "Max Drawdown", "Volatility"]]
        
        st.dataframe(display_df, width='stretch', hide_index=True)
        
        st.download_button(
            label="📥 Download Yearly Summary (CSV)",
            data=display_df.to_csv(index=False),
            file_name=f"sage_backtest_yearly_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No yearly summary data available.")


def render_params_expander(params: dict):
    """Render backtest parameters expander."""
    st.markdown("---")
    with st.expander("🔧 Backtest Parameters", expanded=False):
        if params:
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Universe:**", ", ".join(params.get("universe", [])))
                st.write("**Date Range:**", f"{params.get('start_date')} to {params.get('end_date')}")
                st.write("**Strategies:**", ", ".join(params.get("strategies", [])))
                if params.get('meta_allocator'):
                    st.write("**Meta Allocator:**", params.get('meta_allocator', {}).get('type'))
            with col2:
                st.write("**Target Vol:**", f"{params.get('target_vol', 0):.2%}")
                st.write("**Vol Lookback:**", f"{params.get('vol_lookback')} days")
                st.write("**Leverage:**", f"{params.get('min_leverage')}x - {params.get('max_leverage')}x")
            
            st.download_button(
                label="📥 Download Configuration (JSON)",
                data=json.dumps(params, indent=2, default=str),
                file_name=f"sage_backtest_config_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.json",
                mime="application/json"
            )


def render(results: dict, config: dict) -> None:
    """
    Render full results section.
    
    Args:
        results: Dictionary containing backtest results
        config: Dictionary containing used configuration
    """
    if results is None:
        return
        
    metrics = results.get("metrics", {})
    
    render_success(results)
    
    # Create tabbed interface
    tab1, tab2, tab3, tab4 = st.tabs([
        "Key Performance",
        "Drawdown Analysis", 
        "Portfolio Allocation",
        "Yearly Performance"
    ])
    
    with tab1:
        render_performance_tab(metrics, results)
    with tab2:
        render_drawdown_tab(metrics, results)
    with tab3:
        render_allocation_tab(results)
    with tab4:
        render_yearly_tab(metrics)
    
    render_params_expander(config)
