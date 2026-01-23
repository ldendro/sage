"""Tests for Streamlit app configuration."""

import pytest
from app.config.defaults import (
    AVAILABLE_TICKERS,
    DEFAULT_UNIVERSE,
    BOUNDS,
)


def test_available_tickers():
    """Test that available tickers list is correct."""
    assert len(AVAILABLE_TICKERS) == 12
    assert "SPY" in AVAILABLE_TICKERS
    assert "QQQ" in AVAILABLE_TICKERS
    assert "IWM" in AVAILABLE_TICKERS
    assert "XLK" in AVAILABLE_TICKERS


def test_default_universe():
    """Test default universe selection."""
    assert len(DEFAULT_UNIVERSE) == 3
    assert all(ticker in AVAILABLE_TICKERS for ticker in DEFAULT_UNIVERSE)


def test_bounds_structure():
    """Test parameter bounds are correctly defined."""
    required_params = [
        "max_weight_per_asset",
        "max_sector_weight",
        "min_assets_held",
        "target_vol",
        "vol_lookback",
        "min_leverage",
        "max_leverage",
        "vol_window",
    ]
    
    for param in required_params:
        assert param in BOUNDS
        assert len(BOUNDS[param]) == 2
        assert BOUNDS[param][0] < BOUNDS[param][1]  # min < max


def test_bounds_values():
    """Test that bounds are reasonable."""
    # Max weight per asset should be between 0 and 1
    assert 0 < BOUNDS["max_weight_per_asset"][0] <= 1
    assert 0 < BOUNDS["max_weight_per_asset"][1] <= 1
    
    # Leverage should be non-negative
    assert BOUNDS["min_leverage"][0] >= 0
    assert BOUNDS["max_leverage"][0] > 0
    
    # Lookback periods should be positive
    assert BOUNDS["vol_lookback"][0] > 0
    assert BOUNDS["vol_window"][0] > 0
