"""Tests for warmup period calculation."""

import pytest
from sage_core.utils.warmup import calculate_warmup_period


class TestCalculateWarmupPeriod:
    """Tests for calculate_warmup_period function."""
    
    def test_basic_calculation(self):
        """Test basic warmup calculation."""
        warmup = calculate_warmup_period(vol_window=60, vol_lookback=90)
        
        # Trading days: 60 + 1 + 90 = 151
        assert warmup["total_trading_days"] == 151
        assert warmup["components"]["inverse_vol"] == 60
        assert warmup["components"]["first_return"] == 1
        assert warmup["components"]["vol_targeting"] == 90
        assert "151 trading days" in warmup["description"]
    
    def test_equal_windows(self):
        """Test when vol_window equals vol_lookback."""
        warmup = calculate_warmup_period(vol_window=60, vol_lookback=60)
        
        # Trading days: 60 + 1 + 60 = 121
        assert warmup["total_trading_days"] == 121
        assert warmup["components"]["inverse_vol"] == 60
        assert warmup["components"]["vol_targeting"] == 60
    
    def test_different_values(self):
        """Test with different parameter values."""
        warmup = calculate_warmup_period(vol_window=30, vol_lookback=120)
        
        # Trading days: 30 + 1 + 120 = 151
        assert warmup["total_trading_days"] == 151
        assert warmup["components"]["inverse_vol"] == 30
        assert warmup["components"]["first_return"] == 1
        assert warmup["components"]["vol_targeting"] == 120
    
    def test_minimum_values(self):
        """Test with minimum values."""
        warmup = calculate_warmup_period(vol_window=1, vol_lookback=1)
        
        # Trading days: 1 + 1 + 1 = 3
        assert warmup["total_trading_days"] == 3
        assert warmup["components"]["inverse_vol"] == 1
        assert warmup["components"]["vol_targeting"] == 1
    
    def test_large_values(self):
        """Test with large values."""
        warmup = calculate_warmup_period(vol_window=252, vol_lookback=252)
        
        # Trading days: 252 + 1 + 252 = 505
        assert warmup["total_trading_days"] == 505
        assert warmup["components"]["inverse_vol"] == 252
        assert warmup["components"]["vol_targeting"] == 252
    
    def test_return_structure(self):
        """Test that return dict has correct structure."""
        warmup = calculate_warmup_period(vol_window=60, vol_lookback=90)
        
        # Check all required keys exist
        assert "total_trading_days" in warmup
        assert "components" in warmup
        assert "description" in warmup
        
        # Check components structure
        assert "inverse_vol" in warmup["components"]
        assert "first_return" in warmup["components"]
        assert "vol_targeting" in warmup["components"]
        
        # Check types
        assert isinstance(warmup["total_trading_days"], int)
        assert isinstance(warmup["components"], dict)
        assert isinstance(warmup["description"], str)
    
    def test_description_format(self):
        """Test description string format."""
        warmup = calculate_warmup_period(vol_window=60, vol_lookback=90)
        
        description = warmup["description"]
        assert "60" in description
        assert "90" in description
        assert "151" in description  # Total trading days
        assert "Inverse vol" in description
        assert "Vol targeting" in description
        assert "First return" in description
        assert "trading days" in description
