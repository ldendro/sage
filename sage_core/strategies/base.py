"""
Abstract base class for trading strategies.

All strategies must implement:
- Parameter validation
- Warmup period calculation
- Signal generation from OHLCV data (raw intent, unshifted)

Strategies return INTENT only — never positions or returns.
The ExecutionModule is the only component that converts intent into
positions and returns. This is a design invariant, not a runtime check.

Terminology:
    Intent: per-asset target exposure (discrete or continuous scores)
    Target weights: desired portfolio weights after exposure mapping
    Held weights: actual portfolio weights after execution delay
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import pandas as pd


class Strategy(ABC):
    """Abstract base class for trading strategies.

    All strategies must implement:
    - Parameter validation
    - Warmup period calculation
    - Signal generation from OHLCV data

    Strategies output raw intent (signals/scores) at decision time t
    using data <= t. They do NOT apply any timing lag — the engine's
    ExecutionModule handles that.

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

    @property
    def signal_type(self) -> str:
        """Return the type of signal this strategy produces.

        Returns:
            'discrete' for rule-based strategies ({-1, 0, 1})
            'continuous' for ML-based strategies (probabilities/scores)

        Subclasses may override this for continuous-output strategies
        (e.g., ModelWrapperStrategy in Week 9).
        """
        return "discrete"

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
        before the strategy can generate valid signals. Do NOT include
        execution delay — the engine accounts for that separately.

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
        Generate trading signals (intent) from OHLCV data.

        Signals represent intent at decision time t using data <= t.
        No timing lag is applied — the ExecutionModule handles that.

        Args:
            ohlcv: DataFrame with OHLCV data (date index)

        Returns:
            Series of signals. For discrete strategies: {-1, 0, 1}.
            For continuous strategies: numeric scores.

        Example:
            >>> signals = strategy.generate_signals(ohlcv_df)
            >>> assert signals.isin([1, 0, -1]).all()  # discrete
        """
        pass

    def run(self, asset_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Run strategy on asset data (template method).

        Generates signals for each asset and stores them in the DataFrame.
        The warmup period is masked with NaN.

        NOTE: This method does NOT compute returns (meta_raw_ret).
        The ExecutionModule handles timing and return computation.

        Args:
            asset_data: Dict mapping symbol to DataFrame with OHLCV + raw_ret

        Returns:
            Dict mapping symbol to DataFrame with added 'signal' column.
            The first ``get_warmup_period()`` rows of 'signal' are NaN.

        Example:
            >>> data = load_universe(["SPY", "QQQ"], "2020-01-01", "2020-12-31")
            >>> strategy = TrendStrategy(params={"momentum_lookback": 252})
            >>> result = strategy.run(data)
            >>> assert "signal" in result["SPY"].columns
        """
        result = {}
        warmup = self.get_warmup_period()

        for symbol, df in asset_data.items():
            df_copy = df.copy()

            # Generate signals (raw intent at time t)
            signals = self.generate_signals(df_copy)

            # Mask warmup period with NaN
            if warmup > 0:
                signals.iloc[:warmup] = pd.NA

            df_copy['signal'] = signals
            result[symbol] = df_copy

        return result
