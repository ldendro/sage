"""
Volatility targeting utilities for portfolio construction.

This module provides functions to scale portfolio weights based on
realized volatility to achieve a target volatility level.
"""

import pandas as pd
import numpy as np


def apply_vol_targeting(
    portfolio_returns: pd.Series,
    weights_df: pd.DataFrame,
    target_vol: float = 0.10,
    lookback: int = 60,
    min_leverage: float = 0.0,
    max_leverage: float = 2.0,
) -> pd.DataFrame:
    """
    Apply volatility targeting to portfolio weights.
    
    Scales weights based on realized volatility to achieve target annual volatility.
    
    Args:
        portfolio_returns: Series of portfolio returns (dates)
        weights_df: Wide DataFrame of portfolio weights (dates × symbols)
        target_vol: Target annual volatility (default: 0.10 = 10%)
        lookback: Number of days for volatility calculation (default: 60)
        min_leverage: Minimum leverage multiplier (default: 0.0)
        max_leverage: Maximum leverage multiplier (default: 2.0)
    
    Returns:
        Wide DataFrame of scaled weights (dates × symbols)
    
    Raises:
        ValueError: If parameters are invalid
    
    Example:
        >>> scaled = apply_vol_targeting(
        ...     portfolio_returns,
        ...     weights_df,
        ...     target_vol=0.10,
        ...     lookback=60,
        ... )
    
    Notes:
        - First lookback days will have leverage = 1.0 (warmup + shift)
        - Leverage = target_vol / realized_vol
        - Leverage is capped between min_leverage and max_leverage
        - Uses annualization factor of sqrt(252) for daily returns
        - **Look-ahead bias prevention**: Volatility is shifted by 1 day,
          so weights at date t only depend on returns through t-1
    """
    # Validate inputs
    if target_vol <= 0:
        raise ValueError(f"target_vol must be > 0, got {target_vol}")
    
    if lookback < 2:
        raise ValueError(f"lookback must be >= 2, got {lookback}")
    
    if min_leverage < 0:
        raise ValueError(f"min_leverage must be >= 0, got {min_leverage}")
    
    if max_leverage <= 0:
        raise ValueError(f"max_leverage must be > 0, got {max_leverage}")
    
    if min_leverage > max_leverage:
        raise ValueError(
            f"min_leverage ({min_leverage}) cannot exceed max_leverage ({max_leverage})"
        )
    
    # Ensure indices match
    if not portfolio_returns.index.equals(weights_df.index):
        raise ValueError("portfolio_returns and weights_df must have the same index")
    
    # Calculate rolling volatility (annualized)
    # IMPORTANT: Shift by 1 to avoid look-ahead bias
    # Weights at date t should only use information available through t-1
    rolling_vol = portfolio_returns.rolling(
        window=lookback,
        min_periods=lookback
    ).std() * np.sqrt(252)
    
    # Shift volatility by 1 day to avoid look-ahead bias
    # This ensures weights at date t only depend on returns through t-1
    rolling_vol = rolling_vol.shift(1)
    
    # Calculate leverage multiplier
    # leverage = target_vol / realized_vol
    # For first lookback days, use leverage = 1.0 (no scaling)
    leverage = pd.Series(1.0, index=portfolio_returns.index)
    
    # Only apply vol targeting after warmup period
    valid_mask = ~rolling_vol.isna()
    leverage[valid_mask] = target_vol / rolling_vol[valid_mask]
    
    # Cap leverage
    leverage = leverage.clip(lower=min_leverage, upper=max_leverage)
    
    # Scale weights by leverage
    # Broadcast leverage across all columns
    scaled_weights = weights_df.multiply(leverage, axis=0)
    
    return scaled_weights


def calculate_portfolio_volatility(
    portfolio_returns: pd.Series,
    lookback: int = 60,
    annualize: bool = True,
) -> pd.Series:
    """
    Calculate rolling portfolio volatility.
    
    Args:
        portfolio_returns: Series of portfolio returns
        lookback: Number of days for volatility calculation (default: 60)
        annualize: Whether to annualize volatility (default: True)
    
    Returns:
        Series of rolling volatility
    
    Example:
        >>> vol = calculate_portfolio_volatility(returns, lookback=60)
    """
    rolling_vol = portfolio_returns.rolling(
        window=lookback,
        min_periods=lookback
    ).std()
    
    if annualize:
        rolling_vol = rolling_vol * np.sqrt(252)
    
    return rolling_vol
