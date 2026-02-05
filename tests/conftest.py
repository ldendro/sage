"""
Pytest configuration and shared fixtures for Sage tests.

This module provides reusable fixtures for testing, including:
- Sample configurations
- Mock data generators
- Common test utilities
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

from sage_core.config.system_config import (
    SystemConfig,
    StrategyConfig,
    MetaConfig,
    AllocatorConfig,
    PortfolioConfig,
    ScheduleConfig,
)
from sage_core.walkforward.results import WalkforwardResult
from sage_core.utils import constants


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def sample_universe():
    """Sample universe of 5 symbols for testing."""
    return ["SPY", "QQQ", "IWM", "XLF", "XLE"]


@pytest.fixture
def default_system_config(sample_universe):
    """Default SystemConfig for testing."""
    return SystemConfig(
        name="Test System",
        universe=sample_universe,
        start_date="2020-01-01",
        end_date="2020-12-31",
    )


@pytest.fixture
def minvar_system_config(sample_universe):
    """SystemConfig with MinVar allocator (risk_caps disabled)."""
    return SystemConfig(
        name="Test MinVar",
        universe=sample_universe,
        start_date="2020-01-01",
        end_date="2020-12-31",
        allocator=AllocatorConfig(type="min_variance_v1", lookback=60),
        portfolio=PortfolioConfig(use_risk_caps=False),
    )


@pytest.fixture
def single_strategy_config(sample_universe):
    """SystemConfig with single strategy."""
    return SystemConfig(
        name="Single Strategy Test",
        universe=sample_universe,
        start_date="2020-01-01",
        end_date="2020-12-31",
        strategy=StrategyConfig(strategies=["trend_v1"]),
    )


# ============================================================================
# Data Generation Fixtures
# ============================================================================

@pytest.fixture
def sample_dates():
    """Generate 252 trading days (1 year) for testing."""
    start = pd.Timestamp("2020-01-01")
    return pd.date_range(start=start, periods=252, freq="B")  # Business days


@pytest.fixture
def sample_returns(sample_dates, sample_universe):
    """
    Generate sample returns data for testing.
    
    Returns:
        DataFrame with index=dates, columns=symbols, values=daily returns
    """
    np.random.seed(42)  # Reproducible
    n_days = len(sample_dates)
    n_assets = len(sample_universe)
    
    # Generate random returns with realistic properties
    returns = np.random.normal(0.0005, 0.015, size=(n_days, n_assets))
    
    return pd.DataFrame(
        returns,
        index=sample_dates,
        columns=sample_universe,
    )


@pytest.fixture
def sample_prices(sample_returns):
    """
    Generate sample price data from returns.
    
    Returns:
        DataFrame with index=dates, columns=symbols, values=prices
    """
    # Start at 100, compound returns
    prices = (1 + sample_returns).cumprod() * 100
    return prices


@pytest.fixture
def sample_weights(sample_dates, sample_universe):
    """
    Generate sample portfolio weights for testing.
    
    Returns:
        DataFrame with index=dates, columns=symbols, values=weights (sum to 1)
    """
    np.random.seed(42)
    n_days = len(sample_dates)
    n_assets = len(sample_universe)
    
    # Generate random weights that sum to 1
    raw_weights = np.random.uniform(0, 1, size=(n_days, n_assets))
    weights = raw_weights / raw_weights.sum(axis=1, keepdims=True)
    
    return pd.DataFrame(
        weights,
        index=sample_dates,
        columns=sample_universe,
    )


@pytest.fixture
def sample_equity_curve(sample_dates):
    """
    Generate sample equity curve for testing.
    
    Returns:
        Series with index=dates, values=equity (starting at 1.0)
    """
    np.random.seed(42)
    daily_returns = np.random.normal(0.0005, 0.01, size=len(sample_dates))
    equity = (1 + daily_returns).cumprod()
    
    return pd.Series(equity, index=sample_dates)


@pytest.fixture
def sample_walkforward_result(
    default_system_config,
    sample_equity_curve,
    sample_returns,
    sample_weights,
):
    """
    Generate a complete WalkforwardResult for testing.
    
    Returns:
        WalkforwardResult with sample data
    """
    # Extract daily returns from equity curve
    daily_returns = sample_equity_curve.pct_change().fillna(0)
    
    # Create yearly summary
    years = sample_equity_curve.index.year.unique()
    yearly_data = []
    for year in years:
        year_mask = sample_equity_curve.index.year == year
        year_returns = daily_returns[year_mask]
        
        yearly_data.append({
            "year": year,
            "sharpe": np.sqrt(252) * year_returns.mean() / year_returns.std(),
            "return": (1 + year_returns).prod() - 1,
            "max_drawdown": -0.05,  # Placeholder
            "avg_leverage": 1.0,
        })
    
    yearly_summary = pd.DataFrame(yearly_data).set_index("year")
    
    # Create turnover data
    turnover = pd.DataFrame({
        "year": years,
        "avg_turnover": [0.02] * len(years),
    }).set_index("year")
    
    return WalkforwardResult(
        system_name=default_system_config.name,
        config=default_system_config.to_dict(),
        equity_curve=sample_equity_curve,
        daily_returns=daily_returns,
        weights_history=sample_weights,
        yearly_summary=yearly_summary,
        turnover=turnover,
        metadata={"test": True},
    )


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory for testing."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def sector_map():
    """Return the default sector map for testing."""
    return constants.SECTOR_MAP.copy()


@pytest.fixture
def default_meta_params():
    """Return default hard meta parameters for testing."""
    return constants.DEFAULT_HARD_META_PARAMS.copy()


# ============================================================================
# Warmup Helper Functions
# ============================================================================

def default_warmup_days(vol_window, vol_lookback):
    """
    Calculate default warmup period in trading days.
    
    Args:
        vol_window: Volatility window for inverse vol allocator
        vol_lookback: Lookback period for vol targeting
    
    Returns:
        Total warmup period in trading days
    """
    from sage_core.utils.warmup import calculate_warmup_period
    return calculate_warmup_period(
        strategies={'passthrough': {'params': {}}},
        meta_allocator=None,
        vol_window=vol_window,
        vol_lookback=vol_lookback
    )["total_trading_days"]
