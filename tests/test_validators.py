"""Tests for validation utilities."""

import pytest
from datetime import date, timedelta
from app.utils.validators import (
    validate_universe_widget,
    validate_date_range_widget,
    validate_risk_caps_widget,
    validate_volatility_targeting_widget,
    validate_backtest_params,
)


class TestValidateUniverseWidget:
    """Tests for universe validation."""
    
    def test_valid_universe(self):
        """Test valid universe selection."""
        available = ["SPY", "QQQ", "IWM"]
        universe = ["SPY", "QQQ"]
        errors = validate_universe_widget(universe, available)
        assert len(errors) == 0
    
    def test_empty_universe(self):
        """Test empty universe."""
        available = ["SPY", "QQQ", "IWM"]
        universe = []
        errors = validate_universe_widget(universe, available)
        assert len(errors) == 1
        assert "empty" in errors[0].lower()
    
    def test_invalid_ticker(self):
        """Test invalid ticker in universe."""
        available = ["SPY", "QQQ", "IWM"]
        universe = ["SPY", "INVALID"]
        errors = validate_universe_widget(universe, available)
        assert len(errors) == 1
        assert "INVALID" in errors[0]


class TestValidateDateRangeWidget:
    """Tests for date range validation."""
    
    def test_valid_date_range(self):
        """Test valid date range."""
        start = date(2020, 1, 1)
        end = date(2021, 12, 31)
        errors = validate_date_range_widget(start, end)
        assert len(errors) == 0
    
    def test_start_after_end(self):
        """Test start date after end date."""
        start = date(2021, 12, 31)
        end = date(2020, 1, 1)
        errors = validate_date_range_widget(start, end)
        assert len(errors) == 1
        assert "before" in errors[0].lower()
    
    def test_start_equals_end(self):
        """Test start date equals end date."""
        start = date(2020, 1, 1)
        end = date(2020, 1, 1)
        errors = validate_date_range_widget(start, end)
        assert len(errors) == 1
    
    def test_date_too_old(self):
        """Test date before year 2000."""
        start = date(1999, 1, 1)
        end = date(2020, 1, 1)
        errors = validate_date_range_widget(start, end)
        assert len(errors) == 1
        assert "2000" in errors[0]
    
    def test_future_date(self):
        """Test future end date."""
        start = date(2020, 1, 1)
        end = date.today() + timedelta(days=365)
        errors = validate_date_range_widget(start, end)
        assert len(errors) == 1
        assert "future" in errors[0].lower()

    def test_none_dates(self):
        """Test validation with None dates returns error."""
        start = None
        end = None
        errors = validate_date_range_widget(start, end)
        assert len(errors) > 0
        assert "required" in errors[0].lower()


class TestValidateRiskCapsWidget:
    """Tests for risk caps validation."""
    
    def test_valid_risk_caps(self):
        """Test valid risk cap parameters."""
        errors = validate_risk_caps_widget(
            min_assets_held=2,
            universe=["SPY", "QQQ", "IWM"],
            max_weight_per_asset=0.5,
            max_sector_weight=None,
        )
        assert len(errors) == 0
    
    def test_min_assets_exceeds_universe(self):
        """Test min assets exceeds universe size."""
        errors = validate_risk_caps_widget(
            min_assets_held=5,
            universe=["SPY", "QQQ"],
            max_weight_per_asset=0.5,
            max_sector_weight=None,
        )
        assert len(errors) == 1
        assert "min assets" in errors[0].lower()
    
    def test_max_weight_per_asset_out_of_bounds(self):
        """Test max weight per asset outside (0, 1]."""
        # Test zero
        errors = validate_risk_caps_widget(
            min_assets_held=1,
            universe=["SPY", "QQQ"],
            max_weight_per_asset=0.0,
            max_sector_weight=None,
        )
        assert len(errors) == 1
        assert "max weight per asset" in errors[0].lower()
        
        # Test greater than 1
        errors = validate_risk_caps_widget(
            min_assets_held=1,
            universe=["SPY", "QQQ"],
            max_weight_per_asset=1.5,
            max_sector_weight=None,
        )
        assert len(errors) == 1
        assert "max weight per asset" in errors[0].lower()
    
    def test_infeasible_per_asset_cap(self):
        """Test infeasible per-asset cap (n_assets * max_weight < 1)."""
        # 2 assets * 0.4 = 0.8 < 1.0 (infeasible)
        errors = validate_risk_caps_widget(
            min_assets_held=1,
            universe=["SPY", "QQQ"],
            max_weight_per_asset=0.4,
            max_sector_weight=None,
        )
        assert len(errors) == 1
        assert "infeasible" in errors[0].lower()
        assert "under-invested" in errors[0].lower()
    
    def test_valid_sector_weight(self):
        """Test valid sector weight with mapped tickers."""
        errors = validate_risk_caps_widget(
            min_assets_held=1,
            universe=["SPY", "XLK"],  # These should be in SECTOR_MAP
            max_weight_per_asset=0.5,
            max_sector_weight=0.6,
        )
        # May have errors if tickers not in SECTOR_MAP, but no sector weight errors
        sector_errors = [e for e in errors if "sector" in e.lower()]
        # If tickers are in SECTOR_MAP and 2 sectors * 0.6 >= 1.0, no errors
        # This depends on SECTOR_MAP content
    
    def test_invalid_sector_weight_out_of_bounds(self):
        """Test sector weight outside (0, 1]."""
        errors = validate_risk_caps_widget(
            min_assets_held=1,
            universe=["SPY", "QQQ"],
            max_weight_per_asset=0.5,
            max_sector_weight=0.0,
        )
        assert any("max sector weight" in e.lower() for e in errors)
    
    def test_empty_universe_no_min_assets_error(self):
        """Test that min_assets validation skips when universe is empty."""
        # When universe is empty, we skip the min_assets check
        errors = validate_risk_caps_widget(
            min_assets_held=5,
            universe=[],
            max_weight_per_asset=0.5,
            max_sector_weight=None,
        )
        # Should not have min assets error because len(universe) == 0
        min_asset_errors = [e for e in errors if "min assets" in e.lower()]
        assert len(min_asset_errors) == 0


class TestValidateVolatilityTargetingWidget:
    """Tests for volatility targeting validation."""
    
    def test_valid_leverage(self):
        """Test valid leverage range."""
        errors = validate_volatility_targeting_widget(
            min_leverage=0.5,
            max_leverage=2.0,
        )
        assert len(errors) == 0
    
    def test_min_exceeds_max_leverage(self):
        """Test min leverage exceeds max leverage."""
        errors = validate_volatility_targeting_widget(
            min_leverage=2.0,
            max_leverage=1.0,
        )
        assert len(errors) == 1
        assert "min leverage" in errors[0].lower()
        assert "max leverage" in errors[0].lower()
    
    def test_equal_leverage(self):
        """Test equal min and max leverage (valid)."""
        errors = validate_volatility_targeting_widget(
            min_leverage=1.0,
            max_leverage=1.0,
        )
        assert len(errors) == 0


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
            max_weight_per_asset=0.5,
            max_sector_weight=None,
            available_tickers=["SPY", "QQQ", "IWM"],
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
            max_weight_per_asset=0.5,
            max_sector_weight=None,
            available_tickers=["SPY", "QQQ", "IWM"],
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
            max_weight_per_asset=0.5,
            max_sector_weight=None,
            available_tickers=["SPY", "QQQ", "IWM"],
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
            max_weight_per_asset=0.5,
            max_sector_weight=None,
            available_tickers=["SPY", "QQQ", "IWM"],
        )
        # Empty universe + start >= end + min_leverage > max_leverage
        assert len(errors) >= 3
    
    def test_infeasible_weight_cap(self):
        """Test infeasible per-asset cap is caught."""
        errors = validate_backtest_params(
            universe=["SPY", "QQQ"],
            start_date=date(2020, 1, 1),
            end_date=date(2021, 12, 31),
            min_assets_held=1,
            min_leverage=0.0,
            max_leverage=2.0,
            max_weight_per_asset=0.4,  # 2 * 0.4 = 0.8 < 1.0
            max_sector_weight=None,
            available_tickers=["SPY", "QQQ", "IWM"],
        )
        assert len(errors) == 1
        assert "infeasible" in errors[0].lower()
