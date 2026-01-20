"""
Tests for strategies.
"""

import pytest
import pandas as pd
import numpy as np

from sage_core.strategies.passthrough_v1 import run_passthrough_v1
from sage_core.data.loader import load_universe


class TestPassthroughV1:
    """Tests for passthrough_v1 strategy."""
    
    def test_passthrough_copies_raw_ret(self):
        """Test that passthrough copies raw_ret to meta_raw_ret."""
        # Load real data
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        # Run passthrough strategy
        result = run_passthrough_v1(data)
        
        # Check both symbols
        for symbol in ["SPY", "QQQ"]:
            df = result[symbol]
            
            # Should have meta_raw_ret column
            assert 'meta_raw_ret' in df.columns
            
            # meta_raw_ret should equal raw_ret
            assert (df['meta_raw_ret'] == df['raw_ret']).all()
    
    def test_passthrough_preserves_original_columns(self):
        """Test that passthrough preserves all original columns."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        original_cols = set(data["SPY"].columns)
        
        result = run_passthrough_v1(data)
        result_cols = set(result["SPY"].columns)
        
        # All original columns should be present
        assert original_cols.issubset(result_cols)
        
        # Should have added meta_raw_ret
        assert 'meta_raw_ret' in result_cols
    
    def test_passthrough_does_not_modify_original(self):
        """Test that passthrough doesn't modify original data."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        # Store original raw_ret
        original_raw_ret = data["SPY"]['raw_ret'].copy()
        
        # Run strategy
        result = run_passthrough_v1(data)
        
        # Original data should be unchanged
        assert (data["SPY"]['raw_ret'] == original_raw_ret).all()
        assert 'meta_raw_ret' not in data["SPY"].columns
    
    def test_passthrough_with_empty_params(self):
        """Test that passthrough works with empty params."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        # Should work with no params
        result = run_passthrough_v1(data, params={})
        assert 'meta_raw_ret' in result["SPY"].columns
    
    def test_passthrough_with_none_params(self):
        """Test that passthrough works with None params."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        # Should work with None params
        result = run_passthrough_v1(data, params=None)
        assert 'meta_raw_ret' in result["SPY"].columns
    
    def test_passthrough_multiple_symbols(self):
        """Test passthrough with multiple symbols."""
        data = load_universe(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        result = run_passthrough_v1(data)
        
        # All symbols should be in result
        assert set(result.keys()) == {"SPY", "QQQ", "IWM"}
        
        # Each should have meta_raw_ret
        for symbol in ["SPY", "QQQ", "IWM"]:
            assert 'meta_raw_ret' in result[symbol].columns
            assert (result[symbol]['meta_raw_ret'] == result[symbol]['raw_ret']).all()
    
    def test_passthrough_preserves_index(self):
        """Test that passthrough preserves the datetime index."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        original_index = data["SPY"].index
        
        result = run_passthrough_v1(data)
        
        # Index should be unchanged
        assert (result["SPY"].index == original_index).all()
        assert isinstance(result["SPY"].index, pd.DatetimeIndex)
