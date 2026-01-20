"""
Tests for portfolio constructor.
"""

import pytest
import pandas as pd
import numpy as np

from sage_core.portfolio.constructor import (
    align_asset_returns,
    build_portfolio_raw_returns,
)
from sage_core.data.loader import load_universe
from sage_core.strategies.passthrough_v1 import run_passthrough_v1


class TestAlignAssetReturns:
    """Tests for align_asset_returns function."""
    
    def test_align_basic(self):
        """Test basic alignment of asset returns."""
        # Load and process data
        data = load_universe(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        
        # Align returns
        returns_wide = align_asset_returns(strategy_output)
        
        # Check shape
        assert isinstance(returns_wide, pd.DataFrame)
        assert set(returns_wide.columns) == {"SPY", "QQQ", "IWM"}
        
        # Check index is DatetimeIndex
        assert isinstance(returns_wide.index, pd.DatetimeIndex)
        
        # Check no NaN values
        assert not returns_wide.isnull().any().any()
    
    def test_align_preserves_values(self):
        """Test that alignment preserves original return values."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        
        returns_wide = align_asset_returns(strategy_output)
        
        # Check SPY returns match
        spy_original = strategy_output["SPY"]['meta_raw_ret']
        spy_aligned = returns_wide["SPY"]
        
        assert (spy_original == spy_aligned).all()
    
    def test_align_custom_column(self):
        """Test alignment with custom return column."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        # Use raw_ret instead of meta_raw_ret
        returns_wide = align_asset_returns(data, return_col='raw_ret')
        
        assert 'SPY' in returns_wide.columns
        assert (returns_wide["SPY"] == data["SPY"]['raw_ret']).all()
    
    def test_align_empty_data(self):
        """Test that empty data raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            align_asset_returns({})
    
    def test_align_missing_column(self):
        """Test that missing return column raises ValueError."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        with pytest.raises(ValueError, match="Column.*not found"):
            align_asset_returns(data, return_col='nonexistent_column')
    
    def test_align_single_asset(self):
        """Test alignment with single asset."""
        data = load_universe(
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        
        returns_wide = align_asset_returns(strategy_output)
        
        assert returns_wide.shape[1] == 1  # One column
        assert 'SPY' in returns_wide.columns


class TestBuildPortfolioRawReturns:
    """Tests for build_portfolio_raw_returns function."""
    
    def test_build_equal_weight(self):
        """Test portfolio returns with equal weights."""
        # Load data
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        # Create equal weights (50/50)
        weights_wide = pd.DataFrame(
            0.5,
            index=returns_wide.index,
            columns=returns_wide.columns,
        )
        
        # Build portfolio returns
        portfolio_ret = build_portfolio_raw_returns(returns_wide, weights_wide)
        
        # Check output
        assert isinstance(portfolio_ret, pd.Series)
        assert len(portfolio_ret) == len(returns_wide)
        assert portfolio_ret.index.equals(returns_wide.index)
        
        # Portfolio return should be average of asset returns
        expected = (returns_wide["SPY"] + returns_wide["QQQ"]) / 2
        assert np.allclose(portfolio_ret, expected)
    
    def test_build_single_asset_weight(self):
        """Test portfolio returns with 100% weight in one asset."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        # 100% SPY, 0% QQQ
        weights_wide = pd.DataFrame({
            "SPY": 1.0,
            "QQQ": 0.0,
        }, index=returns_wide.index)
        
        portfolio_ret = build_portfolio_raw_returns(returns_wide, weights_wide)
        
        # Portfolio return should equal SPY return
        assert np.allclose(portfolio_ret, returns_wide["SPY"])
    
    def test_build_varying_weights(self):
        """Test portfolio returns with time-varying weights."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-10",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        # Create varying weights
        n_days = len(returns_wide)
        weights_wide = pd.DataFrame({
            "SPY": np.linspace(0.3, 0.7, n_days),  # 30% to 70%
            "QQQ": np.linspace(0.7, 0.3, n_days),  # 70% to 30%
        }, index=returns_wide.index)
        
        portfolio_ret = build_portfolio_raw_returns(returns_wide, weights_wide)
        
        # Check first day: 30% SPY + 70% QQQ
        expected_first = (
            0.3 * returns_wide["SPY"].iloc[0] +
            0.7 * returns_wide["QQQ"].iloc[0]
        )
        assert np.isclose(portfolio_ret.iloc[0], expected_first)
    
    def test_build_mismatched_shape(self):
        """Test that mismatched shapes raise ValueError."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        # Create weights with wrong shape
        weights_wrong = pd.DataFrame(
            0.5,
            index=returns_wide.index[:10],  # Only 10 days
            columns=returns_wide.columns,
        )
        
        with pytest.raises(ValueError, match="same shape"):
            build_portfolio_raw_returns(returns_wide, weights_wrong)
    
    def test_build_mismatched_columns(self):
        """Test that mismatched columns raise ValueError."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        # Create weights with different columns
        weights_wrong = pd.DataFrame(
            0.5,
            index=returns_wide.index,
            columns=["SPY", "IWM"],  # IWM instead of QQQ
        )
        
        with pytest.raises(ValueError, match="same columns"):
            build_portfolio_raw_returns(returns_wide, weights_wrong)
    
    def test_build_weights_sum_to_one(self):
        """Test portfolio returns when weights sum to 1."""
        data = load_universe(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        strategy_output = run_passthrough_v1(data)
        returns_wide = align_asset_returns(strategy_output)
        
        # Create weights that sum to 1
        weights_wide = pd.DataFrame({
            "SPY": 0.5,
            "QQQ": 0.3,
            "IWM": 0.2,
        }, index=returns_wide.index)
        
        portfolio_ret = build_portfolio_raw_returns(returns_wide, weights_wide)
        
        # Manual calculation for first day
        expected = (
            0.5 * returns_wide["SPY"].iloc[0] +
            0.3 * returns_wide["QQQ"].iloc[0] +
            0.2 * returns_wide["IWM"].iloc[0]
        )
        assert np.isclose(portfolio_ret.iloc[0], expected)
