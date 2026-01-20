"""
Inverse volatility allocator (v1).

This allocator computes portfolio weights based on inverse volatility:
- Higher volatility assets get lower weights
- Lower volatility assets get higher weights
- Weights are normalized to sum to 1
- Optional max weight cap per asset
"""

import pandas as pd
import numpy as np


def compute_inverse_vol_weights(
    returns_wide: pd.DataFrame,
    lookback: int = 20,
    max_weight: float = 1.0,
    min_vol: float = 0.0001,
) -> pd.DataFrame:
    """
    Compute inverse volatility weights for portfolio allocation.
    
    For each date, computes rolling volatility over lookback period,
    then assigns weights inversely proportional to volatility.
    
    Args:
        returns_wide: Wide DataFrame of asset returns (dates × symbols)
        lookback: Number of days for volatility calculation (default: 20)
        max_weight: Maximum weight per asset (default: 1.0 = no cap)
        min_vol: Minimum volatility floor to prevent division by zero (default: 0.0001)
    
    Returns:
        Wide DataFrame of weights (dates × symbols), normalized to sum to 1
    
    Raises:
        ValueError: If lookback < 2 or max_weight <= 0
    
    Example:
        >>> weights = compute_inverse_vol_weights(returns_wide, lookback=20, max_weight=0.3)
        >>> weights.sum(axis=1)  # Should all be 1.0
        
    Notes:
        - First (lookback-1) days will have NaN weights (insufficient history)
        - Weights are recomputed daily based on trailing volatility
        - Higher vol → lower weight, lower vol → higher weight
        - max_weight caps individual asset weights before normalization
    """
    # Validate inputs
    if lookback < 2:
        raise ValueError(f"lookback must be >= 2, got {lookback}")
    
    if max_weight <= 0:
        raise ValueError(f"max_weight must be > 0, got {max_weight}")
    
    if max_weight > 1.0:
        raise ValueError(f"max_weight must be <= 1.0, got {max_weight}")
    
    # Compute rolling volatility (standard deviation)
    rolling_vol = returns_wide.rolling(window=lookback, min_periods=lookback).std()
    
    # Apply minimum volatility floor to prevent division by zero
    rolling_vol = rolling_vol.clip(lower=min_vol)
    
    # Compute inverse volatility (1 / vol)
    inverse_vol = 1.0 / rolling_vol
    
    # Apply max weight cap BEFORE normalization
    # This prevents any single asset from dominating
    raw_weights = inverse_vol.copy()
    
    # Normalize to sum to 1 for each date
    weights = raw_weights.div(raw_weights.sum(axis=1), axis=0)
    
    # Apply max weight cap AFTER normalization
    # If any weight exceeds max, cap it and renormalize
    def cap_and_renormalize(row):
        """Cap weights and renormalize to sum to 1."""
        if row.isna().any():
            return row  # Skip rows with NaN
        
        # Iteratively cap and renormalize until no weight exceeds max
        max_iterations = 100
        for iteration in range(max_iterations):
            # Check if all weights are within cap
            if (row <= max_weight).all():
                break
            
            # Find assets that exceed cap
            exceeds_cap = row > max_weight
            
            # Cap the excess weights
            capped_weights = row.copy()
            capped_weights[exceeds_cap] = max_weight
            
            # Calculate remaining weight to distribute
            total_capped = capped_weights[exceeds_cap].sum()
            total_uncapped = row[~exceeds_cap].sum()
            remaining_weight = 1.0 - total_capped
            
            # Renormalize uncapped weights proportionally
            if total_uncapped > 0:
                capped_weights[~exceeds_cap] = (
                    row[~exceeds_cap] / total_uncapped * remaining_weight
                )
            
            row = capped_weights
        
        return row
    
    weights = weights.apply(cap_and_renormalize, axis=1)
    
    return weights


def compute_equal_weights(
    returns_wide: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute equal weights for all assets.
    
    Simple baseline allocator that assigns 1/N to each asset.
    
    Args:
        returns_wide: Wide DataFrame of asset returns (dates × symbols)
    
    Returns:
        Wide DataFrame of equal weights (dates × symbols)
    
    Example:
        >>> weights = compute_equal_weights(returns_wide)
        >>> weights.iloc[0]  # All equal
        SPY    0.333333
        QQQ    0.333333
        IWM    0.333333
    """
    n_assets = len(returns_wide.columns)
    equal_weight = 1.0 / n_assets
    
    weights = pd.DataFrame(
        equal_weight,
        index=returns_wide.index,
        columns=returns_wide.columns,
    )
    
    return weights
