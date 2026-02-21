"""Results display component."""

import html
import streamlit as st
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional

from app.utils.formatters import (
    format_percentage,
    format_ratio,
    format_days,
)
from app.utils.charts import (
    create_weight_allocation_chart,
    create_multi_equity_curve_chart,
    create_multi_drawdown_chart,
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




def _color_label_html(name: str, color: str) -> str:
    safe_name = html.escape(name)
    return (
        "<div style='display:flex;align-items:center;gap:8px;font-weight:600;'>"
        f"<span style='width:12px;height:12px;border-radius:3px;display:inline-block;"
        f"background:{color};'></span>"
        f"<span>{safe_name}</span>"
        "</div>"
    )


def _hex_to_rgba(color: str, alpha: float = 0.08) -> str:
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join([c * 2 for c in color])
    if len(color) != 6:
        return f"rgba(0, 0, 0, {alpha})"
    r = int(color[0:2], 16)
    g = int(color[2:4], 16)
    b = int(color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def _build_display_names(portfolios: List[dict]) -> Dict[str, str]:
    counts: Dict[str, int] = {}
    for portfolio in portfolios:
        counts[portfolio["name"]] = counts.get(portfolio["name"], 0) + 1

    name_map: Dict[str, str] = {}
    for portfolio in portfolios:
        name = portfolio["name"]
        if counts.get(name, 0) > 1:
            suffix = portfolio["id"].split("_")[-1]
            name_map[portfolio["id"]] = f"{name} ({suffix})"
        else:
            name_map[portfolio["id"]] = name
    return name_map


def render_performance_tab(
    portfolios: List[dict],
    results_by_id: Dict[str, dict],
    name_map: Dict[str, str],
) -> None:
    """Render Key Performance tab for multiple portfolios."""
    st.markdown("### Key Performance Metrics")
    st.caption("Compare top-level metrics across portfolios and view combined equity curves")

    active_portfolios = [p for p in portfolios if p["id"] in results_by_id]
    if not active_portfolios:
        st.info("No completed portfolios to compare.")
        return

    for idx, portfolio in enumerate(active_portfolios):
        metrics = results_by_id[portfolio["id"]].get("metrics", {})
        max_dd = metrics.get("max_drawdown_pct", metrics.get("max_drawdown", 0))
        if idx > 0:
            st.markdown("---")
        col_name, col_return, col_cagr, col_sharpe, col_drawdown, col_vol = st.columns(
            [1, 1, 1, 1, 1, 1]
        )
        with col_name:
            st.markdown(
                _color_label_html(name_map[portfolio["id"]], portfolio["color"]),
                unsafe_allow_html=True,
            )
        col_return.metric("Total Return", format_percentage(metrics.get("total_return", 0)))
        col_cagr.metric("CAGR", format_percentage(metrics.get("cagr", 0)))
        col_sharpe.metric("Sharpe", format_ratio(metrics.get("sharpe_ratio", 0)))
        col_drawdown.metric("Max Drawdown", format_percentage(max_dd))
        col_vol.metric("Volatility", format_percentage(metrics.get("volatility", 0)))

    st.markdown("---")
    equity_curves = {
        name_map[p["id"]]: results_by_id[p["id"]].get("equity_curve")
        for p in active_portfolios
    }
    colors = {name_map[p["id"]]: p["color"] for p in active_portfolios}
    fig_equity = create_multi_equity_curve_chart(equity_curves, colors)
    st.plotly_chart(fig_equity, width='stretch')
    st.caption("Tip: Use the camera icon in the chart toolbar to download as PNG")


def render_drawdown_tab(
    portfolios: List[dict],
    results_by_id: Dict[str, dict],
    name_map: Dict[str, str],
) -> None:
    """Render Drawdown Analysis tab for multiple portfolios."""
    st.markdown("### Drawdown Comparison")

    active_portfolios = [p for p in portfolios if p["id"] in results_by_id]
    if not active_portfolios:
        st.info("No completed portfolios to compare.")
        return

    drawdowns = {
        name_map[p["id"]]: results_by_id[p["id"]].get("drawdown_series")
        for p in active_portfolios
    }
    colors = {name_map[p["id"]]: p["color"] for p in active_portfolios}
    fig_drawdown = create_multi_drawdown_chart(drawdowns, colors)
    st.plotly_chart(fig_drawdown, width='stretch')
    st.caption("Tip: Use the camera icon in the chart toolbar to download as PNG")


def render_allocation_tab(
    portfolios: List[dict],
    results_by_id: Dict[str, dict],
    name_map: Dict[str, str],
) -> None:
    """Render Portfolio Allocation tab for multiple portfolios."""
    st.markdown("### Weight Allocation Over Time")

    active_portfolios = [p for p in portfolios if p["id"] in results_by_id]
    if not active_portfolios:
        st.info("No completed portfolios to compare.")
        return

    tabs = st.tabs([name_map[p["id"]] for p in active_portfolios])
    for tab, portfolio in zip(tabs, active_portfolios):
        with tab:
            weights = results_by_id[portfolio["id"]].get("weights")
            if weights is not None and not weights.empty:
                fig_weights = create_weight_allocation_chart(
                    weights,
                    title=f"{name_map[portfolio['id']]} Allocation Over Time",
                )
                st.plotly_chart(fig_weights, width='stretch')
                st.caption("Tip: Use the camera icon in the chart toolbar to download as PNG")
            else:
                st.warning("No weight allocation data available.")


def render_yearly_tab(
    portfolios: List[dict],
    results_by_id: Dict[str, dict],
    name_map: Dict[str, str],
) -> None:
    """Render Yearly Performance tab for multiple portfolios."""
    st.markdown("### Yearly Performance Summary")

    active_portfolios = [p for p in portfolios if p["id"] in results_by_id]
    if not active_portfolios:
        st.info("No completed portfolios to compare.")
        return

    metric_specs = [
        ("total_return", "Total Return", False),
        ("sharpe", "Sharpe", True),
        ("max_drawdown", "Max Drawdown", False),
        ("volatility", "Volatility", False),
    ]
    metric_keys = [metric[0] for metric in metric_specs]

    yearly_by_portfolio: Dict[str, pd.DataFrame] = {}
    for portfolio in active_portfolios:
        metrics = results_by_id[portfolio["id"]].get("metrics", {})
        yearly_summary = metrics.get("yearly_summary")
        if yearly_summary is None or yearly_summary.empty:
            continue
        df = yearly_summary.copy()
        df = df.set_index("year")[metric_keys]
        yearly_by_portfolio[portfolio["id"]] = df

    if not yearly_by_portfolio:
        st.info("No yearly summary data available.")
        return

    metric_frames: Dict[str, pd.DataFrame] = {}
    for metric_key, metric_label, _ in metric_specs:
        series_list = []
        for portfolio in active_portfolios:
            df = yearly_by_portfolio.get(portfolio["id"])
            if df is None:
                continue
            series_list.append(df[metric_key].rename(name_map[portfolio["id"]]))
        if series_list:
            metric_frames[metric_label] = pd.concat(series_list, axis=1)

    if not metric_frames:
        st.info("No yearly summary data available.")
        return

    combined = pd.concat(metric_frames, axis=1).sort_index(ascending=False)
    combined.index.name = "Year"
    display_df = combined.reset_index()

    def _format_value(value, ratio: bool = False) -> str:
        if pd.isna(value):
            return "N/A"
        return format_ratio(value) if ratio else format_percentage(value)

    year_cols = [col for col in display_df.columns if isinstance(col, tuple) and col[0] == "Year"]
    if year_cols:
        display_df[year_cols[0]] = display_df[year_cols[0]].astype(int)

    metric_ratio = {label: ratio for _, label, ratio in metric_specs}
    formatters = {}
    for col in display_df.columns:
        if not isinstance(col, tuple):
            continue
        metric_label = col[0]
        if metric_label == "Year":
            continue
        ratio = metric_ratio.get(metric_label, False)
        formatters[col] = lambda value, ratio=ratio: _format_value(value, ratio=ratio)

    styler = display_df.style.format(formatters)

    color_map = {
        name_map[p["id"]]: p["color"]
        for p in active_portfolios
        if p["id"] in yearly_by_portfolio
    }

    table_styles = [
        {"selector": "th.col_heading.level0", "props": "text-align:center;font-weight:600;"},
        {"selector": "th.col_heading.level1", "props": "text-align:center;font-weight:600;"},
    ]
    for col_idx, col in enumerate(display_df.columns):
        if not isinstance(col, tuple):
            continue
        if col[0] == "Year":
            continue
        portfolio_name = col[1]
        color = color_map.get(portfolio_name)
        if not color:
            continue
        tint = _hex_to_rgba(color, 0.08)
        styler = styler.set_properties(subset=[col], **{
            "background-color": tint,
            "border-left": f"3px solid {color}",
        })
        table_styles.append({
            "selector": f"th.col_heading.level1.col{col_idx}",
            "props": f"color: {color};",
        })

    styler = styler.set_table_styles(table_styles)

    st.dataframe(styler, width='stretch', hide_index=True)
    st.download_button(
        label="Download Yearly Summary (CSV)",
        data=display_df.to_csv(index=False),
        file_name=f"sage_backtest_yearly_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv",
        mime="text/csv"
    )


def render_metadata_tab(
    portfolios: List[dict],
    results_by_id: Dict[str, dict],
    configs_by_id: Dict[str, dict],
    name_map: Dict[str, str],
) -> None:
    """Render system metadata and warmup details per portfolio."""
    st.markdown("### System Metadata")

    active_portfolios = [p for p in portfolios if p["id"] in configs_by_id]
    if not active_portfolios:
        st.info("No portfolio configurations available.")
        return

    warmup_rows = []
    for portfolio in active_portfolios:
        result = results_by_id.get(portfolio["id"], {})
        warmup = result.get("warmup_info", {})
        if warmup:
            warmup_rows.append({
                "Portfolio": name_map[portfolio["id"]],
                "Warmup Start Date": result.get("warmup_start_date", "N/A"),
                "Total Warmup": format_days(warmup.get("total_trading_days", 0)),
                "Strategy Warmup": format_days(warmup.get("strategy_warmup", 0)),
                "Meta Allocator Warmup": format_days(warmup.get("meta_allocator_warmup", 0)),
                "Asset Allocator Warmup": format_days(warmup.get("asset_allocator_warmup", 0)),
                "Vol Targeting Warmup": format_days(warmup.get("vol_targeting_warmup", 0)),
            })

    if warmup_rows:
        st.markdown("#### Warmup Summary")
        st.markdown("Warmup period is the time required for the strategy to learn market conditions before live trading begins. This period is excluded from the final results. The total warmup calculation is: max(strategy + meta allocator, asset allocator) + 1 trading day + Vol targeting")
        st.dataframe(pd.DataFrame(warmup_rows), width='stretch', hide_index=True)

    st.markdown("---")
    st.markdown("#### Portfolio Configurations")

    for portfolio in active_portfolios:
        config = configs_by_id.get(portfolio["id"], {})
        expander = st.expander(name_map[portfolio["id"]], expanded=False)
        with expander:
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Universe:**", ", ".join(config.get("universe", [])))
                st.write("**Date Range:**", f"{config.get('start_date')} to {config.get('end_date')}")
                st.write("**Strategies:**", ", ".join(config.get("selected_strategies", [])))
                meta_allocator = config.get("meta_allocator")
                if meta_allocator:
                    st.write("**Meta Allocator:**", meta_allocator.get("type"))
                asset_allocator = config.get("asset_allocator")
                if asset_allocator:
                    st.write("**Asset Allocator:**", asset_allocator.get("type"))
            with col2:
                st.write("**Target Vol:**", f"{config.get('target_vol', 0):.2%}")
                st.write("**Vol Lookback:**", f"{config.get('vol_lookback')} days")
                st.write("**Vol Window:**", f"{config.get('vol_window')} days")
                st.write("**Leverage:**", f"{config.get('min_leverage')}x - {config.get('max_leverage')}x")

            st.download_button(
                label="Download Configuration (JSON)",
                data=json.dumps(config, indent=2, default=str),
                file_name=f"sage_backtest_config_{portfolio['name'].replace(' ', '_')}_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.json",
                mime="application/json",
                key=f"download_config_{portfolio['id']}",
            )


def render(
    results_by_id: Dict[str, dict],
    configs_by_id: Dict[str, dict],
    portfolios: List[dict],
    errors_by_id: Optional[Dict[str, str]] = None,
) -> None:
    """
    Render full results section for multiple portfolios.
    """
    errors_by_id = errors_by_id or {}

    if not results_by_id and not errors_by_id:
        return

    display_portfolios = [
        p for p in portfolios
        if p["id"] in results_by_id or p["id"] in errors_by_id
    ]
    known_ids = {p["id"] for p in display_portfolios}
    for portfolio_id, config in configs_by_id.items():
        if portfolio_id in known_ids:
            continue
        if portfolio_id not in results_by_id and portfolio_id not in errors_by_id:
            continue
        display_portfolios.append({
            "id": portfolio_id,
            "name": config.get("portfolio_name", portfolio_id),
            "color": config.get("portfolio_color", "#9ca3af"),
        })

    name_map = _build_display_names(display_portfolios)

    if results_by_id:
        st.success(f"Completed {len(results_by_id)} portfolio(s).")
    if errors_by_id:
        st.warning("Some portfolios failed. Review errors below.")
        known_ids = {p["id"] for p in display_portfolios}
        unknown_errors = {
            key: value for key, value in errors_by_id.items() if key not in known_ids
        }
        for error_msg in unknown_errors.values():
            st.markdown("#### System Error")
            render_error(error_msg)
        for portfolio in display_portfolios:
            if portfolio["id"] in errors_by_id:
                st.markdown(f"#### {portfolio['name']}")
                render_error(errors_by_id[portfolio["id"]])

    if not results_by_id:
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Key Performance",
        "Drawdown Analysis",
        "Portfolio Allocation",
        "Yearly Performance",
        "System Metadata",
    ])

    with tab1:
        render_performance_tab(display_portfolios, results_by_id, name_map)
    with tab2:
        render_drawdown_tab(display_portfolios, results_by_id, name_map)
    with tab3:
        render_allocation_tab(display_portfolios, results_by_id, name_map)
    with tab4:
        render_yearly_tab(display_portfolios, results_by_id, name_map)
    with tab5:
        render_metadata_tab(display_portfolios, results_by_id, configs_by_id, name_map)
