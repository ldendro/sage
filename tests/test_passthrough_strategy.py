"""
Tests for PassthroughStrategy.
"""

import pytest
import pandas as pd
import numpy as np

from sage_core.strategies.passthrough import PassthroughStrategy
from sage_core.data.loader import load_universe


class TestPassthroughStrategy:
    """Tests for PassthroughStrategy class."""
    
    def test_passthrough_class_basic(self):
        """Test PassthroughStrategy class basic functionality."""
        data = load_universe(
            universe=["SPY", "QQQ"],
            start_date="2020-01-01",
            end_date="2020-01-31",
        )
        
        strategy = PassthroughStrategy()
        result = strategy.run(data)
        
        # Check both symbols have signal column
        for symbol in ["SPY", "QQQ"]:
            df = result[symbol]
            assert 'signal' in df.columns
            # Passthrough signal is always 1
            assert (df['signal'] == 1).all()
    
    def test_passthrough_warmup_period(self):
        """Test that passthrough returns 0 warmup."""
        strategy = PassthroughStrategy()
        assert strategy.get_warmup_period() == 0
    
    def test_passthrough_signals(self):
        """Test that passthrough generates all-long signals."""
        dates = pd.date_range('2020-01-01', periods=10)
        ohlcv = pd.DataFrame({
            'close': np.random.randn(10) + 100,
        }, index=dates)
        
        strategy = PassthroughStrategy()
        signals = strategy.generate_signals(ohlcv)
        
        assert len(signals) == 10
        assert (signals == 1).all()
    
    def test_passthrough_signal_type(self):
        """Test that passthrough signal type is discrete."""
        strategy = PassthroughStrategy()
        assert strategy.signal_type == "discrete"
