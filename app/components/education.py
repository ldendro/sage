"""Educational panel for portfolio configuration."""

from typing import Dict, List, Optional, Tuple

import streamlit as st

from app.components.layers import DEFAULT_LAYER_KEY, LABEL_TO_KEY, LAYER_LABELS, PIPELINE_STEPS
from app.meta_allocator_ui.registry import get_meta_allocator_spec
from app.portfolio_allocator_ui.registry import get_portfolio_allocator_spec
from app.strategy_ui.registry import get_strategy_spec
from app.utils.formatters import format_percentage, format_ratio

COMBINATION_LABELS = {
    "majority": "Majority vote",
    "all": "All agree",
    "weighted": "Weighted blend",
}


def _render_pipeline(selected_layer_key: str) -> None:
    items = []
    for key, label in PIPELINE_STEPS:
        is_active = key == selected_layer_key
        dot_color = "var(--primary-color, #22c55e)" if is_active else "var(--secondary-text-color, #9ca3af)"
        text_color = "var(--primary-color, #22c55e)" if is_active else "var(--secondary-text-color, #6b7280)"
        font_weight = "600" if is_active else "500"
        items.append(
            "<div style='display:flex;align-items:center;gap:8px;margin:6px 0;'>"
            f"<span style='width:9px;height:9px;border-radius:999px;display:inline-block;background:{dot_color};'></span>"
            f"<span style='color:{text_color};font-weight:{font_weight};font-size:0.9rem;'>{label}</span>"
            "</div>"
        )

    html = (
        "<div style='border-left:2px solid var(--secondary-background-color, #e5e7eb);"
        "padding-left:12px;margin:10px 0 16px;'>"
        + "".join(items)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _fmt_days(value) -> str:
    if value is None:
        return "N/A"
    return f"{int(value)} days"


def _fmt_pct(value, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return format_percentage(value, decimals)


def _fmt_ratio(value, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return format_ratio(value, decimals)


def _fmt_leverage(value) -> str:
    if value is None:
        return "N/A"
    return f"{value:.1f}x"


def _render_param_lines(lines: List[Tuple[str, str, str]]) -> None:
    for label, value, description in lines:
        st.markdown(f"**{label}:** {value}")
        if description:
            st.caption(description)

def _render_strategy_layer(config: Dict) -> None:
    st.markdown("**Purpose**: Strategies generate signals from price data. You can choose one or more strategies; if multiple are selected, the meta allocator will combine them.")

    selected = config.get("selected_strategies", [])
    if not selected:
        st.info("Select at least one strategy in the sidebar.")
        return

    strategies_config = config.get("strategies", {})

    for strategy_name in selected:
        spec = get_strategy_spec(strategy_name)
        st.markdown(f"#### {spec.display_name}")
        if spec.description:
            st.caption(spec.description)
        params = strategies_config.get(strategy_name, {}).get("params", {})
        if not params:
            st.write("No parameters for this strategy.")
            continue

        combination_method = params.get("combination_method")
        combination_label = COMBINATION_LABELS.get(combination_method, combination_method or "N/A")

        if strategy_name == "trend":
            lines = [
                ("Momentum lookback", _fmt_days(params.get("momentum_lookback")), "Days used for momentum calculation."),
                ("Short SMA", _fmt_days(params.get("sma_short")), "Short moving average window."),
                ("Long SMA", _fmt_days(params.get("sma_long")), "Long moving average window (must exceed short SMA)."),
                ("Breakout period", _fmt_days(params.get("breakout_period")), "Lookback window for breakout signal."),
                ("Signal combination", combination_label, "How momentum, MA, and breakout signals are combined."),
            ]
            _render_param_lines(lines)
            if combination_method == "weighted":
                weights = list(params.get("weights") or [])
                weights += [None] * (3 - len(weights))
                weight_lines = [
                    ("Momentum weight", _fmt_pct(weights[0]), "Weight for momentum signal."),
                    ("MA weight", _fmt_pct(weights[1]), "Weight for moving average signal."),
                    ("Breakout weight", _fmt_pct(weights[2]), "Weight for breakout signal."),
                    ("Weighted threshold", _fmt_pct(params.get("weighted_threshold")), "Higher threshold is more conservative."),
                ]
                _render_param_lines(weight_lines)

        elif strategy_name == "meanrev":
            lines = [
                ("RSI period", _fmt_days(params.get("rsi_period")), "Window length for RSI calculation."),
                ("RSI oversold", _fmt_ratio(params.get("rsi_oversold")), "Buy threshold for RSI."),
                ("RSI overbought", _fmt_ratio(params.get("rsi_overbought")), "Sell threshold for RSI."),
                ("Bollinger period", _fmt_days(params.get("bb_period")), "Window length for Bollinger Bands."),
                ("Bollinger std dev", _fmt_ratio(params.get("bb_std")), "Standard deviation multiplier."),
                ("Z-Score lookback", _fmt_days(params.get("zscore_lookback")), "Window length for Z-Score."),
                ("Z-Score threshold", _fmt_ratio(params.get("zscore_threshold")), "Higher threshold means fewer trades."),
                ("Signal combination", combination_label, "How RSI, BB, and Z-Score are combined."),
            ]
            _render_param_lines(lines)
            if combination_method == "weighted":
                weights = list(params.get("weights") or [])
                weights += [None] * (3 - len(weights)) # Pads weights so the UI can safely index even if the config is missing some weights
                weight_lines = [
                    ("RSI weight", _fmt_pct(weights[0]), "Weight for RSI signal."),
                    ("Bollinger weight", _fmt_pct(weights[1]), "Weight for Bollinger Bands signal."),
                    ("Z-Score weight", _fmt_pct(weights[2]), "Weight for Z-Score signal."),
                    ("Weighted threshold", _fmt_pct(params.get("weighted_threshold")), "Higher threshold is more conservative."),
                ]
                _render_param_lines(weight_lines)


def _render_meta_layer(config: Dict) -> None:
    st.markdown("**Purpose**: Combines returns from multiple strategies into a single strategy portfolio.")

    selected = config.get("selected_strategies", [])
    if len(selected) <= 1:
        st.info("Meta allocator is only active when multiple strategies are selected.")
        return

    meta_allocator = config.get("meta_allocator")
    if not meta_allocator:
        st.info("Select a meta allocator in the sidebar to combine strategies.")
        return

    spec = get_meta_allocator_spec(meta_allocator["type"])
    st.markdown(f"**Allocator:** {spec.display_name}")
    if spec.description:
        st.caption(spec.description)

    params = meta_allocator.get("params", {})
    if meta_allocator["type"] == "fixed_weight":
        weights = params.get("weights", {})
        lines = []
        for strategy_name, weight in weights.items():
            label = get_strategy_spec(strategy_name).display_name
            lines.append((f"{label} weight", _fmt_pct(weight), "Fixed weight assigned to this strategy."))
        _render_param_lines(lines)
    elif meta_allocator["type"] == "risk_parity":
        lines = [
            ("Volatility lookback", _fmt_days(params.get("vol_lookback")), "Window for strategy volatility estimation."),
        ]
        _render_param_lines(lines)


def _render_asset_layer(config: Dict) -> None:
    st.markdown("**Purpose**: Translates strategy signals into asset-level weights.")

    asset_allocator = config.get("asset_allocator")
    if not asset_allocator:
        st.info("Select an asset allocator in the sidebar.")
        return

    spec = get_portfolio_allocator_spec(asset_allocator["type"])
    st.markdown(f"**Allocator:** {spec.display_name}")
    if spec.description:
        st.caption(spec.description)

    params = asset_allocator.get("params", {})
    lines = []
    if asset_allocator["type"] == "inverse_vol_v1":
        lines.append((
            "Inverse vol window",
            _fmt_days(params.get("lookback")),
            "Lookback window for inverse volatility weights.",
        ))

    _render_param_lines(lines)


def _render_risk_caps_layer(config: Dict) -> None:
    st.markdown("**Purpose**: Limits concentration risk before and/or after leverage is applied.")

    cap_mode_labels = {
        "both": "Both (before and after leverage)",
        "pre_leverage": "Pre-leverage only",
        "post_leverage": "Post-leverage only",
    }
    sector_label = "Disabled"
    if config.get("max_sector_weight") is not None:
        sector_label = _fmt_pct(config.get("max_sector_weight"))

    lines = [
        ("Cap mode", cap_mode_labels.get(config.get("cap_mode"), "N/A"), "When to enforce caps relative to leverage."),
        (
            "Max weight per asset",
            _fmt_pct(config.get("max_weight_per_asset")),
            "Maximum allocation to any single asset.",
        ),
        (
            "Max sector weight",
            sector_label,
            "Maximum allocation to any sector (if enabled).",
        ),
        (
            "Min assets held",
            str(config.get("min_assets_held")) if config.get("min_assets_held") is not None else "N/A",
            "Minimum number of assets the portfolio must hold.",
        ),
    ]
    _render_param_lines(lines)


def _render_vol_targeting_layer(config: Dict) -> None:
    st.markdown("**Purpose**: Scales exposure to hit a target annualized volatility.")

    lines = [
        ("Target volatility", _fmt_pct(config.get("target_vol")), "Desired annualized volatility."),
        ("Volatility lookback", _fmt_days(config.get("vol_lookback")), "Window for volatility estimation."),
        ("Min leverage", _fmt_leverage(config.get("min_leverage")), "Lower bound on leverage."),
        ("Max leverage", _fmt_leverage(config.get("max_leverage")), "Upper bound on leverage."),
    ]
    _render_param_lines(lines)


def render(
    portfolios: List[Dict],
    configs: Dict[str, Dict],
    active_portfolio_id: Optional[str],
    active_layer_label: Optional[str],
) -> None:
    active_portfolio = next(
        (p for p in portfolios if p["id"] == active_portfolio_id),
        portfolios[0] if portfolios else None,
    )
    layer_key = LABEL_TO_KEY.get(active_layer_label, DEFAULT_LAYER_KEY)

    st.markdown("### Portfolio System Pipeline")
    st.caption("Follow the flow below to understand how each layer affects the portfolio.")
    _render_pipeline(layer_key)

    st.markdown("---")
    if not active_portfolio:
        st.markdown("### Getting Started")
        st.markdown(
            "Click **Add Portfolio** to create your first system. "
            "You'll configure each layer of the pipeline, starting with Strategy."
        )
        return

    layer_display = LAYER_LABELS.get(layer_key)
    st.markdown(f"### {active_portfolio['name']} - {layer_display}")

    config = configs.get(active_portfolio["id"], {})
    if layer_key == "strategy":
        _render_strategy_layer(config)
    elif layer_key == "meta_allocator":
        _render_meta_layer(config)
    elif layer_key == "asset_allocator":
        _render_asset_layer(config)
    elif layer_key == "risk_caps":
        _render_risk_caps_layer(config)
    elif layer_key == "vol_targeting":
        _render_vol_targeting_layer(config)
