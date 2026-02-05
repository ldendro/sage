"""Fixed weight meta allocator for combining strategy returns."""

from typing import Dict
import pandas as pd
from sage_core.meta.base import MetaAllocator


class FixedWeightAllocator(MetaAllocator):
    """
    Fixed weight meta allocator with user-specified static weights.
    
    Combines strategy returns using constant weights that don't change over time.
    
    Parameters:
        weights: Dict mapping strategy_name -> weight
            - Must sum to 1.0
            - All weights must be >= 0 (long-only)
    
    Example:
        >>> allocator = FixedWeightAllocator(params={
        ...     'weights': {'trend': 0.6, 'meanrev': 0.4}
        ... })
        >>> result = allocator.allocate(strategy_returns)
        >>> # Combined returns = 60% trend + 40% meanrev
    """
    
    def validate_params(self) -> None:
        """
        Validate allocator parameters.
        
        Raises:
            ValueError: If weights are invalid
        """
        if 'weights' not in self.params:
            raise ValueError("FixedWeightAllocator requires 'weights' parameter")
        
        weights = self.params['weights']
        
        if not isinstance(weights, dict):
            raise ValueError("weights must be a dict")
        
        if len(weights) == 0:
            raise ValueError("weights dict cannot be empty")
        
        # Check all weights are non-negative
        for name, weight in weights.items():
            if not isinstance(weight, (int, float)):
                raise ValueError(f"weight for '{name}' must be a number, got {type(weight)}")
            if weight < 0:
                raise ValueError(f"weight for '{name}' must be >= 0, got {weight}")
        
        # Check weights sum to 1.0
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total}")
    
    def get_warmup_period(self) -> int:
        """
        Return allocator warmup period.
        
        Fixed weights have no warmup (weights are constant).
        
        Returns:
            0 (no warmup)
        """
        return 0
    
    def calculate_weights(
        self, 
        strategy_returns: Dict[str, pd.Series]
    ) -> pd.DataFrame:
        """
        Calculate time-varying weights (constant in this case).
        
        Args:
            strategy_returns: Dict mapping strategy_name -> return series
        
        Returns:
            DataFrame with constant weights
        
        Raises:
            ValueError: If a strategy is missing from configured weights
        """
        # Get index from any strategy (all should be aligned)
        index = next(iter(strategy_returns.values())).index
        
        # Get configured weights
        config_weights = self.params['weights']
        
        # Verify all strategies have weights
        for name in strategy_returns.keys():
            if name not in config_weights:
                raise ValueError(f"No weight specified for strategy '{name}'")
        
        # Verify no extra weights
        for name in config_weights.keys():
            if name not in strategy_returns:
                raise ValueError(f"Weight specified for unknown strategy '{name}'")
        
        # Create constant weight DataFrame
        weights_dict = {}
        for name in strategy_returns.keys():
            weights_dict[name] = [config_weights[name]] * len(index)
        
        weights_df = pd.DataFrame(weights_dict, index=index)
        
        return weights_df
