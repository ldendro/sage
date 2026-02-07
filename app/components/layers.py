"""Layer definitions for portfolio configuration flow."""

DEFAULT_LAYER_KEY = "strategy"

PIPELINE_STEPS = [
    ("strategy", "Strategy"),
    ("meta_allocator", "Meta"),
    ("asset_allocator", "Asset Allocator"),
    ("risk_caps", "Risk Caps"),
    ("vol_targeting", "Volatility Targeting"),
]

LAYER_DEFINITIONS = list(PIPELINE_STEPS)
LAYER_LABELS = {key: label for key, label in LAYER_DEFINITIONS}
LABEL_TO_KEY = {label: key for key, label in LAYER_DEFINITIONS}
