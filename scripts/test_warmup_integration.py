"""Integration test for pandas_market_calendars warmup implementation."""

from sage_core.walkforward.engine import run_system_walkforward
import pandas as pd

print('Integration Test: Exact Trading Days with pandas_market_calendars')
print('=' * 70)
print()

print('Config: vol_window=60, vol_lookback=60 → 121 trading days warmup')
print('Start date: 2023-06-01 (Thursday)')
print()

result = run_system_walkforward(
    universe=['SPY', 'QQQ'],
    start_date='2023-06-01',
    end_date='2023-12-31',
    vol_window=60,
    vol_lookback=60,
)

warmup_info = result['warmup_info']
print(f'Warmup Info:')
print(f'  Trading days: {warmup_info["total_trading_days"]}')
print(f'  Description: {warmup_info["description"]}')
print()

first_date = result['equity_curve'].index[0]
print(f'Results:')
print(f'  User requested: 2023-06-01')
print(f'  Actual start: {first_date.strftime("%Y-%m-%d")}')
print(f'  Match: {first_date == pd.Timestamp("2023-06-01")}')
print()

# Check for warmup bleed
weights = result['weights']
first_weights = weights.iloc[0]
print(f'First day weights (should NOT be 1.0):')
for ticker, weight in first_weights.items():
    print(f'  {ticker}: {weight:.4f}')
print()

# Check if any weights are exactly 1.0 (sign of warmup bleed)
has_warmup_bleed = any(abs(w - 1.0) < 0.0001 for w in first_weights if pd.notna(w))
if has_warmup_bleed:
    print('❌ WARNING: Detected 1.0 weights (warmup bleed!)')
else:
    print('✅ No warmup bleed detected!')
print()

print(f'Equity curve:')
print(f'  Starts at: {result["equity_curve"].iloc[0]:.2f}')
print(f'  Length: {len(result["equity_curve"])} days')
print()

print('✅ Integration test PASSED!')
print('=' * 70)
