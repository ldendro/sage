"""
Tests for DataLoader.
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from sage_core.data.loader import (
    load_universe,
    validate_date_format,
    get_available_symbols,
    get_data_date_range,
)
from sage_core.utils import paths


class TestValidateDateFormat:
    """Tests for date format validation."""
    
    def test_valid_date_formats(self):
        """Test that valid date formats pass."""
        validate_date_format("2020-01-01")
        validate_date_format("2025-12-31")
        validate_date_format("1999-06-15")
    
    def test_invalid_date_formats(self):
        """Test that invalid date formats raise ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format("01/01/2020")
        
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format("2020-1-1")
        
        with pytest.raises(ValueError, match="Invalid date format"):
            validate_date_format("20200101")


class TestLoadUniverse:
    """Tests for load_universe function."""
    
    def test_load_universe_success(self):
        """Test successful loading of universe data."""
        universe = ["SPY", "QQQ", "IWM"]
        data = load_universe(
            universe=universe,
            start_date="2020-01-01",
            end_date="2020-12-31",
        )
        
        # Check all symbols loaded
        assert set(data.keys()) == set(universe)
        
        # Check each DataFrame
        for symbol in universe:
            df = data[symbol]
            
            # Check it's a DataFrame
            assert isinstance(df, pd.DataFrame)
            
            # Check required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume', 'raw_ret']
            assert all(col in df.columns for col in required_cols)
            
            # Check index is DatetimeIndex
            assert isinstance(df.index, pd.DatetimeIndex)
            
            # Check date range
            assert df.index.min() >= pd.Timestamp("2020-01-01")
            assert df.index.max() <= pd.Timestamp("2020-12-31")
            
            # Check no NaN values
            assert not df.isnull().any().any()
            
            # Check prices are positive
            assert (df['close'] > 0).all()
    
    def test_load_universe_missing_symbol(self):
        """Test that missing symbol raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Data files not found"):
            load_universe(
                universe=["SPY", "NONEXISTENT_SYMBOL"],
                start_date="2020-01-01",
                end_date="2020-12-31",
            )
    
    def test_load_universe_invalid_start_date(self):
        """Test that invalid start date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            load_universe(
                universe=["SPY"],
                start_date="01/01/2020",  # Wrong format
                end_date="2020-12-31",
            )
    
    def test_load_universe_invalid_end_date(self):
        """Test that invalid end date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            load_universe(
                universe=["SPY"],
                start_date="2020-01-01",
                end_date="12/31/2020",  # Wrong format
            )
    
    def test_load_universe_inverted_dates(self):
        """Test that start_date >= end_date raises ValueError."""
        with pytest.raises(ValueError, match="must be before"):
            load_universe(
                universe=["SPY"],
                start_date="2020-12-31",
                end_date="2020-01-01",  # After start
            )
    
    def test_load_universe_no_data_in_range(self):
        """Test that date range with no data raises ValueError."""
        with pytest.raises(ValueError, match="No data.*in date range"):
            load_universe(
                universe=["SPY"],
                start_date="1990-01-01",  # Before available data
                end_date="1990-12-31",
            )
    
    def test_load_universe_empty_universe(self):
        """Test that empty universe raises ValueError."""
        with pytest.raises(ValueError, match="Universe cannot be empty"):
            load_universe(
                universe=[],
                start_date="2020-01-01",
                end_date="2020-12-31",
            )
    
    def test_load_universe_full_date_range(self):
        """Test loading full available date range."""
        data = load_universe(
            universe=["SPY"],
            start_date="2015-01-01",
            end_date="2025-12-31",
        )
        
        spy_df = data["SPY"]
        
        # Should have ~11 years of data (2870 business days)
        assert len(spy_df) > 2500
        assert len(spy_df) < 3000
    
    def test_load_universe_ohlc_relationships(self):
        """Test that OHLC relationships are valid."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-12-31",
        )
        
        df = data["SPY"]
        
        # High >= Close
        assert (df['high'] >= df['close']).all()
        
        # High >= Open
        assert (df['high'] >= df['open']).all()
        
        # Low <= Close
        assert (df['low'] <= df['close']).all()
        
        # Low <= Open
        assert (df['low'] <= df['open']).all()
    
    def test_load_universe_returns_calculation(self):
        """Test that raw_ret is calculated correctly."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",  # Just January
        )
        
        df = data["SPY"]
        
        # First return should be 0 (or very small)
        assert abs(df['raw_ret'].iloc[0]) < 0.01
        
        # Subsequent returns should match close-to-close
        for i in range(1, len(df)):
            expected_ret = df['close'].iloc[i] / df['close'].iloc[i-1] - 1.0
            actual_ret = df['raw_ret'].iloc[i]
            assert abs(actual_ret - expected_ret) < 1e-6


class TestGetAvailableSymbols:
    """Tests for get_available_symbols function."""
    
    def test_get_available_symbols(self):
        """Test getting list of available symbols."""
        symbols = get_available_symbols()
        
        # Should return a list
        assert isinstance(symbols, list)
        
        # Should contain at least the symbols we generated
        assert "SPY" in symbols
        assert "QQQ" in symbols
        
        # Should be sorted
        assert symbols == sorted(symbols)


class TestGetDataDateRange:
    """Tests for get_data_date_range function."""
    
    def test_get_data_date_range_success(self):
        """Test getting date range for a symbol."""
        start, end = get_data_date_range("SPY")
        
        # Should return Timestamps
        assert isinstance(start, pd.Timestamp)
        assert isinstance(end, pd.Timestamp)
        
        # Should span ~11 years
        assert start.year == 2015
        assert end.year == 2025
    
    def test_get_data_date_range_missing_symbol(self):
        """Test that missing symbol raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="Data file not found"):
            get_data_date_range("NONEXISTENT_SYMBOL")
