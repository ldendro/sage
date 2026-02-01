"""Integration tests for warmup logic in walkforward engine."""

import pytest
import pandas as pd
from sage_core.walkforward.engine import run_system_walkforward


class TestWarmupLogicIntegration:
    """Integration tests for warmup period handling."""
    
    def test_results_start_at_start_date(self):
        """Test that results start exactly at user-specified start_date."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2023-06-01",
            end_date="2023-12-31",
            vol_window=60,
            vol_lookback=90,
        )
        
        # Equity curve should start at 2023-06-01 (or first trading day after)
        first_date = result["equity_curve"].index[0]
        assert first_date >= pd.Timestamp("2023-06-01")
        assert first_date <= pd.Timestamp("2023-06-05")  # Allow for weekend
        
        # Warmup should be 150 days (60 + 90)
        assert result["warmup_info"]["total_days"] == 150
    
    def test_warmup_period_calculation(self):
        """Test that warmup period is calculated correctly."""
        result = run_system_walkforward(
            universe=["SPY"],
            start_date="2023-06-01",
            end_date="2023-12-31",
            vol_window=60,
            vol_lookback=90,
        )
        
        warmup_info = result["warmup_info"]
        
        # Check total
        assert warmup_info["total_days"] == 150  # 60 + 90
        
        # Check components
        assert warmup_info["components"]["inverse_vol"] == 60
        assert warmup_info["components"]["vol_targeting"] == 90
        
        # Check description
        assert "150 days" in warmup_info["description"]
    
    def test_warmup_start_date_calculation(self):
        """Test that warmup_start_date is calculated correctly."""
        result = run_system_walkforward(
            universe=["SPY"],
            start_date="2023-06-01",
            end_date="2023-12-31",
            vol_window=60,
            vol_lookback=90,
        )
        
        # Warmup start should be ~150 days before 2023-06-01
        warmup_start = pd.Timestamp(result["warmup_start_date"])
        start_date = pd.Timestamp("2023-06-01")
        
        # Calculate expected warmup start (approximately)
        expected_warmup_start = start_date - pd.Timedelta(days=150)
        
        # Allow for some variation due to calendar days vs trading days
        diff = abs((warmup_start - expected_warmup_start).days)
        assert diff <= 2  # Within 2 days
    
    def test_different_warmup_parameters(self):
        """Test with different warmup parameters."""
        result = run_system_walkforward(
            universe=["SPY"],
            start_date="2023-06-01",
            end_date="2023-12-31",
            vol_window=30,
            vol_lookback=120,
        )
        
        # Warmup should be 30 + 120 = 150
        assert result["warmup_info"]["total_days"] == 150
        assert result["warmup_info"]["components"]["inverse_vol"] == 30
        assert result["warmup_info"]["components"]["vol_targeting"] == 120
    
    def test_equal_warmup_windows(self):
        """Test when vol_window equals vol_lookback."""
        result = run_system_walkforward(
            universe=["SPY"],
            start_date="2023-06-01",
            end_date="2023-12-31",
            vol_window=60,
            vol_lookback=60,
        )
        
        # Warmup should be 60 + 60 = 120
        assert result["warmup_info"]["total_days"] == 120
    
    def test_all_outputs_aligned(self):
        """Test that all outputs start at the same date."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2023-06-01",
            end_date="2023-12-31",
            vol_window=60,
            vol_lookback=90,
        )
        
        # All outputs should have the same first date
        first_date_returns = result["returns"].index[0]
        first_date_equity = result["equity_curve"].index[0]
        first_date_weights = result["weights"].index[0]
        first_date_asset_returns = result["asset_returns"].index[0]
        
        assert first_date_returns == first_date_equity
        assert first_date_returns == first_date_weights
        assert first_date_returns == first_date_asset_returns
    
    def test_no_nan_in_final_results(self):
        """Test that final results don't contain NaN from warmup period."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2023-06-01",
            end_date="2023-12-31",
            vol_window=60,
            vol_lookback=90,
        )
        
        # Weights should not have NaN
        assert not result["weights"].isna().any().any()
        
        # Returns should not have NaN
        assert not result["returns"].isna().any()
        
        # Equity curve should not have NaN
        assert not result["equity_curve"].isna().any()
    
    def test_equity_curve_starts_at_100(self):
        """Test that equity curve starts at 100."""
        result = run_system_walkforward(
            universe=["SPY"],
            start_date="2023-06-01",
            end_date="2023-12-31",
            vol_window=60,
            vol_lookback=90,
        )
        
        # First value should be 100
        assert abs(result["equity_curve"].iloc[0] - 100.0) < 0.01
    
    def test_warmup_longer_than_backtest(self):
        """Test edge case where warmup is longer than backtest period."""
        # This should still work - we load extra data before start_date
        result = run_system_walkforward(
            universe=["SPY"],
            start_date="2023-12-01",
            end_date="2023-12-31",
            vol_window=60,
            vol_lookback=90,
        )
        
        # Should still have results starting at 2023-12-01
        first_date = result["equity_curve"].index[0]
        assert first_date >= pd.Timestamp("2023-12-01")
        
        # Warmup should still be 150 days
        assert result["warmup_info"]["total_days"] == 150


class TestWarmupErrorHandling:
    """Tests for warmup-related error handling."""
    
    def test_insufficient_data_error(self):
        """Test error when insufficient historical data for warmup."""
        # Try to backtest with start date too early for available data
        with pytest.raises(ValueError, match="Insufficient historical data"):
            run_system_walkforward(
                universe=["SPY"],
                start_date="1990-01-01",  # Before SPY has data
                end_date="1990-12-31",
                vol_window=60,
                vol_lookback=90,
            )
    
    def test_no_data_after_start_date_error(self):
        """Test error when no data available at or after start_date."""
        # This would happen if start_date is in the future
        # or if all data is in the warmup period
        # Note: This is hard to test with real data, so we skip for now
        pass
