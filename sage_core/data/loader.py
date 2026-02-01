"""
Data loading utilities for Sage.

This module provides functions to load market data from parquet files
and prepare it for backtesting.
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import re
import logging

from sage_core.utils import paths
from sage_core.data.yfinance_loader import fetch_ohlcv_yfinance
from sage_core.data.cache import load_from_cache, save_to_cache

logger = logging.getLogger(__name__)


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
    use_real_data: bool = True,
    use_cache: bool = True,
) -> Dict[str, pd.DataFrame]:
    """
    Load OHLCV data for a universe of symbols.
    
    By default, loads real market data from Yahoo Finance via yfinance.
    Falls back to parquet files if use_real_data=False or if real data fetch fails.
    
    Args:
        universe: List of ticker symbols (e.g., ["SPY", "QQQ"])
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        use_real_data: If True, fetch from yfinance; if False, load from parquet (default: True)
        use_cache: If True, use disk cache for real data (default: True)
    
    Returns:
        Dictionary mapping symbol to DataFrame with columns:
        - date (index): DatetimeIndex
        - open, high, low, close: float (prices)
        - volume: int
        - raw_ret: float (daily returns)
    
    Raises:
        FileNotFoundError: If data file missing for any symbol (parquet mode)
        ValueError: If date format invalid, date range invalid, or no data in range
    
    Example:
        >>> # Load real data from yfinance
        >>> data = load_universe(["SPY", "QQQ"], "2023-01-01", "2023-12-31")
        >>> 
        >>> # Load from parquet files (legacy)
        >>> data = load_universe(["SPY", "QQQ"], "2020-01-01", "2020-12-31", use_real_data=False)
    """
    # Validate inputs
    if not universe or len(universe) == 0:
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
    failed_symbols = []
    
    for symbol in universe:
        df: Optional[pd.DataFrame] = None
        
        if use_real_data:
            # Try to load from cache first
            if use_cache:
                df = load_from_cache(symbol, start_date, end_date)
                if df is not None:
                    logger.info(f"Loaded {symbol} from cache")
            
            # If cache miss, fetch from yfinance
            if df is None:
                try:
                    logger.info(f"Fetching {symbol} from yfinance")
                    df = fetch_ohlcv_yfinance(symbol, start_date, end_date)
                    
                    # Save to cache
                    if use_cache:
                        save_to_cache(symbol, start_date, end_date, df)
                    
                except Exception as e:
                    logger.warning(f"Failed to fetch {symbol} from yfinance: {e}")
                    # Try fallback to parquet
                    df = _load_from_parquet(symbol, start_date, end_date)
                    if df is None:
                        failed_symbols.append(symbol)
                        continue
        else:
            # Load from parquet files (legacy mode)
            df = _load_from_parquet(symbol, start_date, end_date)
            if df is None:
                failed_symbols.append(symbol)
                continue
        
        data[symbol] = df
    
    # Report failed symbols
    if failed_symbols:
        if use_real_data:
            raise ValueError(
                f"Failed to load data for symbols: {failed_symbols}\n"
                f"Check that ticker symbols are valid and have data for the specified date range."
            )
        else:
            raise FileNotFoundError(
                f"Data files not found for symbols: {failed_symbols}\n"
                f"Expected location: {paths.PROCESSED_DATA_DIR}\n"
                f"Run 'python scripts/generate_sample_data.py' to generate sample data."
            )
    
    return data


def _load_from_parquet(
    symbol: str,
    start_date: str,
    end_date: str
) -> Optional[pd.DataFrame]:
    """
    Load data from parquet file (internal helper).
    
    Args:
        symbol: Ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        DataFrame if successful, None if file not found or error
    """
    file_path = paths.get_processed_data_path(symbol)
    
    if not file_path.exists():
        return None
    
    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        logger.error(f"Error loading data for {symbol} from {file_path}: {e}")
        return None
    
    # Validate required columns
    required_cols = ['open', 'high', 'low', 'close', 'volume', 'raw_ret']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        logger.error(f"Data for {symbol} missing required columns: {missing_cols}")
        return None
    
    # Ensure index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        else:
            logger.error(f"Data for {symbol} must have DatetimeIndex or 'date' column")
            return None
    
    if df.index.dtype == 'object':
        df.index = pd.to_datetime(df.index)
    
    # Filter to date range
    start_ts = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    df_filtered = df.loc[start_ts:end_ts]
    
    if len(df_filtered) == 0:
        logger.error(
            f"No data for {symbol} in date range {start_date} to {end_date}. "
            f"Available range: {df.index.min().date()} to {df.index.max().date()}"
        )
        return None
    
    # Check for NaN values
    if df_filtered.isnull().any().any():
        nan_cols = df_filtered.columns[df_filtered.isnull().any()].tolist()
        logger.error(f"Data for {symbol} contains NaN values in columns: {nan_cols}")
        return None
    
    # Validate price data is positive
    price_cols = ['open', 'high', 'low', 'close']
    for col in price_cols:
        if (df_filtered[col] <= 0).any():
            logger.error(f"Data for {symbol} contains non-positive prices in column '{col}'")
            return None
    
    # Validate OHLC relationships
    if not (df_filtered['high'] >= df_filtered['close']).all():
        logger.error(f"Data for {symbol}: high must be >= close")
        return None
    if not (df_filtered['high'] >= df_filtered['open']).all():
        logger.error(f"Data for {symbol}: high must be >= open")
        return None
    if not (df_filtered['low'] <= df_filtered['close']).all():
        logger.error(f"Data for {symbol}: low must be <= close")
        return None
    if not (df_filtered['low'] <= df_filtered['open']).all():
        logger.error(f"Data for {symbol}: low must be <= open")
        return None
    
    return df_filtered


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
        Tuple of (start_date, end_date) as pd.Timestamp
    
    Raises:
        FileNotFoundError: If data file not found for symbol
    """
    file_path = paths.get_processed_data_path(symbol)
    
    if not file_path.exists():
        raise FileNotFoundError(
            f"Data file not found for {symbol}: {file_path}"
        )
    
    df = pd.read_parquet(file_path)
    
    # Apply same normalization as load_universe to handle string dates
    # and files saved with index=False (RangeIndex)
    if not isinstance(df.index, pd.DatetimeIndex):
        if 'date' in df.columns:
            # Coerce to datetime in case it's stored as string
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        else:
            raise ValueError(
                f"Data for {symbol} must have DatetimeIndex or 'date' column"
            )
    
    # Ensure index is datetime even if it was already the index
    # (handles case where index is object dtype)
    if df.index.dtype == 'object':
        df.index = pd.to_datetime(df.index)
    
    return df.index.min(), df.index.max()
