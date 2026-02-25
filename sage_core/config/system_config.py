"""
System configuration models for Sage.

This module defines the complete configuration schema for a trading system using Pydantic.
All system parameters are captured in these models, enabling:
- Type-safe configuration
- Automatic validation
- Serialization for caching and presets
- Self-documenting system definitions
"""

from typing import Literal, Dict, Any, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class StrategyConfig(BaseModel):
    """
    Configuration for individual trading strategies.
    
    Defines which individual strategies to run (trend, mean reversion, etc.).
    Multiple strategies can be combined via the MetaConfig layer.
    
    Attributes:
        strategies: List of strategy types to run (e.g., ["trend_v1", "meanrev_v1"])
        params: Strategy-specific parameters (e.g., lookbacks, thresholds)
    """
    
    strategies: List[Literal["trend_v1", "meanrev_v1"]] = Field(
        default=["trend_v1", "meanrev_v1"],
        description="List of individual strategies to run"
    )
    
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Strategy-specific parameters (e.g., lookbacks, feature windows)"
    )
    
    @field_validator("strategies")
    @classmethod
    def validate_strategies(cls, v: List[str]) -> List[str]:
        """Validate at least one strategy is specified."""
        if len(v) == 0:
            raise ValueError("At least one strategy must be specified")
        return v
    
    model_config = ConfigDict(extra="forbid")


class MetaConfig(BaseModel):
    """
    Configuration for meta-allocation layer.
    
    The meta layer combines individual strategy signals and applies regime-based
    filtering. It sits between individual strategies and portfolio allocation.
    
    Behavior depends on number of strategies:
    - Single strategy: Only applies gates (if enabled), combination_method is ignored
    - Multiple strategies: Combines strategies using combination_method, then applies gates
    
    Two combination methods:
    - hard_v1: Hard regime-based switching (discrete on/off per strategy)
    - soft_v1: Probabilistic weighting based on regime features
    
    Attributes:
        combination_method: How to combine strategy signals (ignored for single strategy)
        use_gates: Whether to apply regime-based gates
        gate_params: Parameters for regime gates (e.g., vol thresholds, drawdown limits)
        meta_params: Meta allocation parameters (e.g., HARD_PARAMS_TIGHT thresholds)
    """
    
    combination_method: Literal["hard_v1", "soft_v1"] = Field(
        default="hard_v1",
        description="Method for combining strategy signals (hard=discrete, soft=probabilistic)"
    )
    
    use_gates: bool = Field(
        default=True,
        description="Apply regime-based gates to turn strategies on/off based on market conditions"
    )
    
    gate_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Regime gate parameters (e.g., volatility filters, drawdown thresholds)"
    )
    
    meta_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Meta allocation parameters (e.g., momentum thresholds, regime weights)"
    )
    
    model_config = ConfigDict(extra="forbid")


class AllocatorConfig(BaseModel):
    """
    Configuration for portfolio allocator.
    
    Defines how to allocate capital across assets. Allocators can be:
    - Tactical (daily): inverse_vol_v1
    - Strategic (periodic): min_variance_v1, risk_parity_v1
    
    Note: Rebalancing frequency is controlled by ScheduleConfig.allocator_rebalance_freq,
    not here. This keeps all timing decisions in one place.
    
    Attributes:
        type: Allocator type identifier
        lookback: Number of days of history to use for weight calculation
        extra_params: Allocator-specific parameters (e.g., constraints for optimization)
    """
    
    type: Literal["inverse_vol_v1", "min_variance_v1", "risk_parity_v1"] = Field(
        default="inverse_vol_v1",
        description="Allocator type"
    )
    
    lookback: int = Field(
        default=20,
        ge=5,
        le=252,
        description="Lookback period in days for weight calculation"
    )
    
    extra_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Allocator-specific parameters (e.g., optimization constraints)"
    )
    
    model_config = ConfigDict(extra="forbid")


class PortfolioConfig(BaseModel):
    """
    Configuration for portfolio construction and risk management.
    
    Defines risk caps, position limits, and volatility targeting.
    
    Attributes:
        use_risk_caps: Whether to apply risk caps (per-asset, per-sector, min assets)
        max_weight_per_asset: Maximum weight for any single asset (0-1)
        max_sector_weight: Maximum weight for any sector (0-1)
        min_assets_held: Minimum number of assets to hold
        vol_targeting_enabled: Whether to apply volatility targeting
        target_vol_annual: Target annualized volatility (e.g., 0.10 = 10%)
        vol_lookback: Lookback period for realized volatility calculation
        max_leverage: Maximum allowed leverage (1.0 = no leverage)
    """
    
    use_risk_caps: bool = Field(
        default=True,
        description="Apply risk caps (per-asset, per-sector, min assets)"
    )
    
    max_weight_per_asset: float = Field(
        default=0.20,
        ge=0.0,
        le=1.0,
        description="Maximum weight for any single asset"
    )
    
    max_sector_weight: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
        description="Maximum weight for any sector"
    )
    
    min_assets_held: int = Field(
        default=6,
        ge=1,
        description="Minimum number of assets to hold"
    )
    
    vol_targeting_enabled: bool = Field(
        default=True,
        description="Apply volatility targeting to portfolio returns"
    )
    
    target_vol_annual: float = Field(
        default=0.10,
        ge=0.01,
        le=1.0,
        description="Target annualized volatility (e.g., 0.10 = 10%)"
    )
    
    vol_lookback: int = Field(
        default=20,
        ge=5,
        le=252,
        description="Lookback period in days for realized volatility"
    )
    
    max_leverage: float = Field(
        default=1.0,
        ge=0.0,
        le=10.0,
        description="Maximum allowed leverage (1.0 = no leverage, 2.0 = 2x)"
    )
    
    model_config = ConfigDict(extra="forbid")


class ScheduleConfig(BaseModel):
    """
    Configuration for walkforward schedule and frequencies.
    
    Defines how often each layer is retrained/rebalanced. This is critical for
    preventing lookahead bias and controlling computational cost.
    
    Attributes:
        strategy_train_freq: How often to retrain ML strategies ("none" for rule-based)
        meta_rebalance_freq: How often to recompute meta allocation weights
        allocator_rebalance_freq: How often to recompute portfolio allocator weights
        portfolio_rebalance_freq: How often to recompute portfolio (currently daily only)
    """
    
    strategy_train_freq: Literal["none", "annual", "quarterly"] = Field(
        default="none",
        description="Strategy training frequency ('none' for rule-based strategies)"
    )
    
    meta_rebalance_freq: Literal["daily", "monthly", "quarterly", "annual"] = Field(
        default="daily",
        description="Meta allocation rebalancing frequency"
    )
    
    allocator_rebalance_freq: Literal["daily", "monthly", "quarterly", "annual"] = Field(
        default="annual",
        description="Portfolio allocator weight rebalancing frequency"
    )
    
    portfolio_rebalance_freq: Literal["daily"] = Field(
        default="daily",
        description="Portfolio rebalancing frequency (currently daily only)"
    )
    
    model_config = ConfigDict(extra="forbid")


class ExecutionConfig(BaseModel):
    """Configuration for execution timing.
    
    Controls the temporal lag between decisions and execution.
    All components compute at time t using data <= t. The execution delay
    converts target weights at t into held weights at t + execution_delay_days.
    
    Attributes:
        signal_time: When signals are computed
        execution_time: When trades execute
        price_used: Which price is used for fills
        execution_delay_days: Number of trading days to delay execution
    """
    
    signal_time: Literal["close"] = Field(
        default="close",
        description="When signals are computed (market close)",
    )
    execution_time: Literal["next_open", "next_close"] = Field(
        default="next_open",
        description="When trades execute after signal computation",
    )
    price_used: Literal["open", "close"] = Field(
        default="open",
        description="Which price is used for trade fills",
    )
    execution_delay_days: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Execution delay in trading days (1 = next day execution)",
    )
    
    model_config = ConfigDict(extra="forbid")


class SystemConfig(BaseModel):
    """
    Complete system configuration.
    
    This is the top-level config that defines an entire trading system.
    It combines strategy, meta, allocator, portfolio, and schedule configurations.
    
    The config is:
    - Serializable (for caching and presets)
    - Hashable (for cache keys)
    - Validated (Pydantic ensures type safety and compatibility)
    - Self-documenting (field descriptions explain each parameter)
    
    Attributes:
        name: Human-readable system name
        universe: List of ticker symbols to trade
        start_date: Backtest start date (YYYY-MM-DD)
        end_date: Backtest end date (YYYY-MM-DD)
        strategy: Strategy configuration
        meta: Meta-allocation configuration
        allocator: Portfolio allocator configuration
        portfolio: Portfolio construction configuration
        schedule: Schedule configuration
    """
    
    name: str = Field(
        description="Human-readable system name (e.g., 'Baseline InvVol', 'Strategic RP Q126')"
    )
    
    universe: List[str] = Field(
        description="List of ticker symbols to trade (e.g., ['SPY', 'QQQ', 'IWM'])"
    )
    
    start_date: str = Field(
        description="Backtest start date in YYYY-MM-DD format"
    )
    
    end_date: str = Field(
        description="Backtest end date in YYYY-MM-DD format"
    )
    
    strategy: StrategyConfig = Field(
        default_factory=StrategyConfig,
        description="Strategy layer configuration"
    )
    
    meta: MetaConfig = Field(
        default_factory=MetaConfig,
        description="Meta-allocation layer configuration"
    )
    
    allocator: AllocatorConfig = Field(
        default_factory=AllocatorConfig,
        description="Portfolio allocator layer configuration"
    )
    
    portfolio: PortfolioConfig = Field(
        default_factory=PortfolioConfig,
        description="Portfolio construction layer configuration"
    )
    
    schedule: ScheduleConfig = Field(
        default_factory=ScheduleConfig,
        description="Schedule and frequency configuration"
    )
    
    execution: ExecutionConfig = Field(
        default_factory=ExecutionConfig,
        description="Execution timing configuration (delay, fill prices)"
    )
    
    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate date format is YYYY-MM-DD."""
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError(f"Date must be in YYYY-MM-DD format, got: {v}")
        return v
    
    @field_validator("universe")
    @classmethod
    def validate_universe(cls, v: List[str]) -> List[str]:
        """Validate universe has at least one symbol."""
        if len(v) == 0:
            raise ValueError("Universe must contain at least one symbol")
        return v
    
    @model_validator(mode="after")
    def validate_allocator_portfolio_compatibility(self) -> "SystemConfig":
        """
        Validate compatibility between allocator and portfolio settings.
        
        MinVar allocator incorporates risk caps as optimization constraints,
        so applying post-hoc risk caps would be redundant and incorrect.
        
        Raises:
            ValueError: If incompatible settings are detected
        """
        if self.allocator.type == "min_variance_v1" and self.portfolio.use_risk_caps:
            raise ValueError(
                "Incompatible configuration: MinVar allocator already incorporates risk caps "
                "as optimization constraints. Set portfolio.use_risk_caps=False when using "
                "min_variance_v1 allocator."
            )
        return self
    
    model_config = ConfigDict(extra="forbid")
    
    def has_single_strategy(self) -> bool:
        """
        Check if config uses only a single strategy.
        
        When true, MetaConfig's combination_method will be ignored,
        and only gates (if enabled) will be applied.
        
        Returns:
            True if only one strategy is configured
        """
        return len(self.strategy.strategies) == 1
    
    def get_config_warnings(self) -> list[str]:
        """
        Get list of configuration warnings (non-fatal issues).
        
        Useful for UI to show informational messages to users.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        if self.has_single_strategy():
            warnings.append(
                f"Single strategy configured ({self.strategy.strategies[0]}). "
                f"MetaConfig.combination_method ('{self.meta.combination_method}') will be ignored. "
                f"Only gates will be applied if enabled."
            )
        
        return warnings
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for serialization)."""
        return self.model_dump()
    
    def to_json(self) -> str:
        """Convert to JSON string (for caching)."""
        return self.model_dump_json(indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemConfig":
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "SystemConfig":
        """Create from JSON string."""
        return cls.model_validate_json(json_str)
