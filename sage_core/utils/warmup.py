"""Warmup period calculation utilities."""

from typing import Dict, Any, Optional
import logging

from sage_core.strategies import get_strategy
from sage_core.meta import get_meta_allocator

logger = logging.getLogger(__name__)

def calculate_strategy_warmup(strategies: Dict[str, Dict[str, Any]]) -> int:
    """
    Calculate maximum warmup period across all strategies.
    
    Args:
        strategies: Dict mapping strategy_name -> {'params': {...}}
    
    Returns:
        Maximum warmup period in trading days
    
    Example:
        >>> strategies = {
        ...     'trend': {'params': {}},
        ...     'meanrev': {'params': {}}
        ... }
        >>> calculate_strategy_warmup(strategies)
        253  # TrendStrategy has 253-day warmup (max)
    """
    if not strategies:
        return 0
    
    max_warmup = 0
    for strategy_name, config in strategies.items():
        params = config.get('params', {})
        
        # Use factory function to instantiate strategy
        strategy = get_strategy(strategy_name, params)
        warmup = strategy.get_warmup_period()
        
        max_warmup = max(max_warmup, warmup)
    
    return max_warmup


def calculate_meta_allocator_warmup(
    meta_allocator: Optional[Dict[str, Any]],
    num_strategies: int
) -> int:
    """
    Calculate meta allocator warmup period.
    
    Args:
        meta_allocator: {'type': 'fixed_weight'|'risk_parity', 'params': {...}}
        num_strategies: Number of strategies (skip meta allocator if 1)
    
    Returns:
        Meta allocator warmup period in trading days
    
    Example:
        >>> meta_allocator = {'type': 'risk_parity', 'params': {'vol_lookback': 60}}
        >>> calculate_meta_allocator_warmup(meta_allocator, num_strategies=2)
        60
    """
    # Skip meta allocator if only one strategy
    if num_strategies <= 1:
        return 0
    
    if meta_allocator is None:
        # Default: FixedWeightAllocator has 0 warmup
        return 0
    
    allocator_type = meta_allocator.get('type', 'fixed_weight')
    params = meta_allocator.get('params', {})
    
    # Use factory function to instantiate meta allocator
    allocator = get_meta_allocator(allocator_type, params)
    return allocator.get_warmup_period()

def calculate_warmup_period(
    strategies: Dict[str, Dict[str, Any]],
    meta_allocator: Optional[Dict[str, Any]],
    vol_window: int,
    vol_lookback: int,
) -> Dict[str, Any]:
    """
    Calculate total warmup period needed for all system components.
    
    The asset allocator uses raw price returns (not strategy returns), so its
    warmup runs in PARALLEL with the strategy + meta layers.
    
    Warmup formula (in TRADING DAYS):
        signal_warmup   = strategy_warmup + meta_allocator_warmup
        parallel_warmup = max(signal_warmup, asset_allocator_warmup)
        total           = parallel_warmup + 1 + vol_lookback
    
    Timeline example (Trend+MeanRev, Risk Parity meta allocator, vol_window=60):
    - Day 1-253: Strategy warmup (max of Trend=253, MeanRev=60)
    - Day 1-60:  Asset allocator warmup (inverse vol, runs in parallel)
    - Day 254-313: Meta allocator warmup (Risk Parity needs 60 days)
    - Day 314: First weights + strategy returns ready, first portfolio return
    - Day 315-374: Portfolio returns accumulate (leverage = 1.0)
    - Day 375: Vol targeting activates (60 days of portfolio returns available)
    
    Total warmup = max(253 + 60, 60) + 1 + 60 = 374
    
    Note: The engine uses pandas market calendars to go back this many business days,
    automatically accounting for weekends and holidays.
    
    Args:
        strategies: Dict mapping strategy_name -> {'params': {...}}
        meta_allocator: {'type': 'fixed_weight'|'risk_parity', 'params': {...}}
        vol_window: Lookback for inverse volatility weights (asset allocator)
        vol_lookback: Lookback for volatility targeting
    
    Returns:
        Dictionary with:
            - strategy_warmup: int
            - meta_allocator_warmup: int
            - signal_warmup: int (strategy + meta)
            - asset_allocator_warmup: int
            - parallel_warmup: int (max of signal vs allocator)
            - first_return: int (always 1)
            - vol_targeting_warmup: int
            - total_trading_days: int
            - description: str
    
    Example:
        >>> # Single strategy (no meta allocator)
        >>> warmup = calculate_warmup_period(
        ...     strategies={'trend': {'params': {}}},
        ...     meta_allocator=None,
        ...     vol_window=60,
        ...     vol_lookback=60,
        ... )
        >>> warmup['total_trading_days']
        314  # max(253, 60) + 1 + 60
        
        >>> # Multi-strategy with Risk Parity
        >>> warmup = calculate_warmup_period(
        ...     strategies={'trend': {}, 'meanrev': {}},
        ...     meta_allocator={'type': 'risk_parity', 'params': {'vol_lookback': 60}},
        ...     vol_window=60,
        ...     vol_lookback=60,
        ... )
        >>> warmup['total_trading_days']
        374  # max(253 + 60, 60) + 1 + 60
    """
    # Calculate strategy warmup using helper function
    strategy_warmup_days = calculate_strategy_warmup(strategies)
    
    # Calculate meta allocator warmup using helper function
    num_strategies = len(strategies) if strategies else 0
    meta_allocator_warmup_days = calculate_meta_allocator_warmup(
        meta_allocator, num_strategies
    )
    
    # Signal warmup (strategy + meta, sequential)
    signal_warmup = strategy_warmup_days + meta_allocator_warmup_days
    
    # Asset allocator warmup (inverse vol) — runs in parallel with signal warmup
    asset_allocator_warmup = vol_window
    
    # Parallel warmup: allocator uses raw price returns, not strategy returns
    parallel_warmup = max(signal_warmup, asset_allocator_warmup)
    
    # First return day
    first_return_day = 1
    
    # Vol targeting warmup
    vol_targeting_warmup = vol_lookback
    
    # Total warmup (parallel model)
    total_trading_days = parallel_warmup + first_return_day + vol_targeting_warmup
    
    # Build description
    signal_parts = []
    if strategy_warmup_days > 0:
        signal_parts.append(f"Strategy ({strategy_warmup_days}d)")
    if meta_allocator_warmup_days > 0:
        signal_parts.append(f"Meta ({meta_allocator_warmup_days}d)")
    
    if signal_parts:
        signal_str = " + ".join(signal_parts)
        description = (
            f"max({signal_str}, Allocator ({asset_allocator_warmup}d))"
            f" + First return ({first_return_day}d)"
            f" + Vol targeting ({vol_targeting_warmup}d)"
            f" = {total_trading_days} trading days"
        )
    else:
        description = (
            f"Allocator ({asset_allocator_warmup}d)"
            f" + First return ({first_return_day}d)"
            f" + Vol targeting ({vol_targeting_warmup}d)"
            f" = {total_trading_days} trading days"
        )
    
    return {
        "strategy_warmup": strategy_warmup_days,
        "meta_allocator_warmup": meta_allocator_warmup_days,
        "signal_warmup": signal_warmup,
        "asset_allocator_warmup": asset_allocator_warmup,
        "parallel_warmup": parallel_warmup,
        "first_return": first_return_day,
        "vol_targeting_warmup": vol_targeting_warmup,
        "total_trading_days": total_trading_days,
        "description": description,
    }
