"""
Tests for utility modules (paths and constants).
"""

import pytest
from pathlib import Path
from sage_core.utils import paths, constants


class TestPaths:
    """Tests for paths module."""
    
    def test_project_root_exists(self):
        """Test that project root is correctly identified."""
        assert paths.PROJECT_ROOT.exists()
        assert paths.PROJECT_ROOT.is_dir()
        # Should contain pyproject.toml
        assert (paths.PROJECT_ROOT / "pyproject.toml").exists()
    
    def test_data_directories_exist(self):
        """Test that data directories are created."""
        assert paths.DATA_DIR.exists()
        assert paths.RAW_DATA_DIR.exists()
        assert paths.PROCESSED_DATA_DIR.exists()
    
    def test_cache_directories_exist(self):
        """Test that cache directories are created."""
        assert paths.CACHE_DIR.exists()
        assert paths.CACHE_SYSTEMS_DIR.exists()
    
    def test_config_directories_exist(self):
        """Test that config directories are created."""
        assert paths.CONFIG_DIR.exists()
        assert paths.CONFIG_PRESETS_DIR.exists()
    
    def test_ensure_dir(self):
        """Test ensure_dir creates directories."""
        test_dir = paths.CACHE_DIR / "test_subdir"
        
        # Clean up if exists
        if test_dir.exists():
            test_dir.rmdir()
        
        # Create directory
        result = paths.ensure_dir(test_dir)
        assert result == test_dir
        assert test_dir.exists()
        
        # Should be idempotent
        result2 = paths.ensure_dir(test_dir)
        assert result2 == test_dir
        
        # Clean up
        test_dir.rmdir()
    
    def test_get_processed_data_path(self):
        """Test processed data path generation."""
        path = paths.get_processed_data_path("SPY")
        assert path == paths.PROCESSED_DATA_DIR / "SPY.parquet"
        assert path.suffix == ".parquet"
    
    def test_get_system_cache_dir(self):
        """Test system cache directory generation."""
        config_hash = "abc123"
        cache_dir = paths.get_system_cache_dir(config_hash)
        assert cache_dir == paths.CACHE_SYSTEMS_DIR / "abc123"
    
    def test_get_preset_config_path(self):
        """Test preset config path generation."""
        # Without .toml extension
        path1 = paths.get_preset_config_path("baseline")
        assert path1 == paths.CONFIG_PRESETS_DIR / "baseline.toml"
        
        # With .toml extension
        path2 = paths.get_preset_config_path("baseline.toml")
        assert path2 == paths.CONFIG_PRESETS_DIR / "baseline.toml"
    
    def test_list_processed_symbols_empty(self):
        """Test listing symbols when directory is empty."""
        # Should return empty list or list of existing symbols
        symbols = paths.list_processed_symbols()
        assert isinstance(symbols, list)


class TestConstants:
    """Tests for constants module."""
    
    def test_default_universe_size(self):
        """Test default universe has 12 symbols."""
        assert len(constants.DEFAULT_UNIVERSE) == 12
    
    def test_default_universe_contents(self):
        """Test default universe contains expected symbols."""
        expected_broad = ["SPY", "QQQ", "IWM"]
        expected_sectors = ["XLU", "XLV", "XLP", "XLF", "XLE", "XLI", "XLK", "XLY", "XLB"]
        
        for symbol in expected_broad:
            assert symbol in constants.DEFAULT_UNIVERSE
        
        for symbol in expected_sectors:
            assert symbol in constants.DEFAULT_UNIVERSE
    
    def test_sector_map_coverage(self):
        """Test sector map covers all default universe symbols."""
        for symbol in constants.DEFAULT_UNIVERSE:
            assert symbol in constants.SECTOR_MAP
    
    def test_sector_map_broad_market(self):
        """Test broad market ETFs have unique sectors."""
        broad_sectors = [
            constants.SECTOR_MAP["SPY"],
            constants.SECTOR_MAP["QQQ"],
            constants.SECTOR_MAP["IWM"],
        ]
        # Each should be unique
        assert len(broad_sectors) == len(set(broad_sectors))
    
    def test_default_dates(self):
        """Test default date range."""
        assert constants.DEFAULT_START_DATE == "2015-01-01"
        assert constants.DEFAULT_END_DATE == "2025-12-31"
    
    def test_default_hard_meta_params(self):
        """Test default hard meta parameters exist."""
        params = constants.DEFAULT_HARD_META_PARAMS
        assert "trend_mom60_min" in params
        assert "trend_mom20_min" in params
        assert "meanrev_mom20_max" in params
        assert "meanrev_dd60_max" in params
        assert "meanrev_vol20_max" in params
    
    def test_default_gate_params(self):
        """Test default gate parameters exist."""
        params = constants.DEFAULT_GATE_PARAMS
        assert "max_vol_20d" in params
        assert "max_drawdown_60d" in params
        assert "min_mom_60d" in params
    
    def test_risk_cap_defaults(self):
        """Test risk cap defaults."""
        assert constants.DEFAULT_MAX_WEIGHT_PER_ASSET == 0.20
        assert constants.DEFAULT_MAX_SECTOR_WEIGHT == 0.40
        assert constants.DEFAULT_MIN_ASSETS_HELD == 6
    
    def test_vol_targeting_defaults(self):
        """Test volatility targeting defaults."""
        assert constants.DEFAULT_TARGET_VOL_ANNUAL == 0.10
        assert constants.DEFAULT_VOL_LOOKBACK == 20
        assert constants.DEFAULT_MAX_LEVERAGE == 1.0
    
    def test_get_sector_for_symbol(self):
        """Test sector lookup for symbols."""
        assert constants.get_sector_for_symbol("SPY") == "broad_sp500"
        assert constants.get_sector_for_symbol("XLF") == "financials"
        assert constants.get_sector_for_symbol("UNKNOWN") == "unknown"
    
    def test_validate_universe_valid(self):
        """Test universe validation with valid universe."""
        valid_universe = ["SPY", "QQQ", "XLF"]
        assert constants.validate_universe(valid_universe) is True
    
    def test_validate_universe_invalid(self):
        """Test universe validation with invalid symbols."""
        invalid_universe = ["SPY", "UNKNOWN_SYMBOL"]
        assert constants.validate_universe(invalid_universe) is False
    
    def test_get_missing_sectors(self):
        """Test getting missing sector mappings."""
        universe = ["SPY", "QQQ", "UNKNOWN1", "UNKNOWN2"]
        missing = constants.get_missing_sectors(universe)
        assert missing == ["UNKNOWN1", "UNKNOWN2"]
        
        # Valid universe should have no missing
        valid_universe = ["SPY", "QQQ"]
        missing_valid = constants.get_missing_sectors(valid_universe)
        assert missing_valid == []
