"""Tests for formatting utilities."""

import pytest
from datetime import date
from app.utils.formatters import (
    format_percentage,
    format_ratio,
    format_currency,
    format_days,
    format_date,
    get_metric_color,
)


class TestFormatPercentage:
    """Tests for percentage formatting."""
    
    def test_positive_percentage(self):
        """Test positive percentage formatting."""
        assert format_percentage(0.15) == "15.00%"
        assert format_percentage(0.1567) == "15.67%"
    
    def test_negative_percentage(self):
        """Test negative percentage formatting."""
        assert format_percentage(-0.10) == "-10.00%"
    
    def test_zero_percentage(self):
        """Test zero percentage."""
        assert format_percentage(0.0) == "0.00%"
    
    def test_custom_decimals(self):
        """Test custom decimal places."""
        assert format_percentage(0.15678, decimals=1) == "15.7%"
        assert format_percentage(0.15678, decimals=3) == "15.678%"
    
    def test_none_value(self):
        """Test None value."""
        assert format_percentage(None) == "N/A"


class TestFormatRatio:
    """Tests for ratio formatting."""
    
    def test_positive_ratio(self):
        """Test positive ratio formatting."""
        assert format_ratio(1.5) == "1.50"
    
    def test_negative_ratio(self):
        """Test negative ratio formatting."""
        assert format_ratio(-0.5) == "-0.50"
    
    def test_custom_decimals(self):
        """Test custom decimal places."""
        assert format_ratio(1.5678, decimals=1) == "1.6"
    
    def test_none_value(self):
        """Test None value."""
        assert format_ratio(None) == "N/A"


class TestFormatCurrency:
    """Tests for currency formatting."""
    
    def test_default_format(self):
        """Test default currency formatting."""
        assert format_currency(1000.00) == "$1,000.00"
    
    def test_custom_symbol(self):
        """Test custom currency symbol."""
        assert format_currency(1000.00, symbol="€") == "€1,000.00"
    
    def test_none_value(self):
        """Test None value."""
        assert format_currency(None) == "N/A"


class TestFormatDays:
    """Tests for days formatting."""
    
    def test_zero_days(self):
        """Test zero days."""
        assert format_days(0) == "0 days"
    
    def test_one_day(self):
        """Test singular day."""
        assert format_days(1) == "1 day"
    
    def test_multiple_days(self):
        """Test multiple days."""
        assert format_days(30) == "30 days"
    
    def test_none_value(self):
        """Test None value."""
        assert format_days(None) == "N/A"


class TestFormatDate:
    """Tests for date formatting."""
    
    def test_date_object(self):
        """Test date object formatting."""
        assert format_date(date(2020, 1, 15)) == "2020-01-15"
    
    def test_none_value(self):
        """Test None value."""
        assert format_date(None) == "N/A"


class TestGetMetricColor:
    """Tests for metric color determination."""
    
    def test_positive_good(self):
        """Test positive value when positive is good."""
        assert get_metric_color(0.1, positive_is_good=True) == "green"
        assert get_metric_color(-0.1, positive_is_good=True) == "red"
    
    def test_negative_good(self):
        """Test negative value when negative is good (e.g., drawdown)."""
        assert get_metric_color(-0.1, positive_is_good=False) == "green"
        assert get_metric_color(0.1, positive_is_good=False) == "red"
    
    def test_zero_value(self):
        """Test zero value."""
        assert get_metric_color(0, positive_is_good=True) == "neutral"
    
    def test_none_value(self):
        """Test None value."""
        assert get_metric_color(None) == "neutral"
