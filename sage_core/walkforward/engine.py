"""Walkforward backtesting engine."""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional

from sage_core.data.loader import load_universe
from sage_core.strategies.passthrough_v1 import PassthroughStrategy
from sage_core.allocators.inverse_vol_v1 import compute_inverse_vol_weights
from sage_core.portfolio.constructor import align_asset_returns, build_portfolio_raw_returns
from sage_core.portfolio.risk_caps import apply_all_risk_caps
from sage_core.portfolio.vol_targeting import apply_vol_targeting
from sage_core.metrics.performance import calculate_all_metrics
from sage_core.utils.constants import SECTOR_MAP
from sage_core.utils.trading_calendar import get_warmup_start_date, get_first_trading_day_on_or_after
from sage_core.utils.warmup import calculate_warmup_period

logger = logging.getLogger(__name__)


def run_system_walkforward(
    universe: list[str],
    start_date: str,
    end_date: str,
    # Risk caps
    max_weight_per_asset: float = 0.25,
    max_sector_weight: Optional[float] = None,
    min_assets_held: int = 1,
    cap_mode: str = "both",
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
        cap_mode: When to apply risk caps (default: "both")
            - "both": Apply caps before and after vol targeting (most conservative)
            - "pre_leverage": Apply caps only before vol targeting
            - "post_leverage": Apply caps only after vol targeting
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
            - warmup_info: Warmup period breakdown
            - warmup_start_date: Actual start date for data loading
    
    Example:
        >>> result = run_system_walkforward(
        ...     universe=["SPY", "QQQ", "IWM"],
        ...     start_date="2020-01-01",
        ...     end_date="2021-12-31",
        ... )
        >>> print(f"Sharpe: {result['metrics']['sharpe_ratio']:.2f}")
    """
    # Calculate warmup period using centralized function
    # For now, strategy_warmup=0 since we only have Passthrough (no warmup needed)
    # In Steps 3B.2/3B.3, this will be dynamic based on selected strategy
    strategy_warmup = 0  # Passthrough has 0 warmup
    warmup_info = calculate_warmup_period(
        vol_window=vol_window,
        vol_lookback=vol_lookback,
        strategy_warmup=strategy_warmup,
    )
    warmup_trading_days = warmup_info["total_trading_days"]
    
    logger.info(f"Warmup period: {warmup_trading_days} trading days ({warmup_info['description']})")
    
    # Get first trading day on or after user's start_date
    # (in case they specified a weekend/holiday)
    actual_start_date = get_first_trading_day_on_or_after(start_date)
    if actual_start_date != start_date:
        logger.info(f"Adjusted start_date from {start_date} to {actual_start_date} (first trading day)")
    
    # Calculate exact warmup start date using NYSE trading calendar
    # This goes back exactly warmup_trading_days from actual_start_date
    warmup_start_date = get_warmup_start_date(
        start_date=actual_start_date,
        warmup_trading_days=warmup_trading_days,
    )
    
    logger.info(f"Loading data from {warmup_start_date} to {end_date}")
    
    # Step 1: Load data including warmup period
    ohlcv_data = load_universe(
        universe=universe,
        start_date=warmup_start_date,  # Load extra data for warmup
        end_date=end_date,
    )
    
    # Step 2: Run strategy (adds meta_raw_ret column to each DataFrame)
    strategy_data = PassthroughStrategy().run(ohlcv_data)
    
    # Step 3: Align asset returns (uses meta_raw_ret from strategy)
    asset_returns = align_asset_returns(asset_data=strategy_data)
    
    # Validate cap_mode
    valid_cap_modes = ["both", "pre_leverage", "post_leverage"]
    if cap_mode not in valid_cap_modes:
        raise ValueError(
            f"Invalid cap_mode: {cap_mode}. Must be one of {valid_cap_modes}"
        )
    
    # Step 4: Compute allocations (inverse vol)
    allocated_weights = compute_inverse_vol_weights(
        returns_wide=asset_returns,
        lookback=vol_window,
    )
    
    # Step 5: Apply risk caps (pre-leverage)
    if cap_mode in ["pre_leverage", "both"]:
        logger.info(f"Applying pre-leverage risk caps (mode: {cap_mode})")
        capped_weights = apply_all_risk_caps(
            weights_df=allocated_weights,
            sector_map=SECTOR_MAP,
            max_weight_per_asset=max_weight_per_asset,
            max_sector_weight=max_sector_weight,
            min_assets_held=min_assets_held,
        )
    else:
        logger.info(f"Skipping pre-leverage risk caps (mode: {cap_mode})")
        capped_weights = allocated_weights
    
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
    
    # Step 7b: Reapply risk caps after vol targeting (post-leverage)
    # CRITICAL: Vol targeting scales weights by leverage (can be >1.0)
    # This means a 0.25 cap becomes 0.50 at 2× leverage, violating limits
    # We reapply caps to ensure absolute exposure limits are always respected
    if cap_mode in ["post_leverage", "both"]:
        logger.info(f"Applying post-leverage risk caps (mode: {cap_mode})")
        final_weights = apply_all_risk_caps(
            weights_df=vol_targeted_weights,
            sector_map=SECTOR_MAP,
            max_weight_per_asset=max_weight_per_asset,
            max_sector_weight=max_sector_weight,
            min_assets_held=min_assets_held,
        )
    else:
        logger.info(f"Skipping post-leverage risk caps (mode: {cap_mode})")
        final_weights = vol_targeted_weights
    
    # Step 8: Build final portfolio returns (with post-leverage caps applied)
    final_portfolio_returns = build_portfolio_raw_returns(
        returns_wide=asset_returns,
        weights_wide=final_weights,
    )
    
    # Slice results to start at actual_start_date (first trading day on or after user's start_date)
    # This ensures equity curve starts exactly at the first trading day
    # All warmup period data is excluded from final results
    
    # Use actual_start_date (which is the first trading day on or after user's start_date)
    start_date_ts = pd.Timestamp(actual_start_date)
    
    # Step 1: Filter by date - remove warmup period
    valid_mask = final_weights.index >= start_date_ts
    clean_index = final_weights.index[valid_mask]
    
    if len(clean_index) == 0:
        raise ValueError(
            f"No data available at or after start_date {actual_start_date}. "
            f"First available date is {final_weights.index[0].strftime('%Y-%m-%d')}."
        )
    
    logger.info(f"Results start at {clean_index[0].strftime('%Y-%m-%d')} (user requested {start_date})")
    
    # Apply date filter to all outputs
    final_portfolio_returns_filtered = final_portfolio_returns.loc[clean_index]
    final_weights_filtered = final_weights.loc[clean_index]
    vol_targeted_weights_filtered = vol_targeted_weights.loc[clean_index]
    asset_returns_filtered = asset_returns.loc[clean_index]
    capped_weights_filtered = capped_weights.loc[clean_index]
    
    # Step 2: Filter out rows with NaN weights
    # This handles IPOs, delisted stocks, or data gaps that can appear after start_date
    # Drop rows where ANY weight is NaN (incomplete data for that day)
    nan_mask = ~final_weights_filtered.isna().any(axis=1)
    clean_index_no_nan = final_weights_filtered.index[nan_mask]
    
    if len(clean_index_no_nan) == 0:
        raise ValueError(
            f"No valid data after filtering NaN weights. "
            f"All rows after {actual_start_date} have missing data. "
            f"Check that all tickers in universe have data for the requested period."
        )
    
    rows_dropped = len(clean_index) - len(clean_index_no_nan)
    if rows_dropped > 0:
        logger.info(f"Dropped {rows_dropped} rows with NaN weights (IPOs, delisted stocks, or data gaps)")
    
    # Apply NaN filter to all outputs to ensure alignment
    final_portfolio_returns_clean = final_portfolio_returns_filtered.loc[clean_index_no_nan]
    final_weights_clean = final_weights_filtered.loc[clean_index_no_nan]
    vol_targeted_weights_clean = vol_targeted_weights_filtered.loc[clean_index_no_nan]
    asset_returns_clean = asset_returns_filtered.loc[clean_index_no_nan]
    capped_weights_clean = capped_weights_filtered.loc[clean_index_no_nan]
    
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
        "warmup_info": warmup_info,  # Warmup period breakdown
        "warmup_start_date": warmup_start_date,  # Actual start date for data loading
    }
