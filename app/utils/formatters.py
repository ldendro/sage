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

def format_leverage(value: float, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}"
