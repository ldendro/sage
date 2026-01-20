"""
Generate sample market data for testing.

This script creates realistic OHLCV data for the default universe using
geometric Brownian motion. Data is saved as parquet files in data/processed/.

Usage:
    python scripts/generate_sample_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sage_core.utils import constants, paths


def generate_ohlcv_data(
    symbol: str,
    start_date: str,
    end_date: str,
    initial_price: float = 100.0,
    annual_vol: float = 0.20,
    annual_drift: float = 0.08,
    seed: int = None,
) -> pd.DataFrame:
    """
    Generate realistic OHLCV data using geometric Brownian motion.
    
    Args:
        symbol: Ticker symbol
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        initial_price: Starting price
        annual_vol: Annualized volatility (e.g., 0.20 = 20%)
        annual_drift: Annualized drift (e.g., 0.08 = 8%)
        seed: Random seed for reproducibility
    
    Returns:
        DataFrame with columns: date (index), open, high, low, close, volume, raw_ret
    """
    # Set seed for reproducibility
    if seed is not None:
        np.random.seed(seed)
    
    # Generate business days
    dates = pd.bdate_range(start=start_date, end=end_date)
    n_days = len(dates)
    
    # Daily parameters from annual
    daily_vol = annual_vol / np.sqrt(252)
    daily_drift = annual_drift / 252
    
    # Generate returns using GBM
    returns = np.random.normal(daily_drift, daily_vol, size=n_days)
    
    # Generate close prices
    close_prices = initial_price * np.exp(np.cumsum(returns))
    
    # Generate OHLC from close
    # High/Low are close +/- random percentage
    intraday_range = np.random.uniform(0.005, 0.02, size=n_days)  # 0.5% to 2%
    
    high_prices = close_prices * (1 + intraday_range * np.random.uniform(0.3, 1.0, size=n_days))
    low_prices = close_prices * (1 - intraday_range * np.random.uniform(0.3, 1.0, size=n_days))
    
    # Open is between previous close and current close
    open_prices = np.zeros(n_days)
    open_prices[0] = initial_price
    for i in range(1, n_days):
        open_prices[i] = close_prices[i-1] * (1 + np.random.normal(0, daily_vol * 0.5))
    
    # Ensure OHLC relationships: high >= max(open, close), low <= min(open, close)
    high_prices = np.maximum(high_prices, np.maximum(open_prices, close_prices))
    low_prices = np.minimum(low_prices, np.minimum(open_prices, close_prices))
    
    # Generate volume (log-normal distribution)
    base_volume = 1_000_000
    volume = np.random.lognormal(
        mean=np.log(base_volume),
        sigma=0.5,
        size=n_days
    ).astype(int)
    
    # Calculate raw returns
    raw_ret = np.zeros(n_days)
    raw_ret[1:] = close_prices[1:] / close_prices[:-1] - 1.0
    
    # Create DataFrame
    df = pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume,
        'raw_ret': raw_ret,
    }, index=dates)
    
    df.index.name = 'date'
    
    return df


def main():
    """Generate sample data for all symbols in default universe."""
    print("Generating sample market data...")
    print(f"Universe: {constants.DEFAULT_UNIVERSE}")
    print(f"Date range: {constants.DEFAULT_START_DATE} to {constants.DEFAULT_END_DATE}")
    
    # Ensure output directory exists
    paths.ensure_dir(paths.PROCESSED_DATA_DIR)
    
    # Symbol-specific parameters for variety
    symbol_params = {
        # Broad market - moderate vol
        "SPY": {"annual_vol": 0.16, "annual_drift": 0.10, "initial_price": 200.0},
        "QQQ": {"annual_vol": 0.20, "annual_drift": 0.12, "initial_price": 250.0},
        "IWM": {"annual_vol": 0.22, "annual_drift": 0.08, "initial_price": 150.0},
        
        # Defensive sectors - low vol
        "XLU": {"annual_vol": 0.14, "annual_drift": 0.06, "initial_price": 60.0},
        "XLV": {"annual_vol": 0.15, "annual_drift": 0.08, "initial_price": 90.0},
        "XLP": {"annual_vol": 0.13, "annual_drift": 0.07, "initial_price": 55.0},
        
        # Cyclical sectors - moderate vol
        "XLF": {"annual_vol": 0.20, "annual_drift": 0.09, "initial_price": 25.0},
        "XLI": {"annual_vol": 0.18, "annual_drift": 0.10, "initial_price": 70.0},
        
        # Volatile sectors - high vol
        "XLE": {"annual_vol": 0.28, "annual_drift": 0.05, "initial_price": 50.0},
        "XLK": {"annual_vol": 0.22, "annual_drift": 0.14, "initial_price": 100.0},
        "XLY": {"annual_vol": 0.19, "annual_drift": 0.11, "initial_price": 120.0},
        "XLB": {"annual_vol": 0.21, "annual_drift": 0.08, "initial_price": 65.0},
    }
    
    # Generate data for each symbol
    for i, symbol in enumerate(constants.DEFAULT_UNIVERSE):
        params = symbol_params.get(symbol, {
            "annual_vol": 0.20,
            "annual_drift": 0.08,
            "initial_price": 100.0
        })
        
        print(f"  Generating {symbol}... ", end="")
        
        df = generate_ohlcv_data(
            symbol=symbol,
            start_date=constants.DEFAULT_START_DATE,
            end_date=constants.DEFAULT_END_DATE,
            seed=42 + i,  # Different seed per symbol
            **params
        )
        
        # Save to parquet
        output_path = paths.get_processed_data_path(symbol)
        df.to_parquet(output_path)
        
        print(f"✓ ({len(df)} days, {df['close'].iloc[0]:.2f} → {df['close'].iloc[-1]:.2f})")
    
    print(f"\n✅ Generated data for {len(constants.DEFAULT_UNIVERSE)} symbols")
    print(f"📁 Saved to: {paths.PROCESSED_DATA_DIR}")


if __name__ == "__main__":
    main()
