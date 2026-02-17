"""Portfolio configuration manager component."""

from typing import Dict, List
import copy
import streamlit as st

from app.components import strategies, meta, allocator, risk
from app.components.layers import (
    DEFAULT_LAYER_KEY,
    LABEL_TO_KEY,
    PIPELINE_STEPS,
    LAYER_LABELS,
)
from app.meta_allocator_ui import risk_parity as meta_risk_parity_ui
from app.portfolio_allocator_ui import inverse_vol as inverse_vol_ui
from app.strategy_ui import meanrev as meanrev_ui
from app.strategy_ui import trend as trend_ui
from app.utils.validators import (
    validate_risk_caps_widget,
    validate_volatility_targeting_widget,
)

MAX_PORTFOLIOS = 5

PORTFOLIO_COLORS = [
    "#4C78A8",  # Blue
    "#F58518",  # Orange
    "#E45756",  # Red
    "#72B7B2",  # Teal
    "#54A24B",  # Green
]


def _default_trend_params() -> Dict[str, object]:
    defaults = trend_ui.DEFAULTS
    return {
        "momentum_lookback": defaults["momentum_lookback"],
        "sma_short": defaults["sma_short"],
        "sma_long": defaults["sma_long"],
        "breakout_period": defaults["breakout_period"],
        "combination_method": defaults["combination_method"],
        "weights": list(defaults["weights"]),
        "weighted_threshold": defaults["weighted_threshold"],
    }


def _default_meanrev_params() -> Dict[str, object]:
    defaults = meanrev_ui.DEFAULTS
    return {
        "rsi_period": defaults["rsi_period"],
        "rsi_oversold": defaults["rsi_oversold"],
        "rsi_overbought": defaults["rsi_overbought"],
        "bb_period": defaults["bb_period"],
        "bb_std": defaults["bb_std"],
        "zscore_lookback": defaults["zscore_lookback"],
        "zscore_threshold": defaults["zscore_threshold"],
        "combination_method": defaults["combination_method"],
        "weights": list(defaults["weights"]),
        "weighted_threshold": defaults["weighted_threshold"],
    }


def _default_strategy_params(strategy_name: str) -> Dict[str, object]:
    if strategy_name == "trend":
        return _default_trend_params()
    if strategy_name == "meanrev":
        return _default_meanrev_params()
    return {}


def _default_asset_allocator() -> Dict[str, object]:
    alloc_type = allocator.DEFAULT_ALLOCATOR_TYPE
    params: Dict[str, object] = {}
    if alloc_type == "inverse_vol_v1":
        params["lookback"] = inverse_vol_ui.DEFAULT_LOOKBACK
    return {"type": alloc_type, "params": params}


def _default_meta_allocator() -> Dict[str, object]:
    return {"type": meta.DEFAULT_META_ALLOCATOR_TYPE, "params": {}}


def _default_portfolio_config() -> Dict[str, object]:
    selected_strategies = list(strategies.DEFAULT_STRATEGIES)
    strategies_config = {
        name: {"params": _default_strategy_params(name)} for name in selected_strategies
    }
    return {
        "selected_strategies": selected_strategies,
        "strategies": strategies_config,
        "meta_allocator": _default_meta_allocator(),
        "asset_allocator": _default_asset_allocator(),
        "cap_mode": "both",
        "max_weight_per_asset": risk.DEFAULT_MAX_WEIGHT_PER_ASSET,
        "use_sector_cap": False,
        "max_sector_weight": risk.DEFAULT_MAX_SECTOR_WEIGHT,
        "min_assets_held": risk.DEFAULT_MIN_ASSETS_HELD,
        "target_vol": risk.DEFAULT_TARGET_VOL,
        "vol_lookback": risk.DEFAULT_VOL_LOOKBACK,
        "min_leverage": risk.DEFAULT_MIN_LEVERAGE,
        "max_leverage": risk.DEFAULT_MAX_LEVERAGE,
    }


def _ensure_strategy_entries(config: Dict, selected_strategies: List[str]) -> None:
    strategies_config = config.setdefault("strategies", {})
    for strategy_name in selected_strategies:
        entry = strategies_config.get(strategy_name)
        if not isinstance(entry, dict) or "params" not in entry:
            strategies_config[strategy_name] = {"params": _default_strategy_params(strategy_name)}


def _normalize_portfolio_config(config: Dict) -> None:
    defaults = _default_portfolio_config()
    for key, value in defaults.items():
        if key not in config:
            config[key] = copy.deepcopy(value)

    if not config.get("selected_strategies"):
        config["selected_strategies"] = list(strategies.DEFAULT_STRATEGIES)

    _ensure_strategy_entries(config, config["selected_strategies"])

    asset_allocator = config.get("asset_allocator") or _default_asset_allocator()
    asset_allocator.setdefault("params", {})
    if asset_allocator.get("type") == "inverse_vol_v1":
        asset_allocator["params"].setdefault("lookback", inverse_vol_ui.DEFAULT_LOOKBACK)
    config["asset_allocator"] = asset_allocator

    meta_allocator = config.get("meta_allocator") or _default_meta_allocator()
    meta_allocator.setdefault("params", {})
    if meta_allocator.get("type") == "risk_parity":
        meta_allocator["params"].setdefault(
            "vol_lookback",
            meta_risk_parity_ui.DEFAULTS["vol_lookback"],
        )
    config["meta_allocator"] = meta_allocator

    if "use_sector_cap" not in config:
        config["use_sector_cap"] = False
    if "max_sector_weight" not in config:
        config["max_sector_weight"] = risk.DEFAULT_MAX_SECTOR_WEIGHT


def _ensure_portfolio_config(portfolio_id: str) -> Dict[str, object]:
    configs = st.session_state.portfolio_live_configs
    config = configs.get(portfolio_id)
    if config is None:
        config = _default_portfolio_config()
        configs[portfolio_id] = config
    else:
        _normalize_portfolio_config(config)
    return config


def _strategy_config_from_config(config: Dict, selected_strategies: List[str]) -> Dict[str, Dict]:
    _ensure_strategy_entries(config, selected_strategies)
    strategies_config: Dict[str, Dict] = {}
    for strategy_name in selected_strategies:
        strategies_config[strategy_name] = config["strategies"].get(
            strategy_name,
            {"params": _default_strategy_params(strategy_name)},
        )
    return strategies_config


def _validate_strategies(selected_strategies: List[str]) -> List[str]:
    errors: List[str] = []
    if not selected_strategies:
        errors.append("At least one strategy must be selected")
    if len(selected_strategies) > 1 and "passthrough" in selected_strategies:
        errors.append("Passthrough strategy cannot be combined with other strategies")
    return errors


def _sync_fixed_weight_for_selection(config: Dict, selected_strategies: List[str]) -> None:
    meta_allocator = config.get("meta_allocator")
    if not meta_allocator or meta_allocator.get("type") != "fixed_weight":
        return
    params = meta_allocator.setdefault("params", {})
    weights = dict(params.get("weights", {}))
    weights = {name: weight for name, weight in weights.items() if name in selected_strategies}
    missing = [name for name in selected_strategies if name not in weights]
    if missing:
        remaining = max(0.0, 1.0 - sum(weights.values()))
        add = remaining / len(missing) if missing else 0.0
        for name in missing:
            weights[name] = round(add, 4)
    params["weights"] = weights


def _meta_allocator_for_run(config: Dict, selected_strategies: List[str]) -> Dict:
    if len(selected_strategies) <= 1:
        return None

    meta_allocator = config.get("meta_allocator") or _default_meta_allocator()
    allocator_type = meta_allocator.get("type") or meta.DEFAULT_META_ALLOCATOR_TYPE
    params = dict(meta_allocator.get("params") or {})

    if allocator_type == "fixed_weight":
        weights = params.get("weights", {})
        if not weights or any(name not in weights for name in selected_strategies):
            _sync_fixed_weight_for_selection(config, selected_strategies)
            params = dict(config.get("meta_allocator", {}).get("params", {}))
            weights = params.get("weights", {})
        params = {"weights": weights}
    elif allocator_type == "risk_parity":
        params = {
            "vol_lookback": params.get(
                "vol_lookback",
                meta_risk_parity_ui.DEFAULTS["vol_lookback"],
            ),
        }

    return {"type": allocator_type, "params": params}


def _validate_meta_allocator(meta_allocator: Dict, selected_strategies: List[str]) -> List[str]:
    if len(selected_strategies) <= 1 or not meta_allocator:
        return []
    errors: List[str] = []
    if meta_allocator.get("type") == "fixed_weight":
        weights = meta_allocator.get("params", {}).get("weights", {})
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            errors.append(f"Strategy weights must sum to 100% (currently {total:.0%})")
    return errors


def _asset_allocator_for_run(config: Dict) -> Dict:
    asset_allocator = config.get("asset_allocator") or _default_asset_allocator()
    allocator_type = asset_allocator.get("type") or allocator.DEFAULT_ALLOCATOR_TYPE
    params = dict(asset_allocator.get("params") or {})
    if allocator_type == "inverse_vol_v1":
        params.setdefault("lookback", inverse_vol_ui.DEFAULT_LOOKBACK)
    return {"type": allocator_type, "params": params}


def _vol_window_from_asset_allocator(asset_allocator: Dict) -> int:
    params = asset_allocator.get("params", {})
    return params.get("lookback") or params.get("vol_window")


def _risk_config_for_run(config: Dict) -> Dict[str, object]:
    use_sector_cap = config.get("use_sector_cap", False)
    max_sector_weight_raw = config.get("max_sector_weight", risk.DEFAULT_MAX_SECTOR_WEIGHT)
    max_sector_weight = max_sector_weight_raw if use_sector_cap else None
    return {
        "max_weight_per_asset": config.get("max_weight_per_asset", risk.DEFAULT_MAX_WEIGHT_PER_ASSET),
        "max_sector_weight": max_sector_weight,
        "use_sector_cap": use_sector_cap,
        "min_assets_held": config.get("min_assets_held", risk.DEFAULT_MIN_ASSETS_HELD),
        "cap_mode": config.get("cap_mode", "both"),
        "target_vol": config.get("target_vol", risk.DEFAULT_TARGET_VOL),
        "vol_lookback": config.get("vol_lookback", risk.DEFAULT_VOL_LOOKBACK),
        "min_leverage": config.get("min_leverage", risk.DEFAULT_MIN_LEVERAGE),
        "max_leverage": config.get("max_leverage", risk.DEFAULT_MAX_LEVERAGE),
    }


def _validate_risk_config(config: Dict, universe: List[str]) -> List[str]:
    use_sector_cap = config.get("use_sector_cap", False)
    max_sector_weight_raw = config.get("max_sector_weight", risk.DEFAULT_MAX_SECTOR_WEIGHT)
    max_sector_weight = max_sector_weight_raw if use_sector_cap else None
    errors = validate_risk_caps_widget(
        min_assets_held=config.get("min_assets_held", risk.DEFAULT_MIN_ASSETS_HELD),
        universe=universe,
        max_weight_per_asset=config.get(
            "max_weight_per_asset",
            risk.DEFAULT_MAX_WEIGHT_PER_ASSET,
        ),
        max_sector_weight=max_sector_weight,
    )
    errors.extend(
        validate_volatility_targeting_widget(
            config.get("min_leverage", risk.DEFAULT_MIN_LEVERAGE),
            config.get("max_leverage", risk.DEFAULT_MAX_LEVERAGE),
        )
    )
    return errors

def _build_risk_cv(config: Dict) -> Dict:
    """Build the current_values dict for the risk renderer from a portfolio config."""
    return {
        "cap_mode": config.get("cap_mode", "both"),
        "max_weight_per_asset": config.get("max_weight_per_asset", risk.DEFAULT_MAX_WEIGHT_PER_ASSET),
        "use_sector_cap": config.get("use_sector_cap", False),
        "max_sector_weight": config.get("max_sector_weight", risk.DEFAULT_MAX_SECTOR_WEIGHT),
        "min_assets_held": config.get("min_assets_held", risk.DEFAULT_MIN_ASSETS_HELD),
        "target_vol": config.get("target_vol", risk.DEFAULT_TARGET_VOL),
        "vol_lookback": config.get("vol_lookback", risk.DEFAULT_VOL_LOOKBACK),
        "min_leverage": config.get("min_leverage", risk.DEFAULT_MIN_LEVERAGE),
        "max_leverage": config.get("max_leverage", risk.DEFAULT_MAX_LEVERAGE),
    }


def _write_risk_back(config: Dict, risk_config: Dict) -> None:
    """Write risk renderer output back to the portfolio config."""
    config["cap_mode"] = risk_config["cap_mode"]
    config["max_weight_per_asset"] = risk_config["max_weight_per_asset"]
    config["use_sector_cap"] = risk_config.get(
        "use_sector_cap",
        config.get("use_sector_cap", False),
    )
    config["max_sector_weight"] = risk_config.get(
        "max_sector_weight_raw",
        config.get("max_sector_weight", risk.DEFAULT_MAX_SECTOR_WEIGHT),
    )
    config["min_assets_held"] = risk_config["min_assets_held"]
    config["target_vol"] = risk_config["target_vol"]
    config["vol_lookback"] = risk_config["vol_lookback"]
    config["min_leverage"] = risk_config["min_leverage"]
    config["max_leverage"] = risk_config["max_leverage"]


def _next_color(used_colors: List[str]) -> str:
    """Return the next available portfolio color."""
    for color in PORTFOLIO_COLORS:
        if color not in used_colors:
            return color
    return PORTFOLIO_COLORS[len(used_colors) % len(PORTFOLIO_COLORS)]


def _add_portfolio() -> None:
    """Create and register a new portfolio in session state."""
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
    st.session_state.active_portfolio_id = portfolio_id
    st.session_state[f"{portfolio_id}_layer"] = LAYER_LABELS[DEFAULT_LAYER_KEY]
    _ensure_portfolio_config(portfolio_id)


def _init_state() -> None:
    """Initialize portfolio-related session state keys and defaults."""
    if "portfolios" not in st.session_state:
        st.session_state.portfolios = []
    if "portfolio_counter" not in st.session_state:
        st.session_state.portfolio_counter = 0
    if "portfolio_live_configs" not in st.session_state:
        st.session_state.portfolio_live_configs = {}

    if "active_portfolio_id" not in st.session_state and st.session_state.portfolios:
        st.session_state.active_portfolio_id = st.session_state.portfolios[0]["id"]
    if st.session_state.portfolios:
        known_ids = {p["id"] for p in st.session_state.portfolios}
        if st.session_state.active_portfolio_id not in known_ids:
            st.session_state.active_portfolio_id = st.session_state.portfolios[0]["id"]
    if not st.session_state.portfolios:
        st.session_state.active_portfolio_id = None
    for portfolio in st.session_state.portfolios:
        layer_key = f"{portfolio['id']}_layer"
        if layer_key not in st.session_state or st.session_state[layer_key] not in LABEL_TO_KEY:
            st.session_state[layer_key] = LAYER_LABELS[DEFAULT_LAYER_KEY]


def _set_active_portfolio(portfolio_id: str) -> None:
    """Update the active portfolio id in session state."""
    st.session_state.active_portfolio_id = portfolio_id


def _select_layer(container: st.delta_generator.DeltaGenerator, portfolio_id: str) -> str:
    """Render the layer selector and return the chosen label."""
    layer_key = f"{portfolio_id}_layer"
    labels = [label for _, label in PIPELINE_STEPS]
    current_label = st.session_state.get(layer_key, LAYER_LABELS[DEFAULT_LAYER_KEY])
    if current_label not in labels:
        current_label = LAYER_LABELS[DEFAULT_LAYER_KEY]
        st.session_state[layer_key] = current_label

    label_text = "Portfolio Pipeline (Configure layers)"
    return container.segmented_control(
            label_text,
            options=labels,
            default=current_label,
            key=layer_key,
            on_change=_set_active_portfolio,
            args=(portfolio_id,),
        )

def render(
    universe: List[str],
) -> Dict:
    """
    Render portfolio system configurations.

    Returns:
        dict with keys:
            - portfolios: list of portfolio descriptors (id, name, color)
            - configs: dict mapping portfolio id to config
            - errors: list of validation errors
            - active_portfolio_id: currently active portfolio id
            - active_layer_label: selected layer label for active portfolio
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
    configs: Dict[str, Dict] = {}
    errors: List[str] = []
    configs_store = st.session_state.portfolio_live_configs

    for portfolio in portfolios:
        is_active = portfolio["id"] == st.session_state.active_portfolio_id
        expander = st.sidebar.expander(portfolio["name"], expanded=is_active)
        with expander:
            name_key = f"{portfolio['id']}_name"
            name_value = expander.text_input(
                "Portfolio Name",
                value=portfolio["name"],
                key=name_key,
                on_change=_set_active_portfolio,
                args=(portfolio["id"],),
            )
            if name_value != portfolio["name"]:
                portfolio["name"] = name_value

            key_prefix = f"{portfolio['id']}_"
            config = _ensure_portfolio_config(portfolio["id"])
            selected_strategies = list(
                config.get("selected_strategies", strategies.DEFAULT_STRATEGIES)
            )
            _ensure_strategy_entries(config, selected_strategies)

            # --- Layer selector ---
            layer_label = _select_layer(expander, portfolio["id"])
            selected_layer_key = LABEL_TO_KEY.get(layer_label, DEFAULT_LAYER_KEY)

            # ===================================================================
            # STRATEGY LAYER
            # ===================================================================
            if selected_layer_key == "strategy":
                # Build current_values from the config dict
                strategy_cv = {
                    "selected_strategies": list(config.get("selected_strategies", strategies.DEFAULT_STRATEGIES)),
                    "strategies": config.get("strategies", {}),
                }
                strat_config = strategies.render(
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                    current_values=strategy_cv,
                )
                selected_strategies = strat_config["selected_strategies"]
                strategies_config = strat_config["strategies"]
                strategy_errors = strat_config["errors"]

                # Write back to config
                config["selected_strategies"] = list(selected_strategies)
                _ensure_strategy_entries(config, selected_strategies)
                config["strategies"].update(strategies_config)
                _sync_fixed_weight_for_selection(config, selected_strategies)
            else:
                selected_strategies = list(config.get("selected_strategies", []))
                strategies_config = _strategy_config_from_config(config, selected_strategies)
                strategy_errors = _validate_strategies(selected_strategies)

            # ===================================================================
            # META ALLOCATOR LAYER
            # ===================================================================
            if selected_layer_key == "meta_allocator":
                meta_cv = config.get("meta_allocator") or _default_meta_allocator()
                meta_config = meta.render(
                    selected_strategies,
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                    current_values=meta_cv,
                )
                if len(selected_strategies) <= 1:
                    expander.info("Meta allocator activates when multiple strategies are selected.")
                meta_allocator_config = meta_config["meta_allocator"]
                meta_errors = meta_config["errors"]
                if len(selected_strategies) > 1 and meta_allocator_config is not None:
                    config["meta_allocator"] = meta_allocator_config
            else:
                meta_allocator_config = _meta_allocator_for_run(config, selected_strategies)
                meta_errors = _validate_meta_allocator(meta_allocator_config, selected_strategies)

            # ===================================================================
            # ASSET ALLOCATOR LAYER
            # ===================================================================
            if selected_layer_key == "asset_allocator":
                allocator_cv = config.get("asset_allocator") or _default_asset_allocator()
                allocator_config = allocator.render(
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                    expand_params=True,
                    current_values=allocator_cv,
                )
                asset_allocator_config = allocator_config["asset_allocator"]
                allocator_errors = allocator_config["errors"]
                config["asset_allocator"] = asset_allocator_config
            else:
                asset_allocator_config = _asset_allocator_for_run(config)
                allocator_errors = []

            vol_window = _vol_window_from_asset_allocator(asset_allocator_config)

            # ===================================================================
            # RISK CAPS LAYER
            # ===================================================================
            if selected_layer_key == "risk_caps":
                risk_cv = _build_risk_cv(config)
                risk_config = risk.render(
                    universe,
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                    show_risk_caps=True,
                    show_vol_targeting=False,
                    expand_risk_caps=True,
                    current_values=risk_cv,
                )
                _write_risk_back(config, risk_config)

            # ===================================================================
            # VOLATILITY TARGETING LAYER
            # ===================================================================
            elif selected_layer_key == "vol_targeting":
                vol_cv = _build_risk_cv(config)
                risk_config = risk.render(
                    universe,
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                    show_risk_caps=False,
                    show_vol_targeting=True,
                    expand_vol_targeting=True,
                    current_values=vol_cv,
                )
                _write_risk_back(config, risk_config)

            risk_config = _risk_config_for_run(config)
            risk_errors = _validate_risk_config(config, universe)

            portfolio_errors = (
                strategy_errors
                + meta_errors
                + allocator_errors
                + risk_errors
            )
            if portfolio_errors:
                errors.extend([f"{portfolio['name']}: {err}" for err in portfolio_errors])

            configs[portfolio["id"]] = {
                "strategies": strategies_config,
                "selected_strategies": selected_strategies,
                "meta_allocator": meta_allocator_config,
                "asset_allocator": asset_allocator_config,
                "vol_window": vol_window,
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
        if remove_id in configs_store:
            del configs_store[remove_id]
        layer_key = f"{remove_id}_layer"
        if layer_key in st.session_state:
            del st.session_state[layer_key]
        if st.session_state.portfolios:
            if st.session_state.active_portfolio_id == remove_id:
                st.session_state.active_portfolio_id = st.session_state.portfolios[0]["id"]
        else:
            st.session_state.active_portfolio_id = None
        st.rerun()

    return {
        "portfolios": list(st.session_state.portfolios),
        "configs": configs,
        "errors": errors,
        "active_portfolio_id": st.session_state.active_portfolio_id,
        "active_layer_label": st.session_state.get(
            f"{st.session_state.active_portfolio_id}_layer",
            LAYER_LABELS[DEFAULT_LAYER_KEY],
        ) if st.session_state.active_portfolio_id else LAYER_LABELS[DEFAULT_LAYER_KEY],
    }
