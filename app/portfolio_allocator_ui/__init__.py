"""Portfolio allocator UI registry and renderers."""

from app.portfolio_allocator_ui.registry import (
    PORTFOLIO_ALLOCATOR_SPECS,
    PortfolioAllocatorSpec,
    get_portfolio_allocator_spec,
)

__all__ = [
    "PORTFOLIO_ALLOCATOR_SPECS",
    "PortfolioAllocatorSpec",
    "get_portfolio_allocator_spec",
]
