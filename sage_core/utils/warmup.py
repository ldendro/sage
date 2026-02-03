"""
Warmup period calculation for backtesting.

This module centralizes warmup logic to make it easy to update
when new system parameters are added.
"""

from typing import Dict


def calculate_warmup_period(
    vol_window: int,
    vol_lookback: int,
    strategy_warmup: int = 0,
) -> Dict[str, any]:
    """
    Calculate total warmup period needed for all system components.
    
    Warmup is calculated sequentially in TRADING DAYS:
    1. strategy_warmup days to generate valid strategy returns (meta_raw_ret)
    2. vol_window days to generate first weights (inverse vol on strategy returns)
    3. 1 day for first portfolio return
    4. vol_lookback days to accumulate portfolio returns for vol targeting
    
    Timeline example (strategy_warmup=252, vol_window=60, vol_lookback=60):
    - Day 1-252: Strategy warmup (no valid meta_raw_ret yet)
    - Day 253-312: Inverse vol warmup (using strategy returns from days 1-312)
    - Day 313: First weights generated, first portfolio return
    - Day 314-373: Portfolio returns accumulate (leverage = 1.0)
    - Day 374: Vol targeting activates (60 days of portfolio returns available)
    
    Total warmup = strategy_warmup + vol_window + 1 + vol_lookback (in TRADING DAYS)
    
    Note: The engine uses pandas market calendars to go back this many business days,
    automatically accounting for weekends and holidays.
    
    Args:
        vol_window: Lookback for inverse volatility weights
        vol_lookback: Lookback for volatility targeting
        strategy_warmup: Warmup period for strategy layer (default: 0 for passthrough)
    
    Returns:
        Dictionary with:
            - total_trading_days: Total warmup period in trading days
            - components: Breakdown by component
            - description: Human-readable explanation
    
    Example:
        >>> # Passthrough strategy (no warmup)
        >>> warmup = calculate_warmup_period(vol_window=60, vol_lookback=60)
        >>> print(warmup['total_trading_days'])
        121
        
        >>> # Trend strategy (252-day warmup)
        >>> warmup = calculate_warmup_period(
        ...     vol_window=60, 
        ...     vol_lookback=60, 
        ...     strategy_warmup=252
        ... )
        >>> print(warmup['total_trading_days'])
        373
    """
    # Sequential warmup calculation (in trading days)
    # Components run in sequence: strategy → allocator → vol targeting
    strategy_warmup_days = strategy_warmup
    inverse_vol_warmup = vol_window
    first_return_day = 1  # Day when first portfolio return is generated
    vol_targeting_warmup = vol_lookback
    
    total_trading_days = (
        strategy_warmup_days + 
        inverse_vol_warmup + 
        first_return_day + 
        vol_targeting_warmup
    )
    
    return {
        "total_trading_days": total_trading_days,
        "components": {
            "strategy": strategy_warmup_days,
            "inverse_vol": inverse_vol_warmup,
            "first_return": first_return_day,
            "vol_targeting": vol_targeting_warmup,
        },
        "description": (
            f"Strategy ({strategy_warmup_days}d) + "
            f"Inverse vol ({inverse_vol_warmup}d) + "
            f"First return (1d) + "
            f"Vol targeting ({vol_targeting_warmup}d) = "
            f"{total_trading_days} trading days"
        )
    }
