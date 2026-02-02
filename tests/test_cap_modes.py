"""Tests for risk cap modes in walkforward engine."""

import pytest
import pandas as pd
import numpy as np

from sage_core.walkforward.engine import run_system_walkforward


class TestWalkforwardCapModes:
    """Tests for cap_mode parameter in run_system_walkforward."""
    
    def test_cap_mode_both(self):
        """Test that 'both' mode applies caps before and after vol targeting."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-03-31",
            cap_mode="both",
            max_weight_per_asset=0.3,
            max_leverage=2.0,
        )
        
        # Final weights should never exceed cap
        max_final_weight = result["weights"].max().max()
        assert max_final_weight <= 0.3 + 1e-6, f"Final weight {max_final_weight} exceeds cap 0.3"
        
        # Raw weights (pre-leverage) should also not exceed cap
        max_raw_weight = result["raw_weights"].dropna().max().max()
        assert max_raw_weight <= 0.3 + 1e-6, f"Raw weight {max_raw_weight} exceeds cap 0.3"
    
    def test_cap_mode_pre_leverage(self):
        """Test that 'pre_leverage' mode only caps before vol targeting."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-03-31",
            cap_mode="pre_leverage",
            max_weight_per_asset=0.3,
            max_leverage=2.0,
        )
        
        # Raw weights (pre-leverage) should not exceed cap
        max_raw_weight = result["raw_weights"].dropna().max().max()
        assert max_raw_weight <= 0.3 + 1e-6, f"Raw weight {max_raw_weight} exceeds cap 0.3"
        
        # Final weights CAN exceed cap due to leverage
        # At 2× leverage, 0.3 can become 0.6
        max_final_weight = result["weights"].max().max()
        # We don't assert it MUST exceed (depends on vol), just that it CAN
        # Just verify test ran successfully
        assert max_final_weight >= 0, "Final weights should exist"
    
    def test_cap_mode_post_leverage(self):
        """Test that 'post_leverage' mode only caps after vol targeting."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ", "IWM"],  # Use 3 assets
            start_date="2020-01-01",
            end_date="2020-03-31",
            cap_mode="post_leverage",
            max_weight_per_asset=0.4,  # Higher cap
            max_leverage=1.5,
        )
        
        # Final weights should never exceed cap (with small tolerance for renormalization)
        max_final_weight = result["weights"].max().max()
        assert max_final_weight <= 0.4 + 1e-4, f"Final weight {max_final_weight} exceeds cap 0.4"
        
        # Raw weights (pre-leverage) CAN exceed cap
        # Just verify test ran successfully
        max_raw_weight = result["raw_weights"].dropna().max().max()
        assert max_raw_weight >= 0, "Raw weights should exist"
    
    def test_cap_mode_invalid(self):
        """Test that invalid cap_mode raises ValueError."""
        with pytest.raises(ValueError, match="Invalid cap_mode"):
            run_system_walkforward(
                universe=["SPY"],
                start_date="2020-01-01",
                end_date="2020-03-31",
                cap_mode="invalid_mode",
            )
    
    def test_cap_mode_backward_compatibility(self):
        """Test that omitting cap_mode defaults to 'both'."""
        result_default = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-03-31",
            max_weight_per_asset=0.3,
            # No cap_mode specified
        )
        
        result_both = run_system_walkforward(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-03-31",
            max_weight_per_asset=0.3,
            cap_mode="both",
        )
        
        # Results should be identical
        assert result_default["returns"].equals(result_both["returns"])
        assert result_default["weights"].equals(result_both["weights"])
    
    def test_cap_mode_with_sector_caps(self):
        """Test cap modes work with sector caps enabled."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-03-31",
            cap_mode="both",
            max_weight_per_asset=0.25,
            max_sector_weight=0.6,
        )
        
        # Should complete without errors
        assert "weights" in result
        assert len(result["weights"]) > 0
    
    def test_cap_mode_with_min_assets(self):
        """Test cap modes work with min_assets_held constraint."""
        result = run_system_walkforward(
            universe=["SPY", "QQQ", "IWM"],
            start_date="2020-01-01",
            end_date="2020-03-31",
            cap_mode="both",
            max_weight_per_asset=0.4,
            min_assets_held=2,
        )
        
        # At least 2 assets should have weight each day
        non_zero_counts = (result["weights"] > 1e-6).sum(axis=1)
        assert (non_zero_counts >= 2).all(), "Should have at least 2 assets held"
