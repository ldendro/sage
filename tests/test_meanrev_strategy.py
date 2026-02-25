"""Tests for MeanRevStrategy (multi-indicator mean reversion)."""

import pytest
import pandas as pd
import numpy as np

from sage_core.strategies.meanrev import MeanRevStrategy
from sage_core.data.loader import load_universe


class TestMeanRevStrategyInitialization:
    """Tests for MeanRevStrategy initialization and validation."""
    
    def test_meanrev_initialization_defaults(self):
        """Test MeanRevStrategy initialization with default parameters."""
        strategy = MeanRevStrategy()
        
        assert strategy.params["rsi_period"] == 14
        assert strategy.params["rsi_oversold"] == 30
        assert strategy.params["rsi_overbought"] == 70
        assert strategy.params["bb_period"] == 20
        assert strategy.params["bb_std"] == 2.0
        assert strategy.params["zscore_lookback"] == 60
        assert strategy.params["zscore_threshold"] == 1.5
        assert strategy.params["combination_method"] == "majority"
        assert strategy.params["weights"] == [0.4, 0.3, 0.3]
        assert strategy.params["weighted_threshold"] == 0.1
    
    def test_meanrev_custom_params(self):
        """Test MeanRevStrategy with custom parameters."""
        params = {
            "rsi_period": 21,
            "rsi_oversold": 20,
            "rsi_overbought": 80,
            "bb_period": 30,
            "zscore_lookback": 90,
            "combination_method": "all",
        }
        strategy = MeanRevStrategy(params=params)
        
        assert strategy.params["rsi_period"] == 21
        assert strategy.params["rsi_oversold"] == 20
        assert strategy.params["rsi_overbought"] == 80
        assert strategy.params["bb_period"] == 30
        assert strategy.params["zscore_lookback"] == 90
        assert strategy.params["combination_method"] == "all"
    
    def test_meanrev_param_validation_rsi_period(self):
        """Test parameter validation for rsi_period."""
        # Too small
        with pytest.raises(ValueError, match="rsi_period must be int >= 2"):
            MeanRevStrategy(params={"rsi_period": 1})
        
        # Too large
        with pytest.raises(ValueError, match="rsi_period too large"):
            MeanRevStrategy(params={"rsi_period": 150})
        
        # Invalid type
        with pytest.raises(ValueError, match="rsi_period must be int"):
            MeanRevStrategy(params={"rsi_period": 14.5})
    
    def test_meanrev_param_validation_rsi_thresholds(self):
        """Test parameter validation for RSI thresholds."""
        # oversold >= overbought
        with pytest.raises(ValueError, match="rsi_oversold .* must be < rsi_overbought"):
            MeanRevStrategy(params={"rsi_oversold": 70, "rsi_overbought": 30})
        
        # Out of range
        with pytest.raises(ValueError, match="rsi_oversold must be in"):
            MeanRevStrategy(params={"rsi_oversold": -10})
        
        with pytest.raises(ValueError, match="rsi_overbought must be in"):
            MeanRevStrategy(params={"rsi_overbought": 110})
    
    def test_meanrev_param_validation_bb(self):
        """Test parameter validation for Bollinger Bands."""
        # Period too small
        with pytest.raises(ValueError, match="bb_period must be int >= 2"):
            MeanRevStrategy(params={"bb_period": 1})
        
        # Period too large
        with pytest.raises(ValueError, match="bb_period too large"):
            MeanRevStrategy(params={"bb_period": 250})
        
        # Std too small
        with pytest.raises(ValueError, match="bb_std must be > 0"):
            MeanRevStrategy(params={"bb_std": 0})
        
        # Std too large
        with pytest.raises(ValueError, match="bb_std too large"):
            MeanRevStrategy(params={"bb_std": 10})
    
    def test_meanrev_param_validation_zscore(self):
        """Test parameter validation for Z-Score."""
        # Lookback too small
        with pytest.raises(ValueError, match="zscore_lookback must be int >= 10"):
            MeanRevStrategy(params={"zscore_lookback": 5})
        
        # Lookback too large
        with pytest.raises(ValueError, match="zscore_lookback too large"):
            MeanRevStrategy(params={"zscore_lookback": 300})
        
        # Threshold too small
        with pytest.raises(ValueError, match="zscore_threshold must be > 0"):
            MeanRevStrategy(params={"zscore_threshold": 0})
        
        # Threshold too large
        with pytest.raises(ValueError, match="zscore_threshold too large"):
            MeanRevStrategy(params={"zscore_threshold": 10})
    
    def test_meanrev_param_validation_combination_method(self):
        """Test parameter validation for combination_method."""
        with pytest.raises(ValueError, match="combination_method must be one of"):
            MeanRevStrategy(params={"combination_method": "invalid"})
    
    def test_meanrev_param_validation_weights(self):
        """Test parameter validation for weights."""
        # Wrong length
        with pytest.raises(ValueError, match="weights must be list/tuple of length 3"):
            MeanRevStrategy(params={
                "combination_method": "weighted",
                "weights": [0.5, 0.5]
            })
        
        # Don't sum to 1.0
        with pytest.raises(ValueError, match="weights must sum to 1.0"):
            MeanRevStrategy(params={
                "combination_method": "weighted",
                "weights": [0.5, 0.3, 0.3]
            })
    
    def test_meanrev_param_validation_weighted_threshold(self):
        """Test parameter validation for weighted_threshold."""
        # Out of range
        with pytest.raises(ValueError, match="weighted_threshold must be in"):
            MeanRevStrategy(params={
                "combination_method": "weighted",
                "weighted_threshold": -0.1
            })
        
        # Valid value should work
        strategy = MeanRevStrategy(params={
            "combination_method": "weighted",
            "weighted_threshold": 0.05
        })
        assert strategy.params["weighted_threshold"] == 0.05


class TestMeanRevStrategyWarmup:
    """Tests for warmup period calculation."""
    
    def test_meanrev_warmup_period_max_of_lookbacks(self):
        """Test that warmup period is max of all indicator lookbacks."""
        # Default params: max(14, 20, 60) = 60
        strategy = MeanRevStrategy()
        assert strategy.get_warmup_period() == 60
        
        # Custom params where bb_period is longest
        strategy = MeanRevStrategy(params={
            "rsi_period": 10,
            "bb_period": 100,
            "zscore_lookback": 50,
        })
        assert strategy.get_warmup_period() == 100
        
        # Custom params where rsi_period is longest
        strategy = MeanRevStrategy(params={
            "rsi_period": 50,
            "bb_period": 20,
            "zscore_lookback": 30,
        })
        assert strategy.get_warmup_period() == 50


class TestMeanRevStrategyIndicators:
    """Tests for individual indicator calculations."""
    
    def test_rsi_signal_oversold(self):
        """Test RSI signal when oversold."""
        dates = pd.date_range('2020-01-01', periods=100)
        # Create downtrend to get low RSI
        prices = np.linspace(100, 80, 100)
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"rsi_period": 14, "rsi_oversold": 30})
        signals = strategy.calculate_rsi_signal(ohlcv)
        
        # Should have some long signals (1) when RSI < 30
        assert (signals == 1).sum() > 0
    
    def test_rsi_signal_overbought(self):
        """Test RSI signal when overbought."""
        dates = pd.date_range('2020-01-01', periods=100)
        # Create accelerating uptrend to get high RSI (not linear!)
        # Start flat, then sharp gains
        prices = [80] * 30 + list(np.linspace(80, 100, 70))
        # Add some sharp spikes to boost RSI
        for i in range(50, 70, 5):
            prices[i] = prices[i] + 2
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"rsi_period": 14, "rsi_overbought": 70})
        signals = strategy.calculate_rsi_signal(ohlcv)
        
        # Should have some short signals (-1) when RSI > 70
        assert (signals == -1).sum() > 0
    
    def test_bb_signal_below_lower_band(self):
        """Test BB signal when price below lower band."""
        dates = pd.date_range('2020-01-01', periods=100)
        # Create oscillating pattern with sharp drops
        prices = [100 + 5 * np.sin(i / 5) for i in range(70)] + [85] * 30
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"bb_period": 20, "bb_std": 1.5})
        signals = strategy.calculate_bb_signal(ohlcv)
        
        # Should have some long signals (1) when price drops below lower band
        assert (signals == 1).sum() > 0
    
    def test_bb_signal_above_upper_band(self):
        """Test BB signal when price above upper band."""
        dates = pd.date_range('2020-01-01', periods=100)
        # Create oscillating pattern with sharp spikes
        prices = [100 + 5 * np.sin(i / 5) for i in range(70)] + [115] * 30
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"bb_period": 20, "bb_std": 1.5})
        signals = strategy.calculate_bb_signal(ohlcv)
        
        # Should have some short signals (-1) when price spikes above upper band
        assert (signals == -1).sum() > 0
    
    def test_zscore_signal_negative_extreme(self):
        """Test Z-Score signal when significantly below mean."""
        dates = pd.date_range('2020-01-01', periods=100)
        # Stable around 100, then sharp drop to 70
        prices = [100] * 70 + [70] * 30
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"zscore_lookback": 60, "zscore_threshold": 1.0})
        signals = strategy.calculate_zscore_signal(ohlcv)
        
        # After sharp drop, should have long signals (1)
        assert (signals == 1).sum() > 0
    
    def test_zscore_signal_positive_extreme(self):
        """Test Z-Score signal when significantly above mean."""
        dates = pd.date_range('2020-01-01', periods=100)
        # Stable around 100, then sharp spike to 130
        prices = [100] * 70 + [130] * 30
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"zscore_lookback": 60, "zscore_threshold": 1.0})
        signals = strategy.calculate_zscore_signal(ohlcv)
        
        # After sharp spike, should have short signals (-1)
        assert (signals == -1).sum() > 0


class TestMeanRevStrategyCombination:
    """Tests for signal combination methods."""
    
    def test_combine_signals_all_method(self):
        """Test 'all' combination method (all must agree)."""
        dates = pd.date_range('2020-01-01', periods=10)
        
        # All long
        rsi_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        bb_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        zscore_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        
        strategy = MeanRevStrategy(params={"combination_method": "all"})
        combined = strategy.combine_signals(rsi_sig, bb_sig, zscore_sig)
        
        assert (combined == 1).all()
        
        # Mixed signals → neutral
        rsi_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        bb_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        zscore_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        
        combined = strategy.combine_signals(rsi_sig, bb_sig, zscore_sig)
        assert (combined == 0).all()
    
    def test_combine_signals_majority_method(self):
        """Test 'majority' combination method (at least 2 of 3)."""
        dates = pd.date_range('2020-01-01', periods=10)
        
        # All 3 long → long
        rsi_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        bb_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        zscore_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        
        strategy = MeanRevStrategy(params={"combination_method": "majority"})
        combined = strategy.combine_signals(rsi_sig, bb_sig, zscore_sig)
        
        assert (combined == 1).all()
        
        # 2 long, 1 neutral → long
        rsi_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        bb_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        zscore_sig = pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 0, 0], index=dates)
        
        combined = strategy.combine_signals(rsi_sig, bb_sig, zscore_sig)
        assert (combined == 1).all()
    
    def test_combine_signals_weighted_method(self):
        """Test 'weighted' combination method."""
        dates = pd.date_range('2020-01-01', periods=10)
        
        # Weighted sum > threshold → long
        rsi_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        bb_sig = pd.Series([1, 1, 1, 1, 1, 1, 1, 1, 1, 1], index=dates)
        zscore_sig = pd.Series([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1], index=dates)
        
        strategy = MeanRevStrategy(params={
            "combination_method": "weighted",
            "weights": [0.4, 0.3, 0.3]
        })
        combined = strategy.combine_signals(rsi_sig, bb_sig, zscore_sig)
        
        # 0.4 + 0.3 - 0.3 = 0.4 > 0.1 → long
        assert (combined == 1).all()


class TestMeanRevStrategyIntegration:
    """Integration tests for full strategy execution."""
    
    def test_generate_signals_integration(self):
        """Test full signal generation with all indicators."""
        dates = pd.date_range('2020-01-01', periods=150)
        # Create mean-reverting pattern
        prices = 100 + 10 * np.sin(np.linspace(0, 4 * np.pi, 150))
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy()
        signals = strategy.generate_signals(ohlcv)
        
        # Should generate some signals
        assert signals.notna().sum() > 0
        assert len(signals) == 150
    
    def test_run_with_real_data(self):
        """Test full run() with real market data."""
        data = load_universe(["SPY"], "2020-01-01", "2020-12-31")
        
        strategy = MeanRevStrategy()
        result = strategy.run(data)
        
        spy_df = result["SPY"]
        
        # Should have signal column (not meta_raw_ret)
        assert 'signal' in spy_df.columns
        
        # Should have some valid signals after warmup
        assert spy_df['signal'].notna().sum() > 0
        
        # Signals should be discrete {-1, 0, 1}
        valid_signals = spy_df['signal'].dropna()
        assert valid_signals.isin([-1, 0, 1]).all()
        
        # Warmup period should be 60 (default)
        assert strategy.get_warmup_period() == 60


class TestMeanRevStrategyEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_meanrev_with_flat_prices(self):
        """Test strategy with flat (no movement) prices."""
        dates = pd.date_range('2020-01-01', periods=150)
        ohlcv = pd.DataFrame({
            'close': [100] * 150,
            'raw_ret': [0] * 150,
        }, index=dates)
        
        strategy = MeanRevStrategy()
        signals = strategy.generate_signals(ohlcv)
        
        # Should not crash
        assert len(signals) == 150
    
    def test_meanrev_with_missing_data(self):
        """Test strategy handles NaN values gracefully."""
        dates = pd.date_range('2020-01-01', periods=150)
        prices = 100 + 10 * np.sin(np.linspace(0, 4 * np.pi, 150))
        prices_with_nan = prices.copy()
        prices_with_nan[70:80] = np.nan
        
        ohlcv = pd.DataFrame({
            'close': prices_with_nan,
            'raw_ret': np.random.randn(150) * 0.01,
        }, index=dates)
        
        strategy = MeanRevStrategy()
        
        # Should not crash
        signals = strategy.generate_signals(ohlcv)
        
        assert len(signals) == 150
    
    def test_meanrev_low_volatility(self):
        """Test strategy with very low volatility (BB bands collapse)."""
        dates = pd.date_range('2020-01-01', periods=150)
        # Very small oscillations
        prices = 100 + 0.01 * np.sin(np.linspace(0, 4 * np.pi, 150))
        ohlcv = pd.DataFrame({
            'close': prices,
            'raw_ret': np.random.randn(150) * 0.0001,
        }, index=dates)
        
        strategy = MeanRevStrategy()
        
        # Should not crash even with collapsed bands
        signals = strategy.generate_signals(ohlcv)
        
        assert len(signals) == 150

    def test_rsi_sustained_uptrend_no_losses(self):
        """Test RSI returns 100 (overbought) when avg_loss=0 (sustained uptrend)."""
        dates = pd.date_range('2020-01-01', periods=50)
        # Perfect uptrend - every day gains, no losses
        prices = np.linspace(100, 150, 50)
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"rsi_period": 14, "rsi_overbought": 70})
        signals = strategy.calculate_rsi_signal(ohlcv)
        
        # After warmup, RSI should be 100 (overbought), generating short signals
        # Check last 10 days
        assert (signals.iloc[-10:] == -1).sum() > 0, "Should generate short signals when RSI=100"


    def test_rsi_sustained_downtrend_no_gains(self):
        """Test RSI returns 0 (oversold) when avg_gain=0 (sustained downtrend)."""
        dates = pd.date_range('2020-01-01', periods=50)
        # Perfect downtrend - every day losses, no gains
        prices = np.linspace(100, 50, 50)
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"rsi_period": 14, "rsi_oversold": 30})
        signals = strategy.calculate_rsi_signal(ohlcv)
        
        # After warmup, RSI should be 0 (oversold), generating long signals
        # Check last 10 days
        assert (signals.iloc[-10:] == 1).sum() > 0, "Should generate long signals when RSI=0"


    def test_rsi_flat_prices(self):
        """Test RSI returns 50 (neutral) when both avg_gain=0 and avg_loss=0 (flat)."""
        dates = pd.date_range('2020-01-01', periods=50)
        # Completely flat prices
        prices = [100] * 50
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"rsi_period": 14})
        signals = strategy.calculate_rsi_signal(ohlcv)
        
        # RSI should be 50 (neutral), generating no signals
        assert (signals == 0).all(), "Should generate no signals when RSI=50 (flat prices)"


    def test_zscore_flat_prices(self):
        """Test Z-Score returns 0 (neutral) when std=0 (flat prices)."""
        dates = pd.date_range('2020-01-01', periods=100)
        # Completely flat prices
        prices = [100] * 100
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"zscore_lookback": 60, "zscore_threshold": 1.5})
        signals = strategy.calculate_zscore_signal(ohlcv)
        
        # Z-Score should be 0 (neutral), generating no signals
        assert (signals == 0).all(), "Should generate no signals when Z-Score=0 (flat prices)"


    def test_no_nan_in_rsi_signals(self):
        """Test that RSI signals never contain NaN values."""
        dates = pd.date_range('2020-01-01', periods=100)
        # Mix of uptrend, downtrend, and flat
        prices = list(np.linspace(100, 120, 30)) + [120] * 20 + list(np.linspace(120, 100, 50))
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"rsi_period": 14})
        signals = strategy.calculate_rsi_signal(ohlcv)
        
        # After warmup, should have no NaN signals
        assert signals.iloc[14:].notna().all(), "RSI signals should not contain NaN after warmup"


    def test_no_nan_in_zscore_signals(self):
        """Test that Z-Score signals never contain NaN values."""
        dates = pd.date_range('2020-01-01', periods=100)
        # Mix of volatile and flat periods
        prices = [100 + 10 * np.sin(i / 5) for i in range(50)] + [100] * 50
        ohlcv = pd.DataFrame({'close': prices}, index=dates)
        
        strategy = MeanRevStrategy(params={"zscore_lookback": 60})
        signals = strategy.calculate_zscore_signal(ohlcv)
        
        # After warmup, should have no NaN signals
        assert signals.iloc[60:].notna().all(), "Z-Score signals should not contain NaN after warmup"
