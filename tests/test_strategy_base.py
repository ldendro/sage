"""Tests for Strategy base class."""

import pytest
import pandas as pd
import numpy as np
from abc import ABC

from sage_core.strategies.base import Strategy


class TestStrategyBase:
    """Tests for abstract Strategy base class."""
    
    def test_strategy_is_abstract(self):
        """Test that Strategy cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Strategy()
    
    def test_strategy_requires_all_methods(self):
        """Test that subclass must implement all abstract methods."""
        # Create incomplete strategy (missing generate_signals)
        class IncompleteStrategy(Strategy):
            def validate_params(self):
                pass
            
            def get_warmup_period(self):
                return 0
            
            # Missing: generate_signals()
        
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteStrategy()
    
    def test_strategy_run_template_method(self):
        """Test that run() stores signals, not returns."""
        # Create minimal valid strategy
        class MinimalStrategy(Strategy):
            def validate_params(self):
                pass
            
            def get_warmup_period(self):
                return 0
            
            def generate_signals(self, ohlcv):
                return pd.Series(1, index=ohlcv.index)
        
        # Create test data
        dates = pd.date_range('2020-01-01', periods=10)
        asset_data = {
            'SPY': pd.DataFrame({
                'close': np.random.randn(10) + 100,
                'raw_ret': np.random.randn(10) * 0.01,
            }, index=dates),
            'QQQ': pd.DataFrame({
                'close': np.random.randn(10) + 200,
                'raw_ret': np.random.randn(10) * 0.01,
            }, index=dates),
        }
        
        # Run strategy
        strategy = MinimalStrategy()
        result = strategy.run(asset_data)
        
        # Verify results — strategy now stores 'signal', not 'meta_raw_ret'
        assert 'SPY' in result
        assert 'QQQ' in result
        assert 'signal' in result['SPY'].columns
        assert 'signal' in result['QQQ'].columns
        
        # Signal should be all 1s (always long)
        assert (result['SPY']['signal'] == 1).all()
        assert (result['QQQ']['signal'] == 1).all()
    
    def test_strategy_signal_type_property(self):
        """Test that signal_type returns 'discrete' by default."""
        class MinimalStrategy(Strategy):
            def validate_params(self):
                pass
            def get_warmup_period(self):
                return 0
            def generate_signals(self, ohlcv):
                return pd.Series(1, index=ohlcv.index)
        
        strategy = MinimalStrategy()
        assert strategy.signal_type == "discrete"
    
    def test_strategy_params_initialization(self):
        """Test that strategy params are properly initialized."""
        class ParamStrategy(Strategy):
            def validate_params(self):
                if 'required_param' not in self.params:
                    raise ValueError("Missing required_param")
            
            def get_warmup_period(self):
                return self.params.get('warmup', 0)
            
            def generate_signals(self, ohlcv):
                return pd.Series(1, index=ohlcv.index)
        
        # Test with no params (should fail validation)
        with pytest.raises(ValueError, match="Missing required_param"):
            ParamStrategy()
        
        # Test with params (should succeed)
        strategy = ParamStrategy(params={'required_param': 'value', 'warmup': 60})
        assert strategy.params['required_param'] == 'value'
        assert strategy.get_warmup_period() == 60
    
    def test_strategy_run_preserves_original_data(self):
        """Test that run() doesn't modify original data."""
        class SimpleStrategy(Strategy):
            def validate_params(self):
                pass
            
            def get_warmup_period(self):
                return 0
            
            def generate_signals(self, ohlcv):
                return pd.Series(1, index=ohlcv.index)
        
        # Create test data
        dates = pd.date_range('2020-01-01', periods=5)
        original_data = {
            'SPY': pd.DataFrame({
                'close': [100, 101, 102, 103, 104],
                'raw_ret': [0.01, 0.01, 0.01, 0.01, 0.01],
            }, index=dates)
        }
        
        # Store original values
        original_columns = set(original_data['SPY'].columns)
        original_values = original_data['SPY'].copy()
        
        # Run strategy
        strategy = SimpleStrategy()
        result = strategy.run(original_data)
        
        # Verify original data is unchanged
        assert set(original_data['SPY'].columns) == original_columns
        assert original_data['SPY'].equals(original_values)
        
        # Verify result has signal column (not meta_raw_ret)
        assert 'signal' in result['SPY'].columns
        assert 'signal' not in original_data['SPY'].columns
    
    def test_strategy_run_masks_warmup(self):
        """Test that run() masks warmup period with NaN."""
        class WarmupStrategy(Strategy):
            def validate_params(self):
                pass
            
            def get_warmup_period(self):
                return 3
            
            def generate_signals(self, ohlcv):
                return pd.Series(1, index=ohlcv.index)
        
        dates = pd.date_range('2020-01-01', periods=10)
        asset_data = {
            'SPY': pd.DataFrame({
                'close': range(100, 110),
                'raw_ret': [0.01] * 10,
            }, index=dates),
        }
        
        strategy = WarmupStrategy()
        result = strategy.run(asset_data)
        
        # First 3 rows should be NaN (warmup)
        assert result['SPY']['signal'].iloc[:3].isna().all()
        # Remaining should be valid
        assert (result['SPY']['signal'].iloc[3:] == 1).all()
