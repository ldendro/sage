"""
Tests for volatility targeting.
"""

import pytest
import pandas as pd
import numpy as np

from sage_core.portfolio.vol_targeting import (
    apply_vol_targeting,
    calculate_portfolio_volatility,
)


class TestApplyVolTargeting:
    """Tests for apply_vol_targeting function."""
    
    def test_vol_targeting_basic(self):
        """Test basic volatility targeting."""
        # Create synthetic returns with known volatility
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        # Returns with ~10% annual vol (0.01 daily std * sqrt(252) ≈ 0.16)
        returns = pd.Series(
            np.random.normal(0, 0.01, size=100),
            index=dates
        )
        
        # Equal weights
        weights = pd.DataFrame({
            "A": 0.5,
            "B": 0.5,
        }, index=dates)
        
        # Target 10% vol
        scaled = apply_vol_targeting(
            returns,
            weights,
            target_vol=0.10,
            lookback=20,
        )
        
        # Check shape
        assert scaled.shape == weights.shape
        
        # Check index matches
        assert scaled.index.equals(weights.index)
        
        # First lookback days should have leverage = 1.0 (warmup + shift)
        assert np.allclose(scaled.iloc[:20], weights.iloc[:20])
    
    def test_vol_targeting_scales_weights(self):
        """Test that vol targeting scales weights correctly."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        # High vol returns (~20% annual)
        returns = pd.Series(
            np.random.normal(0, 0.02, size=100),
            index=dates
        )
        
        weights = pd.DataFrame({
            "A": 0.6,
            "B": 0.4,
        }, index=dates)
        
        # Target 10% vol (half of realized)
        scaled = apply_vol_targeting(
            returns,
            weights,
            target_vol=0.10,
            lookback=20,
        )
        
        # After warmup, weights should be scaled down (leverage < 1)
        # Since realized vol is ~20%, leverage should be ~0.5
        avg_leverage = (scaled.iloc[20:] / weights.iloc[20:]).mean().mean()
        assert avg_leverage < 1.0
    
    def test_vol_targeting_leverage_caps(self):
        """Test that leverage is capped correctly."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        # Very low vol returns
        returns = pd.Series(
            np.random.normal(0, 0.001, size=100),
            index=dates
        )
        
        weights = pd.DataFrame({
            "A": 0.5,
            "B": 0.5,
        }, index=dates)
        
        # Target high vol with low max leverage
        scaled = apply_vol_targeting(
            returns,
            weights,
            target_vol=0.20,
            lookback=20,
            max_leverage=1.5,
        )
        
        # Leverage should not exceed 1.5
        leverage = (scaled / weights).max().max()
        assert leverage <= 1.5 + 1e-6
    
    def test_vol_targeting_min_leverage(self):
        """Test minimum leverage constraint."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        # High vol returns
        returns = pd.Series(
            np.random.normal(0, 0.05, size=100),
            index=dates
        )
        
        weights = pd.DataFrame({
            "A": 0.5,
            "B": 0.5,
        }, index=dates)
        
        # Target low vol with min leverage
        scaled = apply_vol_targeting(
            returns,
            weights,
            target_vol=0.05,
            lookback=20,
            min_leverage=0.5,
        )
        
        # Leverage should not go below 0.5
        leverage = (scaled.iloc[20:] / weights.iloc[20:]).min().min()
        assert leverage >= 0.5 - 1e-6
    
    def test_vol_targeting_invalid_params(self):
        """Test that invalid parameters raise ValueError."""
        dates = pd.date_range("2020-01-01", periods=50, freq="B")
        returns = pd.Series(np.random.normal(0, 0.01, 50), index=dates)
        weights = pd.DataFrame({"A": 0.5, "B": 0.5}, index=dates)
        
        # target_vol <= 0
        with pytest.raises(ValueError, match="target_vol must be > 0"):
            apply_vol_targeting(returns, weights, target_vol=0)
        
        # lookback < 2
        with pytest.raises(ValueError, match="lookback must be >= 2"):
            apply_vol_targeting(returns, weights, lookback=1)
        
        # min_leverage < 0
        with pytest.raises(ValueError, match="min_leverage must be >= 0"):
            apply_vol_targeting(returns, weights, min_leverage=-0.1)
        
        # max_leverage <= 0
        with pytest.raises(ValueError, match="max_leverage must be > 0"):
            apply_vol_targeting(returns, weights, max_leverage=0)
        
        # min_leverage > max_leverage
        with pytest.raises(ValueError, match="cannot exceed max_leverage"):
            apply_vol_targeting(returns, weights, min_leverage=2.0, max_leverage=1.0)
    
    def test_vol_targeting_mismatched_indices(self):
        """Test that mismatched indices raise ValueError."""
        dates1 = pd.date_range("2020-01-01", periods=50, freq="B")
        dates2 = pd.date_range("2020-02-01", periods=50, freq="B")
        
        returns = pd.Series(np.random.normal(0, 0.01, 50), index=dates1)
        weights = pd.DataFrame({"A": 0.5, "B": 0.5}, index=dates2)
        
        with pytest.raises(ValueError, match="must have the same index"):
            apply_vol_targeting(returns, weights)
    
    def test_vol_targeting_warmup_period(self):
        """Test that warmup period has leverage = 1.0."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        returns = pd.Series(
            np.random.normal(0, 0.01, size=100),
            index=dates
        )
        
        weights = pd.DataFrame({
            "A": 0.6,
            "B": 0.4,
        }, index=dates)
        
        lookback = 30
        scaled = apply_vol_targeting(
            returns,
            weights,
            target_vol=0.10,
            lookback=lookback,
        )
        
        # First lookback days should have leverage = 1.0 (warmup + shift)
        warmup_leverage = (scaled.iloc[:lookback] / weights.iloc[:lookback])
        assert np.allclose(warmup_leverage, 1.0)
    
    def test_vol_targeting_no_lookahead_bias(self):
        """Test that volatility calculation doesn't use future information."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        # Create returns with a known spike on day 50
        returns = pd.Series(np.random.normal(0, 0.01, size=100), index=dates)
        returns.iloc[50] = 0.10  # Large spike
        
        weights = pd.DataFrame({
            "A": 0.5,
            "B": 0.5,
        }, index=dates)
        
        lookback = 20
        scaled = apply_vol_targeting(
            returns,
            weights,
            target_vol=0.10,
            lookback=lookback,
        )
        
        # The leverage on day 50 should NOT be affected by day 50's return
        # It should only use returns through day 49
        # So the spike on day 50 should affect leverage starting on day 51
        leverage_day_50 = (scaled.iloc[50] / weights.iloc[50]).mean()
        leverage_day_51 = (scaled.iloc[51] / weights.iloc[51]).mean()
        
        # Day 51's leverage should be lower than day 50's (due to spike increasing vol)
        assert leverage_day_51 < leverage_day_50


class TestCalculatePortfolioVolatility:
    """Tests for calculate_portfolio_volatility function."""
    
    def test_calculate_vol_basic(self):
        """Test basic volatility calculation."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        # Returns with known std
        returns = pd.Series(
            np.random.normal(0, 0.01, size=100),
            index=dates
        )
        
        vol = calculate_portfolio_volatility(returns, lookback=20, annualize=True)
        
        # Check shape
        assert len(vol) == len(returns)
        
        # First (lookback-1) should be NaN
        assert vol.iloc[:19].isna().all()
        
        # After warmup should have values
        assert not vol.iloc[19:].isna().any()
    
    def test_calculate_vol_annualized(self):
        """Test annualized vs non-annualized volatility."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        returns = pd.Series(
            np.random.normal(0, 0.01, size=100),
            index=dates
        )
        
        vol_ann = calculate_portfolio_volatility(returns, lookback=20, annualize=True)
        vol_daily = calculate_portfolio_volatility(returns, lookback=20, annualize=False)
        
        # Annualized should be ~sqrt(252) times daily
        ratio = (vol_ann.iloc[20:] / vol_daily.iloc[20:]).mean()
        assert np.isclose(ratio, np.sqrt(252), rtol=0.1)
    
    def test_calculate_vol_different_lookbacks(self):
        """Test different lookback periods."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", periods=200, freq="B")
        
        returns = pd.Series(
            np.random.normal(0, 0.01, size=200),
            index=dates
        )
        
        vol_short = calculate_portfolio_volatility(returns, lookback=20)
        vol_long = calculate_portfolio_volatility(returns, lookback=60)
        
        # Short lookback should be more volatile (reactive)
        # Long lookback should be smoother
        vol_short_std = vol_short.iloc[60:].std()
        vol_long_std = vol_long.iloc[60:].std()
        
        assert vol_short_std > vol_long_std
