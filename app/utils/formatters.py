"""Formatting utilities for displaying metrics and values."""

from typing import Optional


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a decimal value as a percentage.
    
    Args:
        value: Decimal value (e.g., 0.15 for 15%)
        decimals: Number of decimal places
    
    Returns:
        Formatted percentage string (e.g., "15.00%")
    """
    if value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def format_ratio(value: float, decimals: int = 2) -> str:
    """
    Format a ratio value.
    
    Args:
        value: Ratio value
        decimals: Number of decimal places
    
    Returns:
        Formatted ratio string
    """
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"


def format_currency(value: float, symbol: str = "$", decimals: int = 2) -> str:
    """
    Format a currency value.
    
    Args:
        value: Currency value
        symbol: Currency symbol
        decimals: Number of decimal places
    
    Returns:
        Formatted currency string
    """
    if value is None:
        return "N/A"
    return f"{symbol}{value:,.{decimals}f}"


def format_days(days: Optional[int]) -> str:
    """
    Format a duration in days.
    
    Args:
        days: Number of days
    
    Returns:
        Formatted duration string
    """
    if days is None:
        return "N/A"
    if days == 0:
        return "0 days"
    elif days == 1:
        return "1 day"
    else:
        return f"{days} days"


def format_date(date_obj) -> str:
    """
    Format a date object.
    
    Args:
        date_obj: Date or datetime object
    
    Returns:
        Formatted date string (YYYY-MM-DD)
    """
    if date_obj is None:
        return "N/A"
    if hasattr(date_obj, 'strftime'):
        return date_obj.strftime("%Y-%m-%d")
    return str(date_obj)


def get_metric_color(value: float, positive_is_good: bool = True) -> str:
    """
    Get a color indicator based on metric value.
    
    Args:
        value: Metric value
        positive_is_good: If True, positive values are green
    
    Returns:
        Color indicator: "green", "red", or "neutral"
    """
    if value is None:
        return "neutral"
    
    if positive_is_good:
        if value > 0:
            return "green"
        elif value < 0:
            return "red"
    else:
        if value < 0:
            return "green"
        elif value > 0:
            return "red"
    
    return "neutral"


def format_metric_with_delta(
    current: float,
    previous: Optional[float] = None,
    is_percentage: bool = True,
    decimals: int = 2,
    invert_delta: bool = False,
) -> tuple[str, Optional[str], Optional[str]]:
    """
    Format a metric with optional delta for comparison.
    
    Args:
        current: Current value
        previous: Previous value for delta calculation
        is_percentage: If True, format as percentage
        decimals: Number of decimal places
        invert_delta: If True, negative delta is good (e.g., for drawdown)
    
    Returns:
        Tuple of (formatted_value, delta_value, delta_color)
    """
    if is_percentage:
        formatted = format_percentage(current, decimals)
    else:
        formatted = format_ratio(current, decimals)
    
    if previous is None:
        return formatted, None, None
    
    delta = current - previous
    if is_percentage:
        delta_str = format_percentage(delta, decimals)
    else:
        delta_str = format_ratio(delta, decimals)
    
    delta_color = get_metric_color(delta, positive_is_good=not invert_delta)
    
    return formatted, delta_str, delta_color
