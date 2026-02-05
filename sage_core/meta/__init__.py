"""Meta allocators for combining strategy returns.

This module provides allocators that operate at the STRATEGY level,
combining returns from multiple strategies (e.g., Trend + MeanRev).

This is distinct from asset allocators in sage_core/allocators/ which
operate at the ASSET level (e.g., SPY vs QQQ vs TLT).
"""

from sage_core.meta.base import MetaAllocator
from sage_core.meta.fixed_weight import FixedWeightAllocator
from sage_core.meta.risk_parity import RiskParityAllocator

__all__ = [
    "MetaAllocator",
    "FixedWeightAllocator",
    "RiskParityAllocator",
]
