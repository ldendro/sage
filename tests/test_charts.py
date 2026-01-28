"""Tests for chart utilities."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go

from app.utils.charts import (
    create_equity_curve_chart,
    create_drawdown_chart,
    create_weight_allocation_chart,
)


class TestCreateEquityCurveChart:
    """Tests for equity curve chart creation."""
    
    def test_basic_equity_curve(self):
        """Test basic equity curve chart creation."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        equity = pd.Series(
            np.linspace(100, 150, 100),
            index=dates,
            name="equity"
        )
        
        fig = create_equity_curve_chart(equity)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].name == "Portfolio Value"
        assert fig.data[0].mode == "lines"
    
    def test_equity_curve_custom_title(self):
        """Test equity curve with custom title."""
        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        equity = pd.Series(np.linspace(100, 120, 50), index=dates)
        
        fig = create_equity_curve_chart(equity, title="Custom Title")
        
        assert "Custom Title" in fig.layout.title.text


class TestCreateDrawdownChart:
    """Tests for drawdown chart creation."""
    
    def test_basic_drawdown_chart(self):
        """Test basic drawdown chart creation."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        # Create some drawdown data (negative values)
        drawdown = pd.Series(
            -np.abs(np.sin(np.linspace(0, 4*np.pi, 100))) * 0.2,
            index=dates,
            name="drawdown"
        )
        
        fig = create_drawdown_chart(drawdown)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].name == "Drawdown"
        assert fig.data[0].fill == "tozeroy"
    
    def test_drawdown_chart_custom_height(self):
        """Test drawdown chart with custom height."""
        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        drawdown = pd.Series(np.zeros(50), index=dates)
        
        fig = create_drawdown_chart(drawdown, height=600)
        
        assert fig.layout.height == 600


class TestCreateWeightAllocationChart:
    """Tests for weight allocation chart creation."""
    
    def test_basic_weight_allocation(self):
        """Test basic weight allocation chart with 3 assets."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        weights = pd.DataFrame({
            "SPY": np.full(100, 0.4),
            "QQQ": np.full(100, 0.35),
            "IWM": np.full(100, 0.25),
        }, index=dates)
        
        fig = create_weight_allocation_chart(weights)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 3  # One trace per asset
        
        # Check all traces have stackgroup
        for trace in fig.data:
            assert trace.stackgroup == "one"
        
        # Check asset names are in the chart
        trace_names = [trace.name for trace in fig.data]
        assert "SPY" in trace_names
        assert "QQQ" in trace_names
        assert "IWM" in trace_names
    
    def test_weight_allocation_empty_dataframe(self):
        """Test weight allocation with empty DataFrame."""
        weights = pd.DataFrame()
        
        fig = create_weight_allocation_chart(weights)
        
        assert isinstance(fig, go.Figure)
        # Should have annotation instead of traces
        assert len(fig.layout.annotations) > 0
        assert "No weight data available" in fig.layout.annotations[0].text
    
    def test_weight_allocation_single_asset(self):
        """Test weight allocation with single asset."""
        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        weights = pd.DataFrame({
            "SPY": np.full(50, 1.0),
        }, index=dates)
        
        fig = create_weight_allocation_chart(weights)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].name == "SPY"
    
    def test_weight_allocation_many_assets(self):
        """Test weight allocation with 12 assets."""
        dates = pd.date_range("2020-01-01", periods=100, freq="D")
        assets = ["SPY", "QQQ", "IWM", "XLU", "XLV", "XLP", 
                  "XLF", "XLE", "XLI", "XLK", "XLY", "XLB"]
        
        # Equal weight allocation
        weights = pd.DataFrame({
            asset: np.full(100, 1.0 / len(assets))
            for asset in assets
        }, index=dates)
        
        fig = create_weight_allocation_chart(weights)
        
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == len(assets)
        
        # Verify all assets present
        trace_names = [trace.name for trace in fig.data]
        for asset in assets:
            assert asset in trace_names
    
    def test_weight_allocation_sorted_alphabetically(self):
        """Test that assets are sorted alphabetically in the chart."""
        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        weights = pd.DataFrame({
            "ZZZ": np.full(50, 0.3),
            "AAA": np.full(50, 0.4),
            "MMM": np.full(50, 0.3),
        }, index=dates)
        
        fig = create_weight_allocation_chart(weights)
        
        # Extract trace names in order
        trace_names = [trace.name for trace in fig.data]
        
        # Should be sorted alphabetically
        assert trace_names == sorted(trace_names)
    
    def test_weight_allocation_percentage_conversion(self):
        """Test that weights are converted from decimals to percentages."""
        dates = pd.date_range("2020-01-01", periods=10, freq="D")
        weights = pd.DataFrame({
            "SPY": np.full(10, 0.5),  # 50%
            "QQQ": np.full(10, 0.5),  # 50%
        }, index=dates)
        
        fig = create_weight_allocation_chart(weights)
        
        # Y-axis should be in percentages
        assert fig.layout.yaxis.title.text == "Allocation (%)"
        assert list(fig.layout.yaxis.range) == [0, 100]
        
        # Check that data is scaled to percentages
        # Since we have 50% each, sum should be 100%
        assert fig.data[0].y[0] == 50.0  # First asset at 50%
    
    def test_weight_allocation_custom_title(self):
        """Test weight allocation with custom title."""
        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        weights = pd.DataFrame({
            "SPY": np.full(50, 1.0),
        }, index=dates)
        
        fig = create_weight_allocation_chart(weights, title="Custom Allocation")
        
        assert "Custom Allocation" in fig.layout.title.text
    
    def test_weight_allocation_custom_height(self):
        """Test weight allocation with custom height."""
        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        weights = pd.DataFrame({
            "SPY": np.full(50, 1.0),
        }, index=dates)
        
        fig = create_weight_allocation_chart(weights, height=700)
        
        assert fig.layout.height == 700
    
    def test_weight_allocation_has_range_selector(self):
        """Test that weight allocation chart has range selector buttons."""
        dates = pd.date_range("2020-01-01", periods=365, freq="D")
        weights = pd.DataFrame({
            "SPY": np.full(365, 0.5),
            "QQQ": np.full(365, 0.5),
        }, index=dates)
        
        fig = create_weight_allocation_chart(weights)
        
        # Check range selector exists
        assert fig.layout.xaxis.rangeselector is not None
        assert len(fig.layout.xaxis.rangeselector.buttons) > 0
        
        # Check for expected buttons (1M, 3M, 6M, YTD, 1Y, ALL)
        button_labels = [btn.label for btn in fig.layout.xaxis.rangeselector.buttons]
        assert "1M" in button_labels
        assert "ALL" in button_labels
    
    def test_weight_allocation_legend_configuration(self):
        """Test that legend is properly configured."""
        dates = pd.date_range("2020-01-01", periods=50, freq="D")
        weights = pd.DataFrame({
            "SPY": np.full(50, 0.5),
            "QQQ": np.full(50, 0.5),
        }, index=dates)
        
        fig = create_weight_allocation_chart(weights)
        
        # Check legend exists and is configured
        assert fig.layout.legend is not None
        assert fig.layout.legend.orientation == "v"
        assert fig.layout.legend.x == 1.02  # Positioned to the right
