"""
Warmup period calculation for backtesting.

This module centralizes warmup logic to make it easy to update
when new system parameters are added.
"""

from typing import Dict


def calculate_warmup_period(
    vol_window: int,
    vol_lookback: int,
) -> Dict[str, any]:
    """
    Calculate total warmup period needed for all system components.
    
    Warmup is calculated sequentially in TRADING DAYS:
    1. vol_window days to generate first weights (inverse vol)
    2. 1 day for first portfolio return
    3. vol_lookback days to accumulate portfolio returns for vol targeting
    
    Timeline example (vol_window=60, vol_lookback=60):
    - Day 1-60: Inverse vol warmup (no weights yet)
    - Day 61: First weights generated, first portfolio return
    - Day 62-121: Portfolio returns accumulate (leverage = 1.0)
    - Day 122: Vol targeting activates (60 days of portfolio returns available)
    
    Total warmup = vol_window + 1 + vol_lookback (in TRADING DAYS)
    
    Note: The engine uses pandas market calendars to go back this many business days,
    automatically accounting for weekends and holidays.
    
    Future components will be added here as the system evolves.
    
    Args:
        vol_window: Lookback for inverse volatility weights
        vol_lookback: Lookback for volatility targeting
    
    Returns:
        Dictionary with:
            - total_trading_days: Total warmup period in trading days
            - components: Breakdown by component
            - description: Human-readable explanation
    
    Example:
        >>> warmup = calculate_warmup_period(vol_window=60, vol_lookback=60)
        >>> print(warmup['total_trading_days'])
        121
        >>> print(warmup['description'])
        'Inverse vol (60d) + First return (1d) + Vol targeting (60d) = 121 trading days'
    """
    # Sequential warmup calculation (in trading days)
    # We need weights before we can calculate portfolio returns,
    # and we need portfolio returns before we can apply vol targeting
    inverse_vol_warmup = vol_window
    first_return_day = 1  # Day when first portfolio return is generated
    vol_targeting_warmup = vol_lookback
    
    total_trading_days = inverse_vol_warmup + first_return_day + vol_targeting_warmup
    
    return {
        "total_trading_days": total_trading_days,
        "components": {
            "inverse_vol": inverse_vol_warmup,
            "first_return": first_return_day,
            "vol_targeting": vol_targeting_warmup,
            # Future components here
        },
        "description": f"Inverse vol ({inverse_vol_warmup}d) + First return (1d) + Vol targeting ({vol_targeting_warmup}d) = {total_trading_days} trading days"
    }
