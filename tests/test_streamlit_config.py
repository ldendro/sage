"""Tests for Streamlit app configuration."""

import pytest
from app.components.universe import (
    AVAILABLE_TICKERS,
    DEFAULT_UNIVERSE,
)
from app.components.risk import BOUNDS as RISK_BOUNDS
from app.components.strategies import BOUNDS as STRAT_BOUNDS
from app.components.meta import BOUNDS as META_BOUNDS


def test_available_tickers():
    """Test that available tickers list is correct."""
    assert len(AVAILABLE_TICKERS) == 12
    assert "SPY" in AVAILABLE_TICKERS
    assert "QQQ" in AVAILABLE_TICKERS
    assert "IWM" in AVAILABLE_TICKERS
    assert "XLK" in AVAILABLE_TICKERS


def test_default_universe():
    """Test default universe selection."""
    assert len(DEFAULT_UNIVERSE) == 12
    assert all(ticker in AVAILABLE_TICKERS for ticker in DEFAULT_UNIVERSE)


def test_bounds_structure():
    """Test parameter bounds are correctly defined."""
    # Check Risk Bounds
    risk_params = [
        "max_weight_per_asset",
        "max_sector_weight",
        "min_assets_held",
        "target_vol",
        "vol_lookback",
        "min_leverage",
        "max_leverage",
        "vol_window",
    ]
    
    for param in risk_params:
        assert param in RISK_BOUNDS
        assert len(RISK_BOUNDS[param]) == 2
        assert RISK_BOUNDS[param][0] < RISK_BOUNDS[param][1]

    # Check Strategy Bounds
    assert "trend_lookback" in STRAT_BOUNDS
    assert "meanrev_lookback" in STRAT_BOUNDS
    
    # Check Meta Bounds
    assert "meta_vol_lookback" in META_BOUNDS


def test_bounds_values():
    """Test that bounds are reasonable."""
    # Max weight per asset should be between 0 and 1
    assert 0 < RISK_BOUNDS["max_weight_per_asset"][0] <= 1
    assert 0 < RISK_BOUNDS["max_weight_per_asset"][1] <= 1
    
    # Leverage should be non-negative
    assert RISK_BOUNDS["min_leverage"][0] >= 0
    assert RISK_BOUNDS["max_leverage"][0] > 0
    
    # Lookback periods should be positive
    assert RISK_BOUNDS["vol_lookback"][0] > 0
    assert RISK_BOUNDS["vol_window"][0] > 0
