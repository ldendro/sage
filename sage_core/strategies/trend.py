"""
Multi-indicator trend-following strategy.

Combines three complementary trend indicators:
1. Momentum (12-month return)
2. Moving Average Crossover (50/200 SMA)
3. Breakout (52-week high/low)

Signals are combined using configurable methods (majority, all, weighted).
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from sage_core.strategies.base import Strategy


class TrendStrategy(Strategy):
    """
    Multi-indicator trend-following strategy.
    
    Combines momentum, MA crossover, and breakout signals for robust
    trend detection. Configurable combination methods allow tuning
    between aggressive and conservative approaches.
    
    Parameters:
        momentum_lookback: Days for momentum calculation (default: 252)
        sma_short: Short SMA period (default: 50)
        sma_long: Long SMA period (default: 200)
        breakout_period: Days for breakout calculation (default: 252)
        combination_method: How to combine signals (default: "majority")
            - "majority": At least 2 of 3 agree
            - "all": All 3 must agree
            - "weighted": Weighted average (weights configurable)
        weights: Signal weights for weighted method (default: [0.4, 0.3, 0.3])
            - [momentum_weight, ma_weight, breakout_weight]
    
    Example:
        >>> # Default (majority voting)
        >>> strategy = TrendStrategy()
        >>> 
        >>> # Conservative (all must agree)
        >>> strategy = TrendStrategy(params={"combination_method": "all"})
        >>> 
        >>> # Custom weights (emphasize momentum)
        >>> strategy = TrendStrategy(params={
        ...     "combination_method": "weighted",
        ...     "weights": [0.6, 0.2, 0.2]
        ... })
    """
    
    # Default parameters
    DEFAULT_PARAMS = {
        "momentum_lookback": 252,
        "sma_short": 50,
        "sma_long": 200,
        "breakout_period": 252,
        "combination_method": "majority",
        "weights": [0.4, 0.3, 0.3],  # [momentum, ma, breakout]
    }
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        Initialize multi-indicator trend strategy.
        
        Args:
            params: Strategy parameters (see class docstring)
        """
        # Merge with defaults
        if params is None:
            params = {}
        
        merged_params = {**self.DEFAULT_PARAMS, **params}
        
        super().__init__(merged_params)
    
    def validate_params(self) -> None:
        """
        Validate strategy parameters.
        
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate momentum_lookback
        momentum = self.params["momentum_lookback"]
        if not isinstance(momentum, int) or momentum < 1:
            raise ValueError(f"momentum_lookback must be int >= 1, got {momentum}")
        if momentum > 504:  # ~2 years
            raise ValueError(f"momentum_lookback too large (>504), got {momentum}")
        
        # Validate SMAs
        sma_short = self.params["sma_short"]
        sma_long = self.params["sma_long"]
        
        if not isinstance(sma_short, int) or sma_short < 1:
            raise ValueError(f"sma_short must be int >= 1, got {sma_short}")
        if not isinstance(sma_long, int) or sma_long < 1:
            raise ValueError(f"sma_long must be int >= 1, got {sma_long}")
        
        if sma_short >= sma_long:
            raise ValueError(
                f"sma_short ({sma_short}) must be < sma_long ({sma_long})"
            )
        
        # Validate breakout_period
        breakout = self.params["breakout_period"]
        if not isinstance(breakout, int) or breakout < 1:
            raise ValueError(f"breakout_period must be int >= 1, got {breakout}")
        if breakout > 504:
            raise ValueError(f"breakout_period too large (>504), got {breakout}")
        
        # Validate combination_method
        method = self.params["combination_method"]
        valid_methods = ["majority", "all", "weighted"]
        if method not in valid_methods:
            raise ValueError(
                f"combination_method must be one of {valid_methods}, got {method}"
            )
        
        # Validate weights (if using weighted method)
        if method == "weighted":
            weights = self.params["weights"]
            if not isinstance(weights, (list, tuple)) or len(weights) != 3:
                raise ValueError(f"weights must be list/tuple of length 3, got {weights}")
            
            if not all(isinstance(w, (int, float)) and w >= 0 for w in weights):
                raise ValueError(f"weights must be non-negative numbers, got {weights}")
            
            if abs(sum(weights) - 1.0) > 1e-6:
                raise ValueError(f"weights must sum to 1.0, got sum={sum(weights)}")
    
    def get_warmup_period(self) -> int:
        """
        Return required warmup period.
        
        Warmup = max of all indicator lookbacks to ensure all have valid data.
        
        Returns:
            Warmup period in trading days
        """
        return max(
            self.params["momentum_lookback"],
            self.params["sma_long"],  # Long SMA is the longest MA
            self.params["breakout_period"],
        )
    
    def calculate_momentum_signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Calculate momentum signal.
        
        Signal: 1 if momentum > 0, -1 if momentum < 0, 0 otherwise
        
        Args:
            ohlcv: DataFrame with OHLCV data
        
        Returns:
            Series of momentum signals (-1, 0, 1)
        """
        lookback = self.params["momentum_lookback"]
        
        # Calculate momentum (% change over lookback period)
        momentum = ohlcv['close'].pct_change(periods=lookback)
        
        # Generate signals
        signals = pd.Series(0, index=ohlcv.index, dtype=int)
        signals[momentum > 0] = 1
        signals[momentum < 0] = -1
        
        return signals
    
    def calculate_ma_crossover_signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Calculate moving average crossover signal.
        
        Signal: 1 if short SMA > long SMA (bullish), -1 if short < long (bearish)
        
        Args:
            ohlcv: DataFrame with OHLCV data
        
        Returns:
            Series of MA crossover signals (-1, 0, 1)
        """
        sma_short = self.params["sma_short"]
        sma_long = self.params["sma_long"]
        
        # Calculate SMAs
        short_ma = ohlcv['close'].rolling(window=sma_short).mean()
        long_ma = ohlcv['close'].rolling(window=sma_long).mean()
        
        # Generate signals
        signals = pd.Series(0, index=ohlcv.index, dtype=int)
        signals[short_ma > long_ma] = 1   # Bullish
        signals[short_ma < long_ma] = -1  # Bearish
        
        return signals
    
    def calculate_breakout_signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Calculate breakout signal.
        
        Signal: 1 if at 52-week high, -1 if at 52-week low, 0 otherwise
        
        Args:
            ohlcv: DataFrame with OHLCV data
        
        Returns:
            Series of breakout signals (-1, 0, 1)
        """
        period = self.params["breakout_period"]
        
        # Calculate rolling high/low
        rolling_high = ohlcv['close'].rolling(window=period).max()
        rolling_low = ohlcv['close'].rolling(window=period).min()
        
        # Generate signals
        signals = pd.Series(0, index=ohlcv.index, dtype=int)
        
        # At or near high (within 1%)
        at_high = ohlcv['close'] >= rolling_high * 0.99
        signals[at_high] = 1
        
        # At or near low (within 1%)
        at_low = ohlcv['close'] <= rolling_low * 1.01
        signals[at_low] = -1
        
        return signals
    
    def combine_signals(
        self,
        momentum_sig: pd.Series,
        ma_sig: pd.Series,
        breakout_sig: pd.Series,
    ) -> pd.Series:
        """
        Combine individual signals into final signal.
        
        Args:
            momentum_sig: Momentum signals
            ma_sig: MA crossover signals
            breakout_sig: Breakout signals
        
        Returns:
            Series of combined signals (-1, 0, 1)
        """
        method = self.params["combination_method"]
        
        if method == "all":
            # All must agree
            # Long: all 3 are 1
            # Short: all 3 are -1
            # Neutral: otherwise
            combined = pd.Series(0, index=momentum_sig.index, dtype=int)
            
            all_long = (momentum_sig == 1) & (ma_sig == 1) & (breakout_sig == 1)
            all_short = (momentum_sig == -1) & (ma_sig == -1) & (breakout_sig == -1)
            
            combined[all_long] = 1
            combined[all_short] = -1
            
        elif method == "majority":
            # At least 2 of 3 must agree
            signal_sum = momentum_sig + ma_sig + breakout_sig
            
            combined = pd.Series(0, index=momentum_sig.index, dtype=int)
            combined[signal_sum >= 2] = 1    # At least 2 long signals
            combined[signal_sum <= -2] = -1  # At least 2 short signals
            
        else:  # weighted
            # Weighted average of signals
            weights = self.params["weights"]
            
            weighted_sum = (
                weights[0] * momentum_sig +
                weights[1] * ma_sig +
                weights[2] * breakout_sig
            )
            
            combined = pd.Series(0, index=momentum_sig.index, dtype=int)
            combined[weighted_sum > 0.1] = 1    # Threshold for long
            combined[weighted_sum < -0.1] = -1  # Threshold for short
        
        return combined
    
    def generate_signals(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Generate trading signals from multiple indicators.
        
        Args:
            ohlcv: DataFrame with OHLCV data
        
        Returns:
            Series of combined signals (1=long, 0=neutral, -1=short)
        """
        # Calculate individual signals
        momentum_sig = self.calculate_momentum_signal(ohlcv)
        ma_sig = self.calculate_ma_crossover_signal(ohlcv)
        breakout_sig = self.calculate_breakout_signal(ohlcv)
        
        # Combine signals
        combined_sig = self.combine_signals(momentum_sig, ma_sig, breakout_sig)
        
        return combined_sig
    
    def calculate_returns(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Calculate strategy returns.
        
        Strategy return = signal[t-1] × raw_ret[t]
        (Use previous day's signal for today's return)
        
        Args:
            ohlcv: DataFrame with OHLCV + raw_ret
        
        Returns:
            Series of strategy returns (meta_raw_ret)
        """
        signals = self.generate_signals(ohlcv)
        
        # Shift signals by 1 day (use yesterday's signal for today's return)
        # This avoids look-ahead bias
        lagged_signals = signals.shift(1)
        
        # Strategy return = signal × raw_ret
        meta_raw_ret = lagged_signals * ohlcv['raw_ret']
        
        return meta_raw_ret
