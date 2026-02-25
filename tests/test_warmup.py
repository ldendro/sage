"""Tests for warmup period calculation."""

import pytest
from sage_core.utils.warmup import (
    calculate_warmup_period,
    calculate_strategy_warmup,
    calculate_meta_allocator_warmup,
)


class TestCalculateWarmupPeriod:
    """Tests for calculate_warmup_period function."""
    
    def test_basic_calculation(self):
        """Test basic warmup calculation."""
        warmup = calculate_warmup_period(
            strategies={'passthrough': {'params': {}}},
            meta_allocator=None,
            vol_window=60,
            vol_lookback=90
        )
        
        # Trading days: 0 (strategy) + 0 (meta) + 60 (asset) + 1 + 90 (vol) = 151
        assert warmup["total_trading_days"] == 151
        assert warmup["strategy_warmup"] == 0
        assert warmup["meta_allocator_warmup"] == 0
        assert warmup["asset_allocator_warmup"] == 60
        assert warmup["execution_delay"] == 1
        assert warmup["vol_targeting_warmup"] == 90
        assert "151 trading days" in warmup["description"]
    
    def test_equal_windows(self):
        """Test when vol_window equals vol_lookback."""
        warmup = calculate_warmup_period(
            strategies={'passthrough': {'params': {}}},
            meta_allocator=None,
            vol_window=60,
            vol_lookback=60
        )
        
        # Trading days: 0 + 0 + 60 + 1 + 60 = 121
        assert warmup["total_trading_days"] == 121
        assert warmup["asset_allocator_warmup"] == 60
        assert warmup["vol_targeting_warmup"] == 60
    
    def test_different_values(self):
        """Test with different parameter values."""
        warmup = calculate_warmup_period(
            strategies={'passthrough': {'params': {}}},
            meta_allocator=None,
            vol_window=30,
            vol_lookback=120
        )
        
        # Trading days: 0 + 0 + 30 + 1 + 120 = 151
        assert warmup["total_trading_days"] == 151
        assert warmup["asset_allocator_warmup"] == 30
        assert warmup["execution_delay"] == 1
        assert warmup["vol_targeting_warmup"] == 120
    
    def test_minimum_values(self):
        """Test with minimum values."""
        warmup = calculate_warmup_period(
            strategies={'passthrough': {'params': {}}},
            meta_allocator=None,
            vol_window=1,
            vol_lookback=1
        )
        
        # Trading days: 0 + 0 + 1 + 1 + 1 = 3
        assert warmup["total_trading_days"] == 3
        assert warmup["asset_allocator_warmup"] == 1
        assert warmup["vol_targeting_warmup"] == 1
    
    def test_large_values(self):
        """Test with large values."""
        warmup = calculate_warmup_period(
            strategies={'passthrough': {'params': {}}},
            meta_allocator=None,
            vol_window=252,
            vol_lookback=252
        )
        
        # Trading days: 0 + 0 + 252 + 1 + 252 = 505
        assert warmup["total_trading_days"] == 505
        assert warmup["asset_allocator_warmup"] == 252
        assert warmup["vol_targeting_warmup"] == 252
    
    def test_return_structure(self):
        """Test that return dict has correct structure."""
        warmup = calculate_warmup_period(
            strategies={'passthrough': {'params': {}}},
            meta_allocator=None,
            vol_window=60,
            vol_lookback=90
        )
        
        assert "total_trading_days" in warmup
        assert "strategy_warmup" in warmup
        assert "meta_allocator_warmup" in warmup
        assert "signal_warmup" in warmup
        assert "asset_allocator_warmup" in warmup
        assert "parallel_warmup" in warmup
        assert "execution_delay" in warmup
        assert "vol_targeting_warmup" in warmup
        assert "description" in warmup
        
        # Check types
        assert isinstance(warmup["total_trading_days"], int)
        assert isinstance(warmup["strategy_warmup"], int)
        assert isinstance(warmup["meta_allocator_warmup"], int)
        assert isinstance(warmup["signal_warmup"], int)
        assert isinstance(warmup["parallel_warmup"], int)
        assert isinstance(warmup["description"], str)
    
    def test_description_format(self):
        """Test description string format."""
        warmup = calculate_warmup_period(
            strategies={'passthrough': {'params': {}}},
            meta_allocator=None,
            vol_window=60,
            vol_lookback=90
        )
        
        description = warmup["description"]
        assert "60" in description
        assert "90" in description
        assert "151" in description  # Total trading days
        assert "Allocator" in description
        assert "Vol targeting" in description
        assert "Execution delay" in description
        assert "trading days" in description


class TestStrategyWarmupCalculation:
    """Tests for calculate_strategy_warmup helper function."""
    
    def test_single_passthrough(self):
        """Test passthrough strategy has 0 warmup."""
        warmup = calculate_strategy_warmup({'passthrough': {'params': {}}})
        assert warmup == 0
    
    def test_single_trend(self):
        """Test trend strategy has 253-day warmup."""
        warmup = calculate_strategy_warmup({'trend': {'params': {}}})
        assert warmup == 253
    
    def test_single_meanrev(self):
        """Test meanrev strategy has 60-day warmup."""
        warmup = calculate_strategy_warmup({'meanrev': {'params': {}}})
        assert warmup == 60
    
    def test_multiple_strategies(self):
        """Test multiple strategies returns max warmup."""
        warmup = calculate_strategy_warmup({
            'trend': {'params': {}},
            'meanrev': {'params': {}}
        })
        assert warmup == 253  # max(253, 60)
    
    def test_multiple_with_passthrough(self):
        """Test multiple strategies including passthrough."""
        warmup = calculate_strategy_warmup({
            'passthrough': {'params': {}},
            'trend': {'params': {}},
            'meanrev': {'params': {}}
        })
        assert warmup == 253  # max(0, 253, 60)
    
    def test_empty_strategies(self):
        """Test empty strategies dict returns 0."""
        warmup = calculate_strategy_warmup({})
        assert warmup == 0
    
    def test_unknown_strategy(self):
        """Test unknown strategy raises ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            calculate_strategy_warmup({'unknown': {'params': {}}})


class TestMetaAllocatorWarmupCalculation:
    """Tests for calculate_meta_allocator_warmup helper function."""
    
    def test_single_strategy_skips_meta_allocator(self):
        """Test meta allocator warmup is 0 when only one strategy."""
        warmup = calculate_meta_allocator_warmup(
            {'type': 'risk_parity', 'params': {'vol_lookback': 60}},
            num_strategies=1
        )
        assert warmup == 0
    
    def test_fixed_weight_has_zero_warmup(self):
        """Test FixedWeightAllocator has 0 warmup."""
        warmup = calculate_meta_allocator_warmup(
            {'type': 'fixed_weight', 'params': {'weights': {'trend': 0.5, 'meanrev': 0.5}}},
            num_strategies=2
        )
        assert warmup == 0
    
    def test_risk_parity_warmup(self):
        """Test RiskParityAllocator has correct warmup."""
        warmup = calculate_meta_allocator_warmup(
            {'type': 'risk_parity', 'params': {'vol_lookback': 60}},
            num_strategies=2
        )
        assert warmup == 60
    
    def test_risk_parity_custom_lookback(self):
        """Test RiskParityAllocator with custom lookback."""
        warmup = calculate_meta_allocator_warmup(
            {'type': 'risk_parity', 'params': {'vol_lookback': 120}},
            num_strategies=2
        )
        assert warmup == 120
    
    def test_none_meta_allocator(self):
        """Test None meta allocator returns 0 warmup."""
        warmup = calculate_meta_allocator_warmup(None, num_strategies=2)
        assert warmup == 0
    
    def test_zero_strategies(self):
        """Test 0 strategies returns 0 warmup."""
        warmup = calculate_meta_allocator_warmup(
            {'type': 'risk_parity', 'params': {'vol_lookback': 60}},
            num_strategies=0
        )
        assert warmup == 0
    
    def test_unknown_allocator_type(self):
        """Test unknown allocator type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown meta allocator type"):
            calculate_meta_allocator_warmup(
                {'type': 'unknown', 'params': {}},
                num_strategies=2
            )


class TestIntegratedWarmupCalculation:
    """Tests for integrated warmup calculation with strategies and meta allocators."""
    
    def test_single_strategy_trend(self):
        """Test total warmup for single Trend strategy."""
        warmup = calculate_warmup_period(
            strategies={'trend': {'params': {}}},
            meta_allocator=None,
            vol_window=60,
            vol_lookback=60,
        )
        
        # max(253 + 0, 60) + 1 + 60 = 314
        assert warmup['strategy_warmup'] == 253
        assert warmup['meta_allocator_warmup'] == 0
        assert warmup['signal_warmup'] == 253
        assert warmup['asset_allocator_warmup'] == 60
        assert warmup['parallel_warmup'] == 253
        assert warmup['execution_delay'] == 1
        assert warmup['vol_targeting_warmup'] == 60
        assert warmup['total_trading_days'] == 314
    
    def test_multi_strategy_fixed_weight(self):
        """Test total warmup for multi-strategy with FixedWeight."""
        warmup = calculate_warmup_period(
            strategies={'trend': {}, 'meanrev': {}},
            meta_allocator={'type': 'fixed_weight', 'params': {'weights': {'trend': 0.6, 'meanrev': 0.4}}},
            vol_window=60,
            vol_lookback=60,
        )
        
        # max(253 + 0, 60) + 1 + 60 = 314
        assert warmup['strategy_warmup'] == 253
        assert warmup['meta_allocator_warmup'] == 0
        assert warmup['signal_warmup'] == 253
        assert warmup['parallel_warmup'] == 253
        assert warmup['total_trading_days'] == 314
    
    def test_multi_strategy_risk_parity(self):
        """Test total warmup for multi-strategy with RiskParity."""
        warmup = calculate_warmup_period(
            strategies={'trend': {}, 'meanrev': {}},
            meta_allocator={'type': 'risk_parity', 'params': {'vol_lookback': 60}},
            vol_window=60,
            vol_lookback=60,
        )
        
        # max(253 + 60, 60) + 1 + 60 = 374
        assert warmup['strategy_warmup'] == 253
        assert warmup['meta_allocator_warmup'] == 60
        assert warmup['signal_warmup'] == 313
        assert warmup['asset_allocator_warmup'] == 60
        assert warmup['parallel_warmup'] == 313
        assert warmup['execution_delay'] == 1
        assert warmup['vol_targeting_warmup'] == 60
        assert warmup['total_trading_days'] == 374
    
    def test_warmup_description_includes_all_layers(self):
        """Test description includes all warmup layers."""
        warmup = calculate_warmup_period(
            strategies={'trend': {}, 'meanrev': {}},
            meta_allocator={'type': 'risk_parity', 'params': {'vol_lookback': 60}},
            vol_window=60,
            vol_lookback=60,
        )
        
        description = warmup['description']
        assert 'Strategy (253d)' in description
        assert 'Meta (60d)' in description
        assert 'Allocator (60d)' in description
        assert 'Execution delay (1d)' in description
        assert 'Vol targeting (60d)' in description
        assert '374 trading days' in description
