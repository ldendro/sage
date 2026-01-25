"""Tests for validation utilities."""

import pytest
from datetime import date, timedelta
from app.utils.validators import (
    validate_universe,
    validate_date_range,
    validate_backtest_params,
)


class TestValidateUniverse:
    """Tests for universe validation."""
    
    def test_valid_universe(self):
        """Test valid universe selection."""
        available = ["SPY", "QQQ", "IWM"]
        universe = ["SPY", "QQQ"]
        errors = validate_universe(universe, available)
        assert len(errors) == 0
    
    def test_empty_universe(self):
        """Test empty universe."""
        available = ["SPY", "QQQ", "IWM"]
        universe = []
        errors = validate_universe(universe, available)
        assert len(errors) == 1
        assert "empty" in errors[0].lower()
    
    def test_invalid_ticker(self):
        """Test invalid ticker in universe."""
        available = ["SPY", "QQQ", "IWM"]
        universe = ["SPY", "INVALID"]
        errors = validate_universe(universe, available)
        assert len(errors) == 1
        assert "INVALID" in errors[0]


class TestValidateDateRange:
    """Tests for date range validation."""
    
    def test_valid_date_range(self):
        """Test valid date range."""
        start = date(2020, 1, 1)
        end = date(2021, 12, 31)
        errors = validate_date_range(start, end)
        assert len(errors) == 0
    
    def test_start_after_end(self):
        """Test start date after end date."""
        start = date(2021, 12, 31)
        end = date(2020, 1, 1)
        errors = validate_date_range(start, end)
        assert len(errors) == 1
        assert "before" in errors[0].lower()
    
    def test_start_equals_end(self):
        """Test start date equals end date."""
        start = date(2020, 1, 1)
        end = date(2020, 1, 1)
        errors = validate_date_range(start, end)
        assert len(errors) == 1
    
    def test_date_too_old(self):
        """Test date before year 2000."""
        start = date(1999, 1, 1)
        end = date(2020, 1, 1)
        errors = validate_date_range(start, end)
        assert len(errors) == 1
        assert "2000" in errors[0]
    
    def test_future_date(self):
        """Test future end date."""
        start = date(2020, 1, 1)
        end = date.today() + timedelta(days=365)
        errors = validate_date_range(start, end)
        assert len(errors) == 1
        assert "future" in errors[0].lower()

    def test_none_dates(self):
        """Test validation with None dates (should likely fail currently or return error)."""
        # This mirrors what happens when a user clears the input in Streamlit
        start = None
        end = None
        # We expect this to return a friendly error in the future, 
        # but right now it might raise a TypeError, which we want to fix.
        errors = validate_date_range(start, end)
        assert len(errors) > 0
        assert "required" in errors[0].lower() or "missing" in errors[0].lower()


class TestValidateBacktestParams:
    """Tests for complete backtest parameter validation."""
    
    def test_valid_params(self):
        """Test all valid parameters."""
        errors = validate_backtest_params(
            universe=["SPY", "QQQ"],
            start_date=date(2020, 1, 1),
            end_date=date(2021, 12, 31),
            min_assets_held=1,
            min_leverage=0.0,
            max_leverage=2.0,
            available_tickers=["SPY", "QQQ", "IWM"]
        )
        assert len(errors) == 0
    
    def test_min_assets_exceeds_universe(self):
        """Test min assets exceeds universe size."""
        errors = validate_backtest_params(
            universe=["SPY", "QQQ"],
            start_date=date(2020, 1, 1),
            end_date=date(2021, 12, 31),
            min_assets_held=5,
            min_leverage=0.0,
            max_leverage=2.0,
            available_tickers=["SPY", "QQQ", "IWM"]
        )
        assert len(errors) == 1
        assert "min assets" in errors[0].lower()
    
    def test_invalid_leverage(self):
        """Test min leverage exceeds max leverage."""
        errors = validate_backtest_params(
            universe=["SPY", "QQQ"],
            start_date=date(2020, 1, 1),
            end_date=date(2021, 12, 31),
            min_assets_held=1,
            min_leverage=2.0,
            max_leverage=1.0,
            available_tickers=["SPY", "QQQ", "IWM"]
        )
        assert len(errors) == 1
        assert "leverage" in errors[0].lower()
    
    def test_multiple_errors(self):
        """Test multiple validation errors."""
        errors = validate_backtest_params(
            universe=[],
            start_date=date(2021, 12, 31),
            end_date=date(2020, 1, 1),
            min_assets_held=5,
            min_leverage=2.0,
            max_leverage=1.0,
            available_tickers=["SPY", "QQQ", "IWM"]
        )
        assert len(errors) > 1
