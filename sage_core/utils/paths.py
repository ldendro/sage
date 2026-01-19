"""
Path management for Sage.

This module provides centralized path configuration for all data, cache,
and configuration directories. Using a single source of truth prevents
hardcoded paths scattered throughout the codebase.

All paths are relative to the project root and use pathlib.Path for
cross-platform compatibility.
"""

from pathlib import Path
from typing import Optional


# Project root directory (sage/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Cache directories
CACHE_DIR = PROJECT_ROOT / "cache"
CACHE_SYSTEMS_DIR = CACHE_DIR / "systems"

# Configuration directories
CONFIG_DIR = PROJECT_ROOT / "configs"
CONFIG_PRESETS_DIR = CONFIG_DIR / "presets"

# Documentation directories
DOCS_DIR = PROJECT_ROOT / "docs"


def ensure_dir(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Directory path to ensure exists
    
    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_processed_data_path(symbol: str) -> Path:
    """
    Get path to processed data file for a symbol.
    
    Args:
        symbol: Ticker symbol (e.g., "SPY")
    
    Returns:
        Path to processed parquet file
    """
    return PROCESSED_DATA_DIR / f"{symbol}.parquet"


def get_system_cache_dir(config_hash: str) -> Path:
    """
    Get cache directory for a specific system configuration.
    
    Args:
        config_hash: Hash of the system configuration
    
    Returns:
        Path to system cache directory
    """
    return CACHE_SYSTEMS_DIR / config_hash


def get_preset_config_path(preset_name: str) -> Path:
    """
    Get path to a preset configuration file.
    
    Args:
        preset_name: Name of preset (without .toml extension)
    
    Returns:
        Path to preset TOML file
    """
    if not preset_name.endswith(".toml"):
        preset_name = f"{preset_name}.toml"
    return CONFIG_PRESETS_DIR / preset_name


def list_processed_symbols() -> list[str]:
    """
    List all symbols with processed data available.
    
    Returns:
        List of ticker symbols (e.g., ["SPY", "QQQ", ...])
    """
    if not PROCESSED_DATA_DIR.exists():
        return []
    
    parquet_files = PROCESSED_DATA_DIR.glob("*.parquet")
    return sorted([f.stem for f in parquet_files])


def initialize_directories() -> None:
    """
    Initialize all required directories.
    
    This should be called explicitly during development setup or by the application
    at startup. NOT called on import to avoid PermissionError in read-only environments
    (e.g., site-packages, Docker containers, CI/CD).
    
    For normal usage, directories are created lazily via ensure_dir() when first accessed.
    """
    # Ensure all directories exist
    ensure_dir(RAW_DATA_DIR)
    ensure_dir(PROCESSED_DATA_DIR)
    ensure_dir(CACHE_SYSTEMS_DIR)
    ensure_dir(CONFIG_PRESETS_DIR)
    ensure_dir(DOCS_DIR)
    
    # Create .gitkeep files for empty directories
    for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, CACHE_SYSTEMS_DIR]:
        gitkeep = dir_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()


# NOTE: We do NOT call initialize_directories() on import to avoid PermissionError
# in read-only environments. Directories are created lazily when first accessed.
