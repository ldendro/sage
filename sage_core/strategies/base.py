"""
Abstract base class for trading strategies.

All strategies must implement:
- Parameter validation
- Warmup period calculation
- Signal generation from OHLCV data
- Return calculation (meta_raw_ret)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd


class Strategy(ABC):
    """
    Abstract base class for trading strategies.
    
    All strategies must implement:
    - Parameter validation
    - Warmup period calculation
    - Signal generation from OHLCV data
    - Return calculation (meta_raw_ret)
    
    The base class provides a template method (run()) that orchestrates
    the strategy execution flow consistently across all strategies.
    """
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        Initialize strategy with parameters.
        
        Args:
            params: Strategy-specific parameters
        """
        self.params = params if params is not None else {}
        self.validate_params()
    
    @abstractmethod
    def validate_params(self) -> None:
        """
        Validate strategy parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        pass
    
    @abstractmethod
    def get_warmup_period(self) -> int:
        """
        Return required warmup period in trading days.
        
        This is the minimum number of days of historical data needed
        before the strategy can generate valid returns. If
        calculate_returns uses a signal lag (e.g., shift(1)), include
        that lag in the warmup period.
        
        Returns:
            Warmup period in trading days
            
        Example:
            >>> strategy = TrendStrategy(params={"momentum_lookback": 252})
            >>> strategy.get_warmup_period()
            252
        """
        pass
    
    @abstractmethod
    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals from OHLCV data.
        
        Args:
            ohlcv: DataFrame with OHLCV data (date index)
        
        Returns:
            Series of signals (1=long, 0=neutral, -1=short)
            
        Example:
            >>> signals = strategy.generate_signals(ohlcv_df)
            >>> assert signals.isin([1, 0, -1]).all()
        """
        pass
    
    @abstractmethod
    def calculate_returns(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Calculate strategy returns (meta_raw_ret).
        
        This is the core strategy logic that transforms raw returns
        into strategy returns based on signals.
        
        Args:
            ohlcv: DataFrame with OHLCV + raw_ret columns
        
        Returns:
            Series of strategy returns (meta_raw_ret)
            
        Example:
            >>> meta_returns = strategy.calculate_returns(ohlcv_df)
            >>> assert 'raw_ret' in ohlcv_df.columns
            >>> assert len(meta_returns) == len(ohlcv_df)
        """
        pass
    
    def run(self, asset_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Run strategy on asset data (template method).
        
        This is the main entry point that orchestrates the strategy logic.
        It applies the strategy to each asset in the universe and masks
        the warmup period with NaN.
        
        Args:
            asset_data: Dict mapping symbol to DataFrame with OHLCV + raw_ret
        
        Returns:
            Dict mapping symbol to DataFrame with added 'meta_raw_ret' column.
            The first `get_warmup_period()` rows of 'meta_raw_ret' are NaN.
            
        Example:
            >>> data = load_universe(["SPY", "QQQ"], "2020-01-01", "2020-12-31")
            >>> strategy = TrendStrategy(params={"momentum_lookback": 252})
            >>> result = strategy.run(data)
            >>> assert "meta_raw_ret" in result["SPY"].columns
            >>> # First 252 rows are NaN (warmup)
            >>> assert result["SPY"]["meta_raw_ret"].iloc[:252].isna().all()
        """
        result = {}
        warmup = self.get_warmup_period()
        
        for symbol, df in asset_data.items():
            df_copy = df.copy()
            
            # Calculate strategy returns
            raw_returns = self.calculate_returns(df_copy)
            
            # Mask warmup period with NaN
            if warmup > 0:
                raw_returns.iloc[:warmup] = pd.NA
            
            df_copy['meta_raw_ret'] = raw_returns
            result[symbol] = df_copy
        
        return result
