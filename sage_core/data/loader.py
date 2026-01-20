"""
Data loading utilities for Sage.

This module provides functions to load market data from parquet files
and prepare it for backtesting.
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict
import re

from sage_core.utils import paths


def validate_date_format(date_str: str) -> None:
    """
    Validate date string is in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
    
    Raises:
        ValueError: If date format is invalid
    """
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        raise ValueError(
            f"Invalid date format: '{date_str}'. "
            f"Expected YYYY-MM-DD format (e.g., '2020-01-01')"
        )


def load_universe(
    universe: List[str],
    start_date: str,
    end_date: str,
) -> Dict[str, pd.DataFrame]:
    """
    Load OHLCV data for a universe of symbols.
    
    Loads data from parquet files in data/processed/ directory.
    Each symbol must have a corresponding {symbol}.parquet file.
    
    Args:
        universe: List of ticker symbols (e.g., ["SPY", "QQQ"])
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Dictionary mapping symbol to DataFrame with columns:
        - date (index): DatetimeIndex
        - open, high, low, close: float (prices)
        - volume: int
        - raw_ret: float (daily returns)
    
    Raises:
        FileNotFoundError: If data file missing for any symbol
        ValueError: If date format invalid, date range invalid, or no data in range
    
    Example:
        >>> data = load_universe(["SPY", "QQQ"], "2020-01-01", "2020-12-31")
        >>> spy_df = data["SPY"]
        >>> spy_df.head()
                        open    high     low   close    volume   raw_ret
        date                                                            
        2020-01-02  200.10  201.50  199.80  201.20  10000000  0.005500
        ...
    """
    # Validate inputs
    if not universe:
        raise ValueError("Universe cannot be empty")
    
    validate_date_format(start_date)
    validate_date_format(end_date)
    
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    
    if start_ts >= end_ts:
        raise ValueError(
            f"start_date ({start_date}) must be before end_date ({end_date})"
        )
    
    # Load data for each symbol
    data = {}
    missing_symbols = []
    
    for symbol in universe:
        file_path = paths.get_processed_data_path(symbol)
        
        if not file_path.exists():
            missing_symbols.append(symbol)
            continue
        
        # Load parquet file
        try:
            df = pd.read_parquet(file_path)
        except Exception as e:
            raise ValueError(
                f"Error loading data for {symbol} from {file_path}: {e}"
            )
        
        # Validate required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume', 'raw_ret']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(
                f"Data for {symbol} missing required columns: {missing_cols}"
            )
        
        # Ensure index is DatetimeIndex
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns:
                df = df.set_index('date')
            else:
                raise ValueError(
                    f"Data for {symbol} must have DatetimeIndex or 'date' column"
                )
        
        # Filter to date range
        df_filtered = df.loc[start_ts:end_ts]
        
        if len(df_filtered) == 0:
            raise ValueError(
                f"No data for {symbol} in date range {start_date} to {end_date}. "
                f"Available range: {df.index.min().date()} to {df.index.max().date()}"
            )
        
        # Check for NaN values
        if df_filtered.isnull().any().any():
            nan_cols = df_filtered.columns[df_filtered.isnull().any()].tolist()
            raise ValueError(
                f"Data for {symbol} contains NaN values in columns: {nan_cols}"
            )
        
        # Validate price data is positive
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if (df_filtered[col] <= 0).any():
                raise ValueError(
                    f"Data for {symbol} contains non-positive prices in column '{col}'"
                )
        
        # Validate OHLC relationships
        if not (df_filtered['high'] >= df_filtered['close']).all():
            raise ValueError(f"Data for {symbol}: high must be >= close")
        if not (df_filtered['high'] >= df_filtered['open']).all():
            raise ValueError(f"Data for {symbol}: high must be >= open")
        if not (df_filtered['low'] <= df_filtered['close']).all():
            raise ValueError(f"Data for {symbol}: low must be <= close")
        if not (df_filtered['low'] <= df_filtered['open']).all():
            raise ValueError(f"Data for {symbol}: low must be <= open")
        
        data[symbol] = df_filtered
    
    # Report missing symbols
    if missing_symbols:
        raise FileNotFoundError(
            f"Data files not found for symbols: {missing_symbols}\n"
            f"Expected location: {paths.PROCESSED_DATA_DIR}\n"
            f"Run 'python scripts/generate_sample_data.py' to generate sample data."
        )
    
    return data


def get_available_symbols() -> List[str]:
    """
    Get list of symbols with available data.
    
    Returns:
        List of ticker symbols that have data files
    """
    return paths.list_processed_symbols()


def get_data_date_range(symbol: str) -> tuple[pd.Timestamp, pd.Timestamp]:
    """
    Get available date range for a symbol.
    
    Args:
        symbol: Ticker symbol
    
    Returns:
        Tuple of (start_date, end_date)
    
    Raises:
        FileNotFoundError: If data file not found for symbol
    """
    file_path = paths.get_processed_data_path(symbol)
    
    if not file_path.exists():
        raise FileNotFoundError(
            f"Data file not found for {symbol}: {file_path}"
        )
    
    df = pd.read_parquet(file_path)
    return df.index.min(), df.index.max()
