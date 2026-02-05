"""Base class for meta allocators.

Meta allocators combine returns from multiple strategies into a single
portfolio return series. They operate at the STRATEGY level, not the asset level.

Example:
    For each asset (SPY, QQQ, etc.):
    - Trend strategy generates: trend_ret[SPY]
    - MeanRev strategy generates: meanrev_ret[SPY]
    - Meta allocator combines: combined_ret[SPY] = 0.6*trend_ret[SPY] + 0.4*meanrev_ret[SPY]
"""

from abc import ABC, abstractmethod
from typing import Dict
import pandas as pd
import numpy as np


class MetaAllocator(ABC):
    """
    Abstract base class for meta allocators.
    
    Meta allocators combine returns from multiple strategies into a single
    portfolio return series with time-varying weights.
    
    Attributes:
        params: Dict of allocator-specific parameters
    """
    
    def __init__(self, params: Dict = None):
        """
        Initialize meta allocator.
        
        Args:
            params: Allocator-specific parameters
        """
        self.params = params or {}
        self.validate_params()
    
    @abstractmethod
    def validate_params(self) -> None:
        """
        Validate allocator parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        pass
    
    @abstractmethod
    def get_warmup_period(self) -> int:
        """
        Return allocator warmup period.
        
        This is the number of days needed for the allocator's own
        indicators (e.g., rolling volatility) to be valid.
        
        Returns:
            Warmup period in trading days
        """
        pass
    
    @abstractmethod
    def calculate_weights(
        self, 
        strategy_returns: Dict[str, pd.Series]
    ) -> pd.DataFrame:
        """
        Calculate time-varying weights for each strategy.
        
        Args:
            strategy_returns: Dict mapping strategy_name -> return series
                             (already aligned to max strategy warmup)
        
        Returns:
            DataFrame with columns = strategy names, values = weights
            Index aligned with strategy returns
            Weights sum to 1.0 at each timestamp
        """
        pass
    
    def allocate(
        self, 
        strategy_returns: Dict[str, pd.Series]
    ) -> Dict:
        """
        Combine strategy returns with calculated weights.
        
        Handles:
        1. Strategy warmup alignment (all strategies start at max warmup)
        2. Weight calculation
        3. Allocator warmup masking (applied AFTER strategy alignment)
        4. Return combination
        
        Note: Strategies already mask their own warmup in Strategy.run().
        The meta allocator ALSO aligns to max warmup for fair comparison.
        
        Args:
            strategy_returns: Dict mapping strategy_name -> return series
                             Each series has its own warmup already masked
        
        Returns:
            Dict with:
                - 'combined_returns': pd.Series (final portfolio returns)
                - 'weights': pd.DataFrame (time-varying weights)
                - 'individual_returns': Dict[str, pd.Series] (aligned returns)
        
        Example:
            >>> # Strategies have different warmups (already masked)
            >>> trend_ret = pd.Series([np.nan]*252 + [0.01]*100, index=dates)  # 252-day warmup
            >>> meanrev_ret = pd.Series([np.nan]*60 + [0.02]*292, index=dates)  # 60-day warmup
            >>> allocator = FixedWeightAllocator({'weights': {'trend': 0.6, 'meanrev': 0.4}})
            >>> result = allocator.allocate({'trend': trend_ret, 'meanrev': meanrev_ret})
            >>> # Both aligned to start at day 252 for fair comparison
        """
        # Step 1: Align all strategies to max warmup (for fair comparison)
        aligned_returns, strategy_warmup_idx = self._align_strategy_warmups(strategy_returns)
        
        # Step 2: Calculate weights
        weights = self.calculate_weights(aligned_returns)
        
        # Step 3: Apply allocator warmup AFTER strategy alignment
        # Total warmup = strategy_warmup_idx + allocator_warmup
        allocator_warmup = self.get_warmup_period()
        weights_masked = weights.copy()
        
        if allocator_warmup > 0:
            # Mask from strategy_warmup_idx to strategy_warmup_idx + allocator_warmup
            total_warmup_idx = strategy_warmup_idx + allocator_warmup
            weights_masked.iloc[:total_warmup_idx] = np.nan
        elif strategy_warmup_idx > 0:
            # No allocator warmup, but still mask strategy warmup
            weights_masked.iloc[:strategy_warmup_idx] = np.nan
        
        # Step 4: Combine returns
        combined = self._combine_returns(aligned_returns, weights_masked)
        
        return {
            'combined_returns': combined,
            'weights': weights_masked,
            'individual_returns': aligned_returns  # Aligned for fair comparison
        }
    
    def _align_strategy_warmups(
        self, 
        strategy_returns: Dict[str, pd.Series]
    ) -> tuple[Dict[str, pd.Series], int]:
        """
        Align all strategies to start at max warmup.
        
        Ensures fair comparison - all strategies start trading on same day.
        Even though strategies mask their own warmup, they may have different
        warmup periods. We align to the max to ensure apples-to-apples comparison.
        
        Args:
            strategy_returns: Dict mapping strategy_name -> return series
                             (each already has its own warmup masked)
        
        Returns:
            Tuple of (aligned_returns, max_warmup_idx)
            - aligned_returns: Dict with aligned returns (NaN before max warmup)
            - max_warmup_idx: Index where aligned strategies start
        
        Example:
            >>> trend = pd.Series([np.nan]*252 + [0.01]*100, index=dates)  # 252-day warmup
            >>> meanrev = pd.Series([np.nan]*60 + [0.02]*292, index=dates)  # 60-day warmup
            >>> aligned, warmup_idx = self._align_strategy_warmups({'trend': trend, 'meanrev': meanrev})
            >>> # Both start at index 252 (max warmup), warmup_idx = 252
            >>> # MeanRev days 60-251 are masked for fair comparison
        """
        # Find max warmup across all strategies
        max_warmup_idx = 0
        for returns in strategy_returns.values():
            first_valid = returns.first_valid_index()
            if first_valid is not None:
                idx = returns.index.get_loc(first_valid)
                max_warmup_idx = max(max_warmup_idx, idx)
        
        # Mask all strategies to max warmup
        aligned = {}
        for name, returns in strategy_returns.items():
            aligned_ret = returns.copy()
            if max_warmup_idx > 0:
                aligned_ret.iloc[:max_warmup_idx] = np.nan
            aligned[name] = aligned_ret
        
        return aligned, max_warmup_idx
    
    def _combine_returns(
        self, 
        strategy_returns: Dict[str, pd.Series],
        weights: pd.DataFrame
    ) -> pd.Series:
        """
        Combine strategy returns using weights.
        
        Args:
            strategy_returns: Dict mapping strategy_name -> return series
            weights: DataFrame with weights (columns = strategy names)
        
        Returns:
            Combined return series (NaN where weights are NaN)
        
        Example:
            >>> returns = {'trend': pd.Series([0.01, 0.02]), 'meanrev': pd.Series([0.02, 0.01])}
            >>> weights = pd.DataFrame({'trend': [0.6, 0.6], 'meanrev': [0.4, 0.4]})
            >>> combined = self._combine_returns(returns, weights)
            >>> # combined[0] = 0.6*0.01 + 0.4*0.02 = 0.014
        """
        # Convert returns dict to DataFrame
        returns_df = pd.DataFrame(strategy_returns)
        
        # Ensure alignment
        returns_df = returns_df.reindex(weights.index)
        
        # Calculate weighted sum
        combined = (returns_df * weights).sum(axis=1)
        
        # If all weights are NaN for a row, combined should be NaN (not 0)
        # This happens during warmup periods
        all_weights_nan = weights.isna().all(axis=1)
        combined[all_weights_nan] = np.nan
        
        return combined
