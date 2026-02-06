"""Registry for strategy UI renderers (app-side only)."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from app.strategy_ui.meanrev import render_params as render_meanrev_params
from app.strategy_ui.passthrough import render_params as render_passthrough_params
from app.strategy_ui.trend import render_params as render_trend_params

RenderParams = Callable[[str], Dict[str, Any]]


@dataclass(frozen=True)
class StrategySpec:
    name: str
    display_name: str
    description: str
    render_params: Optional[RenderParams]
    has_params: bool = True


STRATEGY_SPECS: Dict[str, StrategySpec] = {
    "passthrough": StrategySpec(
        name="passthrough",
        display_name="Passthrough",
        description="Uses raw asset returns without any signal transformation, so no params are needed.",
        render_params=render_passthrough_params,
        has_params=False,
    ),
    "trend": StrategySpec(
        name="trend",
        display_name="Trend Following",
        description="Long-term momentum strategy using multi-indicator trend signals",
        render_params=render_trend_params,
        has_params=True,
    ),
    "meanrev": StrategySpec(
        name="meanrev",
        display_name="Mean Reversion",
        description="Short-term mean reversion strategy using multiple indicators",
        render_params=render_meanrev_params,
        has_params=True,
    ),
}


def _fallback_display_name(name: str) -> str:
    return name.replace("_", " ").title()


def get_strategy_spec(name: str) -> StrategySpec:
    """Return strategy spec for UI rendering, with a safe fallback."""
    if name in STRATEGY_SPECS:
        return STRATEGY_SPECS[name]

    return StrategySpec(
        name=name,
        display_name=_fallback_display_name(name),
        description="",
        render_params=None,
        has_params=False,
    )
