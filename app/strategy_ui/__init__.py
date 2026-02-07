"""Strategy UI registry and renderers."""

from app.strategy_ui.registry import STRATEGY_SPECS, StrategySpec, get_strategy_spec

__all__ = [
    "STRATEGY_SPECS",
    "StrategySpec",
    "get_strategy_spec",
]
