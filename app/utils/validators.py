"""Input validation utilities."""

from datetime import date


def validate_universe(universe, available_tickers):
    """
    Validate universe selection.
    
    Args:
        universe: List of selected tickers
        available_tickers: List of available tickers
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if not universe or len(universe) == 0:
        errors.append("Universe cannot be empty")
    
    for ticker in universe:
        if ticker not in available_tickers:
            errors.append(f"Invalid ticker: {ticker}")
    
    return errors


def validate_date_range(start_date, end_date):
    """
    Validate date range.
    
    Args:
        start_date: Start date
        end_date: End date
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    today = date.today()
    
    # Check for None values (e.g. cleared inputs)
    if start_date is None or end_date is None:
        errors.append("Start date and end date are required")
        return errors
        
    if start_date >= end_date:
        errors.append(f"Start date ({start_date}) must be before end date ({end_date})")
    
    # Check if dates are too far in the past (before 2000)
    if start_date.year < 2000:
        errors.append("Start date should be after year 2000")
    
    # Check if dates are in the future
    if end_date > today:
        errors.append(f"End date ({end_date}) cannot be in the future")
    
    return errors


def validate_backtest_params(universe, start_date, end_date, min_assets_held, 
                             min_leverage, max_leverage, available_tickers):
    """
    Validate all backtest parameters before execution.
    
    Args:
        universe: List of selected tickers
        start_date: Start date
        end_date: End date
        min_assets_held: Minimum number of assets
        min_leverage: Minimum leverage
        max_leverage: Maximum leverage
        available_tickers: List of available tickers
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    # Validate universe
    errors.extend(validate_universe(universe, available_tickers))
    
    # Validate dates
    errors.extend(validate_date_range(start_date, end_date))
    
    # Validate min assets vs universe size
    if min_assets_held > len(universe) and len(universe) != 0:
        errors.append(
            f"Min assets ({min_assets_held}) cannot exceed universe size ({len(universe)})"
        )
    
    # Validate leverage
    if min_leverage > max_leverage:
        errors.append(
            f"Min leverage ({min_leverage}) cannot exceed max leverage ({max_leverage})"
        )
    
    return errors
