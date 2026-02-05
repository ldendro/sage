"""Tests for TrendStrategy (multi-indicator trend-following)."""

import pytest
import pandas as pd
import numpy as np

from sage_core.strategies.trend import TrendStrategy
from sage_core.data.loader import load_universe


class TestTrendStrategyInitialization:
    """Tests for TrendStrategy initialization and validation."""
    
    def test_trend_initialization_defaults(self):
        """Test TrendStrategy initialization with default parameters."""
        strategy = TrendStrategy()
        
        assert strategy.params["momentum_lookback"] == 252
        assert strategy.params["sma_short"] == 50
        assert strategy.params["sma_long"] == 200
        assert strategy.params["breakout_period"] == 252
        assert strategy.params["combination_method"] == "majority"
        assert strategy.params["weights"] == [0.4, 0.3, 0.3]
    
    def test_trend_custom_params(self):
        """Test TrendStrategy with custom parameters."""
        params = {
            "momentum_lookback": 126,
            "sma_short": 20,
            "sma_long": 100,
            "breakout_period": 126,
            "combination_method": "all",
        }
        strategy = TrendStrategy(params=params)
        
        assert strategy.params["momentum_lookback"] == 126
        assert strategy.params["sma_short"] == 20
        assert strategy.params["sma_long"] == 100
        assert strategy.params["combination_method"] == "all"
    
    def test_trend_param_validation_momentum(self):
        """Test parameter validation for momentum_lookback."""
        # Invalid type
        with pytest.raises(ValueError, match="momentum_lookback must be int"):
            TrendStrategy(params={"momentum_lookback": 252.5})
        
        # Too small
        with pytest.raises(ValueError, match="momentum_lookback must be int >= 1"):
            TrendStrategy(params={"momentum_lookback": 0})
        
        # Too large
        with pytest.raises(ValueError, match="momentum_lookback too large"):
            TrendStrategy(params={"momentum_lookback": 600})
    
    def test_trend_param_validation_sma(self):
        """Test parameter validation for SMA parameters."""
        # sma_short >= sma_long
        with pytest.raises(ValueError, match="sma_short .* must be < sma_long"):
            TrendStrategy(params={"sma_short": 200, "sma_long": 50})
        
        # sma_short == sma_long
        with pytest.raises(ValueError, match="sma_short .* must be < sma_long"):
            TrendStrategy(params={"sma_short": 100, "sma_long": 100})
        
        # Invalid type
        with pytest.raises(ValueError, match="sma_short must be int"):
            TrendStrategy(params={"sma_short": 50.5})
    
    def test_trend_param_validation_breakout(self):
        """Test parameter validation for breakout_period."""
        # Too small
        with pytest.raises(ValueError, match="breakout_period must be int >= 1"):
            TrendStrategy(params={"breakout_period": 0})
        
        # Too large
        with pytest.raises(ValueError, match="breakout_period too large"):
            TrendStrategy(params={"breakout_period": 600})
    
    def test_trend_param_validation_combination_method(self):
        """Test parameter validation for combination_method."""
        # Invalid method
        with pytest.raises(ValueError, match="combination_method must be one of"):
            TrendStrategy(params={"combination_method": "invalid"})
    
    def test_trend_param_validation_weights(self):
        """Test parameter validation for weights (weighted method)."""
        # Wrong length
        with pytest.raises(ValueError, match="weights must be list/tuple of length 3"):
            TrendStrategy(params={
                "combination_method": "weighted",
                "weights": [0.5, 0.5]
            })
        
        # Negative weights
        with pytest.raises(ValueError, match="weights must be non-negative"):
            TrendStrategy(params={
                "combination_method": "weighted",
                "weights": [0.5, 0.5, -0.1]
            })
        
        # Don't sum to 1.0
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            TrendStrategy(params={
                "combination_method": "weighted",
                "weights": [0.5, 0.3, 0.3]
            })
    
    def test_trend_param_validation_weighted_threshold(self):
        """Test parameter validation for weighted_threshold."""
        # Invalid type
        with pytest.raises(ValueError, match="weighted_threshold must be a number"):
            TrendStrategy(params={
                "combination_method": "weighted",
                "weighted_threshold": "invalid"
            })
        
        # Too small
        with pytest.raises(ValueError, match="weighted_threshold must be in"):
            TrendStrategy(params={
                "combination_method": "weighted",
                "weighted_threshold": -0.1
            })
        
        # Too large
        with pytest.raises(ValueError, match="weighted_threshold must be in"):
            TrendStrategy(params={
                "combination_method": "weighted",
                "weighted_threshold": 1.5
            })
        
        # Valid values should work
        strategy = TrendStrategy(params={
            "combination_method": "weighted",
            "weighted_threshold": 0.05
        })
        assert strategy.params["weighted_threshold"] == 0.05


class TestTrendStrategyWarmup:
    """Tests for warmup period calculation."""
    
    def test_trend_warmup_period_max_of_lookbacks(self):
        """Test that warmup period is max of all indicator lookbacks."""
        # Default params: max(252+1, 200, 252) = 253
        strategy = TrendStrategy()
        assert strategy.get_warmup_period() == 253
        
        # Custom params where sma_long is longest
        strategy = TrendStrategy(params={
            "momentum_lookback": 126,
            "sma_long": 300,
            "breakout_period": 126,
        })
        assert strategy.get_warmup_period() == 300
        
        # Custom params where breakout is longest
        strategy = TrendStrategy(params={
            "momentum_lookback": 126,
            "sma_long": 200,
            "breakout_period": 400,
        })
        assert strategy.get_warmup_period() == 400


class TestTrendStrategyIndicators:
    """Tests for individual indicator calculations."""
    
    def test_momentum_signal_positive(self):
        """Test momentum signal when momentum is positive."""
        dates = pd.date_range('2020-01-01', periods=300)
        # Uptrend: prices increasing
        ohlcv = pd.DataFrame({
            'close': np.linspace(100, 150, 300),  # +50% over period
        }, index=dates)
        
        strategy = TrendStrategy(params={"momentum_lookback": 252})
        signals = strategy.calculate_momentum_signal(ohlcv)
        
        # After warmup, should be long (1)
        assert signals.iloc[-1] == 1
    
    def test_momentum_signal_negative(self):
        """Test momentum signal when momentum is negative."""
        dates = pd.date_range('2020-01-01', periods=300)
        # Downtrend: prices decreasing
        ohlcv = pd.DataFrame({
            'close': np.linspace(150, 100, 300),  # -33% over period
        }, index=dates)
        
        strategy = TrendStrategy(params={"momentum_lookback": 252})
        signals = strategy.calculate_momentum_signal(ohlcv)
        
        # After warmup, should be short (-1)
        assert signals.iloc[-1] == -1
    
    def test_ma_crossover_signal_bullish(self):
        """Test MA crossover signal when bullish (short > long)."""
        dates = pd.date_range('2020-01-01', periods=250)
        # Create uptrend where short MA > long MA
        ohlcv = pd.DataFrame({
            'close': np.linspace(100, 150, 250),
        }, index=dates)
        
        strategy = TrendStrategy(params={"sma_short": 50, "sma_long": 200})
        signals = strategy.calculate_ma_crossover_signal(ohlcv)
        
        # After warmup, should be bullish (1)
        assert signals.iloc[-1] == 1
    
    def test_ma_crossover_signal_bearish(self):
        """Test MA crossover signal when bearish (short < long)."""
        dates = pd.date_range('2020-01-01', periods=250)
        # Create downtrend where short MA < long MA
        ohlcv = pd.DataFrame({
            'close': np.linspace(150, 100, 250),
        }, index=dates)
        
        strategy = TrendStrategy(params={"sma_short": 50, "sma_long": 200})
        signals = strategy.calculate_ma_crossover_signal(ohlcv)
        
        # After warmup, should be bearish (-1)
        assert signals.iloc[-1] == -1
    
    def test_breakout_signal_at_high(self):
        """Test breakout signal when at 52-week high."""
        dates = pd.date_range('2020-01-01', periods=300)
        # Prices rising to new high
        prices = np.linspace(100, 150, 300)
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = TrendStrategy(params={"breakout_period": 252})
        signals = strategy.calculate_breakout_signal(ohlcv)
        
        # Last price is at high, should be 1
        assert signals.iloc[-1] == 1
    
    def test_breakout_signal_at_low(self):
        """Test breakout signal when at 52-week low."""
        dates = pd.date_range('2020-01-01', periods=300)
        # Prices falling to new low
        prices = np.linspace(150, 100, 300)
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = TrendStrategy(params={"breakout_period": 252})
        signals = strategy.calculate_breakout_signal(ohlcv)
        
        # Last price is at low, should be -1
        assert signals.iloc[-1] == -1


class TestTrendStrategyCombination:
    """Tests for signal combination methods."""
    
    def test_combine_signals_all_method(self):
        """Test 'all' combination method (all must agree)."""
        dates = pd.date_range('2020-01-01', periods=10)
        
        # All long
        mom_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        ma_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        breakout_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        
        strategy = TrendStrategy(params={"combination_method": "all"})
        combined = strategy.combine_signals(mom_sig, ma_sig, breakout_sig)
        
        assert (combined == 1).all()
        
        # Mixed signals (2 long, 1 short) → neutral
        mom_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        ma_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        breakout_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        
        combined = strategy.combine_signals(mom_sig, ma_sig, breakout_sig)
        assert (combined == 0).all()
    
    def test_combine_signals_majority_method(self):
        """Test 'majority' combination method (at least 2 of 3)."""
        dates = pd.date_range('2020-01-01', periods=10)
        
        # All 3 long → long (sum = 3)
        mom_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        ma_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        breakout_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        
        strategy = TrendStrategy(params={"combination_method": "majority"})
        combined = strategy.combine_signals(mom_sig, ma_sig, breakout_sig)
        
        assert (combined == 1).all()
        
        # 2 long, 1 neutral → long (sum = 2)
        mom_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        ma_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        breakout_sig = pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 0, 0], index=dates)
        
        combined = strategy.combine_signals(mom_sig, ma_sig, breakout_sig)
        assert (combined == 1).all()
        
        # 2 long, 1 short → neutral (sum = 1, not >= 2)
        mom_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        ma_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        breakout_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        
        combined = strategy.combine_signals(mom_sig, ma_sig, breakout_sig)
        assert (combined == 0).all()  # Conflicting signals → neutral
        
        # 2 short, 1 long → short (sum = -1, not <= -2)
        mom_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        ma_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        breakout_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        
        combined = strategy.combine_signals(mom_sig, ma_sig, breakout_sig)
        assert (combined == 0).all()  # Conflicting signals → neutral
        
        # All 3 short → short (sum = -3)
        mom_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        ma_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        breakout_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        
        combined = strategy.combine_signals(mom_sig, ma_sig, breakout_sig)
        assert (combined == -1).all()
    
    def test_combine_signals_weighted_method(self):
        """Test 'weighted' combination method."""
        dates = pd.date_range('2020-01-01', periods=10)
        
        # Weighted sum > 0.1 → long
        # weights = [0.4, 0.3, 0.3]
        # 1*0.4 + 1*0.3 + (-1)*0.3 = 0.4 > 0.1 → long
        mom_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        ma_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        breakout_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        
        strategy = TrendStrategy(params={
            "combination_method": "weighted",
            "weights": [0.4, 0.3, 0.3]
        })
        combined = strategy.combine_signals(mom_sig, ma_sig, breakout_sig)
        
        assert (combined == 1).all()
    
    def test_combine_signals_weighted_threshold_configurable(self):
        """Test that weighted_threshold is configurable and affects signals."""
        dates = pd.date_range('2020-01-01', periods=10)
        
        # Weighted sum = 0.05 (below default 0.1, above 0.01)
        # weights = [0.4, 0.3, 0.3]
        # 1*0.4 + (-1)*0.3 + (-1)*0.3 = 0.4 - 0.6 = -0.2... wait let me recalculate
        # Actually: 1*0.4 + 0*0.3 + 0*0.3 = 0.4 (too high)
        # Let's use: 1*0.4 + (-1)*0.3 + 0*0.3 = 0.1 (exactly at threshold)
        # Better: Use different weights to get exactly 0.05
        
        mom_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        ma_sig = pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 0, 0], index=dates)
        breakout_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        
        # With weights [0.35, 0.3, 0.35]: 1*0.35 + 0*0.3 + (-1)*0.35 = 0
        # Let's use [0.4, 0.3, 0.3]: 1*0.4 + 0*0.3 + (-1)*0.3 = 0.1
        # With threshold 0.15 → neutral (0.1 < 0.15)
        strategy_high_threshold = TrendStrategy(params={
            "combination_method": "weighted",
            "weights": [0.4, 0.3, 0.3],
            "weighted_threshold": 0.15
        })
        combined = strategy_high_threshold.combine_signals(mom_sig, ma_sig, breakout_sig)
        assert (combined == 0).all()  # Below threshold → neutral
        
        # With threshold 0.05 → long (0.1 > 0.05)
        strategy_low_threshold = TrendStrategy(params={
            "combination_method": "weighted",
            "weights": [0.4, 0.3, 0.3],
            "weighted_threshold": 0.05
        })
        combined = strategy_low_threshold.combine_signals(mom_sig, ma_sig, breakout_sig)
        assert (combined == 1).all()  # Above threshold → long


class TestTrendStrategyIntegration:
    """Integration tests for full strategy execution."""
    
    def test_generate_signals_integration(self):
        """Test full signal generation with all indicators."""
        dates = pd.date_range('2020-01-01', periods=300)
        # Strong uptrend
        ohlcv = pd.DataFrame({
            'close': np.linspace(100, 150, 300),
        }, index=dates)
        
        strategy = TrendStrategy()
        signals = strategy.generate_signals(ohlcv)
        
        # Should be mostly long after warmup
        assert signals.iloc[-50:].mean() > 0.5
    
    def test_calculate_returns_signal_lag(self):
        """Test that returns use lagged signals (no look-ahead bias)."""
        dates = pd.date_range('2020-01-01', periods=300)
        ohlcv = pd.DataFrame({
            'close': np.linspace(100, 150, 300),
            'raw_ret': np.random.randn(300) * 0.01,
        }, index=dates)
        
        strategy = TrendStrategy()
        signals = strategy.generate_signals(ohlcv)
        meta_returns = strategy.calculate_returns(ohlcv)
        
        # meta_ret[t] should use signal[t-1]
        # First valid meta_return should be at index where signal[t-1] exists
        first_valid_signal_idx = signals.first_valid_index()
        if first_valid_signal_idx is not None:
            signal_loc = ohlcv.index.get_loc(first_valid_signal_idx)
            if signal_loc + 1 < len(ohlcv):
                next_date = ohlcv.index[signal_loc + 1]
                # meta_ret at next_date should equal signal at first_valid * raw_ret at next_date
                expected = signals.loc[first_valid_signal_idx] * ohlcv.loc[next_date, 'raw_ret']
                assert abs(meta_returns.loc[next_date] - expected) < 1e-10
    
    def test_run_with_real_data(self):
        """Test full run() with real market data."""
        # Use 2 years of data since TrendStrategy has 253-day warmup
        data = load_universe(["SPY"], "2020-01-01", "2021-12-31")
        
        strategy = TrendStrategy()
        result = strategy.run(data)
        
        spy_df = result["SPY"]
        
        # Should have meta_raw_ret column
        assert 'meta_raw_ret' in spy_df.columns
        
        # First warmup days should be NaN
        warmup = strategy.get_warmup_period()
        assert spy_df['meta_raw_ret'].iloc[:warmup].isna().all()
        
        # Should have valid returns after warmup
        assert spy_df['meta_raw_ret'].iloc[warmup:].notna().sum() > 0
        
        # Warmup period should be 253 (default)
        assert strategy.get_warmup_period() == 253


class TestTrendStrategyEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_trend_with_flat_prices(self):
        """Test strategy with flat (no movement) prices."""
        dates = pd.date_range('2020-01-01', periods=300)
        ohlcv = pd.DataFrame({
            'close': [100] * 300,  # Flat prices
            'raw_ret': [0] * 300,
        }, index=dates)
        
        strategy = TrendStrategy()
        signals = strategy.generate_signals(ohlcv)
        meta_returns = strategy.calculate_returns(ohlcv)
        
        # Should not crash
        assert len(signals) == 300
        assert len(meta_returns) == 300
    
    def test_trend_with_missing_data(self):
        """Test strategy handles NaN values gracefully."""
        dates = pd.date_range('2020-01-01', periods=300)
        prices = np.linspace(100, 150, 300)
        prices[100:110] = np.nan  # Introduce missing data
        
        ohlcv = pd.DataFrame({
            'close': prices,
            'raw_ret': np.random.randn(300) * 0.01,
        }, index=dates)
        
        strategy = TrendStrategy()
        
        # Should not crash
        signals = strategy.generate_signals(ohlcv)
        meta_returns = strategy.calculate_returns(ohlcv)
        
        assert len(signals) == 300
        assert len(meta_returns) == 300
    
    def test_breakout_signal_narrow_range_overlap(self):
        """Test breakout signal when range is narrow (both high and low bands overlap)."""
        dates = pd.date_range('2020-01-01', periods=300)
        
        # Create narrow range: prices oscillate in tiny range
        # After warmup, range will be very narrow (99.9 to 100.1)
        prices = [100] * 252  # Warmup period
        prices.extend([100 + 0.05 * np.sin(i / 10) for i in range(48)])  # Tiny oscillation
        
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = TrendStrategy(params={"breakout_period": 252})
        signals = strategy.calculate_breakout_signal(ohlcv)
        
        # In the narrow range period (after warmup), signals should be neutral (0)
        # because both high and low conditions will be true
        narrow_range_signals = signals.iloc[-20:]  # Last 20 days
        
        # Most or all should be neutral (0) due to overlap
        neutral_count = (narrow_range_signals == 0).sum()
        assert neutral_count >= 15  # At least 75% neutral in narrow range
    
    def test_breakout_signal_no_overlap_in_trending_market(self):
        """Test that breakout signal works normally when range is not narrow."""
        dates = pd.date_range('2020-01-01', periods=300)
        
        # Strong uptrend - no overlap expected
        prices = np.linspace(100, 150, 300)
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = TrendStrategy(params={"breakout_period": 252})
        signals = strategy.calculate_breakout_signal(ohlcv)
        
        # In uptrend, should be mostly long (1), not neutral
        trending_signals = signals.iloc[-50:]
        long_count = (trending_signals == 1).sum()
        
        # Should have many long signals in uptrend
        assert long_count >= 40  # At least 80% long
