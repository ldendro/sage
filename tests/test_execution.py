"""Tests for ExecutionPolicy and ExecutionModule."""

import pytest
import pandas as pd
import numpy as np

from sage_core.execution.policy import ExecutionPolicy
from sage_core.execution.module import ExecutionModule


class TestExecutionPolicy:
    """Tests for ExecutionPolicy Pydantic model."""
    
    def test_default_values(self):
        """Test default policy values."""
        policy = ExecutionPolicy()
        assert policy.signal_time == "close"
        assert policy.execution_time == "next_open"
        assert policy.price_used == "open"
        assert policy.execution_delay_days == 1
    
    def test_custom_delay(self):
        """Test custom execution delay."""
        policy = ExecutionPolicy(execution_delay_days=2)
        assert policy.execution_delay_days == 2
    
    def test_zero_delay(self):
        """Test zero delay (same-day execution)."""
        policy = ExecutionPolicy(execution_delay_days=0)
        assert policy.execution_delay_days == 0
    
    def test_invalid_delay_negative(self):
        """Test negative delay raises error."""
        with pytest.raises(Exception):
            ExecutionPolicy(execution_delay_days=-1)
    
    def test_delay_too_large(self):
        """Test excessively large delay raises error."""
        with pytest.raises(Exception):
            ExecutionPolicy(execution_delay_days=11)
    
    def test_policy_attributes(self):
        """Test policy has all expected attributes."""
        policy = ExecutionPolicy()
        assert hasattr(policy, 'signal_time')
        assert hasattr(policy, 'execution_time')
        assert hasattr(policy, 'price_used')
        assert hasattr(policy, 'execution_delay_days')


class TestExecutionModuleApplyDelay:
    """Tests for ExecutionModule.apply_delay()."""
    
    def test_apply_delay_series(self):
        """Test shifting a Series by execution_delay_days."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=dates)
        
        em = ExecutionModule(ExecutionPolicy(execution_delay_days=1))
        result = em.apply_delay(s)
        
        assert pd.isna(result.iloc[0])
        assert result.iloc[1] == 1.0
        assert result.iloc[4] == 4.0
    
    def test_apply_delay_dataframe(self):
        """Test shifting a DataFrame by execution_delay_days."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        df = pd.DataFrame({"A": [1, 2, 3, 4, 5], "B": [10, 20, 30, 40, 50]}, index=dates)
        
        em = ExecutionModule(ExecutionPolicy(execution_delay_days=1))
        result = em.apply_delay(df)
        
        assert result["A"].iloc[0] != result["A"].iloc[0]  # NaN != NaN
        assert result["A"].iloc[1] == 1
        assert result["B"].iloc[1] == 10
    
    def test_apply_delay_zero(self):
        """Test zero delay returns same values."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=dates)
        
        em = ExecutionModule(ExecutionPolicy(execution_delay_days=0))
        result = em.apply_delay(s)
        
        assert (result == s).all()
    
    def test_apply_delay_two_days(self):
        """Test 2-day delay."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=dates)
        
        em = ExecutionModule(ExecutionPolicy(execution_delay_days=2))
        result = em.apply_delay(s)
        
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == 1.0
        assert result.iloc[4] == 3.0


class TestExecutionModuleComputeMetaRawReturns:
    """Tests for ExecutionModule.compute_meta_raw_returns()."""
    
    def test_basic_signal_to_return(self):
        """Test that intent * raw_ret is correctly lagged."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        intent = {"SPY": pd.Series([1, 1, -1, 1, -1], index=dates, dtype=float)}
        raw_ret = {"SPY": pd.Series([0.01, 0.02, -0.01, 0.03, -0.02], index=dates)}
        
        em = ExecutionModule(ExecutionPolicy(execution_delay_days=1))
        result = em.compute_meta_raw_returns(intent, raw_ret)
        
        # At t=1: intent[0] * raw_ret[1] = 1 * 0.02 = 0.02
        assert np.isclose(result["SPY"].iloc[1], 0.02)
        # At t=2: intent[1] * raw_ret[2] = 1 * -0.01 = -0.01
        assert np.isclose(result["SPY"].iloc[2], -0.01)
        # At t=3: intent[2] * raw_ret[3] = -1 * 0.03 = -0.03
        assert np.isclose(result["SPY"].iloc[3], -0.03)
    
    def test_passthrough_invariant(self):
        """Test that all-1 intent yields raw_ret shifted by delay."""
        dates = pd.date_range("2020-01-01", periods=10, freq="B")
        raw_returns = np.random.randn(10) * 0.01
        intent = {"SPY": pd.Series(1.0, index=dates)}
        raw_ret = {"SPY": pd.Series(raw_returns, index=dates)}
        
        em = ExecutionModule(ExecutionPolicy(execution_delay_days=1))
        result = em.compute_meta_raw_returns(intent, raw_ret)
        
        # With all-1 intent and delay=1: meta_raw_ret[t] = 1 * raw_ret[t] = raw_ret[t]
        # But the intent is shifted, so: meta_raw_ret[t] = intent[t-1] * raw_ret[t]
        # Since intent is all 1s: meta_raw_ret[t] = 1 * raw_ret[t] = raw_ret[t]
        # First row is NaN (no lagged intent), rest equal raw_ret
        assert pd.isna(result["SPY"].iloc[0])
        assert np.allclose(result["SPY"].iloc[1:], raw_returns[1:])
    
    def test_multi_asset(self):
        """Test with multiple assets."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        intent = {
            "SPY": pd.Series([1, 1, -1, 1, -1], index=dates, dtype=float),
            "QQQ": pd.Series([-1, 1, 1, -1, 1], index=dates, dtype=float),
        }
        raw_ret = {
            "SPY": pd.Series([0.01] * 5, index=dates),
            "QQQ": pd.Series([0.02] * 5, index=dates),
        }
        
        em = ExecutionModule(ExecutionPolicy(execution_delay_days=1))
        result = em.compute_meta_raw_returns(intent, raw_ret)
        
        assert "SPY" in result
        assert "QQQ" in result
        assert len(result["SPY"]) == 5
        assert len(result["QQQ"]) == 5


class TestExecutionModuleValidateIntent:
    """Tests for ExecutionModule.validate_intent()."""
    
    def test_valid_discrete_intent(self):
        """Test that valid discrete intent passes validation."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        intent = {"SPY": pd.Series([1, 0, -1, 1, 0], index=dates, dtype=float)}
        
        em = ExecutionModule(ExecutionPolicy())
        # Should not raise
        em.validate_intent(intent, intent_type="discrete")
    
    def test_valid_continuous_intent(self):
        """Test that valid continuous intent passes validation."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        intent = {"SPY": pd.Series([0.5, -0.3, 0.8, -0.1, 0.0], index=dates)}
        
        em = ExecutionModule(ExecutionPolicy())
        # Should not raise
        em.validate_intent(intent, intent_type="continuous")
    
    def test_invalid_discrete_values(self):
        """Test that non-{-1,0,1} values raise error for discrete."""
        dates = pd.date_range('2020-01-01', periods=5, freq='B')
        intent = {"SPY": pd.Series([0.5, 1.0, -1.0, 0.0, 2.0], index=dates)}
        
        em = ExecutionModule(ExecutionPolicy())
        with pytest.raises(ValueError, match="Discrete intent"):
            em.validate_intent(intent, intent_type="discrete")
    
    def test_empty_intent_passes(self):
        """Test that empty intent dict does not raise (no assets to validate)."""
        em = ExecutionModule(ExecutionPolicy())
        # Empty dict is valid — no assets to validate
        em.validate_intent({})


class TestExecutionModuleValidateAlignment:
    """Tests for ExecutionModule.validate_alignment()."""
    
    def test_valid_alignment(self):
        """Test that aligned indices pass validation."""
        dates = pd.date_range('2020-01-01', periods=5, freq='B')
        s1 = pd.Series([1, 2, 3, 4, 5], index=dates)
        s2 = pd.Series([10, 20, 30, 40, 50], index=dates)
        
        em = ExecutionModule(ExecutionPolicy())
        # Should not raise (note: validate_alignment(index, *objs))
        em.validate_alignment(dates, s1, s2)
    
    def test_misaligned_raises(self):
        """Test that misaligned indices raise error."""
        dates1 = pd.date_range('2020-01-01', periods=5, freq='B')
        dates2 = pd.date_range('2020-02-01', periods=5, freq='B')
        s1 = pd.Series([1, 2, 3, 4, 5], index=dates1)
        s2 = pd.Series([10, 20, 30, 40, 50], index=dates2)
        
        em = ExecutionModule(ExecutionPolicy())
        with pytest.raises(ValueError, match="does not match"):
            em.validate_alignment(dates1, s1, s2)
    
    def test_duplicate_index_raises(self):
        """Test that duplicate indices raise error."""
        dates = pd.DatetimeIndex(["2020-01-01", "2020-01-01", "2020-01-03"])
        
        em = ExecutionModule(ExecutionPolicy())
        with pytest.raises(ValueError, match="duplicate"):
            em.validate_alignment(dates)
    
    def test_unsorted_index_raises(self):
        """Test that unsorted indices raise error."""
        dates = pd.DatetimeIndex(["2020-01-03", "2020-01-01", "2020-01-02"])
        
        em = ExecutionModule(ExecutionPolicy())
        with pytest.raises(ValueError, match="sorted"):
            em.validate_alignment(dates)


class TestExecutionDelayImpact:
    """Tests verifying impact of different execution_delay_days."""
    
    def test_delay_0_no_lag(self):
        """Test that delay=0 means no lag between signal and return."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        intent = {"SPY": pd.Series([1, -1, 1, -1, 1], index=dates, dtype=float)}
        raw_ret = {"SPY": pd.Series([0.01, 0.02, 0.03, 0.04, 0.05], index=dates)}
        
        em = ExecutionModule(ExecutionPolicy(execution_delay_days=0))
        result = em.compute_meta_raw_returns(intent, raw_ret)
        
        # No lag: meta_raw_ret[t] = intent[t] * raw_ret[t]
        expected = intent["SPY"] * raw_ret["SPY"]
        assert np.allclose(result["SPY"], expected)
    
    def test_delay_2_double_lag(self):
        """Test that delay=2 shifts intent by 2."""
        dates = pd.date_range("2020-01-01", periods=5, freq="B")
        intent = {"SPY": pd.Series([1, -1, 1, -1, 1], index=dates, dtype=float)}
        raw_ret = {"SPY": pd.Series([0.01, 0.02, 0.03, 0.04, 0.05], index=dates)}
        
        em = ExecutionModule(ExecutionPolicy(execution_delay_days=2))
        result = em.compute_meta_raw_returns(intent, raw_ret)
        
        # First 2 days NaN
        assert pd.isna(result["SPY"].iloc[0])
        assert pd.isna(result["SPY"].iloc[1])
        # Day 2: intent[0] * raw_ret[2] = 1 * 0.03 = 0.03
        assert np.isclose(result["SPY"].iloc[2], 0.03)
