"""
Portfolio construction utilities.

This module provides functions to:
- Align asset returns into wide DataFrames
- Build portfolio returns from weights and asset returns
"""

import pandas as pd
from typing import Dict


def align_asset_returns(
    asset_data: Dict[str, pd.DataFrame],
    return_col: str = 'meta_raw_ret',
) -> pd.DataFrame:
    """
    Align asset returns into a wide DataFrame.
    
    Converts a dictionary of per-asset DataFrames into a single wide DataFrame
    with dates as index and symbols as columns.
    
    Args:
        asset_data: Dictionary mapping symbol to DataFrame
        return_col: Name of the return column to extract (default: 'meta_raw_ret')
    
    Returns:
        Wide DataFrame with:
        - Index: DatetimeIndex (dates)
        - Columns: Symbols
        - Values: Returns from return_col
    
    Raises:
        ValueError: If return_col not found in any DataFrame
        ValueError: If asset_data is empty
    
    Example:
        >>> data = {"SPY": spy_df, "QQQ": qqq_df}
        >>> returns_wide = align_asset_returns(data)
        >>> returns_wide.shape
        (252, 2)  # 252 days, 2 assets
    """
    if not asset_data:
        raise ValueError("asset_data cannot be empty")
    
    # Check that return_col exists in all DataFrames
    for symbol, df in asset_data.items():
        if return_col not in df.columns:
            raise ValueError(
                f"Column '{return_col}' not found in data for {symbol}. "
                f"Available columns: {list(df.columns)}"
            )
    
    # Extract return series for each asset
    returns_dict = {
        symbol: df[return_col]
        for symbol, df in asset_data.items()
    }
    
    # Combine into wide DataFrame
    # Use outer join to handle any date misalignments
    returns_wide = pd.DataFrame(returns_dict)
    
    return returns_wide


def build_portfolio_raw_returns(
    returns_wide: pd.DataFrame,
    weights_wide: pd.DataFrame,
) -> pd.Series:
    """
    Build portfolio returns from asset returns and weights.
    
    Computes portfolio returns as the element-wise product of returns and weights,
    summed across assets for each date.
    
    Args:
        returns_wide: Wide DataFrame of asset returns (dates × symbols)
        weights_wide: Wide DataFrame of portfolio weights (dates × symbols)
    
    Returns:
        Series of portfolio returns (index = dates)
    
    Raises:
        ValueError: If returns and weights have mismatched shapes or indices
    
    Example:
        >>> portfolio_ret = build_portfolio_raw_returns(returns_wide, weights_wide)
        >>> portfolio_ret.mean()  # Average daily return
        0.0005
    
    Notes:
        - Returns and weights must have the same index (dates)
        - Returns and weights must have the same columns (symbols)
        - Portfolio return = sum(weight[i] * return[i]) for each date
    """
    # Validate inputs
    if returns_wide.shape != weights_wide.shape:
        raise ValueError(
            f"Returns and weights must have same shape. "
            f"Returns: {returns_wide.shape}, Weights: {weights_wide.shape}"
        )
    
    if not returns_wide.index.equals(weights_wide.index):
        raise ValueError(
            "Returns and weights must have the same index (dates)"
        )
    
    if not set(returns_wide.columns) == set(weights_wide.columns):
        raise ValueError(
            f"Returns and weights must have the same columns (symbols). "
            f"Returns: {sorted(returns_wide.columns)}, "
            f"Weights: {sorted(weights_wide.columns)}"
        )
    
    # Align columns (in case order differs)
    weights_aligned = weights_wide[returns_wide.columns]
    
    # Element-wise multiply and sum across assets
    portfolio_returns = (returns_wide * weights_aligned).sum(axis=1)
    
    return portfolio_returns
