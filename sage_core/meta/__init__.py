"""Meta allocators for combining strategy returns.

This module provides allocators that operate at the STRATEGY level,
combining returns from multiple strategies (e.g., Trend + MeanRev).

This is distinct from asset allocators in sage_core/allocators/ which
operate at the ASSET level (e.g., SPY vs QQQ vs TLT).
"""

from sage_core.meta.base import MetaAllocator
from sage_core.meta.fixed_weight import FixedWeightAllocator
from sage_core.meta.risk_parity import RiskParityAllocator

# Meta allocator registry for dynamic instantiation
META_ALLOCATOR_REGISTRY = {
    'fixed_weight': FixedWeightAllocator,
    'risk_parity': RiskParityAllocator,
}


def get_meta_allocator(allocator_type: str, params: dict = None):
    """
    Factory function to instantiate a meta allocator by type.
    
    Args:
        allocator_type: Allocator type (e.g., 'fixed_weight', 'risk_parity')
        params: Allocator parameters (default: {})
    
    Returns:
        MetaAllocator instance
    
    Raises:
        ValueError: If allocator type is not recognized
    
    Example:
        >>> allocator = get_meta_allocator('risk_parity', {'vol_lookback': 60})
        >>> allocator = get_meta_allocator('fixed_weight', {'weights': {'trend': 0.6, 'meanrev': 0.4}})
    """
    if params is None:
        params = {}
    
    if allocator_type not in META_ALLOCATOR_REGISTRY:
        raise ValueError(
            f"Unknown meta allocator type: {allocator_type}. "
            f"Available types: {list(META_ALLOCATOR_REGISTRY.keys())}"
        )
    
    allocator_class = META_ALLOCATOR_REGISTRY[allocator_type]
    return allocator_class(params=params)


__all__ = [
    "MetaAllocator",
    "FixedWeightAllocator",
    "RiskParityAllocator",
    "META_ALLOCATOR_REGISTRY",
    "get_meta_allocator",
]
