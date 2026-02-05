"""
Warmup period calculation for backtesting.

This module centralizes warmup logic to make it easy to update
when new system parameters are added.
"""

from typing import Dict, Any, Optional



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
        252  # TrendStrategy has 252-day warmup (max)
    """
    if not strategies:
        return 0
    
    max_warmup = 0
    for strategy_name, config in strategies.items():
        params = config.get('params', {})
        
        if strategy_name == 'passthrough':
            from sage_core.strategies.passthrough import PassthroughStrategy
            warmup = PassthroughStrategy().get_warmup_period()
        elif strategy_name == 'trend':
            from sage_core.strategies.trend import TrendStrategy
            warmup = TrendStrategy(params=params).get_warmup_period()
        elif strategy_name == 'meanrev':
            from sage_core.strategies.meanrev import MeanRevStrategy
            warmup = MeanRevStrategy(params=params).get_warmup_period()
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")
        
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
    
    if allocator_type == 'fixed_weight':
        from sage_core.meta import FixedWeightAllocator
        return FixedWeightAllocator(params=params).get_warmup_period()
    elif allocator_type == 'risk_parity':
        from sage_core.meta import RiskParityAllocator
        return RiskParityAllocator(params=params).get_warmup_period()
    else:
        raise ValueError(f"Unknown meta allocator type: {allocator_type}")

def calculate_warmup_period(
    strategies: Dict[str, Dict[str, Any]],
    meta_allocator: Optional[Dict[str, Any]],
    vol_window: int,
    vol_lookback: int,
) -> Dict[str, Any]:
    """
    Calculate total warmup period needed for all system components.
    
    Warmup is calculated sequentially in TRADING DAYS:
    1. strategy_warmup days to generate valid strategy returns (meta_raw_ret)
    2. meta_allocator_warmup days to combine strategy returns (if multi-strategy)
    3. vol_window days to generate first weights (inverse vol on combined returns)
    4. 1 day for first portfolio return
    5. vol_lookback days to accumulate portfolio returns for vol targeting
    
    Timeline example (Trend+MeanRev, Risk Parity meta allocator):
    - Day 1-252: Strategy warmup (max of Trend=252, MeanRev=60)
    - Day 253-312: Meta allocator warmup (Risk Parity needs 60 days)
    - Day 313-372: Asset allocator warmup (inverse vol needs 60 days)
    - Day 373: First weights generated, first portfolio return
    - Day 374-433: Portfolio returns accumulate (leverage = 1.0)
    - Day 434: Vol targeting activates (60 days of portfolio returns available)
    
    Total warmup = strategy + meta_allocator + vol_window + 1 + vol_lookback
    
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
            - asset_allocator_warmup: int
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
        373  # 252 + 0 + 60 + 1 + 60
        
        >>> # Multi-strategy with Risk Parity
        >>> warmup = calculate_warmup_period(
        ...     strategies={'trend': {}, 'meanrev': {}},
        ...     meta_allocator={'type': 'risk_parity', 'params': {'vol_lookback': 60}},
        ...     vol_window=60,
        ...     vol_lookback=60,
        ... )
        >>> warmup['total_trading_days']
        433  # 252 + 60 + 60 + 1 + 60
    """
    # Calculate strategy warmup using helper function
    strategy_warmup_days = calculate_strategy_warmup(strategies)
    
    # Calculate meta allocator warmup using helper function
    num_strategies = len(strategies) if strategies else 0
    meta_allocator_warmup_days = calculate_meta_allocator_warmup(
        meta_allocator, num_strategies
    )
    
    # Asset allocator warmup (inverse vol)
    asset_allocator_warmup = vol_window
    
    # First return day
    first_return_day = 1
    
    # Vol targeting warmup
    vol_targeting_warmup = vol_lookback
    
    # Total warmup (sequential)
    total_trading_days = (
        strategy_warmup_days + 
        meta_allocator_warmup_days +
        asset_allocator_warmup + 
        first_return_day + 
        vol_targeting_warmup
    )
    
    # Build description
    parts = []
    if strategy_warmup_days > 0:
        parts.append(f"Strategy ({strategy_warmup_days}d)")
    if meta_allocator_warmup_days > 0:
        parts.append(f"Meta allocator ({meta_allocator_warmup_days}d)")
    parts.append(f"Asset allocator ({asset_allocator_warmup}d)")
    parts.append(f"First return ({first_return_day}d)")
    parts.append(f"Vol targeting ({vol_targeting_warmup}d)")
    
    description = " + ".join(parts) + f" = {total_trading_days} trading days"
    
    return {
        "strategy_warmup": strategy_warmup_days,
        "meta_allocator_warmup": meta_allocator_warmup_days,
        "asset_allocator_warmup": asset_allocator_warmup,
        "first_return": first_return_day,
        "vol_targeting_warmup": vol_targeting_warmup,
        "total_trading_days": total_trading_days,
        "description": description,
    }
