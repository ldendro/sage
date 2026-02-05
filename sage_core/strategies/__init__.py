"""Strategy module exports."""

from sage_core.strategies.base import Strategy
from sage_core.strategies.passthrough import PassthroughStrategy
from sage_core.strategies.trend import TrendStrategy
from sage_core.strategies.meanrev import MeanRevStrategy

# Strategy registry for dynamic instantiation
STRATEGY_REGISTRY = {
    'passthrough': PassthroughStrategy,
    'trend': TrendStrategy,
    'meanrev': MeanRevStrategy,
}


def get_strategy(name: str, params: dict = None):
    """
    Factory function to instantiate a strategy by name.
    
    Args:
        name: Strategy name (e.g., 'trend', 'meanrev', 'passthrough')
        params: Strategy parameters (default: {})
    
    Returns:
        Strategy instance
    
    Raises:
        ValueError: If strategy name is not recognized
    
    Example:
        >>> strategy = get_strategy('trend', {'lookback': 200})
        >>> strategy = get_strategy('passthrough')
    """
    if params is None:
        params = {}
    
    if name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy: {name}. "
            f"Available strategies: {list(STRATEGY_REGISTRY.keys())}"
        )
    
    strategy_class = STRATEGY_REGISTRY[name]
    return strategy_class(params=params)


__all__ = [
    "Strategy",
    "PassthroughStrategy",
    "TrendStrategy",
    "MeanRevStrategy",
    "STRATEGY_REGISTRY",
    "get_strategy",
]
