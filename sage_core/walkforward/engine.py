"""
Walkforward backtesting engine.

This module orchestrates the complete backtesting pipeline:
1. Load data
2. Run strategy
3. Compute allocations
4. Apply risk caps
5. Apply volatility targeting
6. Calculate metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

from sage_core.data.loader import load_universe
from sage_core.strategies.passthrough_v1 import run_passthrough_v1
from sage_core.allocators.inverse_vol_v1 import compute_inverse_vol_weights
from sage_core.portfolio.constructor import align_asset_returns, build_portfolio_raw_returns
from sage_core.portfolio.risk_caps import apply_all_risk_caps
from sage_core.portfolio.vol_targeting import apply_vol_targeting
from sage_core.metrics.performance import calculate_all_metrics
from sage_core.utils.constants import SECTOR_MAP


def run_system_walkforward(
    universe: list[str],
    start_date: str,
    end_date: str,
    # Risk caps
    max_weight_per_asset: float = 0.25,
    max_sector_weight: Optional[float] = None,
    min_assets_held: int = 1,
    # Vol targeting
    target_vol: float = 0.10,
    vol_lookback: int = 60,
    min_leverage: float = 0.0,
    max_leverage: float = 2.0,
    # Allocator
    vol_window: int = 60,
) -> Dict[str, Any]:
    """
    Run complete walkforward backtest.
    
    This orchestrates the full pipeline:
    1. Load OHLCV data
    2. Run passthrough strategy (adds meta_raw_ret column)
    3. Align asset returns (extracts meta_raw_ret)
    4. Compute inverse volatility weights
    5. Apply risk caps
    6. Build portfolio returns
    7. Apply volatility targeting
    8. Calculate metrics
    
    Args:
        universe: List of symbols to trade
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        max_weight_per_asset: Maximum weight per asset (default: 0.25)
        max_sector_weight: Maximum weight per sector (default: None)
        min_assets_held: Minimum number of assets (default: 1)
        target_vol: Target annual volatility (default: 0.10)
        vol_lookback: Lookback for vol targeting (default: 60)
        min_leverage: Minimum leverage (default: 0.0)
        max_leverage: Maximum leverage (default: 2.0)
        vol_window: Window for inverse vol calculation (default: 60)
    
    Returns:
        Dictionary with:
            - returns: Portfolio returns series
            - equity_curve: Cumulative equity series
            - weights: Final weights DataFrame (post-leverage caps applied)
            - vol_targeted_weights: Pre-cap weights after vol targeting (for analysis)
            - raw_weights: Pre-vol-targeting weights (post-risk-caps, pre-leverage)
            - metrics: Performance metrics dictionary
            - asset_returns: Asset returns DataFrame
    
    Example:
        >>> result = run_system_walkforward(
        ...     universe=["SPY", "QQQ", "IWM"],
        ...     start_date="2020-01-01",
        ...     end_date="2021-12-31",
        ... )
        >>> print(f"Sharpe: {result['metrics']['sharpe_ratio']:.2f}")
    """
    # Validate inputs
    if not universe or len(universe) == 0:
        raise ValueError("universe cannot be empty")
    
    # Step 1: Load data
    ohlcv_data = load_universe(
        universe=universe,
        start_date=start_date,
        end_date=end_date,
    )
    
    # Step 2: Run strategy (adds meta_raw_ret column to each DataFrame)
    strategy_data = run_passthrough_v1(ohlcv_data)
    
    # Step 3: Align asset returns (uses meta_raw_ret from strategy)
    asset_returns = align_asset_returns(asset_data=strategy_data)
    
    # Step 4: Compute allocations (inverse vol)
    allocated_weights = compute_inverse_vol_weights(
        returns_wide=asset_returns,
        lookback=vol_window,
    )
    
    # Step 5: Apply risk caps
    capped_weights = apply_all_risk_caps(
        weights_df=allocated_weights,
        sector_map=SECTOR_MAP,
        max_weight_per_asset=max_weight_per_asset,
        max_sector_weight=max_sector_weight,
        min_assets_held=min_assets_held,
    )
    
    # Step 6: Build portfolio returns (before vol targeting)
    raw_portfolio_returns = build_portfolio_raw_returns(
        returns_wide=asset_returns,
        weights_wide=capped_weights,
    )
    
    # CRITICAL: Mask returns where weights are NaN (warmup period)
    # build_portfolio_raw_returns uses sum(skipna=True), so NaN weights → 0.0 returns
    # If we pass these 0.0 returns to vol_targeting, the rolling vol window will
    # include artificial zeros, understate realized volatility, and drive leverage
    # to max cap regardless of true risk (biasing early results)
    # Solution: Set returns to NaN where any weight is NaN
    weight_is_nan_mask = capped_weights.isna().any(axis=1)
    raw_portfolio_returns_masked = raw_portfolio_returns.copy()
    raw_portfolio_returns_masked[weight_is_nan_mask] = np.nan
    
    # Step 7: Apply volatility targeting (with masked returns)
    vol_targeted_weights = apply_vol_targeting(
        portfolio_returns=raw_portfolio_returns_masked,
        weights_df=capped_weights,
        target_vol=target_vol,
        lookback=vol_lookback,
        min_leverage=min_leverage,
        max_leverage=max_leverage,
    )
    
    # Step 7b: Reapply risk caps after vol targeting
    # CRITICAL: Vol targeting scales weights by leverage (can be >1.0)
    # This means a 0.25 cap becomes 0.50 at 2× leverage, violating limits
    # We reapply caps to ensure absolute exposure limits are always respected
    # TODO (Phase 2+): Make this configurable via cap_enforcement_mode parameter
    #   - "post_leverage": Current behavior (caps apply to final portfolio)
    #   - "pre_leverage": Caps apply before leverage (current violation)
    #   - "leverage_aware": Constrain leverage to respect caps
    final_weights = apply_all_risk_caps(
        weights_df=vol_targeted_weights,
        sector_map=SECTOR_MAP,
        max_weight_per_asset=max_weight_per_asset,
        max_sector_weight=max_sector_weight,
        min_assets_held=min_assets_held,
    )
    
    # Step 8: Build final portfolio returns (with post-leverage caps applied)
    final_portfolio_returns = build_portfolio_raw_returns(
        returns_wide=asset_returns,
        weights_wide=final_weights,
    )
    
    # Drop warmup period rows
    # IMPORTANT: We filter on weights, not returns!
    # build_portfolio_raw_returns uses sum(skipna=True), so NaN weights → 0.0 returns
    # If we filtered on returns.dropna(), warmup period wouldn't be dropped
    # This would bias volatility, Sharpe, turnover, and equity curve length
    
    # Drop rows where any weight is NaN (warmup period)
    valid_weight_mask = ~final_weights.isna().any(axis=1)
    clean_index = final_weights.index[valid_weight_mask]
    
    # Apply to all outputs to ensure alignment
    final_portfolio_returns_clean = final_portfolio_returns.loc[clean_index]
    final_weights_clean = final_weights.loc[clean_index]
    vol_targeted_weights_clean = vol_targeted_weights.loc[clean_index]  # Pre-cap weights
    asset_returns_clean = asset_returns.loc[clean_index]
    capped_weights_clean = capped_weights.loc[clean_index]
    
    # Step 9: Build equity curve (starting at 100)
    equity_curve = (1 + final_portfolio_returns_clean).cumprod() * 100
    
    # Calculate drawdown series for charting
    running_max = equity_curve.expanding().max()
    drawdown_series = (equity_curve - running_max) / running_max
    
    # Step 10: Calculate metrics
    metrics = calculate_all_metrics(
        returns=final_portfolio_returns_clean,
        equity_curve=equity_curve,
        weights_df=final_weights_clean,
        returns_df=asset_returns_clean,
    )
    
    return {
        "returns": final_portfolio_returns_clean,
        "equity_curve": equity_curve,
        "drawdown_series": drawdown_series,  # Separate from metrics for charting
        "weights": final_weights_clean,  # Final weights (post-leverage caps)
        "vol_targeted_weights": vol_targeted_weights_clean,  # Pre-cap weights (for analysis)
        "raw_weights": capped_weights_clean,  # Pre-vol-targeting weights
        "metrics": metrics,
        "asset_returns": asset_returns_clean,
    }
