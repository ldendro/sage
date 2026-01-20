"""
Passthrough strategy (v1) - Trivial strategy for testing.

This strategy simply passes through the raw returns without any signal generation.
It sets meta_raw_ret = raw_ret for all assets.

This is useful for:
- Testing the backtesting pipeline
- Baseline comparison (buy-and-hold equivalent)
- Debugging allocator/portfolio logic
"""

import pandas as pd
from typing import Dict


def run_passthrough_v1(
    asset_data: Dict[str, pd.DataFrame],
    params: Dict = None,
) -> Dict[str, pd.DataFrame]:
    """
    Run passthrough strategy on asset data.
    
    This is the simplest possible strategy: it just copies raw_ret to meta_raw_ret
    for each asset, effectively creating a buy-and-hold signal.
    
    Args:
        asset_data: Dictionary mapping symbol to DataFrame with OHLCV + raw_ret
        params: Strategy parameters (unused for passthrough)
    
    Returns:
        Dictionary mapping symbol to DataFrame with added 'meta_raw_ret' column
    
    Example:
        >>> data = load_universe(["SPY", "QQQ"], "2020-01-01", "2020-12-31")
        >>> result = run_passthrough_v1(data)
        >>> spy_df = result["SPY"]
        >>> assert (spy_df['meta_raw_ret'] == spy_df['raw_ret']).all()
    """
    if params is None:
        params = {}
    
    result = {}
    
    for symbol, df in asset_data.items():
        # Create a copy to avoid modifying original
        df_copy = df.copy()
        
        # Simply copy raw_ret to meta_raw_ret
        df_copy['meta_raw_ret'] = df_copy['raw_ret']
        
        result[symbol] = df_copy
    
    return result
