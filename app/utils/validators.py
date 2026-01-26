"""Input validation utilities."""

from datetime import date

from sage_core.utils.constants import SECTOR_MAP

def validate_universe_widget(universe, available_tickers):
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


def validate_date_range_widget(start_date, end_date):
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

def validate_risk_caps_widget(
    min_assets_held,
    universe,
    max_weight_per_asset,
    max_sector_weight,
):
    """
    Validate Risk Caps widget.
    
    Args:
        min_assets_held: Minimum number of assets
        universe: List of selected tickers
        max_weight_per_asset: Maximum weight per asset
        max_sector_weight: Maximum sector weight
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if min_assets_held > len(universe) and len(universe) != 0:
        errors.append(
            f"Min assets ({min_assets_held}) cannot exceed universe size ({len(universe)})"
        )

    if max_weight_per_asset <= 0 or max_weight_per_asset > 1:
        errors.append(
            f"Max weight per asset must be in (0, 1], got {max_weight_per_asset}"
        )
    elif len(universe) > 0 and len(universe) * max_weight_per_asset < 1.0:
        errors.append(
            f"Infeasible per-asset cap: {len(universe)} asset(s) * "
            f"Max weight per asset ({max_weight_per_asset:.2f}) = "
            f"{len(universe) * max_weight_per_asset:.2f} < 1.0. "
            "This will force the portfolio to be under-invested."
        )

    if max_sector_weight is not None:
        if max_sector_weight <= 0 or max_sector_weight > 1:
            errors.append(
                f"Max sector weight must be in (0, 1], got {max_sector_weight}"
            )
        else:
            missing_sectors = [s for s in universe if s not in SECTOR_MAP]
            if missing_sectors:
                errors.append(
                    "Sector cap enabled but missing sector mappings for: "
                    + ", ".join(missing_sectors)
                )
            else:
                unique_sectors = {SECTOR_MAP[s] for s in universe}
                n_sectors = len(unique_sectors)
                if n_sectors > 0 and n_sectors * max_sector_weight < 1.0:
                    errors.append(
                        f"Infeasible sector cap: {n_sectors} sector(s) * "
                        f"Max sector weight ({max_sector_weight:.2f}) = "
                        f"{n_sectors * max_sector_weight:.2f} < 1.0. "
                        f"With {n_sectors} sector(s), max_sector_weight must be >= "
                        f"{1.0 / n_sectors:.2f}."
                    )

    return errors


def validate_volatility_targeting_widget(min_leverage, max_leverage):
    """
    Validate Volatility Targeting widget.
    
    Args:
        min_leverage: Minimum leverage
        max_leverage: Maximum leverage
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if min_leverage > max_leverage:
        errors.append(
            f"Min leverage ({min_leverage}) cannot exceed max leverage ({max_leverage})"
        )

    return errors


def validate_backtest_params(
    universe,
    start_date,
    end_date,
    min_assets_held,
    min_leverage,
    max_leverage,
    max_weight_per_asset,
    max_sector_weight,
    available_tickers,
):
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
    errors.extend(validate_universe_widget(universe, available_tickers))

    # Validate dates
    errors.extend(validate_date_range_widget(start_date, end_date))

    # Validate risk caps
    errors.extend(
        validate_risk_caps_widget(
            min_assets_held=min_assets_held,
            universe=universe,
            max_weight_per_asset=max_weight_per_asset,
            max_sector_weight=max_sector_weight,
        )
    )

    # Validate volatility targeting
    errors.extend(validate_volatility_targeting_widget(min_leverage, max_leverage))
    
    return errors
