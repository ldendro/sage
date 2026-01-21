"""
Tests for risk caps.
"""

import pytest
import pandas as pd
import numpy as np

from sage_core.portfolio.risk_caps import (
    apply_all_risk_caps,
    apply_per_asset_caps,
    apply_per_sector_caps,
    apply_min_assets_constraint,
)
from sage_core.utils.constants import SECTOR_MAP


class TestApplyPerAssetCaps:
    """Tests for apply_per_asset_caps function."""
    
    def test_per_asset_caps_basic(self):
        """Test basic per-asset capping."""
        # Create weights with one asset over cap
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        weights = pd.DataFrame({
            "A": [0.6, 0.5, 0.4, 0.3, 0.2],
            "B": [0.3, 0.3, 0.3, 0.4, 0.5],
            "C": [0.1, 0.2, 0.3, 0.3, 0.3],
        }, index=dates)
        
        # Cap at 0.4
        capped = apply_per_asset_caps(weights, max_weight=0.4)
        
        # No weight should exceed 0.4
        assert (capped <= 0.4 + 1e-6).all().all()
        
        # Weights should sum to 1
        assert np.allclose(capped.sum(axis=1), 1.0)
    
    def test_per_asset_caps_preserves_below_cap(self):
        """Test that weights below cap are preserved proportionally."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        weights = pd.DataFrame({
            "A": [0.5],
            "B": [0.3],
            "C": [0.2],
        }, index=dates)
        
        capped = apply_per_asset_caps(weights, max_weight=0.4)
        
        # A should be capped to 0.4
        assert np.isclose(capped["A"].iloc[0], 0.4)
        
        # B and C should be scaled up proportionally
        # Original B:C ratio = 0.3:0.2 = 3:2
        # After capping A, remaining = 0.6 for B and C
        # B should get 0.6 * (3/5) = 0.36
        # C should get 0.6 * (2/5) = 0.24
        assert np.isclose(capped["B"].iloc[0], 0.36)
        assert np.isclose(capped["C"].iloc[0], 0.24)


class TestApplyPerSectorCaps:
    """Tests for apply_per_sector_caps function."""
    
    def test_per_sector_caps_basic(self):
        """Test basic per-sector capping."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        # Create weights where one sector is over cap
        weights = pd.DataFrame({
            "SPY": [0.3],  # Broad Market
            "XLF": [0.3],  # Financials
            "XLK": [0.2],  # Technology
            "XLE": [0.2],  # Energy
        }, index=dates)
        
        sector_map = {
            "SPY": "Broad Market",
            "XLF": "Financials",
            "XLK": "Technology",
            "XLE": "Energy",
        }
        
        # Cap sectors at 0.25 (Financials at 0.3 should be capped)
        # Call function directly to bypass feasibility check
        capped = apply_per_sector_caps(weights, sector_map, max_sector_weight=0.25)
        
        # Calculate sector weights
        sector_weights = {}
        for symbol in capped.columns:
            sector = sector_map[symbol]
            sector_weights[sector] = sector_weights.get(sector, 0) + capped[symbol].iloc[0]
        
        # No sector should exceed 0.25
        assert all(w <= 0.25 + 1e-6 for w in sector_weights.values())
        
        # Weights should sum to 1
        assert np.isclose(capped.sum(axis=1).iloc[0], 1.0)
    
    def test_per_sector_caps_multiple_assets_per_sector(self):
        """Test sector capping with multiple assets per sector."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        weights = pd.DataFrame({
            "XLF": [0.3],  # Financials
            "JPM": [0.2],  # Financials
            "XLK": [0.3],  # Technology
            "AAPL": [0.2],  # Technology
        }, index=dates)
        
        sector_map = {
            "XLF": "Financials",
            "JPM": "Financials",
            "XLK": "Technology",
            "AAPL": "Technology",
        }
        
        # Both sectors at 0.5, cap at 0.4
        # After capping both to 0.4, total = 0.8, renorm gives 0.5 each
        capped = apply_per_sector_caps(weights, sector_map, max_sector_weight=0.4)
        
        # Calculate sector weights
        fin_weight = capped["XLF"].iloc[0] + capped["JPM"].iloc[0]
        tech_weight = capped["XLK"].iloc[0] + capped["AAPL"].iloc[0]
        
        # After renormalization, both sectors should be 0.5
        assert np.isclose(fin_weight, 0.5, atol=1e-4)
        assert np.isclose(tech_weight, 0.5, atol=1e-4)
        
        # Weights should sum to 1
        assert np.isclose(capped.sum(axis=1).iloc[0], 1.0)


class TestApplyMinAssetsConstraint:
    """Tests for apply_min_assets_constraint function."""
    
    def test_min_assets_basic(self):
        """Test basic minimum assets constraint."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        # Have only 2 assets with weight
        weights = pd.DataFrame({
            "A": [0.6],
            "B": [0.4],
            "C": [0.0],
            "D": [0.0],
        }, index=dates)
        
        # Require at least 3 assets - but can't create weight from nothing
        # Function will keep top 3 by value (A, B, C) but C is still 0
        constrained = apply_min_assets_constraint(weights, min_assets=3)
        
        # Will still only have 2 non-zero weights (can't create weight from 0)
        non_zero = (constrained.iloc[0] > 1e-6).sum()
        assert non_zero == 2
        
        # Weights should sum to 1
        assert np.isclose(constrained.sum(axis=1).iloc[0], 1.0)
    
    def test_min_assets_already_satisfied(self):
        """Test that constraint is no-op when already satisfied."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        weights = pd.DataFrame({
            "A": [0.4],
            "B": [0.3],
            "C": [0.2],
            "D": [0.1],
        }, index=dates)
        
        # Require at least 3 assets (already have 4)
        # Call function directly
        constrained = apply_min_assets_constraint(weights, min_assets=3)
        
        # Should be unchanged
        assert (constrained == weights).all().all()


class TestApplyAllRiskCaps:
    """Tests for apply_all_risk_caps function."""
    
    def test_all_risk_caps_basic(self):
        """Test applying all risk caps together."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        weights = pd.DataFrame({
            "SPY": [0.5],
            "QQQ": [0.3],
            "IWM": [0.2],
        }, index=dates)
        
        sector_map = {
            "SPY": "Broad Market",
            "QQQ": "Technology",  # Different sector
            "IWM": "Broad Market",
        }
        
        # Use feasible parameters: 2 * 0.5 = 1.0 >= 1.0
        # 2 sectors * 0.8 = 1.6 >= 1.0 (sector feasible)
        capped = apply_all_risk_caps(
            weights,
            sector_map=sector_map,
            max_weight_per_asset=0.5,
            max_sector_weight=0.8,
            min_assets_held=2,
        )
        
        # SPY should be capped to 0.5
        assert capped["SPY"].iloc[0] <= 0.5 + 1e-6
        
        # Weights should sum to 1
        assert np.isclose(capped.sum(axis=1).iloc[0], 1.0)
        
        # At least 2 assets should have weight
        non_zero = (capped.iloc[0] > 1e-6).sum()
        assert non_zero >= 2
    
    def test_all_risk_caps_infeasible_constraints(self):
        """Test that infeasible constraints raise ValueError."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        weights = pd.DataFrame({
            "A": [0.5],
            "B": [0.3],
            "C": [0.2],
        }, index=dates)
        
        sector_map = {"A": "X", "B": "Y", "C": "Z"}
        
        # min_assets=5 but only 3 assets
        with pytest.raises(ValueError, match="cannot exceed number of assets"):
            apply_all_risk_caps(
                weights,
                sector_map=sector_map,
                min_assets_held=5,
            )
        
        # min_assets=5 * max_weight=0.15 = 0.75 < 1.0 (infeasible)
        # Need more assets for this to work
        weights_5 = pd.DataFrame({
            "A": [0.2], "B": [0.2], "C": [0.2], "D": [0.2], "E": [0.2],
        }, index=dates)
        sector_map_5 = {"A": "X", "B": "Y", "C": "Z", "D": "W", "E": "V"}
        
        with pytest.raises(ValueError, match="Infeasible constraints"):
            apply_all_risk_caps(
                weights_5,
                sector_map=sector_map_5,
                max_weight_per_asset=0.15,
                min_assets_held=5,
            )
    
    def test_all_risk_caps_invalid_sector_weight(self):
        """Test that invalid max_sector_weight raises ValueError."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        weights = pd.DataFrame({
            "A": [0.5],
            "B": [0.3],
            "C": [0.2],
        }, index=dates)
        
        sector_map = {"A": "X", "B": "Y", "C": "Z"}
        
        # max_sector_weight = 0 should fail
        with pytest.raises(ValueError, match="max_sector_weight must be in"):
            apply_all_risk_caps(
                weights,
                sector_map=sector_map,
                max_sector_weight=0,
            )
        
        # max_sector_weight > 1.0 should fail
        with pytest.raises(ValueError, match="max_sector_weight must be in"):
            apply_all_risk_caps(
                weights,
                sector_map=sector_map,
                max_sector_weight=1.5,
            )
        
        # Negative max_sector_weight should fail
        with pytest.raises(ValueError, match="max_sector_weight must be in"):
            apply_all_risk_caps(
                weights,
                sector_map=sector_map,
                max_sector_weight=-0.1,
            )
    
    def test_all_risk_caps_infeasible_sector_weight(self):
        """Test that infeasible max_sector_weight raises ValueError."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        # All assets in same sector
        weights = pd.DataFrame({
            "A": [0.4],
            "B": [0.3],
            "C": [0.3],
        }, index=dates)
        
        sector_map = {"A": "X", "B": "X", "C": "X"}  # All in sector X
        
        # max_sector_weight = 0.8 < 1.0 is infeasible (all assets in one sector)
        with pytest.raises(ValueError, match="Infeasible sector constraint"):
            apply_all_risk_caps(
                weights,
                sector_map=sector_map,
                max_weight_per_asset=0.5,  # Feasible: 1 * 0.5 = 0.5 >= 0.5
                max_sector_weight=0.8,
            )
        
        # max_sector_weight = 1.0 should work
        capped = apply_all_risk_caps(
            weights,
            sector_map=sector_map,
            max_weight_per_asset=0.5,
            max_sector_weight=1.0,
        )
        assert capped is not None
    
    def test_all_risk_caps_with_sector_map(self):
        """Test risk caps with real sector map."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        weights = pd.DataFrame({
            "SPY": [0.3],
            "XLF": [0.25],
            "XLK": [0.25],
            "XLE": [0.2],
        }, index=dates)
        
        # Use feasible parameters: 3 * 0.34 = 1.02 >= 1.0
        capped = apply_all_risk_caps(
            weights,
            sector_map=SECTOR_MAP,
            max_weight_per_asset=0.34,
            max_sector_weight=0.50,
            min_assets_held=3,
        )
        
        # All constraints should be satisfied
        assert (capped <= 0.34 + 1e-6).all().all()  # Per-asset cap
        assert np.isclose(capped.sum(axis=1).iloc[0], 1.0)  # Normalized
        assert (capped.iloc[0] > 1e-6).sum() >= 3  # Min assets
    
    def test_all_risk_caps_no_sector_cap(self):
        """Test that sector caps can be disabled."""
        dates = pd.date_range("2020-01-01", periods=1, freq="B")
        
        weights = pd.DataFrame({
            "A": [0.4],
            "B": [0.3],
            "C": [0.3],
        }, index=dates)
        
        sector_map = {"A": "X", "B": "X", "C": "Y"}
        
        # Sector X has 0.7 weight, but no sector cap
        capped = apply_all_risk_caps(
            weights,
            sector_map=sector_map,
            max_weight_per_asset=0.5,
            max_sector_weight=None,  # No sector cap
            min_assets_held=2,
        )
        
        # Sector X should still have 0.7 (no capping)
        sector_x_weight = capped["A"].iloc[0] + capped["B"].iloc[0]
        assert np.isclose(sector_x_weight, 0.7)
