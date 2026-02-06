"""Registry for meta allocator UI renderers (app-side only)."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from app.meta_allocator_ui.fixed_weight import render_params as render_fixed_weight_params
from app.meta_allocator_ui.risk_parity import render_params as render_risk_parity_params

RenderParams = Callable[[str, List[str]], Dict[str, Any]]


@dataclass(frozen=True)
class MetaAllocatorSpec:
    name: str
    display_name: str
    description: str
    render_params: Optional[RenderParams]
    has_params: bool = True


META_ALLOCATOR_SPECS: Dict[str, MetaAllocatorSpec] = {
    "fixed_weight": MetaAllocatorSpec(
        name="fixed_weight",
        display_name="Fixed Weight",
        description="Allocate fixed weights to each strategy",
        render_params=render_fixed_weight_params,
        has_params=True,
    ),
    "risk_parity": MetaAllocatorSpec(
        name="risk_parity",
        display_name="Risk Parity",
        description="Allocate based on inverse volatility of strategy returns",
        render_params=render_risk_parity_params,
        has_params=True,
    ),
}


def _fallback_display_name(name: str) -> str:
    return name.replace("_", " ").title()


def get_meta_allocator_spec(name: str) -> MetaAllocatorSpec:
    """Return meta allocator spec for UI rendering, with a safe fallback."""
    if name in META_ALLOCATOR_SPECS:
        return META_ALLOCATOR_SPECS[name]

    return MetaAllocatorSpec(
        name=name,
        display_name=_fallback_display_name(name),
        description="",
        render_params=None,
        has_params=False,
    )
