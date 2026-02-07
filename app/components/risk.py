"""Risk caps and volatility targeting component."""

import streamlit as st
from typing import List, Optional

from app.utils.validators import validate_risk_caps_widget, validate_volatility_targeting_widget

# ==================== DEFAULTS ====================
DEFAULT_MAX_WEIGHT_PER_ASSET = 0.25
DEFAULT_MAX_SECTOR_WEIGHT = 0.6
DEFAULT_MIN_ASSETS_HELD = 1
DEFAULT_TARGET_VOL = 0.10
DEFAULT_VOL_LOOKBACK = 60
DEFAULT_MIN_LEVERAGE = 0.0
DEFAULT_MAX_LEVERAGE = 2.0

BOUNDS = {
    "max_weight_per_asset": (0.05, 1.0),
    "max_sector_weight": (0.1, 1.0),
    "min_assets_held": (1, 10),
    "target_vol": (0.01, 0.50),
    "vol_lookback": (10, 252),
    "min_leverage": (0.0, 3.0),
    "max_leverage": (0.5, 5.0),
}


def render(
    universe: List[str],
    key_prefix: str = "",
    container: Optional[st.delta_generator.DeltaGenerator] = None,
    show_header: bool = True,
    show_risk_caps: bool = True,
    show_vol_targeting: bool = True,
    expand_risk_caps: bool = False,
    expand_vol_targeting: bool = False,
) -> dict:
    """
    Render risk caps and volatility targeting UI.
    
    Args:
        universe: List of selected assets (for validation)
        show_risk_caps: Whether to render the risk caps section
        show_vol_targeting: Whether to render the volatility targeting section
        expand_risk_caps: Expand risk caps section when rendered
        expand_vol_targeting: Expand vol targeting section when rendered
        
    Returns:
        dict with keys:
            - max_weight_per_asset: float
            - max_sector_weight: float or None
            - min_assets_held: int
            - cap_mode: str
            - target_vol: float
            - vol_lookback: int
            - min_leverage: float
            - max_leverage: float
            - errors: list of validation error strings
    """
    container = container or st.sidebar
    errors = []

    def _state_value(key: str, default):
        return st.session_state.get(key, default)
    
    # ==================== RISK CAPS ====================
    if show_risk_caps:
        cap_container = container.expander("Risk Caps", expanded=expand_risk_caps)
        with cap_container:
            # Cap Mode Selector
            cap_container.markdown("**Risk Cap Enforcement Mode**")
            cap_mode = cap_container.radio(
                "When to apply risk caps:",
                options=["both", "pre_leverage", "post_leverage"],
                index=0,
                help="Controls when risk caps are enforced relative to volatility targeting",
                format_func=lambda x: {
                    "both": "Both (Before & After Leverage) - Most Conservative",
                    "pre_leverage": "Pre-Leverage Only (Caps before vol targeting)",
                    "post_leverage": "Post-Leverage Only (Caps after vol targeting)"
                }[x],
                key=f"{key_prefix}cap_mode",
            )
            
            # Show explanation based on selected mode
            if cap_mode == "both":
                cap_container.info("ℹ️ Caps applied before and after vol targeting. Most conservative - ensures limits never violated.")
            elif cap_mode == "pre_leverage":
                cap_container.warning("⚠️ Caps only before leverage. Final weights may exceed caps (e.g., 25% → 50% at 2× leverage).")
            else:
                cap_container.warning("⚠️ Caps only after leverage. Pre-leverage weights may exceed caps before scaling.")
            
            # Risk Cap Parameters
            max_weight_per_asset = cap_container.slider(
                "Max Weight per Asset",
                min_value=BOUNDS["max_weight_per_asset"][0],
                max_value=BOUNDS["max_weight_per_asset"][1],
                value=DEFAULT_MAX_WEIGHT_PER_ASSET,
                step=0.05,
                format="%.2f",
                help="Maximum allocation to any single asset (e.g., 0.25 = 25%)",
                key=f"{key_prefix}max_weight_per_asset",
            )
            
            use_sector_cap = cap_container.checkbox(
                "Enable Sector Weight Cap",
                value=False,
                help="Limit total exposure to any sector",
                key=f"{key_prefix}use_sector_cap",
            )
            
            if use_sector_cap:
                max_sector_weight = cap_container.slider(
                    "Max Sector Weight",
                    min_value=BOUNDS["max_sector_weight"][0],
                    max_value=BOUNDS["max_sector_weight"][1],
                    value=DEFAULT_MAX_SECTOR_WEIGHT,
                    step=0.05,
                    format="%.2f",
                    help="Maximum allocation to any sector (e.g., 0.6 = 60%)",
                    key=f"{key_prefix}max_sector_weight",
                )
            else:
                max_sector_weight = None
            
            min_assets_held = cap_container.number_input(
                "Min Assets Held",
                min_value=BOUNDS["min_assets_held"][0],
                max_value=BOUNDS["min_assets_held"][1],
                value=DEFAULT_MIN_ASSETS_HELD,
                step=1,
                help="Minimum number of assets to hold in the portfolio",
                key=f"{key_prefix}min_assets_held",
            )
            
            risk_caps_errors = validate_risk_caps_widget(
                min_assets_held=min_assets_held,
                universe=universe,
                max_weight_per_asset=max_weight_per_asset,
                max_sector_weight=max_sector_weight,
            )
            if risk_caps_errors:
                for error in risk_caps_errors:
                    cap_container.error(f"⚠️ {error}")
                errors.extend(risk_caps_errors)
    else:
        cap_mode = _state_value(f"{key_prefix}cap_mode", "both")
        max_weight_per_asset = _state_value(
            f"{key_prefix}max_weight_per_asset",
            DEFAULT_MAX_WEIGHT_PER_ASSET,
        )
        use_sector_cap = _state_value(f"{key_prefix}use_sector_cap", False)
        max_sector_weight = _state_value(
            f"{key_prefix}max_sector_weight",
            DEFAULT_MAX_SECTOR_WEIGHT,
        ) if use_sector_cap else None
        min_assets_held = _state_value(
            f"{key_prefix}min_assets_held",
            DEFAULT_MIN_ASSETS_HELD,
        )
        risk_caps_errors = validate_risk_caps_widget(
            min_assets_held=min_assets_held,
            universe=universe,
            max_weight_per_asset=max_weight_per_asset,
            max_sector_weight=max_sector_weight,
        )
        errors.extend(risk_caps_errors)
    
    # ==================== VOLATILITY TARGETING ====================
    if show_vol_targeting:
        vol_container = container.expander("Volatility Targeting", expanded=expand_vol_targeting)
        with vol_container:
            target_vol = vol_container.slider(
                "Target Volatility",
                min_value=BOUNDS["target_vol"][0],
                max_value=BOUNDS["target_vol"][1],
                value=DEFAULT_TARGET_VOL,
                step=0.01,
                format="%.2f",
                help="Target annual volatility (e.g., 0.10 = 10% annualized)",
                key=f"{key_prefix}target_vol",
            )
            
            vol_lookback = vol_container.slider(
                "Vol Lookback (trading days)",
                min_value=BOUNDS["vol_lookback"][0],
                max_value=BOUNDS["vol_lookback"][1],
                value=DEFAULT_VOL_LOOKBACK,
                step=10,
                help="Rolling window for volatility calculation in trading days",
                key=f"{key_prefix}vol_lookback",
            )
            
            col1, col2 = vol_container.columns(2)
            
            min_leverage = col1.number_input(
                "Min Leverage",
                min_value=BOUNDS["min_leverage"][0],
                max_value=BOUNDS["min_leverage"][1],
                value=DEFAULT_MIN_LEVERAGE,
                step=0.1,
                format="%.1f",
                help="Minimum portfolio leverage",
                key=f"{key_prefix}min_leverage",
            )
            
            max_leverage = col2.number_input(
                "Max Leverage",
                min_value=BOUNDS["max_leverage"][0],
                max_value=BOUNDS["max_leverage"][1],
                value=DEFAULT_MAX_LEVERAGE,
                step=0.1,
                format="%.1f",
                help="Maximum portfolio leverage",
                key=f"{key_prefix}max_leverage",
            )
            
            volatility_errors = validate_volatility_targeting_widget(min_leverage, max_leverage)
            if volatility_errors:
                for error in volatility_errors:
                    vol_container.error(f"⚠️ {error}")
                errors.extend(volatility_errors)
    else:
        target_vol = _state_value(f"{key_prefix}target_vol", DEFAULT_TARGET_VOL)
        vol_lookback = _state_value(f"{key_prefix}vol_lookback", DEFAULT_VOL_LOOKBACK)
        min_leverage = _state_value(f"{key_prefix}min_leverage", DEFAULT_MIN_LEVERAGE)
        max_leverage = _state_value(f"{key_prefix}max_leverage", DEFAULT_MAX_LEVERAGE)
        volatility_errors = validate_volatility_targeting_widget(min_leverage, max_leverage)
        errors.extend(volatility_errors)
    
    return {
        'max_weight_per_asset': max_weight_per_asset,
        'max_sector_weight': max_sector_weight,
        'min_assets_held': min_assets_held,
        'cap_mode': cap_mode,
        'target_vol': target_vol,
        'vol_lookback': vol_lookback,
        'min_leverage': min_leverage,
        'max_leverage': max_leverage,
        'errors': errors,
    }
