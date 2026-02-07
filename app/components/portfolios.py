"""Portfolio configuration manager component."""

from typing import Dict, List, Tuple
import streamlit as st

from app.components import strategies, meta, allocator, risk
from app.components.layers import (
    DEFAULT_LAYER_KEY,
    LABEL_TO_KEY,
    LAYER_DEFINITIONS,
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
_UNSET = object()

PORTFOLIO_COLORS = [
    "#4C78A8",  # Blue
    "#F58518",  # Orange
    "#E45756",  # Red
    "#72B7B2",  # Teal
    "#54A24B",  # Green
]

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


def _init_state() -> None:
    """Initialize portfolio-related session state keys and defaults."""
    if "portfolios" not in st.session_state:
        st.session_state.portfolios = []
    if "portfolio_counter" not in st.session_state:
        st.session_state.portfolio_counter = 0
    if "portfolio_drafts" not in st.session_state:
        st.session_state.portfolio_drafts = {}
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


def _state_value(key: str, default, fallback=_UNSET):
    """Resolve a value from session state with optional fallback/default."""
    if key in st.session_state:
        return st.session_state[key]
    if fallback is not _UNSET:
        return fallback
    return default


def _seed_value(key: str, value) -> None:
    """Seed a session state value once if it is not already set."""
    if key in st.session_state:
        return
    if value is None:
        return
    st.session_state[key] = value


def _set_active_portfolio(portfolio_id: str) -> None:
    """Update the active portfolio id in session state."""
    st.session_state.active_portfolio_id = portfolio_id


def _select_layer(container: st.delta_generator.DeltaGenerator, portfolio_id: str) -> str:
    """Render the layer selector and return the chosen label."""
    layer_key = f"{portfolio_id}_layer"
    labels = [label for _, label in LAYER_DEFINITIONS]
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

def _get_selected_strategies(key_prefix: str, draft_config: Dict) -> List[str]:
    """Return selected strategies from state or draft config."""
    return _state_value(
        f"{key_prefix}strategies",
        strategies.DEFAULT_STRATEGIES,
        draft_config.get("selected_strategies", _UNSET),
    )


def _seed_strategy_state(
    key_prefix: str,
    draft_config: Dict,
    selected_strategies: List[str],
) -> None:
    """Seed strategy widget state from draft config."""
    _seed_value(f"{key_prefix}strategies", selected_strategies)

    strategy_configs = draft_config.get("strategies", {})
    for strategy_name in selected_strategies:
        params = strategy_configs.get(strategy_name, {}).get("params", {})
        prefix = f"{key_prefix}{strategy_name}_"

        if strategy_name == "trend":
            _seed_value(f"{prefix}momentum_lookback", params.get("momentum_lookback"))
            _seed_value(f"{prefix}sma_short", params.get("sma_short"))
            _seed_value(f"{prefix}sma_long", params.get("sma_long"))
            _seed_value(f"{prefix}breakout_period", params.get("breakout_period"))
            _seed_value(f"{prefix}combination_method", params.get("combination_method"))
            weights = list(params.get("weights") or [])
            if weights:
                _seed_value(f"{prefix}weight_momentum", weights[0])
                if len(weights) > 1:
                    _seed_value(f"{prefix}weight_ma", weights[1])
            _seed_value(f"{prefix}weighted_threshold", params.get("weighted_threshold"))
        elif strategy_name == "meanrev":
            _seed_value(f"{prefix}rsi_period", params.get("rsi_period"))
            _seed_value(f"{prefix}rsi_oversold", params.get("rsi_oversold"))
            _seed_value(f"{prefix}rsi_overbought", params.get("rsi_overbought"))
            _seed_value(f"{prefix}bb_period", params.get("bb_period"))
            _seed_value(f"{prefix}bb_std", params.get("bb_std"))
            _seed_value(f"{prefix}zscore_lookback", params.get("zscore_lookback"))
            _seed_value(f"{prefix}zscore_threshold", params.get("zscore_threshold"))
            _seed_value(f"{prefix}combination_method", params.get("combination_method"))
            weights = list(params.get("weights") or [])
            if weights:
                _seed_value(f"{prefix}weight_rsi", weights[0])
                if len(weights) > 1:
                    _seed_value(f"{prefix}weight_bb", weights[1])
            _seed_value(f"{prefix}weighted_threshold", params.get("weighted_threshold"))


def _seed_meta_state(
    key_prefix: str,
    draft_config: Dict,
    selected_strategies: List[str],
) -> None:
    """Seed meta allocator widget state from draft config."""
    meta_allocator = draft_config.get("meta_allocator")
    if not meta_allocator:
        return
    _seed_value(f"{key_prefix}meta_allocator_type", meta_allocator.get("type"))

    params = meta_allocator.get("params", {})
    if meta_allocator.get("type") == "fixed_weight":
        weights = params.get("weights", {})
        remaining = 100.0
        n_strategies = len(selected_strategies)
        for i, strategy_name in enumerate(selected_strategies):
            if i == n_strategies - 1:
                break
            fallback_weight = weights.get(strategy_name)
            if fallback_weight is None:
                fallback_pct = min(100.0 / n_strategies, remaining) if n_strategies else 0.0
            else:
                fallback_pct = round(fallback_weight * 100.0, 2)
                if fallback_pct > remaining:
                    fallback_pct = remaining
            _seed_value(
                f"{key_prefix}meta_fixed_weight_weight_{strategy_name}",
                fallback_pct,
            )
            remaining = round(remaining - fallback_pct, 2)
    elif meta_allocator.get("type") == "risk_parity":
        _seed_value(
            f"{key_prefix}meta_risk_parity_vol_lookback",
            params.get("vol_lookback"),
        )


def _seed_asset_allocator_state(key_prefix: str, draft_config: Dict) -> None:
    """Seed asset allocator widget state from draft config."""
    asset_allocator = draft_config.get("asset_allocator")
    if not asset_allocator:
        return
    _seed_value(f"{key_prefix}asset_allocator_type", asset_allocator.get("type"))
    params = asset_allocator.get("params", {})
    if asset_allocator.get("type") == "inverse_vol_v1":
        _seed_value(
            f"{key_prefix}allocator_inverse_vol_v1_lookback",
            params.get("lookback"),
        )


def _seed_risk_state(key_prefix: str, draft_config: Dict) -> None:
    """Seed risk and volatility targeting widget state from draft config."""
    _seed_value(f"{key_prefix}cap_mode", draft_config.get("cap_mode"))
    _seed_value(f"{key_prefix}max_weight_per_asset", draft_config.get("max_weight_per_asset"))
    _seed_value(
        f"{key_prefix}use_sector_cap",
        draft_config.get("max_sector_weight") is not None,
    )
    _seed_value(f"{key_prefix}max_sector_weight", draft_config.get("max_sector_weight"))
    _seed_value(f"{key_prefix}min_assets_held", draft_config.get("min_assets_held"))
    _seed_value(f"{key_prefix}target_vol", draft_config.get("target_vol"))
    _seed_value(f"{key_prefix}vol_lookback", draft_config.get("vol_lookback"))
    _seed_value(f"{key_prefix}min_leverage", draft_config.get("min_leverage"))
    _seed_value(f"{key_prefix}max_leverage", draft_config.get("max_leverage"))


def _merge_draft_config(
    draft_config: Dict,
    new_config: Dict,
    selected_strategies: List[str],
) -> Dict:
    """Merge current config into the stored draft to preserve values."""
    merged = dict(draft_config)
    merged.update({
        "selected_strategies": list(selected_strategies),
        "asset_allocator": new_config.get("asset_allocator"),
        "vol_window": new_config.get("vol_window"),
        "max_weight_per_asset": new_config.get("max_weight_per_asset"),
        "max_sector_weight": new_config.get("max_sector_weight"),
        "min_assets_held": new_config.get("min_assets_held"),
        "cap_mode": new_config.get("cap_mode"),
        "target_vol": new_config.get("target_vol"),
        "vol_lookback": new_config.get("vol_lookback"),
        "min_leverage": new_config.get("min_leverage"),
        "max_leverage": new_config.get("max_leverage"),
    })

    draft_strategies = dict(draft_config.get("strategies", {}))
    new_strategies = new_config.get("strategies", {})
    draft_strategies.update(new_strategies)
    merged["strategies"] = draft_strategies

    if len(selected_strategies) > 1:
        merged["meta_allocator"] = new_config.get("meta_allocator")
    else:
        merged["meta_allocator"] = draft_config.get("meta_allocator")

    return merged


def _build_trend_params(prefix: str, draft_params: Dict) -> Dict:
    """Assemble trend parameters from state/draft with safeguards."""
    defaults = trend_ui.DEFAULTS
    momentum_lookback = _state_value(
        f"{prefix}momentum_lookback",
        defaults["momentum_lookback"],
        draft_params.get("momentum_lookback", _UNSET),
    )
    sma_short = _state_value(
        f"{prefix}sma_short",
        defaults["sma_short"],
        draft_params.get("sma_short", _UNSET),
    )
    sma_long_default = defaults["sma_long"]
    if sma_long_default < sma_short + 1:
        sma_long_default = sma_short + 1
    sma_long = _state_value(
        f"{prefix}sma_long",
        sma_long_default,
        draft_params.get("sma_long", _UNSET),
    )
    if sma_long < sma_short + 1:
        sma_long = sma_short + 1
    breakout_period = _state_value(
        f"{prefix}breakout_period",
        defaults["breakout_period"],
        draft_params.get("breakout_period", _UNSET),
    )
    combination_method = _state_value(
        f"{prefix}combination_method",
        defaults["combination_method"],
        draft_params.get("combination_method", _UNSET),
    )

    weights = list(defaults["weights"])
    weighted_threshold = _state_value(
        f"{prefix}weighted_threshold",
        defaults["weighted_threshold"],
        draft_params.get("weighted_threshold", _UNSET),
    )
    draft_weights = list(draft_params.get("weights") or weights)
    if combination_method == "weighted":
        weight_momentum = _state_value(
            f"{prefix}weight_momentum",
            weights[0],
            draft_weights[0] if len(draft_weights) > 0 else _UNSET,
        )
        weight_ma = _state_value(
            f"{prefix}weight_ma",
            weights[1],
            draft_weights[1] if len(draft_weights) > 1 else _UNSET,
        )
        weight_breakout = max(0.0, 1.0 - weight_momentum - weight_ma)
        weights = [weight_momentum, weight_ma, weight_breakout]
        weighted_threshold = _state_value(
            f"{prefix}weighted_threshold",
            defaults["weighted_threshold"],
            draft_params.get("weighted_threshold", _UNSET),
        )

    return {
        "momentum_lookback": momentum_lookback,
        "sma_short": sma_short,
        "sma_long": sma_long,
        "breakout_period": breakout_period,
        "combination_method": combination_method,
        "weights": weights,
        "weighted_threshold": weighted_threshold,
    }


def _build_meanrev_params(prefix: str, draft_params: Dict) -> Dict:
    """Assemble mean-reversion parameters from state/draft with safeguards."""
    defaults = meanrev_ui.DEFAULTS
    rsi_period = _state_value(
        f"{prefix}rsi_period",
        defaults["rsi_period"],
        draft_params.get("rsi_period", _UNSET),
    )
    rsi_oversold = _state_value(
        f"{prefix}rsi_oversold",
        defaults["rsi_oversold"],
        draft_params.get("rsi_oversold", _UNSET),
    )
    rsi_overbought_default = defaults["rsi_overbought"]
    if rsi_overbought_default < rsi_oversold + 1:
        rsi_overbought_default = rsi_oversold + 1
    rsi_overbought = _state_value(
        f"{prefix}rsi_overbought",
        rsi_overbought_default,
        draft_params.get("rsi_overbought", _UNSET),
    )
    if rsi_overbought < rsi_oversold + 1:
        rsi_overbought = rsi_oversold + 1
    bb_period = _state_value(
        f"{prefix}bb_period",
        defaults["bb_period"],
        draft_params.get("bb_period", _UNSET),
    )
    bb_std = _state_value(
        f"{prefix}bb_std",
        defaults["bb_std"],
        draft_params.get("bb_std", _UNSET),
    )
    zscore_lookback = _state_value(
        f"{prefix}zscore_lookback",
        defaults["zscore_lookback"],
        draft_params.get("zscore_lookback", _UNSET),
    )
    zscore_threshold = _state_value(
        f"{prefix}zscore_threshold",
        defaults["zscore_threshold"],
        draft_params.get("zscore_threshold", _UNSET),
    )
    combination_method = _state_value(
        f"{prefix}combination_method",
        defaults["combination_method"],
        draft_params.get("combination_method", _UNSET),
    )

    weights = list(defaults["weights"])
    weighted_threshold = _state_value(
        f"{prefix}weighted_threshold",
        defaults["weighted_threshold"],
        draft_params.get("weighted_threshold", _UNSET),
    )
    draft_weights = list(draft_params.get("weights") or weights)
    if combination_method == "weighted":
        weight_rsi = _state_value(
            f"{prefix}weight_rsi",
            weights[0],
            draft_weights[0] if len(draft_weights) > 0 else _UNSET,
        )
        weight_bb = _state_value(
            f"{prefix}weight_bb",
            weights[1],
            draft_weights[1] if len(draft_weights) > 1 else _UNSET,
        )
        weight_zscore = max(0.0, 1.0 - weight_rsi - weight_bb)
        weights = [weight_rsi, weight_bb, weight_zscore]
        weighted_threshold = _state_value(
            f"{prefix}weighted_threshold",
            defaults["weighted_threshold"],
            draft_params.get("weighted_threshold", _UNSET),
        )

    return {
        "rsi_period": rsi_period,
        "rsi_oversold": rsi_oversold,
        "rsi_overbought": rsi_overbought,
        "bb_period": bb_period,
        "bb_std": bb_std,
        "zscore_lookback": zscore_lookback,
        "zscore_threshold": zscore_threshold,
        "combination_method": combination_method,
        "weights": weights,
        "weighted_threshold": weighted_threshold,
    }


def _build_strategy_params(strategy_name: str, key_prefix: str, draft_params: Dict) -> Dict:
    """Build strategy parameters for a given strategy name."""
    prefix = f"{key_prefix}{strategy_name}_"
    if strategy_name == "trend":
        return _build_trend_params(prefix, draft_params)
    if strategy_name == "meanrev":
        return _build_meanrev_params(prefix, draft_params)
    return {}


def _build_strategies_from_state(
    key_prefix: str,
    draft_config: Dict,
) -> Tuple[List[str], Dict[str, Dict], List[str]]:
    """Build strategy configs and validation errors from session state."""
    selected_strategies = _get_selected_strategies(key_prefix, draft_config)
    errors: List[str] = []
    if not selected_strategies:
        errors.append("At least one strategy must be selected")
    if len(selected_strategies) > 1 and "passthrough" in selected_strategies:
        errors.append("Passthrough strategy cannot be combined with other strategies")

    strategies_config: Dict[str, Dict] = {}
    draft_strategies = draft_config.get("strategies", {})
    for strategy_name in selected_strategies:
        draft_params = draft_strategies.get(strategy_name, {}).get("params", {})
        params = _build_strategy_params(strategy_name, key_prefix, draft_params)
        strategies_config[strategy_name] = {"params": params}

    return selected_strategies, strategies_config, errors


def _build_meta_allocator_from_state(
    key_prefix: str,
    selected_strategies: List[str],
    draft_config: Dict,
) -> Tuple[Dict, List[str]]:
    """Build meta allocator config from state/draft."""
    if len(selected_strategies) <= 1:
        return None, []

    draft_meta = draft_config.get("meta_allocator")
    allocator_type = _state_value(
        f"{key_prefix}meta_allocator_type",
        meta.DEFAULT_META_ALLOCATOR_TYPE,
        draft_meta.get("type", _UNSET) if draft_meta else _UNSET,
    )
    errors: List[str] = []
    params: Dict = {}

    if allocator_type == "fixed_weight":
        weights: Dict[str, float] = {}
        remaining = 100.0
        n_strategies = len(selected_strategies)
        draft_weights = {}
        if draft_meta:
            draft_weights = draft_meta.get("params", {}).get("weights", {})
        for i, strategy_name in enumerate(selected_strategies):
            if i == n_strategies - 1:
                weight_pct = remaining
            else:
                default_weight = (100.0 / n_strategies) if n_strategies else 0.0
                fallback_weight = draft_weights.get(strategy_name, _UNSET)
                fallback_pct = _UNSET
                if fallback_weight is not _UNSET:
                    fallback_pct = round(fallback_weight * 100.0, 2)
                    if fallback_pct > remaining:
                        fallback_pct = remaining
                weight_pct = _state_value(
                    f"{key_prefix}meta_fixed_weight_weight_{strategy_name}",
                    min(default_weight, remaining),
                    fallback_pct,
                )
                if weight_pct > remaining:
                    weight_pct = remaining
            weights[strategy_name] = round(weight_pct / 100.0, 4)
            remaining = round(remaining - weight_pct, 2)

        params = {"weights": weights}
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            errors.append(f"Strategy weights must sum to 100% (currently {total:.0%})")

    elif allocator_type == "risk_parity":
        vol_lookback = _state_value(
            f"{key_prefix}meta_risk_parity_vol_lookback",
            meta_risk_parity_ui.DEFAULTS["vol_lookback"],
            draft_meta.get("params", {}).get("vol_lookback", _UNSET) if draft_meta else _UNSET,
        )
        params = {"vol_lookback": vol_lookback}

    return {"type": allocator_type, "params": params}, errors


def _build_asset_allocator_from_state(
    key_prefix: str,
    draft_config: Dict,
) -> Tuple[Dict, int, List[str]]:
    """Build asset allocator config from state/draft."""
    draft_asset = draft_config.get("asset_allocator")
    allocator_type = _state_value(
        f"{key_prefix}asset_allocator_type",
        allocator.DEFAULT_ALLOCATOR_TYPE,
        draft_asset.get("type", _UNSET) if draft_asset else _UNSET,
    )
    params: Dict = {}
    if allocator_type == "inverse_vol_v1":
        lookback = _state_value(
            f"{key_prefix}allocator_inverse_vol_v1_lookback",
            inverse_vol_ui.DEFAULT_LOOKBACK,
            draft_asset.get("params", {}).get("lookback", _UNSET) if draft_asset else _UNSET,
        )
        params = {"lookback": lookback}

    vol_window = params.get("lookback") or params.get("vol_window")
    return {"type": allocator_type, "params": params}, vol_window, []


def _build_risk_from_state(
    key_prefix: str,
    universe: List[str],
    draft_config: Dict,
) -> Tuple[Dict[str, object], List[str]]:
    """Build risk caps and vol targeting config from state/draft."""
    cap_mode = _state_value(
        f"{key_prefix}cap_mode",
        "both",
        draft_config.get("cap_mode", _UNSET),
    )
    max_weight_per_asset = _state_value(
        f"{key_prefix}max_weight_per_asset",
        risk.DEFAULT_MAX_WEIGHT_PER_ASSET,
        draft_config.get("max_weight_per_asset", _UNSET),
    )
    use_sector_cap = _state_value(
        f"{key_prefix}use_sector_cap",
        False,
        draft_config.get("max_sector_weight", _UNSET) is not None,
    )
    max_sector_weight = _state_value(
        f"{key_prefix}max_sector_weight",
        risk.DEFAULT_MAX_SECTOR_WEIGHT,
        draft_config.get("max_sector_weight", _UNSET),
    ) if use_sector_cap else None
    min_assets_held = _state_value(
        f"{key_prefix}min_assets_held",
        risk.DEFAULT_MIN_ASSETS_HELD,
        draft_config.get("min_assets_held", _UNSET),
    )

    target_vol = _state_value(
        f"{key_prefix}target_vol",
        risk.DEFAULT_TARGET_VOL,
        draft_config.get("target_vol", _UNSET),
    )
    vol_lookback = _state_value(
        f"{key_prefix}vol_lookback",
        risk.DEFAULT_VOL_LOOKBACK,
        draft_config.get("vol_lookback", _UNSET),
    )
    min_leverage = _state_value(
        f"{key_prefix}min_leverage",
        risk.DEFAULT_MIN_LEVERAGE,
        draft_config.get("min_leverage", _UNSET),
    )
    max_leverage = _state_value(
        f"{key_prefix}max_leverage",
        risk.DEFAULT_MAX_LEVERAGE,
        draft_config.get("max_leverage", _UNSET),
    )

    errors = validate_risk_caps_widget(
        min_assets_held=min_assets_held,
        universe=universe,
        max_weight_per_asset=max_weight_per_asset,
        max_sector_weight=max_sector_weight,
    )
    errors.extend(validate_volatility_targeting_widget(min_leverage, max_leverage))

    return {
        "max_weight_per_asset": max_weight_per_asset,
        "max_sector_weight": max_sector_weight,
        "min_assets_held": min_assets_held,
        "cap_mode": cap_mode,
        "target_vol": target_vol,
        "vol_lookback": vol_lookback,
        "min_leverage": min_leverage,
        "max_leverage": max_leverage,
    }, errors


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
    drafts: Dict[str, Dict] = st.session_state.portfolio_drafts

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
            draft_config = drafts.get(portfolio["id"], {})
            selected_strategies = _get_selected_strategies(key_prefix, draft_config)
            layer_label = _select_layer(expander, portfolio["id"])
            selected_layer_key = LABEL_TO_KEY.get(layer_label, DEFAULT_LAYER_KEY)

            if selected_layer_key == "strategy":
                _seed_strategy_state(key_prefix, draft_config, selected_strategies)
                strat_config = strategies.render(
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                )
                selected_strategies = strat_config["selected_strategies"]
                strategies_config = strat_config["strategies"]
                strategy_errors = strat_config["errors"]
            else:
                selected_strategies, strategies_config, strategy_errors = _build_strategies_from_state(
                    key_prefix,
                    draft_config,
                )

            if selected_layer_key == "meta_allocator":
                _seed_meta_state(key_prefix, draft_config, selected_strategies)
                meta_config = meta.render(
                    selected_strategies,
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                )
                if len(selected_strategies) <= 1:
                    expander.info("Meta allocator activates when multiple strategies are selected.")
                meta_allocator_config = meta_config["meta_allocator"]
                meta_errors = meta_config["errors"]
            else:
                meta_allocator_config, meta_errors = _build_meta_allocator_from_state(
                    key_prefix,
                    selected_strategies,
                    draft_config,
                )

            if selected_layer_key == "asset_allocator":
                _seed_asset_allocator_state(key_prefix, draft_config)
                allocator_config = allocator.render(
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                    expand_params=True,
                )
                asset_allocator_config = allocator_config["asset_allocator"]
                vol_window = allocator_config["vol_window"]
                allocator_errors = allocator_config["errors"]
            else:
                asset_allocator_config, vol_window, allocator_errors = _build_asset_allocator_from_state(
                    key_prefix,
                    draft_config,
                )

            if selected_layer_key == "risk_caps":
                _seed_risk_state(key_prefix, draft_config)
                risk_config = risk.render(
                    universe,
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                    show_risk_caps=True,
                    show_vol_targeting=False,
                    expand_risk_caps=True,
                )
                risk_errors = risk_config["errors"]
            elif selected_layer_key == "vol_targeting":
                _seed_risk_state(key_prefix, draft_config)
                risk_config = risk.render(
                    universe,
                    key_prefix=key_prefix,
                    container=expander,
                    show_header=False,
                    show_risk_caps=False,
                    show_vol_targeting=True,
                    expand_vol_targeting=True,
                )
                risk_errors = risk_config["errors"]
            else:
                risk_config, risk_errors = _build_risk_from_state(
                    key_prefix,
                    universe,
                    draft_config,
                )

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
            drafts[portfolio["id"]] = _merge_draft_config(
                draft_config,
                configs[portfolio["id"]],
                selected_strategies,
            )

            if expander.button(
                "Remove Portfolio",
                key=f"{portfolio['id']}_remove",
            ):
                remove_id = portfolio["id"]

    if remove_id:
        st.session_state.portfolios = [p for p in portfolios if p["id"] != remove_id]
        if remove_id in st.session_state.portfolio_drafts:
            del st.session_state.portfolio_drafts[remove_id]
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
