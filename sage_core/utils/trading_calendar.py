"""
Trading calendar utilities for warmup calculations.

Uses pandas_market_calendars to get exact trading days.
"""

import pandas as pd
import pandas_market_calendars as mcal
import logging

logger = logging.getLogger(__name__)

# Cache calendar instances by exchange code
_CALENDARS = {}


def get_calendar(exchange: str = "NYSE"):
    """Get exchange calendar instance (cached by exchange code)."""
    key = exchange.upper()
    calendar = _CALENDARS.get(key)
    if calendar is None:
        calendar = mcal.get_calendar(key)
        _CALENDARS[key] = calendar
    return calendar


def get_warmup_start_date(
    start_date: str,
    warmup_trading_days: int,
    exchange: str = "NYSE"
) -> str:
    """
    Calculate exact warmup start date using market calendar.
    
    Goes back exactly warmup_trading_days trading days from start_date,
    accounting for weekends and holidays.
    
    Args:
        start_date: User's requested start date (YYYY-MM-DD)
        warmup_trading_days: Number of trading days needed for warmup
        exchange: Exchange calendar to use (default: NYSE)
    
    Returns:
        Exact warmup start date (YYYY-MM-DD)
    
    Raises:
        ValueError: If insufficient trading days available
    
    Example:
        >>> get_warmup_start_date("2023-06-01", 121)
        "2022-12-19"  # Exactly 121 trading days before 2023-06-01
    """
    start_date_ts = pd.Timestamp(start_date)
    
    # Get calendar
    calendar = get_calendar(exchange)
    
    # Estimate how far back to go (conservative buffer)
    # Typical: ~252 trading days per year
    # So warmup_trading_days / 252 * 365 ≈ calendar days needed
    # Add 20% buffer for safety
    estimated_calendar_days = int(warmup_trading_days / 252 * 365 * 1.2)
    estimated_start = start_date_ts - pd.Timedelta(days=estimated_calendar_days)
    
    # Get trading days in this range
    schedule = calendar.schedule(
        start_date=estimated_start,
        end_date=start_date_ts
    )
    trading_days = schedule.index
    
    # Filter to only days before start_date
    trading_days_before = trading_days[trading_days < start_date_ts]
    
    # Validate we have enough
    available_days = len(trading_days_before)
    if available_days < warmup_trading_days:
        # Need to go back further
        # Double the buffer and try again
        estimated_calendar_days = int(warmup_trading_days / 252 * 365 * 2.0)
        estimated_start = start_date_ts - pd.Timedelta(days=estimated_calendar_days)
        
        schedule = calendar.schedule(
            start_date=estimated_start,
            end_date=start_date_ts
        )
        trading_days = schedule.index
        trading_days_before = trading_days[trading_days < start_date_ts]
        available_days = len(trading_days_before)
        
        if available_days < warmup_trading_days:
            raise ValueError(
                f"Insufficient trading days available. "
                f"Need {warmup_trading_days} trading days before {start_date}, "
                f"but only {available_days} available in {exchange} calendar. "
                f"Earliest available: {trading_days_before[0].strftime('%Y-%m-%d')}. "
                f"Try a later start_date or reduce vol_window/vol_lookback."
            )
    
    # Count back exactly warmup_trading_days
    warmup_start_date = trading_days_before[-warmup_trading_days]
    
    logger.info(
        f"Warmup start date: {warmup_start_date.strftime('%Y-%m-%d')} "
        f"({warmup_trading_days} {exchange} trading days before {start_date})"
    )
    
    return warmup_start_date.strftime("%Y-%m-%d")


def get_first_trading_day_on_or_after(
    date: str,
    exchange: str = "NYSE",
) -> str:
    """
    Get first trading day on or after the given date for an exchange.
    
    If date is a trading day, returns it.
    If date is a weekend/holiday, returns next trading day.
    
    Args:
        date: Date to check (YYYY-MM-DD)
    
    Returns:
        First trading day on or after date (YYYY-MM-DD)
    
    Example:
        >>> get_first_trading_day_on_or_after("2023-07-04")  # July 4th holiday
        "2023-07-05"
    """
    date_ts = pd.Timestamp(date)
    calendar = get_calendar(exchange)
    
    # Get schedule for a week after the date (enough to find next trading day)
    schedule = calendar.schedule(
        start_date=date_ts,
        end_date=date_ts + pd.Timedelta(days=7)
    )
    
    if len(schedule) == 0:
        raise ValueError(f"No trading days found after {date} for {exchange}")
    
    first_trading_day = schedule.index[0]
    return first_trading_day.strftime("%Y-%m-%d")
