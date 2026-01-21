"""
Tests for performance metrics.
"""

import pytest
import pandas as pd
import numpy as np

from sage_core.metrics.performance import (
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_turnover,
    calculate_yearly_summary,
    calculate_all_metrics,
)


class TestCalculateSharpeRatio:
    """Tests for calculate_sharpe_ratio function."""
    
    def test_sharpe_basic(self):
        """Test basic Sharpe ratio calculation."""
        # Create returns with known mean and std
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.001, 0.01, 252))
        
        sharpe = calculate_sharpe_ratio(returns)
        
        # Should be positive (positive mean return)
        assert sharpe > 0
        
        # Rough check: sharpe ≈ mean / std * sqrt(252)
        expected = returns.mean() / returns.std() * np.sqrt(252)
        assert np.isclose(sharpe, expected, rtol=0.01)
    
    def test_sharpe_zero_returns(self):
        """Test Sharpe with zero returns."""
        returns = pd.Series([0.0] * 100)
        sharpe = calculate_sharpe_ratio(returns)
        assert sharpe == 0.0
    
    def test_sharpe_empty_returns(self):
        """Test Sharpe with empty returns."""
        returns = pd.Series([], dtype=float)
        sharpe = calculate_sharpe_ratio(returns)
        assert sharpe == 0.0
    
    def test_sharpe_with_risk_free_rate(self):
        """Test Sharpe with risk-free rate."""
        returns = pd.Series([0.001] * 252)
        
        sharpe_no_rf = calculate_sharpe_ratio(returns, risk_free_rate=0.0)
        sharpe_with_rf = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        
        # With positive risk-free rate, Sharpe should be lower
        assert sharpe_with_rf < sharpe_no_rf
    
    def test_sharpe_with_nans(self):
        """Test Sharpe with NaN values in returns."""
        returns = pd.Series([0.001, np.nan, 0.002, np.nan, 0.001])
        
        # Should drop NaNs and calculate on valid values
        sharpe = calculate_sharpe_ratio(returns)
        
        # Should be a valid number, not NaN
        assert not np.isnan(sharpe)
        assert isinstance(sharpe, float)
    
    def test_sharpe_all_nans(self):
        """Test Sharpe with all NaN returns."""
        returns = pd.Series([np.nan, np.nan, np.nan])
        
        sharpe = calculate_sharpe_ratio(returns)
        
        # Should return 0, not NaN
        assert sharpe == 0.0
    
    def test_sharpe_single_value(self):
        """Test Sharpe with single non-NaN value."""
        returns = pd.Series([0.001])
        
        sharpe = calculate_sharpe_ratio(returns)
        
        # Single value has std = 0, should return 0
        assert sharpe == 0.0


class TestCalculateMaxDrawdown:
    """Tests for calculate_max_drawdown function."""
    
    def test_max_drawdown_basic(self):
        """Test basic max drawdown calculation."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        
        # Equity curve with known drawdown
        equity = pd.Series([100, 110, 105, 95, 90, 100, 110, 105, 115, 120], index=dates)
        
        dd_info = calculate_max_drawdown(equity)
        
        # Max DD should be from 110 to 90 = -20
        assert dd_info["max_drawdown"] == -20
        assert np.isclose(dd_info["max_drawdown_pct"], -20/110)
        
        # Peak should be at index 1 (110)
        assert dd_info["peak_date"] == dates[1]
        
        # Trough should be at index 4 (90)
        assert dd_info["trough_date"] == dates[4]
        
        # Should recover at index 5 (100 < 110, but let's check)
        # Actually recovers at index 6 (110)
        assert dd_info["recovery_date"] == dates[6]
    
    def test_max_drawdown_no_recovery(self):
        """Test max drawdown with no recovery."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        
        # Continuous decline
        equity = pd.Series([100, 90, 80, 70, 60], index=dates)
        
        dd_info = calculate_max_drawdown(equity)
        
        # Max DD should be -40 (from 100 to 60)
        assert dd_info["max_drawdown"] == -40
        
        # No recovery
        assert dd_info["recovery_date"] is None
        assert dd_info["recovery_duration_days"] is None
    
    def test_max_drawdown_empty(self):
        """Test max drawdown with empty series."""
        equity = pd.Series([], dtype=float)
        
        dd_info = calculate_max_drawdown(equity)
        
        assert dd_info["max_drawdown"] == 0.0
        assert dd_info["peak_date"] is None
    
    def test_max_drawdown_no_drawdown(self):
        """Test with no drawdown (monotonically increasing)."""
        dates = pd.date_range("2020-01-01", periods=5, freq="D")
        equity = pd.Series([100, 110, 120, 130, 140], index=dates)
        
        dd_info = calculate_max_drawdown(equity)
        
        # Max DD should be 0 (no drawdown)
        assert dd_info["max_drawdown"] == 0.0
    
    def test_max_drawdown_repeated_peaks(self):
        """Test that last peak is selected when there are multiple peaks."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        
        # Equity reaches 110 twice before dropping to 90
        # Should use the LAST peak at index 5, not the first at index 1
        equity = pd.Series([100, 110, 105, 100, 105, 110, 105, 100, 95, 90], index=dates)
        
        dd_info = calculate_max_drawdown(equity)
        
        # Max DD should be from 110 to 90 = -20
        assert dd_info["max_drawdown"] == -20
        assert np.isclose(dd_info["max_drawdown_pct"], -20/110)
        
        # Peak should be at index 5 (last occurrence of 110), not index 1
        assert dd_info["peak_date"] == dates[5]
        
        # Trough should be at index 9 (90)
        assert dd_info["trough_date"] == dates[9]
        
        # Drawdown duration should be 4 days (from index 5 to 9)
        # Not 8 days (from index 1 to 9)
        assert dd_info["drawdown_duration_days"] == 4


class TestCalculateTurnover:
    """Tests for calculate_turnover function."""
    
    def test_turnover_basic(self):
        """Test basic turnover calculation."""
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        
        # Simple weight changes
        weights = pd.DataFrame({
            "A": [0.5, 0.6, 0.5],
            "B": [0.5, 0.4, 0.5],
        }, index=dates)
        
        turnover = calculate_turnover(weights)
        
        # First day should be 0
        assert turnover.iloc[0] == 0.0
        
        # Day 2: |0.6-0.5| + |0.4-0.5| = 0.2, turnover = 0.2/2 = 0.1
        assert np.isclose(turnover.iloc[1], 0.1)
        
        # Day 3: |0.5-0.6| + |0.5-0.4| = 0.2, turnover = 0.2/2 = 0.1
        assert np.isclose(turnover.iloc[2], 0.1)
    
    def test_turnover_with_drift(self):
        """Test turnover with return drift adjustment."""
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        
        weights = pd.DataFrame({
            "A": [0.5, 0.5, 0.5],
            "B": [0.5, 0.5, 0.5],
        }, index=dates)
        
        # Asset A goes up 10%, B goes down 10%
        returns = pd.DataFrame({
            "A": [0.0, 0.1, 0.0],
            "B": [0.0, -0.1, 0.0],
        }, index=dates)
        
        turnover = calculate_turnover(weights, returns)
        
        # Day 2: After drift, A would be 0.55/(0.55+0.45) = 0.55
        # To rebalance to 0.5, need to sell 0.05 of A, buy 0.05 of B
        # Turnover = (0.05 + 0.05) / 2 = 0.05
        assert turnover.iloc[1] > 0
    
    def test_turnover_empty(self):
        """Test turnover with empty weights."""
        weights = pd.DataFrame()
        turnover = calculate_turnover(weights)
        assert len(turnover) == 0
    
    def test_turnover_single_day(self):
        """Test turnover with single day."""
        dates = pd.date_range("2020-01-01", periods=1, freq="D")
        weights = pd.DataFrame({"A": [0.5], "B": [0.5]}, index=dates)
        
        turnover = calculate_turnover(weights)
        
        assert len(turnover) == 1
        assert turnover.iloc[0] == 0.0
    
    def test_turnover_different_frequencies(self):
        """Test turnover with weekly weights and daily returns."""
        # Weekly weights (rebalance every 5 days)
        weight_dates = pd.date_range("2020-01-01", periods=3, freq="5D")
        weights = pd.DataFrame({
            "A": [0.5, 0.5, 0.5],  # Keep constant to isolate drift effect
            "B": [0.5, 0.5, 0.5],
        }, index=weight_dates)
        
        # Daily returns - create known returns to test compounding
        return_dates = pd.date_range("2020-01-01", periods=11, freq="D")
        # Asset A gains 1% per day, B loses 1% per day
        returns = pd.DataFrame({
            "A": [0.01] * 11,
            "B": [-0.01] * 11,
        }, index=return_dates)
        
        # Calculate turnover
        turnover = calculate_turnover(weights, returns)
        
        # Should have same length as weights
        assert len(turnover) == len(weights)
        
        # First day should be 0
        assert turnover.iloc[0] == 0.0
        
        # Second rebalance (after 5 days of returns):
        # A: 0.5 * (1.01^5) = 0.5 * 1.051 ≈ 0.5255
        # B: 0.5 * (0.99^5) = 0.5 * 0.951 ≈ 0.4755
        # After renorm: A ≈ 0.525, B ≈ 0.475
        # To rebalance to 0.5/0.5, need turnover ≈ 0.025
        # Turnover should be > 0 due to drift
        assert turnover.iloc[1] > 0
        
        # Should be approximately 0.025 (half of the weight shift)
        # (0.525 - 0.5) + (0.5 - 0.475) = 0.05, turnover = 0.05/2 = 0.025
        assert 0.02 < turnover.iloc[1] < 0.03
    
    def test_turnover_non_trading_day_rebalance(self):
        """Test turnover when rebalance dates fall on non-trading days."""
        # Rebalance on dates that include weekends (not in returns)
        weight_dates = pd.to_datetime(["2020-01-03", "2020-01-12", "2020-01-19"])  # Fri, Sun, Sun
        weights = pd.DataFrame({
            "A": [0.5, 0.5, 0.5],
            "B": [0.5, 0.5, 0.5],
        }, index=weight_dates)
        
        # Daily returns only on business days
        return_dates = pd.bdate_range("2020-01-03", "2020-01-20", freq="B")
        # A gains 1% per day, B loses 1% per day
        returns = pd.DataFrame({
            "A": [0.01] * len(return_dates),
            "B": [-0.01] * len(return_dates),
        }, index=return_dates)
        
        # Calculate turnover
        turnover = calculate_turnover(weights, returns)
        
        # Should work without error
        assert len(turnover) == len(weights)
        
        # First rebalance should be 0
        assert turnover.iloc[0] == 0.0
        
        # Second rebalance (Jan 12, Sunday - not in returns)
        # Should use returns from Jan 3 (exclusive) to Jan 10 (last trading day before Jan 12)
        # That's 5 business days: Jan 6-10
        # A: 0.5 * 1.01^5 ≈ 0.5255, B: 0.5 * 0.99^5 ≈ 0.4755
        # Turnover ≈ 0.025
        assert turnover.iloc[1] > 0
        assert 0.02 < turnover.iloc[1] < 0.03
    
    def test_turnover_extra_columns_and_nans(self):
        """Test turnover with extra columns in returns and NaNs."""
        dates = pd.date_range("2020-01-01", periods=3, freq="D")
        
        # Weights only for A and B
        weights = pd.DataFrame({
            "A": [0.5, 0.6, 0.5],
            "B": [0.5, 0.4, 0.5],
        }, index=dates)
        
        # Returns have extra column C and some NaNs
        returns = pd.DataFrame({
            "A": [0.01, 0.01, np.nan],  # NaN on day 3
            "B": [0.01, 0.01, 0.01],
            "C": [0.02, 0.02, 0.02],  # Extra column not in weights
        }, index=dates)
        
        # Should work without error and not produce NaN turnover
        turnover = calculate_turnover(weights, returns)
        
        # Should have same length as weights
        assert len(turnover) == len(weights)
        
        # No NaN values in turnover
        assert not turnover.isna().any()
        
        # First day should be 0
        assert turnover.iloc[0] == 0.0
        
        # Subsequent days should have valid turnover
        assert turnover.iloc[1] > 0
        assert turnover.iloc[2] > 0


class TestCalculateYearlySummary:
    """Tests for calculate_yearly_summary function."""
    
    def test_yearly_summary_basic(self):
        """Test basic yearly summary."""
        # Create 2 years of data
        dates = pd.date_range("2020-01-01", periods=504, freq="B")  # ~2 years
        np.random.seed(42)
        returns = pd.Series(np.random.normal(0.0005, 0.01, 504), index=dates)
        
        equity = (1 + returns).cumprod() * 100
        
        yearly = calculate_yearly_summary(returns, equity)
        
        # Should have 2 years
        assert len(yearly) == 2
        assert 2020 in yearly["year"].values
        assert 2021 in yearly["year"].values
        
        # Check columns
        assert "total_return" in yearly.columns
        assert "sharpe" in yearly.columns
        assert "max_drawdown" in yearly.columns
        assert "volatility" in yearly.columns
    
    def test_yearly_summary_empty(self):
        """Test yearly summary with empty returns."""
        returns = pd.Series([], dtype=float)
        yearly = calculate_yearly_summary(returns)
        
        assert len(yearly) == 0
    
    def test_yearly_summary_without_equity(self):
        """Test yearly summary without equity curve."""
        dates = pd.date_range("2020-01-01", periods=252, freq="B")
        returns = pd.Series(np.random.normal(0.001, 0.01, 252), index=dates)
        
        yearly = calculate_yearly_summary(returns, equity_curve=None)
        
        assert len(yearly) == 1
        # Max drawdown should be 0 without equity curve
        assert yearly["max_drawdown"].iloc[0] == 0.0


class TestCalculateAllMetrics:
    """Tests for calculate_all_metrics function."""
    
    def test_all_metrics_basic(self):
        """Test comprehensive metrics calculation."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=252, freq="B")
        
        returns = pd.Series(np.random.normal(0.001, 0.01, 252), index=dates)
        equity = (1 + returns).cumprod() * 100
        
        weights = pd.DataFrame({
            "A": np.random.uniform(0.3, 0.7, 252),
            "B": np.random.uniform(0.3, 0.7, 252),
        }, index=dates)
        # Normalize weights
        weights = weights.div(weights.sum(axis=1), axis=0)
        
        asset_returns = pd.DataFrame({
            "A": np.random.normal(0.001, 0.01, 252),
            "B": np.random.normal(0.001, 0.01, 252),
        }, index=dates)
        
        metrics = calculate_all_metrics(returns, equity, weights, asset_returns)
        
        # Check all expected keys
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert "max_drawdown_pct" in metrics
        assert "volatility" in metrics
        assert "total_return" in metrics
        assert "cagr" in metrics
        assert "avg_daily_turnover" in metrics
        assert "total_turnover" in metrics
        assert "yearly_summary" in metrics
        
        # Check types
        assert isinstance(metrics["sharpe_ratio"], float)
        assert isinstance(metrics["yearly_summary"], pd.DataFrame)
    
    def test_all_metrics_without_turnover(self):
        """Test metrics without turnover calculation."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        returns = pd.Series(np.random.normal(0.001, 0.01, 100), index=dates)
        equity = (1 + returns).cumprod() * 100
        
        metrics = calculate_all_metrics(returns, equity)
        
        # Should not have turnover metrics
        assert "avg_daily_turnover" not in metrics
        assert "total_turnover" not in metrics
        
        # Should have other metrics
        assert "sharpe_ratio" in metrics
        assert "cagr" in metrics
