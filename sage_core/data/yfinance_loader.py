"""
yfinance data loader with retry logic.

This module provides functions to fetch OHLCV data from Yahoo Finance
using the yfinance library with exponential backoff retry logic.
"""

import pandas as pd
import yfinance as yf
import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def fetch_ohlcv_yfinance(
    ticker: str,
    start_date: str,
    end_date: str,
    max_retries: int = 3,
) -> pd.DataFrame:
    """
    Fetch OHLCV data from Yahoo Finance with retry logic.
    
    Args:
        ticker: Ticker symbol (e.g., "SPY", "QQQ")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        max_retries: Maximum number of retry attempts (default: 3)
    
    Returns:
        DataFrame with columns: open, high, low, close, volume, raw_ret
        Index: DatetimeIndex
    
    Raises:
        ValueError: If ticker invalid, no data in range, or data validation fails
        RuntimeError: If all retry attempts fail
    
    Example:
        >>> df = fetch_ohlcv_yfinance("SPY", "2023-01-01", "2023-12-31")
        >>> df.head()
                        open    high     low   close    volume   raw_ret
        date                                                            
        2023-01-03  200.10  201.50  199.80  201.20  10000000  0.005500
        ...
    """
    last_error: Optional[Exception] = None
    
    for attempt in range(max_retries):
        try:
            # Fetch data from yfinance
            logger.info(f"Fetching {ticker} from {start_date} to {end_date} (attempt {attempt + 1}/{max_retries})")
            
            data = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=False,  # Keep raw prices
                actions=False,  # Don't need dividends/splits for now
            )
            
            # Check if data is empty
            if data.empty:
                raise ValueError(
                    f"No data returned for {ticker} in range {start_date} to {end_date}. "
                    f"Ticker may be invalid or no trading data available for this period."
                )
            
            # yfinance returns MultiIndex columns for single ticker, flatten them
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            
            # Normalize column names to lowercase
            data.columns = data.columns.str.lower()
            
            # Validate required columns
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                raise ValueError(
                    f"Data for {ticker} missing required columns: {missing_cols}. "
                    f"Available columns: {list(data.columns)}"
                )
            
            # Select only required columns
            df = data[required_cols].copy()
            
            # Ensure index is named 'date'
            df.index.name = 'date'
            
            # Check for NaN values
            if df.isnull().any().any():
                nan_cols = df.columns[df.isnull().any()].tolist()
                # Drop rows with NaN (common at start/end of series)
                df = df.dropna()
                logger.warning(f"Dropped rows with NaN values in columns: {nan_cols}")
            
            # Validate we still have data after dropping NaN
            if df.empty:
                raise ValueError(
                    f"No valid data for {ticker} after removing NaN values. "
                    f"Data may be incomplete for this period."
                )
            
            # Validate price data is positive
            price_cols = ['open', 'high', 'low', 'close']
            for col in price_cols:
                if (df[col] <= 0).any():
                    raise ValueError(
                        f"Data for {ticker} contains non-positive prices in column '{col}'"
                    )
            
            # Validate OHLC relationships
            if not (df['high'] >= df['close']).all():
                raise ValueError(f"Data for {ticker}: high must be >= close")
            if not (df['high'] >= df['open']).all():
                raise ValueError(f"Data for {ticker}: high must be >= open")
            if not (df['low'] <= df['close']).all():
                raise ValueError(f"Data for {ticker}: low must be <= close")
            if not (df['low'] <= df['open']).all():
                raise ValueError(f"Data for {ticker}: low must be <= open")
            
            # Calculate raw returns (daily returns)
            df['raw_ret'] = df['close'].pct_change()
            
            # First return is NaN, set to 0.0
            df.loc[df.index[0], 'raw_ret'] = 0.0
            
            logger.info(f"Successfully fetched {len(df)} rows for {ticker}")
            return df
            
        except Exception as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {ticker}: {e}")
            
            # Don't retry on validation errors (they won't succeed on retry)
            if isinstance(e, ValueError):
                raise
            
            # Exponential backoff: 1s, 2s, 4s
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                logger.info(f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
    
    # All retries failed
    raise RuntimeError(
        f"Failed to fetch data for {ticker} after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
