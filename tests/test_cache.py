"""Tests for data caching functionality."""

import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import time

from sage_core.data.cache import (
    get_cache_path,
    is_cache_valid,
    load_from_cache,
    save_to_cache,
    clear_cache,
    get_cache_size,
    purge_expired_cache,
    _parse_end_date_from_filename,
    CACHE_DIR
)


@pytest.fixture
def sample_data():
    """Create sample OHLCV data for testing."""
    return pd.DataFrame({
        'open': [100.0, 101.0, 102.0],
        'high': [101.0, 102.0, 103.0],
        'low': [99.0, 100.0, 101.0],
        'close': [100.5, 101.5, 102.5],
        'volume': [1000000, 1100000, 1200000],
        'raw_ret': [0.0, 0.01, 0.01],
    }, index=pd.date_range('2023-01-01', periods=3, freq='D', name='date'))


@pytest.fixture(autouse=True)
def cleanup_cache():
    """Clean up cache before and after each test."""
    clear_cache()
    yield
    clear_cache()


class TestCachePath:
    """Tests for cache path generation."""
    
    def test_get_cache_path(self):
        """Test cache path generation."""
        path = get_cache_path("SPY", "2023-01-01", "2023-12-31")
        
        assert isinstance(path, Path)
        assert path.parent == CACHE_DIR
        assert path.name == "SPY_2023-01-01_2023-12-31.parquet"
    
    def test_cache_dir_created(self):
        """Test that cache directory is created if it doesn't exist."""
        # Remove cache dir if it exists
        if CACHE_DIR.exists():
            for file in CACHE_DIR.glob("*.parquet"):
                file.unlink()
            CACHE_DIR.rmdir()
        
        # Get cache path should create directory
        path = get_cache_path("SPY", "2023-01-01", "2023-12-31")
        
        assert CACHE_DIR.exists()
        assert CACHE_DIR.is_dir()


class TestCacheValidation:
    """Tests for cache validation."""
    
    def test_is_cache_valid_nonexistent(self):
        """Test validation of nonexistent cache file."""
        path = get_cache_path("SPY", "2023-01-01", "2023-12-31")
        assert not is_cache_valid(path, "2023-12-31")
    
    def test_is_cache_valid_fresh(self, sample_data):
        """Test validation of fresh cache file."""
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        path = get_cache_path("SPY", "2023-01-01", "2023-12-31")
        
        assert is_cache_valid(path, "2023-12-31")
    
    def test_is_cache_valid_expired_historical(self, sample_data):
        """Test validation of expired historical cache."""
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        path = get_cache_path("SPY", "2023-01-01", "2023-12-31")
        
        # Modify file timestamp to be 2 days old
        old_time = (datetime.now() - timedelta(days=2)).timestamp()
        path.touch()
        import os
        os.utime(path, (old_time, old_time))
        
        assert not is_cache_valid(path, "2023-12-31")


class TestCacheOperations:
    """Tests for cache save/load operations."""
    
    def test_save_and_load_cache(self, sample_data):
        """Test saving and loading data from cache."""
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        loaded_data = load_from_cache("SPY", "2023-01-01", "2023-12-31")
        
        assert loaded_data is not None
        assert len(loaded_data) == len(sample_data)
        # Compare values without checking frequency attribute
        pd.testing.assert_frame_equal(loaded_data, sample_data, check_freq=False)
    
    def test_load_from_cache_miss(self):
        """Test loading from cache when file doesn't exist."""
        loaded_data = load_from_cache("SPY", "2023-01-01", "2023-12-31")
        assert loaded_data is None
    
    def test_load_from_cache_expired(self, sample_data):
        """Test loading from expired cache returns None."""
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        path = get_cache_path("SPY", "2023-01-01", "2023-12-31")
        
        # Make cache expired
        old_time = (datetime.now() - timedelta(days=2)).timestamp()
        import os
        os.utime(path, (old_time, old_time))
        
        loaded_data = load_from_cache("SPY", "2023-01-01", "2023-12-31")
        assert loaded_data is None


class TestCacheManagement:
    """Tests for cache management operations."""
    
    def test_clear_cache_all(self, sample_data):
        """Test clearing all cache."""
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        save_to_cache("QQQ", "2023-01-01", "2023-12-31", sample_data)
        
        deleted = clear_cache()
        
        assert deleted == 2
        assert load_from_cache("SPY", "2023-01-01", "2023-12-31") is None
        assert load_from_cache("QQQ", "2023-01-01", "2023-12-31") is None
    
    def test_clear_cache_specific_ticker(self, sample_data):
        """Test clearing cache for specific ticker."""
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        save_to_cache("QQQ", "2023-01-01", "2023-12-31", sample_data)
        
        deleted = clear_cache("SPY")
        
        assert deleted == 1
        assert load_from_cache("SPY", "2023-01-01", "2023-12-31") is None
        assert load_from_cache("QQQ", "2023-01-01", "2023-12-31") is not None
    
    def test_clear_cache_empty(self):
        """Test clearing empty cache."""
        deleted = clear_cache()
        assert deleted == 0
    
    def test_get_cache_size(self, sample_data):
        """Test getting cache statistics."""
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        save_to_cache("QQQ", "2023-01-01", "2023-12-31", sample_data)
        
        count, size = get_cache_size()
        
        assert count == 2
        assert size > 0  # Should have some size
    
    def test_get_cache_size_empty(self):
        """Test getting cache size when empty."""
        count, size = get_cache_size()
        assert count == 0
        assert size == 0


class TestParseEndDateFromFilename:
    """Tests for _parse_end_date_from_filename helper function."""
    
    def test_parse_valid_filename(self):
        """Test parsing valid cache filename."""
        path = CACHE_DIR / "SPY_2023-01-01_2023-12-31.parquet"
        end_date = _parse_end_date_from_filename(path)
        assert end_date == "2023-12-31"
    
    def test_parse_different_ticker(self):
        """Test parsing with different ticker symbols."""
        path = CACHE_DIR / "AAPL_2020-01-01_2020-06-30.parquet"
        end_date = _parse_end_date_from_filename(path)
        assert end_date == "2020-06-30"
    
    def test_parse_invalid_format_too_few_parts(self):
        """Test parsing filename with too few parts."""
        path = CACHE_DIR / "SPY_2023-01-01.parquet"
        end_date = _parse_end_date_from_filename(path)
        assert end_date is None
    
    def test_parse_invalid_format_no_underscores(self):
        """Test parsing filename with no underscores."""
        path = CACHE_DIR / "invalid.parquet"
        end_date = _parse_end_date_from_filename(path)
        assert end_date is None
    
    def test_parse_with_underscores_in_ticker(self):
        """Test parsing filename where ticker contains underscores."""
        # This should still work because we use rsplit with maxsplit=2
        path = CACHE_DIR / "BRK_B_2023-01-01_2023-12-31.parquet"
        end_date = _parse_end_date_from_filename(path)
        assert end_date == "2023-12-31"


class TestPurgeExpiredCache:
    """Tests for purge_expired_cache function."""
    
    def test_purge_expired_cache_empty_dir(self):
        """Test purging when cache directory is empty."""
        deleted = purge_expired_cache()
        assert deleted == 0
    
    def test_purge_expired_cache_no_expired_files(self, sample_data):
        """Test purging when all files are fresh."""
        # Create fresh cache files
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        save_to_cache("QQQ", "2023-01-01", "2023-12-31", sample_data)
        
        deleted = purge_expired_cache()
        
        assert deleted == 0
        # Files should still exist
        assert load_from_cache("SPY", "2023-01-01", "2023-12-31") is not None
        assert load_from_cache("QQQ", "2023-01-01", "2023-12-31") is not None
    
    def test_purge_expired_cache_all_expired(self, sample_data):
        """Test purging when all files are expired."""
        # Create cache files
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        save_to_cache("QQQ", "2023-01-01", "2023-12-31", sample_data)
        
        # Make them expired (2 days old)
        import os
        old_time = (datetime.now() - timedelta(days=2)).timestamp()
        for file in CACHE_DIR.glob("*.parquet"):
            os.utime(file, (old_time, old_time))
        
        deleted = purge_expired_cache()
        
        assert deleted == 2
        # Files should be deleted
        count, _ = get_cache_size()
        assert count == 0
    
    def test_purge_expired_cache_mixed(self, sample_data):
        """Test purging with mix of fresh and expired files."""
        # Create cache files
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        save_to_cache("QQQ", "2023-01-01", "2023-12-31", sample_data)
        save_to_cache("IWM", "2023-01-01", "2023-12-31", sample_data)
        
        # Make SPY and QQQ expired, keep IWM fresh
        import os
        old_time = (datetime.now() - timedelta(days=2)).timestamp()
        
        spy_path = get_cache_path("SPY", "2023-01-01", "2023-12-31")
        qqq_path = get_cache_path("QQQ", "2023-01-01", "2023-12-31")
        
        os.utime(spy_path, (old_time, old_time))
        os.utime(qqq_path, (old_time, old_time))
        
        deleted = purge_expired_cache()
        
        assert deleted == 2
        # Only IWM should remain
        count, _ = get_cache_size()
        assert count == 1
        assert load_from_cache("IWM", "2023-01-01", "2023-12-31") is not None
    
    def test_purge_expired_cache_with_malformed_filenames(self, sample_data):
        """Test purging skips files with malformed names."""
        # Create valid cache file
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        
        # Create malformed file
        malformed_path = CACHE_DIR / "malformed.parquet"
        sample_data.to_parquet(malformed_path)
        
        # Make SPY expired
        import os
        old_time = (datetime.now() - timedelta(days=2)).timestamp()
        spy_path = get_cache_path("SPY", "2023-01-01", "2023-12-31")
        os.utime(spy_path, (old_time, old_time))
        
        deleted = purge_expired_cache()
        
        # Should delete SPY but skip malformed file
        assert deleted == 1
        assert not spy_path.exists()
        assert malformed_path.exists()  # Malformed file should remain
        
        # Clean up malformed file
        malformed_path.unlink()
    
    def test_purge_expired_cache_called_on_load(self, sample_data):
        """Test that purge is called opportunistically during load_from_cache."""
        # Create two cache files
        save_to_cache("SPY", "2023-01-01", "2023-12-31", sample_data)
        save_to_cache("QQQ", "2023-01-01", "2023-12-31", sample_data)
        
        # Make QQQ expired
        import os
        old_time = (datetime.now() - timedelta(days=2)).timestamp()
        qqq_path = get_cache_path("QQQ", "2023-01-01", "2023-12-31")
        os.utime(qqq_path, (old_time, old_time))
        
        # Load SPY (should trigger purge)
        result = load_from_cache("SPY", "2023-01-01", "2023-12-31")
        
        # SPY should be loaded successfully
        assert result is not None
        
        # QQQ should have been purged
        count, _ = get_cache_size()
        assert count == 1
        assert not qqq_path.exists()
    
    def test_purge_expired_cache_recent_data_expiry(self, sample_data):
        """Test that recent data (last 7 days) has shorter expiry."""
        # Get a date within last 7 days
        recent_end_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        
        # Create cache file with recent end date
        save_to_cache("SPY", start_date, recent_end_date, sample_data)
        
        # Make it 2 hours old (should be expired since recent data expires in 1 hour)
        import os
        old_time = (datetime.now() - timedelta(hours=2)).timestamp()
        spy_path = get_cache_path("SPY", start_date, recent_end_date)
        os.utime(spy_path, (old_time, old_time))
        
        deleted = purge_expired_cache()
        
        # Should be deleted (2 hours > 1 hour expiry for recent data)
        assert deleted == 1
        assert not spy_path.exists()
    
    def test_purge_expired_cache_nonexistent_dir(self):
        """Test purging when cache directory doesn't exist."""
        # Remove cache directory
        if CACHE_DIR.exists():
            for file in CACHE_DIR.glob("*.parquet"):
                file.unlink()
            CACHE_DIR.rmdir()
        
        deleted = purge_expired_cache()
        assert deleted == 0
