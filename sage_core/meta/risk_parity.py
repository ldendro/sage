"""Risk parity meta allocator (inverse volatility weighting)."""

from typing import Dict
import pandas as pd
import numpy as np
from sage_core.meta.base import MetaAllocator


class RiskParityAllocator(MetaAllocator):
    """
    Risk parity meta allocator using inverse volatility weighting.
    
    Allocates more to lower-volatility strategies, less to higher-volatility.
    Rebalances daily based on rolling volatility.
    
    Parameters:
        vol_lookback: Lookback period for volatility calculation (default: 60)
        min_weight: Minimum weight for any strategy (default: 0.0)
        max_weight: Maximum weight for any strategy (default: 1.0)
    
    Example:
        >>> allocator = RiskParityAllocator(params={
        ...     'vol_lookback': 60
        ... })
        >>> result = allocator.allocate(strategy_returns)
        >>> # Weights inversely proportional to volatility
    """
    
    DEFAULT_PARAMS = {
        'vol_lookback': 60,
        'min_weight': 0.0,
        'max_weight': 1.0,
    }
    
    def __init__(self, params: Dict = None):
        """Initialize risk parity allocator."""
        if params is None:
            params = {}
        
        # Merge with defaults
        merged_params = {**self.DEFAULT_PARAMS, **params}
        
        super().__init__(merged_params)
    
    def validate_params(self) -> None:
        """
        Validate allocator parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        vol_lookback = self.params['vol_lookback']
        if not isinstance(vol_lookback, int) or vol_lookback < 10:
            raise ValueError(f"vol_lookback must be int >= 10, got {vol_lookback}")
        if vol_lookback > 252:
            raise ValueError(f"vol_lookback too large (>252), got {vol_lookback}")
        
        min_weight = self.params['min_weight']
        max_weight = self.params['max_weight']
        
        if not isinstance(min_weight, (int, float)) or min_weight < 0:
            raise ValueError(f"min_weight must be >= 0, got {min_weight}")
        if not isinstance(max_weight, (int, float)) or max_weight > 1:
            raise ValueError(f"max_weight must be <= 1, got {max_weight}")
        if min_weight >= max_weight:
            raise ValueError(f"min_weight ({min_weight}) must be < max_weight ({max_weight})")
    
    def get_warmup_period(self) -> int:
        """
        Return allocator warmup period.
        
        Warmup = volatility lookback period.
        
        Returns:
            Volatility lookback period
        """
        return self.params['vol_lookback']
    
    def calculate_weights(
        self, 
        strategy_returns: Dict[str, pd.Series]
    ) -> pd.DataFrame:
        """
        Calculate inverse volatility weights.
        
        Weight_i = (1 / Vol_i) / sum(1 / Vol_j)
        
        Args:
            strategy_returns: Dict mapping strategy_name -> return series
        
        Returns:
            DataFrame with time-varying weights
        """
        vol_lookback = self.params['vol_lookback']
        
        # Calculate rolling volatility for each strategy
        vols = {}
        for name, returns in strategy_returns.items():
            vols[name] = returns.rolling(window=vol_lookback).std()
        
        vols_df = pd.DataFrame(vols)
        
        # Calculate inverse volatility
        inv_vols = 1.0 / vols_df
        
        # Handle zero/inf volatility
        inv_vols = inv_vols.replace([np.inf, -np.inf], np.nan)
        
        # Calculate weights (normalize to sum to 1)
        weights = inv_vols.div(inv_vols.sum(axis=1), axis=0)
        
        # Handle rows where all strategies have zero/NaN volatility
        # Set to equal weight in such cases
        all_nan_mask = weights.isna().all(axis=1)
        if all_nan_mask.any():
            n_strategies = len(strategy_returns)
            equal_weight = 1.0 / n_strategies
            weights.loc[all_nan_mask] = equal_weight
        
        # Fill any remaining NaN with 0 (redistribute to other strategies)
        weights = weights.fillna(0)
        
        # Renormalize to ensure sum = 1
        row_sums = weights.sum(axis=1)
        row_sums = row_sums.replace(0, 1)  # Avoid division by zero
        weights = weights.div(row_sums, axis=0)
        
        # Apply min/max constraints
        min_weight = self.params['min_weight']
        max_weight = self.params['max_weight']
        weights = weights.clip(lower=min_weight, upper=max_weight)
        
        # Renormalize after clipping (soft caps)
        row_sums = weights.sum(axis=1)
        row_sums = row_sums.replace(0, 1)  # Avoid division by zero
        weights = weights.div(row_sums, axis=0)
        
        # NOTE: No shift applied here. Per the design contract, the meta
        # allocator computes at time t using data <= t. The engine's
        # ExecutionModule applies the single execution delay.
        
        return weights
