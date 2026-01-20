"""
Tests for allocators.
"""

import pytest
import pandas as pd
import numpy as np

from sage_core.allocators.inverse_vol_v1 import (
    compute_inverse_vol_weights,
    compute_equal_weights,
)
from sage_core.data.loader import load_universe
from sage_core.strategies.passthrough_v1 import run_passthrough_v1
from sage_core.portfolio.constructor import align_asset_returns


class TestComputeInverseVolWeights:
    """Tests for compute_inverse_vol_weights function."""
    
    def test_inverse_vol_basic(self):
        """Test basic inverse vol weight computation."""
        # Load data
        data = load_universe(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-03-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        # Compute weights
        weights = compute_inverse_vol_weights(returns_wide, lookback=20)
        
        # Check shape
        assert weights.shape == returns_wide.shape
        
        # Check columns match
        assert list(weights.columns) == list(returns_wide.columns)
        
        # Check index matches
        assert weights.index.equals(returns_wide.index)
    
    def test_inverse_vol_weights_sum_to_one(self):
        """Test that weights sum to 1 for each date (after warmup)."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-02-29",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        weights = compute_inverse_vol_weights(returns_wide, lookback=20)
        
        # After warmup period, weights should sum to 1
        weights_after_warmup = weights.iloc[20:]
        weight_sums = weights_after_warmup.sum(axis=1)
        
        assert np.allclose(weight_sums, 1.0)
    
    def test_inverse_vol_warmup_period(self):
        """Test that first (lookback-1) days have NaN weights."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        lookback = 10
        weights = compute_inverse_vol_weights(returns_wide, lookback=lookback)
        
        # First (lookback-1) rows should be NaN
        assert weights.iloc[:lookback-1].isna().all().all()
        
        # After warmup should have values
        assert not weights.iloc[lookback:].isna().any().any()
    
    def test_inverse_vol_higher_vol_lower_weight(self):
        """Test that higher volatility assets get lower weights."""
        # Create synthetic data with known volatilities
        dates = pd.date_range("2020-01-01", periods=100, freq="B")
        
        # Low vol asset (vol ~0.01)
        low_vol_returns = np.random.normal(0, 0.01, size=100)
        
        # High vol asset (vol ~0.03)
        high_vol_returns = np.random.normal(0, 0.03, size=100)
        
        returns_wide = pd.DataFrame({
            "LOW_VOL": low_vol_returns,
            "HIGH_VOL": high_vol_returns,
        }, index=dates)
        
        weights = compute_inverse_vol_weights(returns_wide, lookback=20)
        
        # After warmup, low vol should have higher weight
        avg_weights = weights.iloc[20:].mean()
        
        assert avg_weights["LOW_VOL"] > avg_weights["HIGH_VOL"]
    
    def test_inverse_vol_max_weight_cap(self):
        """Test that max_weight cap is enforced."""
        data = load_universe(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-02-29",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        max_weight = 0.4
        weights = compute_inverse_vol_weights(
            returns_wide,
            lookback=20,
            max_weight=max_weight,
        )
        
        # No weight should exceed max_weight
        weights_after_warmup = weights.iloc[20:]
        assert (weights_after_warmup <= max_weight + 1e-6).all().all()
    
    def test_inverse_vol_invalid_lookback(self):
        """Test that invalid lookback raises ValueError."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        with pytest.raises(ValueError, match="lookback must be >= 2"):
            compute_inverse_vol_weights(returns_wide, lookback=1)
    
    def test_inverse_vol_invalid_max_weight(self):
        """Test that invalid max_weight raises ValueError."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        with pytest.raises(ValueError, match="max_weight must be > 0"):
            compute_inverse_vol_weights(returns_wide, max_weight=0)
        
        with pytest.raises(ValueError, match="max_weight must be <= 1.0"):
            compute_inverse_vol_weights(returns_wide, max_weight=1.5)
    
    def test_inverse_vol_max_weight_too_small_for_assets(self):
        """Test that max_weight < 1/n_assets raises ValueError."""
        data = load_universe(
            universe=["SPY", "QQQ", "IWM"],  # 3 assets
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        # max_weight = 0.3 < 1/3 = 0.333... would cause underinvestment
        with pytest.raises(ValueError, match="max_weight.*too small.*assets"):
            compute_inverse_vol_weights(returns_wide, max_weight=0.3)
        
        # max_weight = 0.33 < 1/3 should also fail
        with pytest.raises(ValueError, match="max_weight.*too small.*assets"):
            compute_inverse_vol_weights(returns_wide, max_weight=0.33)
        
        # max_weight = 0.34 > 1/3 should work
        weights = compute_inverse_vol_weights(returns_wide, max_weight=0.34)
        assert weights is not None
    
    def test_inverse_vol_invalid_min_vol(self):
        """Test that invalid min_vol raises ValueError."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        # min_vol = 0 would cause division by zero
        with pytest.raises(ValueError, match="min_vol must be > 0"):
            compute_inverse_vol_weights(returns_wide, min_vol=0)
        
        # Negative min_vol should also fail
        with pytest.raises(ValueError, match="min_vol must be > 0"):
            compute_inverse_vol_weights(returns_wide, min_vol=-0.001)
    
    def test_inverse_vol_handles_zero_volatility(self):
        """Test that zero volatility assets are handled correctly."""
        # Create synthetic data with one zero-vol asset
        dates = pd.date_range("2020-01-01", periods=50, freq="B")
        
        # Normal vol asset
        normal_returns = np.random.normal(0, 0.01, size=50)
        
        # Zero vol asset (constant returns)
        zero_vol_returns = np.zeros(50)
        
        returns_wide = pd.DataFrame({
            "NORMAL": normal_returns,
            "ZERO_VOL": zero_vol_returns,
        }, index=dates)
        
        # Should work with min_vol floor
        weights = compute_inverse_vol_weights(
            returns_wide,
            lookback=20,
            min_vol=0.0001,
        )
        
        # After warmup, weights should be valid (no NaN/inf)
        weights_after_warmup = weights.iloc[20:]
        assert not weights_after_warmup.isna().any().any()
        assert not np.isinf(weights_after_warmup).any().any()
        
        # Weights should sum to 1
        assert np.allclose(weights_after_warmup.sum(axis=1), 1.0)
        
        # Zero vol asset should get higher weight (due to min_vol floor)
        avg_weights = weights_after_warmup.mean()
        assert avg_weights["ZERO_VOL"] > avg_weights["NORMAL"]
    
    def test_inverse_vol_single_asset(self):
        """Test inverse vol with single asset."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-02-29",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        weights = compute_inverse_vol_weights(returns_wide, lookback=20)
        
        # Single asset should always have weight 1.0
        weights_after_warmup = weights.iloc[20:]
        assert np.allclose(weights_after_warmup["SPY"], 1.0)


class TestComputeEqualWeights:
    """Tests for compute_equal_weights function."""
    
    def test_equal_weights_basic(self):
        """Test basic equal weight computation."""
        data = load_universe(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        weights = compute_equal_weights(returns_wide)
        
        # Check shape
        assert weights.shape == returns_wide.shape
        
        # All weights should be 1/3
        assert np.allclose(weights, 1/3)
    
    def test_equal_weights_sum_to_one(self):
        """Test that equal weights sum to 1."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        weights = compute_equal_weights(returns_wide)
        
        weight_sums = weights.sum(axis=1)
        assert np.allclose(weight_sums, 1.0)
    
    def test_equal_weights_single_asset(self):
        """Test equal weights with single asset."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        weights = compute_equal_weights(returns_wide)
        
        # Single asset should have weight 1.0
        assert np.allclose(weights["SPY"], 1.0)
