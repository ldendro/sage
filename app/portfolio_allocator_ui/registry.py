"""Registry for portfolio allocator UI renderers (app-side only)."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from app.portfolio_allocator_ui.inverse_vol import render_params as render_inverse_vol_params

RenderParams = Callable[[str], Dict[str, Any]]


@dataclass(frozen=True)
class PortfolioAllocatorSpec:
    name: str
    display_name: str
    description: str
    render_params: Optional[RenderParams]
    has_params: bool = True


PORTFOLIO_ALLOCATOR_SPECS: Dict[str, PortfolioAllocatorSpec] = {
    "inverse_vol_v1": PortfolioAllocatorSpec(
        name="inverse_vol_v1",
        display_name="Inverse Volatility",
        description="Allocate across assets by inverse volatility weighting",
        render_params=render_inverse_vol_params,
        has_params=True,
    ),
}


def _fallback_display_name(name: str) -> str:
    return name.replace("_", " ").title()


def get_portfolio_allocator_spec(name: str) -> PortfolioAllocatorSpec:
    """Return portfolio allocator spec for UI rendering, with a safe fallback."""
    if name in PORTFOLIO_ALLOCATOR_SPECS:
        return PORTFOLIO_ALLOCATOR_SPECS[name]

    return PortfolioAllocatorSpec(
        name=name,
        display_name=_fallback_display_name(name),
        description="",
        render_params=None,
        has_params=False,
    )
