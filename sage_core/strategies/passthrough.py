"""
Passthrough strategy - Trivial strategy for testing.

This strategy simply passes through the raw returns without any signal generation.
It sets meta_raw_ret = raw_ret for all assets.

This is useful for:
- Testing the backtesting pipeline
- Baseline comparison (buy-and-hold equivalent)
- Debugging allocator/portfolio logic
"""

import pandas as pd
from sage_core.strategies.base import Strategy


class PassthroughStrategy(Strategy):
    """
    Passthrough strategy that returns raw asset returns.
    
    This is the simplest possible strategy: buy-and-hold with no signals.
    Useful for testing and baseline comparison.
    """
    
    def validate_params(self) -> None:
        """Passthrough has no parameters to validate."""
        pass
    
    def get_warmup_period(self) -> int:
        """
        Passthrough requires no warmup.
        
        Returns:
            0 (no warmup needed)
        """
        return 0
    
    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Generate signals (always 1 = long for passthrough).
        
        Args:
            ohlcv: DataFrame with OHLCV data
        
        Returns:
            Series of 1s (always long)
        """
        return pd.Series(1, index=ohlcv.index)

