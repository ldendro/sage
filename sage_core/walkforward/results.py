"""
Walkforward backtest result models.

This module defines the standardized output format for all backtests.
Results are designed to be:
- Comparable across different system configurations
- Cacheable for fast iteration
- Rich enough for comprehensive analysis
- Lightweight enough to store many systems
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import pandas as pd


@dataclass
class WalkforwardResult:
    """
    Complete result of a walkforward backtest.
    
    This is the standardized output format for all backtests in Sage.
    It contains everything needed for:
    - Performance comparison (equity curves, Sharpe, returns)
    - Risk analysis (drawdowns, leverage, concentration)
    - Implementation feasibility (turnover, weights history)
    - Reproducibility (config, metadata)
    
    Attributes:
        system_name: Human-readable system name
        config: Serialized SystemConfig (dict) for reproducibility
        equity_curve: Daily portfolio equity (index=date, values=equity)
        daily_returns: Daily portfolio returns (index=date, values=return)
        weights_history: Daily asset weights (index=date, columns=assets, values=weights)
        yearly_summary: Per-year performance metrics (index=year, columns=metrics)
        risk_metrics: Per-year risk metrics (index=year, columns=risk_metrics) [v2+]
        turnover: Per-year or per-rebalance turnover (index=year/date, columns=metrics)
        metadata: Additional information (engine version, cache info, timing, etc.)
    
    Notes:
        - All pandas objects use DatetimeIndex for time series
        - Weights sum to ~1.0 (or leverage if vol targeting applied)
        - Returns are simple returns (not log returns)
        - Equity curve starts at 1.0
    """
    
    system_name: str
    config: Dict[str, Any]
    equity_curve: pd.Series
    daily_returns: pd.Series
    weights_history: pd.DataFrame
    yearly_summary: pd.DataFrame
    turnover: pd.DataFrame
    metadata: Dict[str, Any] = field(default_factory=dict)
    risk_metrics: Optional[pd.DataFrame] = None  # v2+ feature
    
    def __post_init__(self):
        """Validate result integrity after creation."""
        # Validate equity curve and returns have same length
        if len(self.equity_curve) != len(self.daily_returns):
            raise ValueError(
                f"Equity curve ({len(self.equity_curve)}) and daily returns "
                f"({len(self.daily_returns)}) must have same length"
            )
        
        # Validate weights history has same length
        if len(self.weights_history) != len(self.daily_returns):
            raise ValueError(
                f"Weights history ({len(self.weights_history)}) and daily returns "
                f"({len(self.daily_returns)}) must have same length"
            )
        
        # Validate indices are aligned
        if not self.equity_curve.index.equals(self.daily_returns.index):
            raise ValueError("Equity curve and daily returns must have same index")
        
        if not self.weights_history.index.equals(self.daily_returns.index):
            raise ValueError("Weights history and daily returns must have same index")
    
    @property
    def start_date(self) -> pd.Timestamp:
        """First date in the backtest."""
        return self.equity_curve.index[0]
    
    @property
    def end_date(self) -> pd.Timestamp:
        """Last date in the backtest."""
        return self.equity_curve.index[-1]
    
    @property
    def num_days(self) -> int:
        """Number of trading days in the backtest."""
        return len(self.equity_curve)
    
    @property
    def num_years(self) -> float:
        """Approximate number of years in the backtest."""
        return self.num_days / 252.0
    
    @property
    def assets(self) -> list[str]:
        """List of assets in the universe."""
        return list(self.weights_history.columns)
    
    def get_yearly_metric(self, metric: str) -> pd.Series:
        """
        Get a specific yearly metric.
        
        Args:
            metric: Metric name (e.g., 'sharpe', 'return', 'max_drawdown')
        
        Returns:
            Series of yearly values for the metric
        
        Raises:
            KeyError: If metric not found in yearly_summary
        """
        if metric not in self.yearly_summary.columns:
            available = ", ".join(self.yearly_summary.columns)
            raise KeyError(f"Metric '{metric}' not found. Available: {available}")
        return self.yearly_summary[metric]
    
    def get_full_period_sharpe(self) -> float:
        """
        Calculate full-period Sharpe ratio.
        
        This is the primary metric for ranking systems.
        
        Returns:
            Annualized Sharpe ratio over the entire backtest period
        """
        import numpy as np
        returns = self.daily_returns.values
        if np.std(returns) == 0:
            return 0.0
        return float(np.sqrt(252) * np.mean(returns) / np.std(returns))
    
    def get_full_period_return(self) -> float:
        """
        Calculate full-period total return.
        
        Returns:
            Total return over the entire backtest period (e.g., 0.50 = 50%)
        """
        return float(self.equity_curve.iloc[-1] / self.equity_curve.iloc[0] - 1.0)
    
    def get_full_period_cagr(self) -> float:
        """
        Calculate full-period CAGR (Compound Annual Growth Rate).
        
        Returns:
            Annualized return over the entire backtest period
        """
        total_return = self.get_full_period_return()
        years = self.num_years
        if years == 0:
            return 0.0
        return float((1 + total_return) ** (1 / years) - 1)
    
    def get_full_period_max_drawdown(self) -> float:
        """
        Calculate full-period maximum drawdown.
        
        Returns:
            Maximum drawdown over the entire backtest period (negative value)
        """
        import numpy as np
        equity = self.equity_curve.values
        peak = np.maximum.accumulate(equity)
        drawdown = equity / peak - 1.0
        return float(drawdown.min())
    
    def get_average_leverage(self) -> float:
        """
        Calculate average leverage over the backtest.
        
        Leverage is measured as the L1 norm of weights (sum of absolute values).
        
        Returns:
            Average leverage (1.0 = fully invested, no leverage)
        """
        leverage = self.weights_history.abs().sum(axis=1)
        return float(leverage.mean())
    
    def summary_stats(self) -> Dict[str, float]:
        """
        Get summary statistics for the entire backtest.
        
        Returns:
            Dictionary of key metrics:
            - sharpe: Full-period Sharpe ratio
            - total_return: Total return
            - cagr: Compound annual growth rate
            - max_drawdown: Maximum drawdown
            - avg_leverage: Average leverage
            - num_years: Number of years
        """
        return {
            "sharpe": self.get_full_period_sharpe(),
            "total_return": self.get_full_period_return(),
            "cagr": self.get_full_period_cagr(),
            "max_drawdown": self.get_full_period_max_drawdown(),
            "avg_leverage": self.get_average_leverage(),
            "num_years": self.num_years,
        }
    
    def __repr__(self) -> str:
        """String representation."""
        stats = self.summary_stats()
        return (
            f"WalkforwardResult('{self.system_name}', "
            f"{self.start_date.date()} to {self.end_date.date()}, "
            f"Sharpe={stats['sharpe']:.2f}, "
            f"CAGR={stats['cagr']:.1%}, "
            f"MDD={stats['max_drawdown']:.1%})"
        )
