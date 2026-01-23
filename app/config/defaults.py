"""Default configuration values for the Streamlit app."""

from datetime import date

# Available universe (tickers with processed data)
AVAILABLE_TICKERS = [
    "SPY", "QQQ", "IWM",  # Equities
    "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"  # Sectors
]

# Default parameters
DEFAULT_UNIVERSE = ["SPY", "QQQ", "IWM"]
DEFAULT_START_DATE = date(2020, 1, 1)
DEFAULT_END_DATE = date(2021, 12, 31)
DEFAULT_MAX_WEIGHT_PER_ASSET = 0.25
DEFAULT_MAX_SECTOR_WEIGHT = None
DEFAULT_MIN_ASSETS_HELD = 1
DEFAULT_TARGET_VOL = 0.10
DEFAULT_VOL_LOOKBACK = 60
DEFAULT_MIN_LEVERAGE = 0.0
DEFAULT_MAX_LEVERAGE = 2.0
DEFAULT_VOL_WINDOW = 60

# Parameter bounds (min, max)
BOUNDS = {
    "max_weight_per_asset": (0.05, 1.0),
    "max_sector_weight": (0.1, 1.0),
    "min_assets_held": (1, 10),
    "target_vol": (0.01, 0.50),
    "vol_lookback": (10, 252),
    "min_leverage": (0.0, 3.0),
    "max_leverage": (0.5, 5.0),
    "vol_window": (10, 252),
}
