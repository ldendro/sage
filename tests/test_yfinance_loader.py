"""Tests for yfinance data loader."""

import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock

from sage_core.data.yfinance_loader import fetch_ohlcv_yfinance


class TestFetchOHLCVYfinance:
    """Tests for fetch_ohlcv_yfinance function."""
    
    def test_fetch_ohlcv_success(self):
        """Test successful data fetch from yfinance."""
        # Mock yfinance.download to return sample data
        mock_data = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0],
            'High': [101.0, 102.0, 103.0],
            'Low': [99.0, 100.0, 101.0],
            'Close': [100.5, 101.5, 102.5],
            'Volume': [1000000, 1100000, 1200000],
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        mock_data.index.name = 'Date'
        
        with patch('sage_core.data.yfinance_loader.yf.download', return_value=mock_data):
            df = fetch_ohlcv_yfinance("SPY", "2023-01-01", "2023-01-03")
        
        # Verify structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ['open', 'high', 'low', 'close', 'volume', 'raw_ret']
        assert df.index.name == 'date'
        
        # Verify raw_ret calculation
        assert df.loc[df.index[0], 'raw_ret'] == 0.0  # First return is 0
        expected_ret_1 = (101.5 - 100.5) / 100.5
        assert abs(df.loc[df.index[1], 'raw_ret'] - expected_ret_1) < 1e-10
    
    def test_fetch_ohlcv_invalid_ticker(self):
        """Test handling of invalid ticker symbol."""
        # Mock yfinance.download to return empty DataFrame
        with patch('sage_core.data.yfinance_loader.yf.download', return_value=pd.DataFrame()):
            with pytest.raises(ValueError, match="No data returned"):
                fetch_ohlcv_yfinance("INVALID123", "2023-01-01", "2023-12-31")
    
    def test_fetch_ohlcv_no_data_in_range(self):
        """Test handling of no data in specified range."""
        # Mock yfinance.download to return empty DataFrame
        with patch('sage_core.data.yfinance_loader.yf.download', return_value=pd.DataFrame()):
            with pytest.raises(ValueError, match="No data returned"):
                fetch_ohlcv_yfinance("SPY", "1900-01-01", "1900-12-31")
    
    def test_fetch_ohlcv_network_error_with_retry(self):
        """Test retry logic on network errors."""
        # Mock yfinance.download to fail twice, then succeed
        mock_data = pd.DataFrame({
            'Open': [100.0],
            'High': [101.0],
            'Low': [99.0],
            'Close': [100.5],
            'Volume': [1000000],
        }, index=pd.date_range('2023-01-01', periods=1, freq='D'))
        mock_data.index.name = 'Date'
        
        mock_download = MagicMock(side_effect=[
            Exception("Network error"),
            Exception("Network error"),
            mock_data
        ])
        
        with patch('sage_core.data.yfinance_loader.yf.download', mock_download):
            with patch('sage_core.data.yfinance_loader.time.sleep'):  # Skip sleep in tests
                df = fetch_ohlcv_yfinance("SPY", "2023-01-01", "2023-01-01", max_retries=3)
        
        # Verify it succeeded after retries
        assert len(df) == 1
        assert mock_download.call_count == 3
    
    def test_fetch_ohlcv_all_retries_fail(self):
        """Test failure after all retry attempts."""
        mock_download = MagicMock(side_effect=Exception("Network error"))
        
        with patch('sage_core.data.yfinance_loader.yf.download', mock_download):
            with patch('sage_core.data.yfinance_loader.time.sleep'):
                with pytest.raises(RuntimeError, match="Failed to fetch data.*after 3 attempts"):
                    fetch_ohlcv_yfinance("SPY", "2023-01-01", "2023-12-31", max_retries=3)
    
    def test_fetch_ohlcv_data_validation(self):
        """Test OHLC relationship validation."""
        # Create invalid data (high < close)
        mock_data = pd.DataFrame({
            'Open': [100.0],
            'High': [99.0],  # Invalid: high < close
            'Low': [98.0],
            'Close': [100.5],
            'Volume': [1000000],
        }, index=pd.date_range('2023-01-01', periods=1, freq='D'))
        mock_data.index.name = 'Date'
        
        with patch('sage_core.data.yfinance_loader.yf.download', return_value=mock_data):
            with pytest.raises(ValueError, match="high must be >= close"):
                fetch_ohlcv_yfinance("SPY", "2023-01-01", "2023-01-01")
    
    def test_fetch_ohlcv_handles_nan_values(self):
        """Test handling of NaN values in data."""
        # Create data with NaN
        mock_data = pd.DataFrame({
            'Open': [100.0, None, 102.0],  # NaN in middle
            'High': [101.0, 102.0, 103.0],
            'Low': [99.0, 100.0, 101.0],
            'Close': [100.5, 101.5, 102.5],
            'Volume': [1000000, 1100000, 1200000],
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        mock_data.index.name = 'Date'
        
        with patch('sage_core.data.yfinance_loader.yf.download', return_value=mock_data):
            df = fetch_ohlcv_yfinance("SPY", "2023-01-01", "2023-01-03")
        
        # Should drop NaN rows
        assert len(df) == 2  # Only 2 valid rows
        assert not df.isnull().any().any()
    
    def test_fetch_ohlcv_raw_ret_calculation(self):
        """Test raw_ret calculation is correct."""
        mock_data = pd.DataFrame({
            'Open': [100.0, 105.0, 103.0],
            'High': [102.0, 107.0, 105.0],
            'Low': [99.0, 104.0, 102.0],
            'Close': [101.0, 106.0, 104.0],
            'Volume': [1000000, 1100000, 1200000],
        }, index=pd.date_range('2023-01-01', periods=3, freq='D'))
        mock_data.index.name = 'Date'
        
        with patch('sage_core.data.yfinance_loader.yf.download', return_value=mock_data):
            df = fetch_ohlcv_yfinance("SPY", "2023-01-01", "2023-01-03")
        
        # Verify raw_ret
        assert df.loc[df.index[0], 'raw_ret'] == 0.0
        expected_ret_1 = (106.0 - 101.0) / 101.0
        expected_ret_2 = (104.0 - 106.0) / 106.0
        assert abs(df.loc[df.index[1], 'raw_ret'] - expected_ret_1) < 1e-10
        assert abs(df.loc[df.index[2], 'raw_ret'] - expected_ret_2) < 1e-10
