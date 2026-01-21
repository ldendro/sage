"""
Performance metrics calculation for backtesting.

This module provides functions to calculate key performance metrics:
- Sharpe ratio
- Maximum drawdown
- Turnover
- Yearly summaries
"""

import pandas as pd
import numpy as np
from typing import Dict, Any


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    annualization_factor: float = 252.0,
) -> float:
    """
    Calculate annualized Sharpe ratio.
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate (default: 0.0)
        annualization_factor: Factor to annualize (default: 252 for daily)
    
    Returns:
        Annualized Sharpe ratio
    
    Example:
        >>> sharpe = calculate_sharpe_ratio(returns)
    """
    if len(returns) == 0:
        return 0.0
    
    # Drop NaNs to handle sparse data
    returns_clean = returns.dropna()
    
    if len(returns_clean) == 0:
        return 0.0
    
    excess_returns = returns_clean - (risk_free_rate / annualization_factor)
    
    std = excess_returns.std()
    
    # Check for zero or NaN std (can happen with single value or all same)
    if std == 0 or np.isnan(std):
        return 0.0
    
    sharpe = excess_returns.mean() / std * np.sqrt(annualization_factor)
    return float(sharpe)


def calculate_max_drawdown(equity_curve: pd.Series) -> Dict[str, Any]:
    """
    Calculate maximum drawdown and related metrics.
    
    Args:
        equity_curve: Series of cumulative equity values
    
    Returns:
        Dictionary with:
            - max_drawdown: Maximum drawdown (negative value)
            - max_drawdown_pct: Maximum drawdown as percentage
            - peak_date: Date of peak before max drawdown
            - trough_date: Date of trough (max drawdown)
            - recovery_date: Date of recovery (None if not recovered)
            - drawdown_duration_days: Days from peak to trough
            - recovery_duration_days: Days from trough to recovery (None if not recovered)
    
    Example:
        >>> dd_info = calculate_max_drawdown(equity_curve)
        >>> print(f"Max DD: {dd_info['max_drawdown_pct']:.2%}")
    """
    if len(equity_curve) == 0:
        return {
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "peak_date": None,
            "trough_date": None,
            "recovery_date": None,
            "drawdown_duration_days": 0,
            "recovery_duration_days": None,
        }
    
    # Calculate running maximum
    running_max = equity_curve.expanding().max()
    
    # Calculate drawdown
    drawdown = equity_curve - running_max
    drawdown_pct = drawdown / running_max
    
    # Find maximum drawdown
    max_dd_idx = drawdown.idxmin()
    max_dd = drawdown[max_dd_idx]
    max_dd_pct = drawdown_pct[max_dd_idx]
    
    # Find peak before max drawdown
    # Use the LAST occurrence of the peak value before the trough
    # This gives accurate drawdown duration when there are repeated peaks
    peak_value = running_max[max_dd_idx]
    pre_trough = equity_curve[:max_dd_idx]
    # Find all dates where equity equals the peak value
    at_peak = pre_trough[pre_trough == peak_value]
    if len(at_peak) > 0:
        peak_idx = at_peak.index[-1]  # Last occurrence
    else:
        # Fallback (shouldn't happen, but handle edge case)
        peak_idx = running_max[:max_dd_idx].idxmax()
    
    # Find recovery date (if any)
    recovery_idx = None
    if max_dd_idx < equity_curve.index[-1]:
        # Look for recovery after trough
        post_trough = equity_curve[max_dd_idx:]
        peak_value = equity_curve[peak_idx]
        recovered = post_trough[post_trough >= peak_value]
        if len(recovered) > 0:
            recovery_idx = recovered.index[0]
    
    # Calculate durations
    drawdown_duration = (max_dd_idx - peak_idx).days if hasattr(max_dd_idx - peak_idx, 'days') else 0
    recovery_duration = None
    if recovery_idx is not None:
        recovery_duration = (recovery_idx - max_dd_idx).days if hasattr(recovery_idx - max_dd_idx, 'days') else 0
    
    return {
        "max_drawdown": float(max_dd),
        "max_drawdown_pct": float(max_dd_pct),
        "peak_date": peak_idx,
        "trough_date": max_dd_idx,
        "recovery_date": recovery_idx,
        "drawdown_duration_days": drawdown_duration,
        "recovery_duration_days": recovery_duration,
    }


def calculate_turnover(
    weights_df: pd.DataFrame,
    returns_df: pd.DataFrame = None,
) -> pd.Series:
    """
    Calculate portfolio turnover.
    
    Turnover is the sum of absolute weight changes, adjusted for returns.
    
    Args:
        weights_df: Wide DataFrame of weights (dates × symbols)
        returns_df: Optional DataFrame of returns for drift adjustment
                   If None, assumes no drift (simple weight changes)
    
    Returns:
        Series of daily turnover values
    
    Example:
        >>> turnover = calculate_turnover(weights_df, returns_df)
        >>> annual_turnover = turnover.sum()
    
    Notes:
        - Turnover on day t = sum(|w_t - w_t-1_drifted|) / 2
        - w_t-1_drifted accounts for price changes between t-1 and t
        - First day has turnover = 0
        - Uses date-based alignment to handle different rebalance frequencies
        - Compounds returns over the interval for non-daily rebalances
    """
    if len(weights_df) == 0:
        return pd.Series(dtype=float)
    
    # Initialize turnover series
    turnover = pd.Series(0.0, index=weights_df.index)
    
    if len(weights_df) == 1:
        return turnover
    
    # Calculate weight changes using date-based indexing
    for i in range(1, len(weights_df)):
        prev_date = weights_df.index[i-1]
        curr_date = weights_df.index[i]
        
        prev_weights = weights_df.loc[prev_date]
        curr_weights = weights_df.loc[curr_date]
        
        # Adjust previous weights for returns (drift)
        if returns_df is not None:
            # Get returns between prev_date and curr_date
            # Use explicit filtering to handle non-trading days correctly
            # We want returns where: prev_date < date <= curr_date
            mask = (returns_df.index > prev_date) & (returns_df.index <= curr_date)
            interval_returns = returns_df.loc[mask]
            
            # Compound returns over the interval: (1+r1)*(1+r2)*...*(1+rn) - 1
            if len(interval_returns) > 0:
                compounded_returns = (1 + interval_returns).prod() - 1
            else:
                # No returns in interval, assume zero return
                compounded_returns = pd.Series(0.0, index=prev_weights.index)
            
            # Align compounded returns to weight index to handle:
            # 1. Extra columns in returns (superset of traded assets)
            # 2. NaNs for some assets over the interval
            # Reindex to weight columns and fill missing with 0 (no return)
            compounded_returns = compounded_returns.reindex(prev_weights.index, fill_value=0.0)
            
            # Drifted weights = prev_weights * (1 + compounded_returns)
            drifted_weights = prev_weights * (1 + compounded_returns)
            # Renormalize
            if drifted_weights.sum() > 0:
                drifted_weights = drifted_weights / drifted_weights.sum()
        else:
            drifted_weights = prev_weights
        
        # Turnover = sum(|change|) / 2
        weight_change = (curr_weights - drifted_weights).abs().sum() / 2
        turnover.loc[curr_date] = weight_change
    
    return turnover


def calculate_yearly_summary(
    returns: pd.Series,
    equity_curve: pd.Series = None,
) -> pd.DataFrame:
    """
    Calculate yearly performance summary.
    
    Args:
        returns: Series of returns
        equity_curve: Optional series of equity curve
    
    Returns:
        DataFrame with yearly metrics:
            - year: Year
            - total_return: Total return for the year
            - sharpe: Sharpe ratio for the year
            - max_drawdown: Max drawdown for the year
            - volatility: Annualized volatility
    
    Example:
        >>> yearly = calculate_yearly_summary(returns, equity_curve)
    """
    if len(returns) == 0:
        return pd.DataFrame()
    
    # Group by year
    yearly_data = []
    
    for year in returns.index.year.unique():
        year_returns = returns[returns.index.year == year]
        
        # Total return
        total_return = (1 + year_returns).prod() - 1
        
        # Sharpe ratio
        sharpe = calculate_sharpe_ratio(year_returns)
        
        # Volatility
        volatility = year_returns.std() * np.sqrt(252)
        
        # Max drawdown (if equity curve provided)
        max_dd_pct = 0.0
        if equity_curve is not None:
            year_equity = equity_curve[equity_curve.index.year == year]
            if len(year_equity) > 0:
                dd_info = calculate_max_drawdown(year_equity)
                max_dd_pct = dd_info["max_drawdown_pct"]
        
        yearly_data.append({
            "year": year,
            "total_return": total_return,
            "sharpe": sharpe,
            "max_drawdown": max_dd_pct,
            "volatility": volatility,
        })
    
    return pd.DataFrame(yearly_data)


def calculate_all_metrics(
    returns: pd.Series,
    equity_curve: pd.Series,
    weights_df: pd.DataFrame = None,
    returns_df: pd.DataFrame = None,
) -> Dict[str, Any]:
    """
    Calculate all performance metrics.
    
    Args:
        returns: Series of portfolio returns
        equity_curve: Series of cumulative equity
        weights_df: Optional DataFrame of weights for turnover
        returns_df: Optional DataFrame of asset returns for turnover
    
    Returns:
        Dictionary with all metrics
    
    Example:
        >>> metrics = calculate_all_metrics(returns, equity, weights, asset_returns)
    """
    metrics = {}
    
    # Sharpe ratio
    metrics["sharpe_ratio"] = calculate_sharpe_ratio(returns)
    
    # Max drawdown
    dd_info = calculate_max_drawdown(equity_curve)
    metrics.update(dd_info)
    
    # Volatility
    metrics["volatility"] = returns.std() * np.sqrt(252)
    
    # Total return
    metrics["total_return"] = equity_curve.iloc[-1] / equity_curve.iloc[0] - 1 if len(equity_curve) > 0 else 0.0
    
    # CAGR
    if len(equity_curve) > 0:
        years = (equity_curve.index[-1] - equity_curve.index[0]).days / 365.25
        if years > 0:
            metrics["cagr"] = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1 / years) - 1
        else:
            metrics["cagr"] = 0.0
    else:
        metrics["cagr"] = 0.0
    
    # Turnover
    if weights_df is not None:
        turnover_series = calculate_turnover(weights_df, returns_df)
        metrics["avg_daily_turnover"] = turnover_series.mean()
        metrics["total_turnover"] = turnover_series.sum()
    
    # Yearly summary
    metrics["yearly_summary"] = calculate_yearly_summary(returns, equity_curve)
    
    return metrics
