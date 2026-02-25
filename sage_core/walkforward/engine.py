"""Walkforward backtesting engine.

Pipeline flow:
    1. Load OHLCV data
    2. Run strategies → intent/signals
    3. ExecutionModule.validate_intent() → structural check
    4. ExecutionModule.compute_meta_raw_returns() → lagged returns
    5. Active mask (align_asset_returns) → wide DataFrame
    6. Meta allocator (if multi-strategy) → combined returns
    7. Asset allocator → target weights at t (from raw returns ≤ t)
    8. Risk caps → capped target weights at t
    9. Vol targeting → scaled target weights at t
    10. ExecutionModule.apply_delay() → held weights at t+1
    11. Portfolio returns → equity curve → metrics
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, Any, Optional

from sage_core.data.loader import load_universe
from sage_core.strategies import get_strategy
from sage_core.meta import get_meta_allocator
from sage_core.execution.policy import ExecutionPolicy
from sage_core.execution.module import ExecutionModule
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
    # Strategy configuration
    strategies: Optional[Dict[str, Dict[str, Any]]] = None,
    meta_allocator: Optional[Dict[str, Any]] = None,
    # Execution policy
    execution_delay_days: int = 1,
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
    
    This orchestrates the full pipeline with centralized execution timing.
    All components compute at time t using data <= t. The ExecutionModule
    applies the single execution delay (target weights at t -> held weights
    at t+1).
    
    Args:
        universe: List of symbols to trade
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        strategies: Strategy configurations
        meta_allocator: Meta allocator configuration
        execution_delay_days: Execution delay in trading days (default: 1)
        max_weight_per_asset: Maximum weight per asset (default: 0.25)
        max_sector_weight: Maximum weight per sector (default: None)
        min_assets_held: Minimum number of assets (default: 1)
        cap_mode: When to apply risk caps (default: "both")
        target_vol: Target annual volatility (default: 0.10)
        vol_lookback: Lookback for vol targeting (default: 60)
        min_leverage: Minimum leverage (default: 0.0)
        max_leverage: Maximum leverage (default: 2.0)
        vol_window: Window for inverse vol calculation (default: 60)
    
    Returns:
        Dictionary with:
            - returns: Portfolio returns series
            - equity_curve: Cumulative equity series
            - weights: Final weights DataFrame (held weights, post-delay)
            - vol_targeted_weights: Pre-delay weights after vol targeting
            - raw_weights: Pre-vol-targeting weights
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
    # Default to passthrough if no strategies specified (backward compatible)
    if strategies is None:
        strategies = {'passthrough': {'params': {}}}
    
    # Create ExecutionPolicy and ExecutionModule
    execution_policy = ExecutionPolicy(execution_delay_days=execution_delay_days)
    execution_module = ExecutionModule(execution_policy)
    
    # Calculate warmup period
    warmup_info = calculate_warmup_period(
        strategies=strategies,
        meta_allocator=meta_allocator,
        vol_window=vol_window,
        vol_lookback=vol_lookback,
        execution_delay_days=execution_delay_days,
    )
    warmup_trading_days = warmup_info["total_trading_days"]
    
    logger.info(f"Warmup period: {warmup_trading_days} trading days ({warmup_info['description']})")
    
    # Get first trading day on or after user's start_date
    actual_start_date = get_first_trading_day_on_or_after(start_date)
    if actual_start_date != start_date:
        logger.info(f"Adjusted start_date from {start_date} to {actual_start_date} (first trading day)")
    
    # Calculate exact warmup start date using NYSE trading calendar
    warmup_start_date = get_warmup_start_date(
        start_date=actual_start_date,
        warmup_trading_days=warmup_trading_days,
    )
    
    logger.info(f"Loading data from {warmup_start_date} to {end_date}")
    
    # Step 1: Load data including warmup period
    ohlcv_data = load_universe(
        universe=universe,
        start_date=warmup_start_date,
        end_date=end_date,
    )
    
    # Step 2: Run strategies → produce signals (intent at time t)
    strategy_instances = {}
    strategy_results = {}
    
    for strategy_name, config in strategies.items():
        params = config.get('params', {})
        strategy_instances[strategy_name] = get_strategy(strategy_name, params)
        
        logger.info(f"Running strategy: {strategy_name}")
        strategy_results[strategy_name] = strategy_instances[strategy_name].run(ohlcv_data)
    
    # Step 3: Extract intent and compute realized returns via ExecutionModule
    # For each strategy, extract signals and raw returns, then use
    # ExecutionModule.compute_meta_raw_returns() for proper execution lag.
    strategy_data_with_returns = {}
    
    for strategy_name, strategy_result in strategy_results.items():
        intent_by_asset = {}
        raw_returns_by_asset = {}
        
        for symbol, df in strategy_result.items():
            intent_by_asset[symbol] = df['signal']
            raw_returns_by_asset[symbol] = ohlcv_data[symbol]['raw_ret']
        
        # Validate intent structure
        strategy_instance = strategy_instances[strategy_name]
        execution_module.validate_intent(
            intent_by_asset,
            intent_type=strategy_instance.signal_type,
        )
        
        # Compute realized returns with execution delay
        meta_raw_returns = execution_module.compute_meta_raw_returns(
            intent_by_asset=intent_by_asset,
            raw_returns_by_asset=raw_returns_by_asset,
        )
        
        # Store results with meta_raw_ret column
        strategy_data = {}
        for symbol, df in strategy_result.items():
            df_copy = df.copy()
            df_copy['meta_raw_ret'] = meta_raw_returns[symbol]
            strategy_data[symbol] = df_copy
        
        strategy_data_with_returns[strategy_name] = strategy_data
    
    # Step 4: Combine strategies using meta allocator (if multiple strategies)
    if len(strategies) == 1:
        logger.info("Single strategy detected - skipping meta allocator")
        strategy_name = list(strategies.keys())[0]
        combined_strategy_data = strategy_data_with_returns[strategy_name]
    else:
        logger.info(f"Multiple strategies detected ({len(strategies)}) - using meta allocator")
        
        # Instantiate meta allocator
        if meta_allocator is None:
            weights = {name: 1.0 / len(strategies) for name in strategies.keys()}
            allocator = get_meta_allocator('fixed_weight', {'weights': weights})
            logger.info(f"Using default FixedWeightAllocator with equal weights")
        else:
            allocator_type = meta_allocator.get('type') if meta_allocator else None
            params = meta_allocator.get('params', {}) if meta_allocator else {}
            allocator = get_meta_allocator(allocator_type, params)
            logger.info(f"Using {allocator_type} meta allocator")
        
        # Combine returns for each asset
        combined_strategy_data = {}
        for symbol in ohlcv_data.keys():
            strategy_returns = {
                name: results[symbol]['meta_raw_ret']
                for name, results in strategy_data_with_returns.items()
            }
            
            result = allocator.allocate(strategy_returns)
            
            df = ohlcv_data[symbol].copy()
            df['meta_raw_ret'] = result['combined_returns']
            combined_strategy_data[symbol] = df
    
    # Step 5: Align asset returns (active mask)
    asset_returns = align_asset_returns(asset_data=combined_strategy_data)
    
    # Validate cap_mode
    valid_cap_modes = ["both", "pre_leverage", "post_leverage"]
    if cap_mode not in valid_cap_modes:
        raise ValueError(
            f"Invalid cap_mode: {cap_mode}. Must be one of {valid_cap_modes}"
        )
    
    # Step 6: Compute allocations (target weights at t from raw returns <= t)
    allocated_weights = compute_inverse_vol_weights(
        returns_wide=asset_returns,
        lookback=vol_window,
    )
    
    # Step 7: Apply risk caps (pre-leverage) — target weight transforms
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
    
    # Step 8: Build portfolio returns (before vol targeting)
    raw_portfolio_returns = build_portfolio_raw_returns(
        returns_wide=asset_returns,
        weights_wide=capped_weights,
    )
    
    # Mask returns where weights are NaN (warmup period)
    weight_is_nan_mask = capped_weights.isna().any(axis=1)
    raw_portfolio_returns_masked = raw_portfolio_returns.copy()
    raw_portfolio_returns_masked[weight_is_nan_mask] = np.nan
    
    # Step 9: Apply volatility targeting (target weight transform at t)
    vol_targeted_weights = apply_vol_targeting(
        portfolio_returns=raw_portfolio_returns_masked,
        weights_df=capped_weights,
        target_vol=target_vol,
        lookback=vol_lookback,
        min_leverage=min_leverage,
        max_leverage=max_leverage,
    )
    
    # Step 9b: Reapply risk caps after vol targeting (post-leverage)
    if cap_mode in ["post_leverage", "both"]:
        logger.info(f"Applying post-leverage risk caps (mode: {cap_mode})")
        target_weights = apply_all_risk_caps(
            weights_df=vol_targeted_weights,
            sector_map=SECTOR_MAP,
            max_weight_per_asset=max_weight_per_asset,
            max_sector_weight=max_sector_weight,
            min_assets_held=min_assets_held,
        )
    else:
        logger.info(f"Skipping post-leverage risk caps (mode: {cap_mode})")
        target_weights = vol_targeted_weights
    
    # Step 10: ExecutionModule.apply_delay() → held weights at t+1
    # This is the SINGLE place where the execution delay is applied to weights.
    final_weights = execution_module.apply_delay(target_weights)
    
    # Step 11: Build final portfolio returns (with held weights)
    final_portfolio_returns = build_portfolio_raw_returns(
        returns_wide=asset_returns,
        weights_wide=final_weights,
    )
    
    # Slice results to start at actual_start_date
    start_date_ts = pd.Timestamp(actual_start_date)
    
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
    
    # Filter out rows with NaN weights (IPOs, delisted, data gaps, execution delay)
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
        logger.info(f"Dropped {rows_dropped} rows with NaN weights (warmup, delay, or data gaps)")
    
    # Apply NaN filter to all outputs
    final_portfolio_returns_clean = final_portfolio_returns_filtered.loc[clean_index_no_nan]
    final_weights_clean = final_weights_filtered.loc[clean_index_no_nan]
    vol_targeted_weights_clean = vol_targeted_weights_filtered.loc[clean_index_no_nan]
    asset_returns_clean = asset_returns_filtered.loc[clean_index_no_nan]
    capped_weights_clean = capped_weights_filtered.loc[clean_index_no_nan]
    
    # Step 12: Build equity curve (starting at 100)
    equity_curve = (1 + final_portfolio_returns_clean).cumprod() * 100
    
    # Calculate drawdown series for charting
    running_max = equity_curve.expanding().max()
    drawdown_series = (equity_curve - running_max) / running_max
    
    # Step 13: Calculate metrics
    metrics = calculate_all_metrics(
        returns=final_portfolio_returns_clean,
        equity_curve=equity_curve,
        weights_df=final_weights_clean,
        returns_df=asset_returns_clean,
    )
    
    return {
        "returns": final_portfolio_returns_clean,
        "equity_curve": equity_curve,
        "drawdown_series": drawdown_series,
        "weights": final_weights_clean,            # Held weights (post-delay)
        "vol_targeted_weights": vol_targeted_weights_clean,  # Pre-delay target weights
        "raw_weights": capped_weights_clean,        # Pre-vol-targeting weights
        "metrics": metrics,
        "asset_returns": asset_returns_clean,
        "warmup_info": warmup_info,
        "warmup_start_date": warmup_start_date,
        "strategies_used": list(strategies.keys()),
        "meta_allocator_used": (
            meta_allocator['type'] if meta_allocator else 'fixed_weight'
        ) if len(strategies) > 1 else None,
    }
