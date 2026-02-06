"""Portfolio configuration manager component."""

from typing import Dict, List
import re

import streamlit as st

from app.components import strategies, meta, allocator, risk
from app.utils.palette import PORTFOLIO_COLORS

MAX_PORTFOLIOS = 5


def _next_color(used_colors: List[str]) -> str:
    for color in PORTFOLIO_COLORS:
        if color not in used_colors:
            return color
    return PORTFOLIO_COLORS[len(used_colors) % len(PORTFOLIO_COLORS)]


def _is_default_name(name: str) -> bool:
    return bool(re.match(r"^Portfolio \\d+$", name.strip()))


def _reindex_default_names(portfolios: List[Dict]) -> None:
    counter = 1
    for portfolio in portfolios:
        if _is_default_name(portfolio["name"]):
            new_name = f"Portfolio {counter}"
            if portfolio["name"] != new_name:
                portfolio["name"] = new_name
                name_key = f"{portfolio['id']}_name"
                if name_key in st.session_state:
                    st.session_state[name_key] = new_name
            counter += 1


def _add_portfolio() -> None:
    portfolios = st.session_state.portfolios
    if len(portfolios) >= MAX_PORTFOLIOS:
        return

    st.session_state.portfolio_counter += 1
    portfolio_id = f"portfolio_{st.session_state.portfolio_counter}"
    used_colors = [p["color"] for p in portfolios]

    portfolios.append({
        "id": portfolio_id,
        "name": f"Portfolio {st.session_state.portfolio_counter}",
        "color": _next_color(used_colors),
    })
    _reindex_default_names(portfolios)


def _init_state() -> None:
    if "portfolios" not in st.session_state:
        st.session_state.portfolios = []
    if "portfolio_counter" not in st.session_state:
        st.session_state.portfolio_counter = 0
    if not st.session_state.portfolios:
        _add_portfolio()
    else:
        _reindex_default_names(st.session_state.portfolios)


def _color_badge(color: str, label: str) -> str:
    return (
        "<div style='display:flex;align-items:center;gap:8px;'>"
        f"<span style='width:12px;height:12px;border-radius:3px;display:inline-block;"
        f"background:{color};'></span>"
        f"<span style='color:#6b7280;font-size:0.85rem;'>{label}</span>"
        "</div>"
    )


def render(universe: List[str]) -> Dict:
    """
    Render portfolio system configurations.

    Returns:
        dict with keys:
            - portfolios: list of portfolio descriptors (id, name, color)
            - configs: dict mapping portfolio id to config
            - errors: list of validation errors
    """
    _init_state()

    portfolios = st.session_state.portfolios

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Portfolio Systems")
    st.sidebar.caption("Define up to 5 portfolio configurations")

    add_disabled = len(portfolios) >= MAX_PORTFOLIOS
    if st.sidebar.button(
        "Add Portfolio",
        disabled=add_disabled,
        help="Add another portfolio configuration",
        key="add_portfolio",
    ):
        _add_portfolio()
        st.rerun()

    remove_id = None
    needs_reindex = False
    configs: Dict[str, Dict] = {}
    errors: List[str] = []

    for portfolio in portfolios:
        expander = st.sidebar.expander(portfolio["name"], expanded=False)
        with expander:
            name_key = f"{portfolio['id']}_name"
            name_value = expander.text_input(
                "Portfolio Name",
                value=portfolio["name"],
                key=name_key,
            )
            if name_value != portfolio["name"]:
                portfolio["name"] = name_value
                needs_reindex = True

            expander.markdown(_color_badge(portfolio["color"], "Assigned color"), unsafe_allow_html=True)

            key_prefix = f"{portfolio['id']}_"

            strat_config = strategies.render(
                key_prefix=key_prefix,
                container=expander,
                show_header=False,
            )
            meta_config = meta.render(
                strat_config["selected_strategies"],
                key_prefix=key_prefix,
                container=expander,
                show_header=False,
            )
            allocator_config = allocator.render(
                key_prefix=key_prefix,
                container=expander,
                show_header=False,
            )
            risk_config = risk.render(
                universe,
                key_prefix=key_prefix,
                container=expander,
                show_header=False,
            )

            portfolio_errors = (
                strat_config["errors"]
                + meta_config["errors"]
                + allocator_config["errors"]
                + risk_config["errors"]
            )
            if portfolio_errors:
                errors.extend([f"{portfolio['name']}: {err}" for err in portfolio_errors])

            configs[portfolio["id"]] = {
                "strategies": strat_config["strategies"],
                "selected_strategies": strat_config["selected_strategies"],
                "meta_allocator": meta_config["meta_allocator"],
                "asset_allocator": allocator_config["asset_allocator"],
                "vol_window": allocator_config["vol_window"],
                "max_weight_per_asset": risk_config["max_weight_per_asset"],
                "max_sector_weight": risk_config["max_sector_weight"],
                "min_assets_held": risk_config["min_assets_held"],
                "cap_mode": risk_config["cap_mode"],
                "target_vol": risk_config["target_vol"],
                "vol_lookback": risk_config["vol_lookback"],
                "min_leverage": risk_config["min_leverage"],
                "max_leverage": risk_config["max_leverage"],
            }

            if expander.button(
                "Remove Portfolio",
                key=f"{portfolio['id']}_remove",
            ):
                remove_id = portfolio["id"]

    if remove_id:
        st.session_state.portfolios = [p for p in portfolios if p["id"] != remove_id]
        _reindex_default_names(st.session_state.portfolios)
        st.rerun()
    elif needs_reindex:
        _reindex_default_names(st.session_state.portfolios)

    return {
        "portfolios": list(st.session_state.portfolios),
        "configs": configs,
        "errors": errors,
    }
