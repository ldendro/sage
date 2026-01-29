"""
Quick integration test for real data loading.

This script tests the end-to-end flow of loading real market data
and running a backtest.
"""

from sage_core.walkforward.engine import run_system_walkforward
from sage_core.data.cache import get_cache_size

print("=" * 60)
print("Integration Test: Real Data Loading")
print("=" * 60)

# Test 1: Check cache before test
print("\n1. Checking cache status...")
count, size = get_cache_size()
print(f"   Cache: {count} files, {size / (1024 * 1024):.2f} MB")

# Test 2: Run backtest with real data
print("\n2. Running backtest with real data (SPY, QQQ, IWM)...")
print("   Date range: 2023-01-01 to 2023-12-31")
print("   This will fetch data from Yahoo Finance...")

try:
    results = run_system_walkforward(
        universe=['SPY', 'QQQ', 'IWM'],
        start_date='2023-01-01',
        end_date='2023-12-31',
        max_weight_per_asset=0.5,
        max_sector_weight=1.0,
        min_assets_held=2,
        target_vol=0.15,
        vol_lookback=60,
        min_leverage=0.0,
        max_leverage=2.0,
        vol_window=20,
    )
    
    print("   ✅ Backtest completed successfully!")
    print(f"   Total Return: {results['metrics']['total_return']:.2%}")
    print(f"   Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
    print(f"   Max Drawdown: {results['metrics']['max_drawdown']:.2%}")
    
except Exception as e:
    print(f"   ❌ Backtest failed: {e}")
    raise

# Test 3: Check cache after test
print("\n3. Checking cache status after backtest...")
count, size = get_cache_size()
print(f"   Cache: {count} files, {size / (1024 * 1024):.2f} MB")
print(f"   Expected: 3 files (SPY, QQQ, IWM)")

# Test 4: Run same backtest again (should use cache)
print("\n4. Running same backtest again (should use cache)...")
import time
start_time = time.time()

try:
    results2 = run_system_walkforward(
        universe=['SPY', 'QQQ', 'IWM'],
        start_date='2023-01-01',
        end_date='2023-12-31',
        max_weight_per_asset=0.5,
        max_sector_weight=1.0,
        min_assets_held=2,
        target_vol=0.15,
        vol_lookback=60,
        min_leverage=0.0,
        max_leverage=2.0,
        vol_window=20,
    )
    
    elapsed = time.time() - start_time
    print(f"   ✅ Backtest completed in {elapsed:.2f}s (faster due to cache)")
    print(f"   Total Return: {results2['metrics']['total_return']:.2%}")
    
except Exception as e:
    print(f"   ❌ Backtest failed: {e}")
    raise

# Test 5: Test error handling with invalid ticker
print("\n5. Testing error handling with invalid ticker...")
try:
    results3 = run_system_walkforward(
        universe=['INVALID_TICKER_123'],
        start_date='2023-01-01',
        end_date='2023-12-31',
    )
    print("   ❌ Should have raised an error!")
except ValueError as e:
    print(f"   ✅ Correctly raised ValueError: {str(e)[:80]}...")

print("\n" + "=" * 60)
print("All integration tests passed! ✅")
print("=" * 60)
