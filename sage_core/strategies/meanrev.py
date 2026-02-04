"""
Multi-indicator mean reversion strategy.

Combines three complementary mean reversion indicators:
1. RSI (Relative Strength Index) - momentum oscillator
2. Bollinger Bands - volatility-based price envelope
3. Z-Score - statistical measure of price deviation

Signals are contrarian: buy oversold, sell overbought.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any
from sage_core.strategies.base import Strategy


class MeanRevStrategy(Strategy):
    """
    Multi-indicator mean reversion strategy.
    
    Combines RSI, Bollinger Bands, and Z-Score for robust mean reversion
    signals. Generates contrarian signals: long when oversold, short when
    overbought.
    
    Parameters:
        rsi_period: Period for RSI calculation (default: 14)
        rsi_oversold: RSI threshold for oversold (default: 30)
        rsi_overbought: RSI threshold for overbought (default: 70)
        bb_period: Period for Bollinger Bands (default: 20)
        bb_std: Standard deviation multiplier for BB (default: 2.0)
        zscore_lookback: Lookback period for Z-Score (default: 60)
        zscore_threshold: Z-Score threshold for extremes (default: 1.5)
        combination_method: How to combine signals (default: "majority")
            - "majority": At least 2 of 3 agree (strong majority, no conflicts)
            - "all": All 3 must agree
            - "weighted": Weighted average (weights configurable)
        weights: Signal weights for weighted method (default: [0.4, 0.3, 0.3])
            - [rsi_weight, bb_weight, zscore_weight]
        weighted_threshold: Threshold for weighted method (default: 0.1)
            - Long if weighted_sum > threshold
            - Short if weighted_sum < -threshold
            - Lower threshold = more aggressive (more trades)
            - Higher threshold = more conservative (fewer trades)
    
    Example:
        >>> # Default (majority voting)
        >>> strategy = MeanRevStrategy()
        >>> 
        >>> # Conservative (all must agree)
        >>> strategy = MeanRevStrategy(params={"combination_method": "all"})
        >>> 
        >>> # Custom thresholds (more sensitive)
        >>> strategy = MeanRevStrategy(params={
        ...     "rsi_oversold": 40,
        ...     "rsi_overbought": 60,
        ...     "zscore_threshold": 1.0
        ... })
    """
    
    # Default parameters
    DEFAULT_PARAMS = {
        # RSI parameters
        "rsi_period": 14,
        "rsi_oversold": 30,
        "rsi_overbought": 70,
        
        # Bollinger Bands parameters
        "bb_period": 20,
        "bb_std": 2.0,
        
        # Z-Score parameters
        "zscore_lookback": 60,
        "zscore_threshold": 1.5,
        
        # Combination method
        "combination_method": "majority",
        "weights": [0.4, 0.3, 0.3],  # [rsi, bb, zscore]
        "weighted_threshold": 0.1,
    }
    
    def __init__(self, params: Dict[str, Any] = None):
        """
        Initialize mean reversion strategy.
        
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
        # Validate RSI parameters
        rsi_period = self.params["rsi_period"]
        if not isinstance(rsi_period, int) or rsi_period < 2:
            raise ValueError(f"rsi_period must be int >= 2, got {rsi_period}")
        if rsi_period > 100:
            raise ValueError(f"rsi_period too large (>100), got {rsi_period}")
        
        rsi_oversold = self.params["rsi_oversold"]
        rsi_overbought = self.params["rsi_overbought"]
        
        if not isinstance(rsi_oversold, (int, float)) or rsi_oversold < 0 or rsi_oversold > 100:
            raise ValueError(f"rsi_oversold must be in [0, 100], got {rsi_oversold}")
        if not isinstance(rsi_overbought, (int, float)) or rsi_overbought < 0 or rsi_overbought > 100:
            raise ValueError(f"rsi_overbought must be in [0, 100], got {rsi_overbought}")
        
        if rsi_oversold >= rsi_overbought:
            raise ValueError(
                f"rsi_oversold ({rsi_oversold}) must be < rsi_overbought ({rsi_overbought})"
            )
        
        # Validate Bollinger Bands parameters
        bb_period = self.params["bb_period"]
        if not isinstance(bb_period, int) or bb_period < 2:
            raise ValueError(f"bb_period must be int >= 2, got {bb_period}")
        if bb_period > 200:
            raise ValueError(f"bb_period too large (>200), got {bb_period}")
        
        bb_std = self.params["bb_std"]
        if not isinstance(bb_std, (int, float)) or bb_std <= 0:
            raise ValueError(f"bb_std must be > 0, got {bb_std}")
        if bb_std > 5:
            raise ValueError(f"bb_std too large (>5), got {bb_std}")
        
        # Validate Z-Score parameters
        zscore_lookback = self.params["zscore_lookback"]
        if not isinstance(zscore_lookback, int) or zscore_lookback < 10:
            raise ValueError(f"zscore_lookback must be int >= 10, got {zscore_lookback}")
        if zscore_lookback > 252:
            raise ValueError(f"zscore_lookback too large (>252), got {zscore_lookback}")
        
        zscore_threshold = self.params["zscore_threshold"]
        if not isinstance(zscore_threshold, (int, float)) or zscore_threshold <= 0:
            raise ValueError(f"zscore_threshold must be > 0, got {zscore_threshold}")
        if zscore_threshold > 5:
            raise ValueError(f"zscore_threshold too large (>5), got {zscore_threshold}")
        
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
            
            # Validate weighted_threshold
            threshold = self.params["weighted_threshold"]
            if not isinstance(threshold, (int, float)):
                raise ValueError(f"weighted_threshold must be a number, got {threshold}")
            if threshold < 0 or threshold > 1:
                raise ValueError(f"weighted_threshold must be in [0, 1], got {threshold}")
    
    def get_warmup_period(self) -> int:
        """
        Return required warmup period.
        
        Warmup = max of all indicator lookbacks to ensure all have valid data.
        
        Returns:
            Warmup period in trading days
        """
        return max(
            self.params["rsi_period"],
            self.params["bb_period"],
            self.params["zscore_lookback"],
        )
    
    def calculate_rsi_signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Calculate RSI signal.
        
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss
        
        Signal: 1 if RSI < oversold (buy the dip)
                -1 if RSI > overbought (sell the rally)
                0 otherwise
        
        Args:
            ohlcv: DataFrame with OHLCV data
        
        Returns:
            Series of RSI signals (-1, 0, 1)
        """
        period = self.params["rsi_period"]
        oversold = self.params["rsi_oversold"]
        overbought = self.params["rsi_overbought"]
        
        # Calculate price changes
        delta = ohlcv['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss using rolling mean
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        # Generate signals (contrarian)
        signals = pd.Series(0, index=ohlcv.index, dtype=int)
        signals[rsi < oversold] = 1    # Oversold → Long
        signals[rsi > overbought] = -1  # Overbought → Short
        
        return signals
    
    def calculate_bb_signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Calculate Bollinger Bands signal.
        
        BB = SMA ± (std_dev × std)
        
        Signal: 1 if close < lower_band (oversold)
                -1 if close > upper_band (overbought)
                0 otherwise
        
        Args:
            ohlcv: DataFrame with OHLCV data
        
        Returns:
            Series of BB signals (-1, 0, 1)
        """
        period = self.params["bb_period"]
        std_dev = self.params["bb_std"]
        
        # Calculate SMA and standard deviation
        sma = ohlcv['close'].rolling(window=period).mean()
        std = ohlcv['close'].rolling(window=period).std()
        
        # Calculate bands
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        # Generate signals (contrarian)
        signals = pd.Series(0, index=ohlcv.index, dtype=int)
        signals[ohlcv['close'] < lower_band] = 1   # Below lower band → Long
        signals[ohlcv['close'] > upper_band] = -1  # Above upper band → Short
        
        return signals
    
    def calculate_zscore_signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        """
        Calculate Z-Score signal.
        
        Z-Score = (close - mean) / std
        
        Signal: 1 if z < -threshold (significantly below mean)
                -1 if z > threshold (significantly above mean)
                0 otherwise
        
        Args:
            ohlcv: DataFrame with OHLCV data
        
        Returns:
            Series of Z-Score signals (-1, 0, 1)
        """
        lookback = self.params["zscore_lookback"]
        threshold = self.params["zscore_threshold"]
        
        # Calculate rolling mean and std
        mean = ohlcv['close'].rolling(window=lookback).mean()
        std = ohlcv['close'].rolling(window=lookback).std()
        
        # Calculate Z-Score (handle division by zero)
        zscore = (ohlcv['close'] - mean) / std.replace(0, np.nan)
        
        # Generate signals (contrarian)
        signals = pd.Series(0, index=ohlcv.index, dtype=int)
        signals[zscore < -threshold] = 1   # Below mean → Long
        signals[zscore > threshold] = -1   # Above mean → Short
        
        return signals
    
    def combine_signals(
        self,
        rsi_sig: pd.Series,
        bb_sig: pd.Series,
        zscore_sig: pd.Series,
    ) -> pd.Series:
        """
        Combine individual signals into final signal.
        
        Args:
            rsi_sig: RSI signals
            bb_sig: Bollinger Bands signals
            zscore_sig: Z-Score signals
        
        Returns:
            Series of combined signals (-1, 0, 1)
        """
        method = self.params["combination_method"]
        
        if method == "all":
            # All must agree
            combined = pd.Series(0, index=rsi_sig.index, dtype=int)
            
            all_long = (rsi_sig == 1) & (bb_sig == 1) & (zscore_sig == 1)
            all_short = (rsi_sig == -1) & (bb_sig == -1) & (zscore_sig == -1)
            
            combined[all_long] = 1
            combined[all_short] = -1
            
        elif method == "majority":
            # Strong majority: at least 2 of 3 agree, no conflicts
            signal_sum = rsi_sig + bb_sig + zscore_sig
            
            combined = pd.Series(0, index=rsi_sig.index, dtype=int)
            combined[signal_sum >= 2] = 1    # At least 2 long, 0 or 1 neutral
            combined[signal_sum <= -2] = -1  # At least 2 short, 0 or 1 neutral
            
        else:  # weighted
            # Weighted average of signals with configurable threshold
            weights = self.params["weights"]
            threshold = self.params["weighted_threshold"]
            
            weighted_sum = (
                weights[0] * rsi_sig +
                weights[1] * bb_sig +
                weights[2] * zscore_sig
            )
            
            combined = pd.Series(0, index=rsi_sig.index, dtype=int)
            combined[weighted_sum > threshold] = 1    # Long if above threshold
            combined[weighted_sum < -threshold] = -1  # Short if below -threshold
        
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
        rsi_sig = self.calculate_rsi_signal(ohlcv)
        bb_sig = self.calculate_bb_signal(ohlcv)
        zscore_sig = self.calculate_zscore_signal(ohlcv)
        
        # Combine signals
        combined_sig = self.combine_signals(rsi_sig, bb_sig, zscore_sig)
        
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
