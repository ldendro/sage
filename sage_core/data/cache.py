"""
Disk caching for market data.

This module provides functions to cache OHLCV data to disk to minimize
API calls and improve performance.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Cache directory
CACHE_DIR = Path.home() / ".sage" / "cache"

# Cache expiration times
CACHE_EXPIRY_HISTORICAL = timedelta(days=1)  # 24 hours for historical data
CACHE_EXPIRY_RECENT = timedelta(hours=1)  # 1 hour for recent data (last 7 days)


def _parse_end_date_from_filename(cache_path: Path) -> Optional[str]:
    """
    Extract end_date from a cache filename like TICKER_START_END.parquet.
    """
    stem = cache_path.stem  # strip .parquet
    parts = stem.rsplit("_", 2)
    if len(parts) != 3:
        return None
    return parts[2]


def get_cache_path(ticker: str, start_date: str, end_date: str) -> Path:
    """
    Get cache file path for ticker and date range.
    
    Args:
        ticker: Ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        Path to cache file
    
    Example:
        >>> path = get_cache_path("SPY", "2023-01-01", "2023-12-31")
        >>> print(path)
        /Users/username/.sage/cache/SPY_2023-01-01_2023-12-31.parquet
    """
    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create filename from ticker and date range
    filename = f"{ticker}_{start_date}_{end_date}.parquet"
    return CACHE_DIR / filename


def is_cache_valid(cache_path: Path, end_date: str) -> bool:
    """
    Check if cache file is valid (exists and not expired).
    
    Args:
        cache_path: Path to cache file
        end_date: End date of data range (YYYY-MM-DD)
    
    Returns:
        True if cache is valid, False otherwise
    """
    if not cache_path.exists():
        return False
    
    # Get file modification time
    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
    now = datetime.now()
    age = now - mtime
    
    # Check if end_date is recent (within last 7 days)
    end_ts = pd.Timestamp(end_date)
    is_recent = (pd.Timestamp.now() - end_ts).days <= 7
    
    # Use different expiry times for recent vs historical data
    expiry = CACHE_EXPIRY_RECENT if is_recent else CACHE_EXPIRY_HISTORICAL
    
    if age > expiry:
        logger.debug(f"Cache expired: {cache_path.name} (age: {age}, expiry: {expiry})")
        return False
    
    return True


def load_from_cache(
    ticker: str,
    start_date: str,
    end_date: str
) -> Optional[pd.DataFrame]:
    """
    Load data from cache if available and valid.
    
    Args:
        ticker: Ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
    
    Returns:
        DataFrame if cache hit, None if cache miss
    
    Example:
        >>> df = load_from_cache("SPY", "2023-01-01", "2023-12-31")
        >>> if df is not None:
        ...     print(f"Cache hit! {len(df)} rows")
        ... else:
        ...     print("Cache miss")
    """
    # Opportunistically clean expired entries to avoid unbounded cache growth
    purge_expired_cache()

    cache_path = get_cache_path(ticker, start_date, end_date)
    
    if not is_cache_valid(cache_path, end_date):
        return None
    
    try:
        df = pd.read_parquet(cache_path)
        logger.info(f"Cache hit: {ticker} ({len(df)} rows)")
        return df
    except Exception as e:
        logger.warning(f"Failed to load cache for {ticker}: {e}")
        return None


def save_to_cache(
    ticker: str,
    start_date: str,
    end_date: str,
    data: pd.DataFrame
) -> None:
    """
    Save data to cache.
    
    Args:
        ticker: Ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        data: DataFrame to cache
    
    Example:
        >>> df = fetch_ohlcv_yfinance("SPY", "2023-01-01", "2023-12-31")
        >>> save_to_cache("SPY", "2023-01-01", "2023-12-31", df)
    """
    cache_path = get_cache_path(ticker, start_date, end_date)
    
    try:
        data.to_parquet(cache_path)
        logger.info(f"Saved to cache: {ticker} ({len(data)} rows)")
    except Exception as e:
        logger.warning(f"Failed to save cache for {ticker}: {e}")


def purge_expired_cache() -> int:
    """
    Delete expired cache files across all tickers/date ranges.

    Returns:
        Number of files deleted
    """
    if not CACHE_DIR.exists():
        return 0

    deleted = 0

    for file in CACHE_DIR.glob("*.parquet"):
        end_date = _parse_end_date_from_filename(file)
        if not end_date:
            logger.debug(f"Skipping cache file with unexpected name: {file.name}")
            continue

        try:
            if not is_cache_valid(file, end_date):
                file.unlink()
                deleted += 1
                logger.info(f"Deleted expired cache file: {file.name}")
        except Exception as e:
            logger.warning(f"Failed to evaluate/delete {file.name}: {e}")

    return deleted


def clear_cache(ticker: Optional[str] = None) -> int:
    """
    Clear cache for specific ticker or all tickers.
    
    Args:
        ticker: Ticker symbol to clear, or None to clear all
    
    Returns:
        Number of files deleted
    
    Example:
        >>> # Clear cache for SPY
        >>> count = clear_cache("SPY")
        >>> print(f"Deleted {count} cache files")
        
        >>> # Clear all cache
        >>> count = clear_cache()
        >>> print(f"Deleted {count} cache files")
    """
    if not CACHE_DIR.exists():
        return 0
    
    deleted = 0
    
    if ticker is None:
        # Clear all cache files
        for file in CACHE_DIR.glob("*.parquet"):
            try:
                file.unlink()
                deleted += 1
                logger.info(f"Deleted cache file: {file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete {file.name}: {e}")
    else:
        # Clear cache for specific ticker
        for file in CACHE_DIR.glob(f"{ticker}_*.parquet"):
            try:
                file.unlink()
                deleted += 1
                logger.info(f"Deleted cache file: {file.name}")
            except Exception as e:
                logger.warning(f"Failed to delete {file.name}: {e}")
    
    return deleted


def get_cache_size() -> tuple[int, int]:
    """
    Get cache statistics.
    
    Returns:
        Tuple of (number of files, total size in bytes)
    
    Example:
        >>> count, size_bytes = get_cache_size()
        >>> size_mb = size_bytes / (1024 * 1024)
        >>> print(f"Cache: {count} files, {size_mb:.2f} MB")
    """
    if not CACHE_DIR.exists():
        return 0, 0
    
    files = list(CACHE_DIR.glob("*.parquet"))
    count = len(files)
    total_size = sum(f.stat().st_size for f in files)
    
    return count, total_size
