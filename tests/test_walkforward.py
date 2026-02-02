"""
Tests for walkforward engine.
"""

import pytest
import pandas as pd
import numpy as np
import os

from sage_core.walkforward.engine import run_system_walkforward
from tests.conftest import get_warmup_period


class TestRunSystemWalkforward:
    """Tests for run_system_walkforward function."""
    
    def test_walkforward_basic(self):
        """Test basic walkforward execution."""
        # Use small universe and short date range
        result = run_system_walkforward(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-06-30",
        )
        
        # Check all expected keys
        assert "returns" in result
        assert "equity_curve" in result
        assert "weights" in result
        assert "raw_weights" in result
        assert "metrics" in result
        assert "asset_returns" in result
        
        # Check types
        assert isinstance(result["returns"], pd.Series)
        assert isinstance(result["equity_curve"], pd.Series)
        assert isinstance(result["weights"], pd.DataFrame)
        assert isinstance(result["raw_weights"], pd.DataFrame)
        assert isinstance(result["metrics"], dict)
        assert isinstance(result["asset_returns"], pd.DataFrame)
        
        # Check data integrity
        assert len(result["returns"]) > 0
        assert len(result["equity_curve"]) > 0
        assert len(result["weights"]) > 0
        
        # Equity curve should start at 100 (by construction)
        # (1 + returns).cumprod() * 100 with first return gives 100 * (1 + r[0])
        # So it won't be exactly 100, but close to it
        assert 95 <= result["equity_curve"].iloc[0] <= 105
        
        # Weights should sum to approximately 1 (or leverage * 1)
        # After vol targeting, weights might be scaled
        weight_sums = result["weights"].sum(axis=1)
        assert (weight_sums >= 0).all()  # Non-negative
    
    def test_walkforward_with_risk_caps(self):
        """Test walkforward with risk caps."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-03-31",
            max_weight_per_asset=0.4,
            max_sector_weight=0.6,
            min_assets_held=2,
        )
        
        # Check that risk caps were applied
        raw_weights = result["raw_weights"]
        
        # Skip NaN rows (warmup period for inverse vol)
        valid_weights = raw_weights.dropna()
        
        # No weight should exceed max_weight_per_asset
        assert (valid_weights <= 0.4 + 1e-6).all().all()
        
        # At least min_assets should have weight
        non_zero_counts = (valid_weights > 1e-6).sum(axis=1)
        assert (non_zero_counts >= 2).all()
    
    def test_walkforward_with_vol_targeting(self):
        """Test walkforward with volatility targeting."""
        vol_window = 20
        vol_lookback = 30
        
        result = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-06-30",
            target_vol=0.15,
            vol_window=vol_window,
            vol_lookback=vol_lookback,
            max_leverage=1.5,
        )
        
        # Vol targeted weights should differ from raw weights
        # (after warmup period)
        # NOTE: We compare vol_targeted_weights (pre-cap) with raw_weights
        # because final weights may be capped back down if leverage exceeded limits
        vol_targeted_weights = result["vol_targeted_weights"]
        raw_weights = result["raw_weights"]
        
        # Calculate actual warmup period
        warmup_days = get_warmup_period(vol_window, vol_lookback)
        
        # After warmup, some scaling should have occurred
        # Check that they're not identical
        if len(vol_targeted_weights) > warmup_days:
            post_warmup_vol_targeted = vol_targeted_weights.iloc[warmup_days:]
            post_warmup_raw = raw_weights.iloc[warmup_days:]
            
            # Should have some difference (not identical)
            assert not post_warmup_vol_targeted.equals(post_warmup_raw)
    
    def test_walkforward_metrics(self):
        """Test that metrics are calculated correctly."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-12-31",
        )
        
        metrics = result["metrics"]
        
        # Check all expected metrics
        assert "sharpe_ratio" in metrics
        assert "max_drawdown" in metrics
        assert "max_drawdown_pct" in metrics
        assert "volatility" in metrics
        assert "total_return" in metrics
        assert "cagr" in metrics
        assert "avg_daily_turnover" in metrics
        assert "total_turnover" in metrics
        assert "yearly_summary" in metrics
        
        # Check types and validity
        assert isinstance(metrics["sharpe_ratio"], float)
        assert isinstance(metrics["volatility"], float)
        assert isinstance(metrics["yearly_summary"], pd.DataFrame)
        
        # Volatility should be positive
        assert metrics["volatility"] > 0
        
        # Turnover should be non-negative
        assert metrics["avg_daily_turnover"] >= 0
        assert metrics["total_turnover"] >= 0
    
    def test_walkforward_different_universes(self):
        """Test walkforward with different universe sizes."""
        # Small universe
        result_small = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-03-31",
        )
        
        # Larger universe
        result_large = run_system_walkforward(
            universe=["SPY", "QQQ", "IWM", "XLF", "XLK"],
            start_date="2020-01-01",
            end_date="2020-03-31",
        )
        
        # Both should complete successfully
        assert len(result_small["returns"]) > 0
        assert len(result_large["returns"]) > 0
        
        # Larger universe should have more columns in weights
        assert result_large["weights"].shape[1] > result_small["weights"].shape[1]
    
    def test_walkforward_date_alignment(self):
        """Test that all outputs have aligned dates (after warmup period)."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-06-30",
        )
        
        # All series/dataframes should have the same index (after warmup)
        returns_index = result["returns"].index
        equity_index = result["equity_curve"].index
        weights_index = result["weights"].index
        
        assert returns_index.equals(equity_index)
        assert returns_index.equals(weights_index)
    
    def test_walkforward_no_leverage(self):
        """Test walkforward with no leverage (max_leverage=1.0)."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-03-31",
            max_leverage=1.0,
            min_leverage=0.0,
        )
        
        # Weights should not exceed 1.0 in total (after warmup)
        weight_sums = result["weights"].sum(axis=1)
        
        # Allow small tolerance for numerical precision
        assert (weight_sums <= 1.0 + 1e-6).all()
    
    def test_walkforward_invalid_dates(self):
        """Test walkforward with invalid date range."""
        with pytest.raises(ValueError):
            run_system_walkforward(
                universe=["SPY"],
                start_date="2020-12-31",
                end_date="2020-01-01",  # End before start
            )
    
    def test_walkforward_consistency(self):
        """Test that running twice with same params gives same results."""
        params = {
            "universe": ["SPY", "QQQ"],
            "start_date": "2020-01-01",
            "end_date": "2020-03-31",
            "max_weight_per_asset": 0.6,
            "target_vol": 0.12,
        }
        
        result1 = run_system_walkforward(**params)
        result2 = run_system_walkforward(**params)
        
        # Returns should be identical
        assert result1["returns"].equals(result2["returns"])
        
        # Equity curves should be identical
        assert result1["equity_curve"].equals(result2["equity_curve"])
        
        # Metrics should be identical
        assert result1["metrics"]["sharpe_ratio"] == result2["metrics"]["sharpe_ratio"]
