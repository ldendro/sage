"""
Test that pytest fixtures work correctly.
"""

import pytest
import pandas as pd
import numpy as np


def test_sample_universe_fixture(sample_universe):
    """Test sample universe fixture."""
    assert len(sample_universe) == 5
    assert "SPY" in sample_universe
    assert "QQQ" in sample_universe


def test_default_system_config_fixture(default_system_config):
    """Test default system config fixture."""
    assert default_system_config.name == "Test System"
    assert len(default_system_config.universe) == 5
    assert default_system_config.start_date == "2020-01-01"


def test_sample_returns_fixture(sample_returns, sample_universe):
    """Test sample returns fixture."""
    assert isinstance(sample_returns, pd.DataFrame)
    assert len(sample_returns) == 252  # 1 year of trading days
    assert list(sample_returns.columns) == sample_universe
    # Returns should be reasonable
    assert sample_returns.mean().mean() < 0.01  # Average daily return < 1%


def test_sample_prices_fixture(sample_prices, sample_universe):
    """Test sample prices fixture."""
    assert isinstance(sample_prices, pd.DataFrame)
    assert len(sample_prices) == 252
    assert list(sample_prices.columns) == sample_universe
    # Prices should be positive
    assert (sample_prices > 0).all().all()


def test_sample_weights_fixture(sample_weights, sample_universe):
    """Test sample weights fixture."""
    assert isinstance(sample_weights, pd.DataFrame)
    assert len(sample_weights) == 252
    assert list(sample_weights.columns) == sample_universe
    # Weights should sum to 1
    assert np.allclose(sample_weights.sum(axis=1), 1.0)


def test_sample_equity_curve_fixture(sample_equity_curve):
    """Test sample equity curve fixture."""
    assert isinstance(sample_equity_curve, pd.Series)
    assert len(sample_equity_curve) == 252
    # Should start near 1.0
    assert 0.8 < sample_equity_curve.iloc[0] < 1.2


def test_sample_walkforward_result_fixture(sample_walkforward_result):
    """Test sample walkforward result fixture."""
    result = sample_walkforward_result
    
    assert result.system_name == "Test System"
    assert len(result.equity_curve) == 252
    assert len(result.daily_returns) == 252
    assert len(result.weights_history) == 252
    assert not result.yearly_summary.empty
    
    # Test helper methods work
    sharpe = result.get_full_period_sharpe()
    assert isinstance(sharpe, float)
    
    total_return = result.get_full_period_return()
    assert isinstance(total_return, float)


def test_minvar_config_fixture(minvar_system_config):
    """Test MinVar config fixture."""
    assert minvar_system_config.allocator.type == "min_variance_v1"
    assert minvar_system_config.portfolio.use_risk_caps is False


def test_single_strategy_config_fixture(single_strategy_config):
    """Test single strategy config fixture."""
    assert len(single_strategy_config.strategy.strategies) == 1
    assert single_strategy_config.has_single_strategy() is True
