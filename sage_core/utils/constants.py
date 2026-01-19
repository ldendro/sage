"""
Constants and default values for Sage.

This module provides default configurations, universes, and mappings
used throughout the system. Centralizing these values makes it easy
to maintain consistency and update defaults as needed.
"""

from typing import Dict, List


# Default universe (12 symbols: 3 broad market ETFs + 9 sector ETFs)
DEFAULT_UNIVERSE: List[str] = [
    # Broad market ETFs
    "SPY",   # S&P 500
    "QQQ",   # Nasdaq 100
    "IWM",   # Russell 2000
    
    # Sector ETFs
    "XLU",   # Utilities
    "XLV",   # Healthcare
    "XLP",   # Consumer Staples
    "XLF",   # Financials
    "XLE",   # Energy
    "XLI",   # Industrials
    "XLK",   # Technology
    "XLY",   # Consumer Discretionary
    "XLB",   # Materials
]


# Sector mapping for risk caps
# Maps ticker symbols to sector categories
SECTOR_MAP: Dict[str, str] = {
    # Broad market (each gets its own "sector" to allow independent caps)
    "SPY": "broad_sp500",
    "QQQ": "broad_nasdaq",
    "IWM": "broad_small_cap",
    
    # Sector ETFs (grouped by actual sector)
    "XLU": "utilities",
    "XLV": "healthcare",
    "XLP": "consumer_staples",
    "XLF": "financials",
    "XLE": "energy",
    "XLI": "industrials",
    "XLK": "technology",
    "XLY": "consumer_discretionary",
    "XLB": "materials",
}


# Default date range for backtests
DEFAULT_START_DATE = "2015-01-01"
DEFAULT_END_DATE = "2025-12-31"


# Default meta allocation parameters (from Phase 2 HARD_PARAMS_TIGHT)
DEFAULT_HARD_META_PARAMS: Dict[str, float] = {
    "trend_mom60_min": 0.0,       # Minimum 60-day momentum for trend
    "trend_mom20_min": -0.005,    # Minimum 20-day momentum for trend
    "meanrev_mom20_max": -0.025,  # Maximum 20-day momentum for mean reversion (negative)
    "meanrev_dd60_max": -0.03,    # Maximum 60-day drawdown for mean reversion
    "meanrev_vol20_max": 0.40,    # Maximum 20-day volatility for mean reversion
}


# Default gate parameters (regime filters)
DEFAULT_GATE_PARAMS: Dict[str, float] = {
    "max_vol_20d": 0.50,          # Maximum 20-day volatility to allow trading
    "max_drawdown_60d": -0.15,    # Maximum 60-day drawdown to allow trading
    "min_mom_60d": -0.10,         # Minimum 60-day momentum to allow trading
}


# Risk cap defaults
DEFAULT_MAX_WEIGHT_PER_ASSET = 0.20   # 20% max per asset
DEFAULT_MAX_SECTOR_WEIGHT = 0.40      # 40% max per sector
DEFAULT_MIN_ASSETS_HELD = 6           # Minimum 6 assets


# Volatility targeting defaults
DEFAULT_TARGET_VOL_ANNUAL = 0.10      # 10% annual volatility target
DEFAULT_VOL_LOOKBACK = 20             # 20-day lookback for realized vol
DEFAULT_MAX_LEVERAGE = 1.0            # No leverage by default


# Strategy defaults
DEFAULT_TREND_LOOKBACK = 60           # 60-day lookback for trend features
DEFAULT_MEANREV_LOOKBACK = 20         # 20-day lookback for mean reversion


# Allocator defaults
DEFAULT_ALLOCATOR_LOOKBACK = 126      # ~6 months for covariance estimation


def get_sector_for_symbol(symbol: str) -> str:
    """
    Get sector for a given symbol.
    
    Args:
        symbol: Ticker symbol
    
    Returns:
        Sector name, or "unknown" if not in SECTOR_MAP
    """
    return SECTOR_MAP.get(symbol, "unknown")


def validate_universe(universe: List[str]) -> bool:
    """
    Validate that all symbols in universe have sector mappings.
    
    Args:
        universe: List of ticker symbols
    
    Returns:
        True if all symbols have sector mappings, False otherwise
    """
    return all(symbol in SECTOR_MAP for symbol in universe)


def get_missing_sectors(universe: List[str]) -> List[str]:
    """
    Get list of symbols in universe that don't have sector mappings.
    
    Args:
        universe: List of ticker symbols
    
    Returns:
        List of symbols without sector mappings
    """
    return [symbol for symbol in universe if symbol not in SECTOR_MAP]
