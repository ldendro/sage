"""
Basic tests for SystemConfig validation.

These tests verify that the config models work correctly and catch invalid configurations.
"""

import pytest
from sage_core.config.system_config import (
    SystemConfig,
    StrategyConfig,
    MetaConfig,
    AllocatorConfig,
    PortfolioConfig,
    ScheduleConfig,
)


def test_default_system_config():
    """Test that default SystemConfig can be created."""
    config = SystemConfig(
        name="Test System",
        universe=["SPY", "QQQ"],
        start_date="2015-01-01",
        end_date="2024-12-31",
    )
    
    assert config.name == "Test System"
    assert config.universe == ["SPY", "QQQ"]
    assert config.strategy.strategies == ["trend_v1", "meanrev_v1"]
    assert config.meta.combination_method == "hard_v1"
    assert config.meta.use_gates is True
    assert config.allocator.type == "inverse_vol_v1"
    assert config.portfolio.use_risk_caps is True


def test_strategy_config_validation():
    """Test StrategyConfig validation."""
    # Valid: at least one strategy
    config = StrategyConfig(strategies=["trend_v1"])
    assert len(config.strategies) == 1
    
    # Invalid: empty strategies list
    with pytest.raises(ValueError, match="At least one strategy must be specified"):
        StrategyConfig(strategies=[])


def test_date_format_validation():
    """Test date format validation."""
    # Valid date format
    config = SystemConfig(
        name="Test",
        universe=["SPY"],
        start_date="2020-01-01",
        end_date="2020-12-31",
    )
    assert config.start_date == "2020-01-01"
    
    # Invalid date format
    with pytest.raises(ValueError, match="Date must be in YYYY-MM-DD format"):
        SystemConfig(
            name="Test",
            universe=["SPY"],
            start_date="01/01/2020",  # Wrong format
            end_date="2020-12-31",
        )


def test_universe_validation():
    """Test universe validation."""
    # Invalid: empty universe
    with pytest.raises(ValueError, match="Universe must contain at least one symbol"):
        SystemConfig(
            name="Test",
            universe=[],  # Empty
            start_date="2020-01-01",
            end_date="2020-12-31",
        )


def test_minvar_risk_caps_incompatibility():
    """Test that MinVar + risk_caps raises validation error."""
    # This should raise an error
    with pytest.raises(ValueError, match="MinVar allocator already incorporates risk caps"):
        SystemConfig(
            name="Test",
            universe=["SPY"],
            start_date="2020-01-01",
            end_date="2020-12-31",
            allocator=AllocatorConfig(type="min_variance_v1"),
            portfolio=PortfolioConfig(use_risk_caps=True),  # Incompatible!
        )


def test_minvar_without_risk_caps_valid():
    """Test that MinVar without risk_caps is valid."""
    config = SystemConfig(
        name="Test MinVar",
        universe=["SPY"],
        start_date="2020-01-01",
        end_date="2020-12-31",
        allocator=AllocatorConfig(type="min_variance_v1"),
        portfolio=PortfolioConfig(use_risk_caps=False),  # Valid
    )
    assert config.allocator.type == "min_variance_v1"
    assert config.portfolio.use_risk_caps is False


def test_risk_parity_with_risk_caps_valid():
    """Test that Risk Parity with risk_caps is valid."""
    config = SystemConfig(
        name="Test RP",
        universe=["SPY"],
        start_date="2020-01-01",
        end_date="2020-12-31",
        allocator=AllocatorConfig(type="risk_parity_v1"),
        portfolio=PortfolioConfig(use_risk_caps=True),  # Valid for RP
    )
    assert config.allocator.type == "risk_parity_v1"
    assert config.portfolio.use_risk_caps is True


def test_meta_config_defaults():
    """Test MetaConfig defaults."""
    meta = MetaConfig()
    assert meta.combination_method == "hard_v1"
    assert meta.use_gates is True
    assert meta.gate_params == {}
    assert meta.meta_params == {}


def test_meta_config_soft_allocation():
    """Test MetaConfig with soft allocation."""
    meta = MetaConfig(
        combination_method="soft_v1",
        use_gates=False,
        meta_params={"smoothing_window": 5},
    )
    assert meta.combination_method == "soft_v1"
    assert meta.use_gates is False
    assert meta.meta_params["smoothing_window"] == 5


def test_config_serialization():
    """Test config serialization to dict and JSON."""
    config = SystemConfig(
        name="Test System",
        universe=["SPY", "QQQ"],
        start_date="2020-01-01",
        end_date="2020-12-31",
    )
    
    # To dict
    config_dict = config.to_dict()
    assert config_dict["name"] == "Test System"
    assert config_dict["universe"] == ["SPY", "QQQ"]
    
    # To JSON
    config_json = config.to_json()
    assert "Test System" in config_json
    
    # From dict
    config_restored = SystemConfig.from_dict(config_dict)
    assert config_restored.name == config.name
    
    # From JSON
    config_from_json = SystemConfig.from_json(config_json)
    assert config_from_json.name == config.name


def test_schedule_config_frequencies():
    """Test ScheduleConfig with different frequencies."""
    schedule = ScheduleConfig(
        strategy_train_freq="annual",
        meta_rebalance_freq="monthly",
        allocator_rebalance_freq="quarterly",
        portfolio_rebalance_freq="daily",
    )
    assert schedule.strategy_train_freq == "annual"
    assert schedule.meta_rebalance_freq == "monthly"
    assert schedule.allocator_rebalance_freq == "quarterly"
    assert schedule.portfolio_rebalance_freq == "daily"


def test_single_strategy_detection():
    """Test that single strategy configs are detected correctly."""
    # Single strategy
    config_single = SystemConfig(
        name="Single Strategy",
        universe=["SPY"],
        start_date="2020-01-01",
        end_date="2020-12-31",
        strategy=StrategyConfig(strategies=["trend_v1"]),
    )
    assert config_single.has_single_strategy() is True
    
    # Multiple strategies
    config_multi = SystemConfig(
        name="Multi Strategy",
        universe=["SPY"],
        start_date="2020-01-01",
        end_date="2020-12-31",
        strategy=StrategyConfig(strategies=["trend_v1", "meanrev_v1"]),
    )
    assert config_multi.has_single_strategy() is False


def test_single_strategy_warnings():
    """Test that warnings are generated for single-strategy configs."""
    # Single strategy should generate warning
    config = SystemConfig(
        name="Test",
        universe=["SPY"],
        start_date="2020-01-01",
        end_date="2020-12-31",
        strategy=StrategyConfig(strategies=["trend_v1"]),
        meta=MetaConfig(combination_method="soft_v1"),
    )
    
    warnings = config.get_config_warnings()
    assert len(warnings) == 1
    assert "Single strategy configured" in warnings[0]
    assert "combination_method" in warnings[0]
    assert "will be ignored" in warnings[0]
    
    # Multiple strategies should not generate warning
    config_multi = SystemConfig(
        name="Test",
        universe=["SPY"],
        start_date="2020-01-01",
        end_date="2020-12-31",
        strategy=StrategyConfig(strategies=["trend_v1", "meanrev_v1"]),
    )
    
    warnings_multi = config_multi.get_config_warnings()
    assert len(warnings_multi) == 0
