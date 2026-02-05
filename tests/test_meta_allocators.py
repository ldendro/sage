"""Tests for meta allocators."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from sage_core.meta.base import MetaAllocator
from sage_core.meta.fixed_weight import FixedWeightAllocator
from sage_core.meta.risk_parity import RiskParityAllocator


class TestFixedWeightAllocator:
    """Tests for FixedWeightAllocator."""
    
    def test_initialization_valid(self):
        """Test valid initialization."""
        allocator = FixedWeightAllocator(params={
            'weights': {'trend': 0.6, 'meanrev': 0.4}
        })
        assert allocator.params['weights'] == {'trend': 0.6, 'meanrev': 0.4}
    
    def test_validation_weights_sum(self):
        """Test weights must sum to 1.0."""
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            FixedWeightAllocator(params={
                'weights': {'trend': 0.5, 'meanrev': 0.4}
            })
    
    def test_validation_negative_weights(self):
        """Test no negative weights allowed."""
        with pytest.raises(ValueError, match="must be >= 0"):
            FixedWeightAllocator(params={
                'weights': {'trend': 1.2, 'meanrev': -0.2}
            })
    
    def test_validation_missing_weights(self):
        """Test weights parameter required."""
        with pytest.raises(ValueError, match="requires 'weights' parameter"):
            FixedWeightAllocator(params={})
    
    def test_validation_empty_weights(self):
        """Test weights dict cannot be empty."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FixedWeightAllocator(params={'weights': {}})
    
    def test_warmup_period_zero(self):
        """Test fixed weight has no warmup."""
        allocator = FixedWeightAllocator(params={
            'weights': {'trend': 0.6, 'meanrev': 0.4}
        })
        assert allocator.get_warmup_period() == 0
    
    def test_calculate_weights_constant(self):
        """Test weights are constant over time."""
        dates = pd.date_range('2020-01-01', periods=100)
        returns = {
            'trend': pd.Series(np.random.randn(100) * 0.01, index=dates),
            'meanrev': pd.Series(np.random.randn(100) * 0.01, index=dates)
        }
        
        allocator = FixedWeightAllocator(params={
            'weights': {'trend': 0.6, 'meanrev': 0.4}
        })
        
        weights = allocator.calculate_weights(returns)
        
        assert weights.shape == (100, 2)
        assert (weights['trend'] == 0.6).all()
        assert (weights['meanrev'] == 0.4).all()
    
    def test_calculate_weights_missing_strategy(self):
        """Test error if strategy missing from weights."""
        dates = pd.date_range('2020-01-01', periods=100)
        returns = {
            'trend': pd.Series(np.random.randn(100) * 0.01, index=dates),
            'meanrev': pd.Series(np.random.randn(100) * 0.01, index=dates),
            'carry': pd.Series(np.random.randn(100) * 0.01, index=dates)
        }
        
        allocator = FixedWeightAllocator(params={
            'weights': {'trend': 0.6, 'meanrev': 0.4}
        })
        
        with pytest.raises(ValueError, match="No weight specified for strategy 'carry'"):
            allocator.calculate_weights(returns)
    
    def test_allocate_basic(self):
        """Test basic allocation with fixed weights."""
        dates = pd.date_range('2020-01-01', periods=100)
        returns = {
            'trend': pd.Series([0.01] * 100, index=dates),
            'meanrev': pd.Series([0.02] * 100, index=dates)
        }
        
        allocator = FixedWeightAllocator(params={
            'weights': {'trend': 0.6, 'meanrev': 0.4}
        })
        
        result = allocator.allocate(returns)
        
        assert 'combined_returns' in result
        assert 'weights' in result
        assert 'individual_returns' in result
        
        # Combined = 0.6*0.01 + 0.4*0.02 = 0.014
        expected = 0.6 * 0.01 + 0.4 * 0.02
        assert np.allclose(result['combined_returns'], expected)


class TestRiskParityAllocator:
    """Tests for RiskParityAllocator."""
    
    def test_initialization_defaults(self):
        """Test initialization with default parameters."""
        allocator = RiskParityAllocator()
        assert allocator.params['vol_lookback'] == 60
        assert allocator.params['min_weight'] == 0.0
        assert allocator.params['max_weight'] == 1.0
    
    def test_initialization_custom(self):
        """Test initialization with custom parameters."""
        allocator = RiskParityAllocator(params={'vol_lookback': 120})
        assert allocator.params['vol_lookback'] == 120
    
    def test_validation_vol_lookback(self):
        """Test vol_lookback validation."""
        with pytest.raises(ValueError, match="vol_lookback must be int >= 10"):
            RiskParityAllocator(params={'vol_lookback': 5})
        
        with pytest.raises(ValueError, match="vol_lookback too large"):
            RiskParityAllocator(params={'vol_lookback': 300})
    
    def test_validation_min_max_weights(self):
        """Test min/max weight validation."""
        with pytest.raises(ValueError, match="min_weight must be >= 0"):
            RiskParityAllocator(params={'min_weight': -0.1})
        
        with pytest.raises(ValueError, match="max_weight must be <= 1"):
            RiskParityAllocator(params={'max_weight': 1.5})
        
        with pytest.raises(ValueError, match="min_weight .* must be < max_weight"):
            RiskParityAllocator(params={'min_weight': 0.6, 'max_weight': 0.4})
    
    def test_warmup_period(self):
        """Test warmup period equals vol_lookback."""
        allocator = RiskParityAllocator(params={'vol_lookback': 120})
        assert allocator.get_warmup_period() == 120
    
    def test_calculate_weights_inverse_vol(self):
        """Test weights are inversely proportional to volatility."""
        dates = pd.date_range('2020-01-01', periods=200)
        
        # High vol strategy (std ~0.02)
        high_vol = pd.Series(np.random.randn(200) * 0.02, index=dates)
        # Low vol strategy (std ~0.01)
        low_vol = pd.Series(np.random.randn(200) * 0.01, index=dates)
        
        returns = {'high_vol': high_vol, 'low_vol': low_vol}
        
        allocator = RiskParityAllocator(params={'vol_lookback': 60})
        weights = allocator.calculate_weights(returns)
        
        # After warmup, low vol should have higher weight
        # Check last 50 days
        assert (weights['low_vol'].iloc[-50:] > weights['high_vol'].iloc[-50:]).mean() > 0.8
    
    def test_calculate_weights_sum_to_one(self):
        """Test weights sum to 1.0 at each timestamp."""
        dates = pd.date_range('2020-01-01', periods=200)
        returns = {
            'trend': pd.Series(np.random.randn(200) * 0.01, index=dates),
            'meanrev': pd.Series(np.random.randn(200) * 0.015, index=dates),
            'carry': pd.Series(np.random.randn(200) * 0.008, index=dates)
        }
        
        allocator = RiskParityAllocator(params={'vol_lookback': 60})
        weights = allocator.calculate_weights(returns)
        
        # After warmup, weights should sum to 1
        row_sums = weights.iloc[60:].sum(axis=1)
        assert np.allclose(row_sums, 1.0)
    
    def test_calculate_weights_zero_volatility(self):
        """Test handling of zero volatility."""
        dates = pd.date_range('2020-01-01', periods=200)
        
        # Normal strategy
        normal = pd.Series(np.random.randn(200) * 0.01, index=dates)
        # Flat strategy (zero vol)
        flat = pd.Series([0.0] * 200, index=dates)
        
        returns = {'normal': normal, 'flat': flat}
        
        allocator = RiskParityAllocator(params={'vol_lookback': 60})
        weights = allocator.calculate_weights(returns)
        
        # Should not have NaN or inf except for first row because of lookahead avoidance shift
        assert not weights[1:].isna().any().any()
        assert not np.isinf(weights[1:]).any().any()
        
        # After warmup, normal strategy should have most weight
        assert (weights['normal'].iloc[-50:] > 0.9).mean() > 0.8
    
    def test_calculate_weights_all_zero_volatility(self):
        """Test equal weights when all strategies have zero volatility."""
        dates = pd.date_range('2020-01-01', periods=200)
        
        # All flat
        flat1 = pd.Series([0.0] * 200, index=dates)
        flat2 = pd.Series([0.0] * 200, index=dates)
        
        returns = {'flat1': flat1, 'flat2': flat2}
        
        allocator = RiskParityAllocator(params={'vol_lookback': 60})
        weights = allocator.calculate_weights(returns)
        
        # Should default to equal weight
        assert np.allclose(weights['flat1'].iloc[60:], 0.5)
        assert np.allclose(weights['flat2'].iloc[60:], 0.5)
    
    def test_allocate_with_warmup(self):
        """Test allocation respects warmup period."""
        dates = pd.date_range('2020-01-01', periods=200)
        returns = {
            'trend': pd.Series(np.random.randn(200) * 0.01, index=dates),
            'meanrev': pd.Series(np.random.randn(200) * 0.01, index=dates)
        }
        
        allocator = RiskParityAllocator(params={'vol_lookback': 60})
        result = allocator.allocate(returns)
        
        # First 60 days should be NaN (warmup)
        assert result['weights'].iloc[:60].isna().all().all()
        assert result['combined_returns'].iloc[:60].isna().all()
        
        # After warmup should have values
        assert not result['weights'].iloc[60:].isna().any().any()
        assert not result['combined_returns'].iloc[60:].isna().any()


class TestWarmupAlignment:
    """Tests for warmup alignment logic."""
    
    def test_align_different_warmups(self):
        """Test alignment when strategies have different warmup periods."""
        dates = pd.date_range('2020-01-01', periods=100)
        
        # Trend has warmup of 3 days
        trend = pd.Series([np.nan, np.nan, np.nan] + [0.01] * 97, index=dates)
        # MeanRev has warmup of 2 days
        meanrev = pd.Series([np.nan, np.nan] + [0.02] * 98, index=dates)
        
        returns = {'trend': trend, 'meanrev': meanrev}
        
        allocator = FixedWeightAllocator(params={
            'weights': {'trend': 0.5, 'meanrev': 0.5}
        })
        
        result = allocator.allocate(returns)
        
        # Both should start at index 3 (max warmup) for fair comparison
        assert result['individual_returns']['trend'].iloc[:3].isna().all()
        assert result['individual_returns']['meanrev'].iloc[:3].isna().all()
        assert not result['individual_returns']['trend'].iloc[3:].isna().any()
        assert not result['individual_returns']['meanrev'].iloc[3:].isna().any()
    
    def test_align_same_warmup(self):
        """Test alignment when strategies have same warmup."""
        dates = pd.date_range('2020-01-01', periods=100)
        
        # Both have warmup of 2 days
        trend = pd.Series([np.nan, np.nan] + [0.01] * 98, index=dates)
        meanrev = pd.Series([np.nan, np.nan] + [0.02] * 98, index=dates)
        
        returns = {'trend': trend, 'meanrev': meanrev}
        
        allocator = FixedWeightAllocator(params={
            'weights': {'trend': 0.5, 'meanrev': 0.5}
        })
        
        result = allocator.allocate(returns)
        
        # Both should start at index 2
        assert result['individual_returns']['trend'].iloc[:2].isna().all()
        assert result['individual_returns']['meanrev'].iloc[:2].isna().all()
    
    def test_two_layer_warmup(self):
        """Test two-layer warmup (strategy + allocator)."""
        dates = pd.date_range('2020-01-01', periods=200)
        
        # Strategies have warmup of 10 days
        trend = pd.Series([np.nan] * 10 + [0.01] * 190, index=dates)
        meanrev = pd.Series([np.nan] * 10 + [0.02] * 190, index=dates)
        
        returns = {'trend': trend, 'meanrev': meanrev}
        
        # Risk parity has warmup of 60 days
        allocator = RiskParityAllocator(params={'vol_lookback': 60})
        result = allocator.allocate(returns)
        
        # Total warmup = max(10, 10) + 60 = 70 days
        # First 10 days: strategy warmup (aligned)
        # Next 60 days: allocator warmup
        # Total: 70 days
        assert result['combined_returns'].iloc[:70].isna().all()
        assert not result['combined_returns'].iloc[70:].isna().any()


class TestIntegration:
    """Integration tests with real strategies."""
    
    def test_fixed_weight_with_strategies(self):
        """Test fixed weight allocator with trend and meanrev strategies."""
        from sage_core.strategies.trend import TrendStrategy
        from sage_core.strategies.meanrev import MeanRevStrategy
        from sage_core.data.loader import load_universe
        
        # Load data
        data = load_universe(["SPY"], "2020-01-01", "2023-12-31")
        
        # Run strategies
        trend = TrendStrategy()
        meanrev = MeanRevStrategy()
        
        trend_result = trend.run(data)
        meanrev_result = meanrev.run(data)
        
        # Extract returns
        trend_returns = trend_result["SPY"]["meta_raw_ret"]
        meanrev_returns = meanrev_result["SPY"]["meta_raw_ret"]
        
        strategy_returns = {
            "trend": trend_returns,
            "meanrev": meanrev_returns
        }
        
        # Allocate
        allocator = FixedWeightAllocator(params={
            'weights': {'trend': 0.6, 'meanrev': 0.4}
        })
        result = allocator.allocate(strategy_returns)
        
        # Verify structure
        assert 'combined_returns' in result
        assert 'weights' in result
        assert 'individual_returns' in result
        
        # Find first valid index (after warmup)
        first_valid_idx = result['weights']['trend'].first_valid_index()
        weights_after_warmup = result['weights'].loc[first_valid_idx:]
        
        # Verify weights are constant after warmup
        assert (weights_after_warmup['trend'] == 0.6).all()
        assert (weights_after_warmup['meanrev'] == 0.4).all()
        
        # Verify combined returns
        aligned_trend = result['individual_returns']['trend'].loc[first_valid_idx:]
        aligned_meanrev = result['individual_returns']['meanrev'].loc[first_valid_idx:]
        expected = 0.6 * aligned_trend + 0.4 * aligned_meanrev
        combined_after_warmup = result['combined_returns'].loc[first_valid_idx:]
        
        assert np.allclose(combined_after_warmup.dropna(), expected.dropna())
    
    def test_risk_parity_with_strategies(self):
        """Test risk parity allocator with trend and meanrev strategies."""
        from sage_core.strategies.trend import TrendStrategy
        from sage_core.strategies.meanrev import MeanRevStrategy
        from sage_core.data.loader import load_universe
        
        # Load data
        data = load_universe(["SPY"], "2020-01-01", "2023-12-31")
        
        # Run strategies
        trend = TrendStrategy()
        meanrev = MeanRevStrategy()
        
        trend_result = trend.run(data)
        meanrev_result = meanrev.run(data)
        
        # Extract returns
        trend_returns = trend_result["SPY"]["meta_raw_ret"]
        meanrev_returns = meanrev_result["SPY"]["meta_raw_ret"]
        
        strategy_returns = {
            "trend": trend_returns,
            "meanrev": meanrev_returns
        }
        
        # Allocate
        allocator = RiskParityAllocator(params={'vol_lookback': 60})
        result = allocator.allocate(strategy_returns)
        
        # Verify structure
        assert 'combined_returns' in result
        assert 'weights' in result
        assert 'individual_returns' in result
        
        # Find first valid index (after total warmup)
        first_valid_idx = result['combined_returns'].first_valid_index()
        
        # After warmup, should have values
        combined_after_warmup = result['combined_returns'].loc[first_valid_idx:]
        assert not combined_after_warmup.isna().any()
        
        # Weights should change over time (not constant)
        weights_after_warmup = result['weights'].loc[first_valid_idx:]
        assert weights_after_warmup['trend'].std() > 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
