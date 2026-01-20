# Sage Architecture

## Overview

Sage is a production-grade systematic trading research platform designed for rigorous walkforward backtesting with strict no-lookahead guarantees. This document explains the key architectural decisions and design patterns.

---

## Core Principles

### 1. **No Lookahead Bias**
- Strict train/test splits at every layer
- Explicit data availability windows
- Rolling vs expanding window support
- Validation of temporal dependencies

### 2. **Live Trading Feasibility**
- Focus on drawdowns, leverage, turnover
- Transaction cost awareness
- Risk concentration metrics
- Implementation-ready designs

### 3. **Config-Driven Everything**
- All systems defined via `SystemConfig`
- Reproducible via serialization
- Cacheable by config hash
- Version-controlled presets

### 4. **Pluggable Components**
- Strategies, allocators, meta layers are interfaces
- Easy to add new implementations
- Testable in isolation
- Composable via config

---

## System Architecture

### Layer Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                     SystemConfig                         │
│  (Top-level: defines entire trading system)             │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┬──────────────┐
        │                 │                 │              │
        ▼                 ▼                 ▼              ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Strategy   │  │     Meta     │  │  Allocator   │  │  Portfolio   │
│    Layer     │─▶│    Layer     │─▶│    Layer     │─▶│    Layer     │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
     │                  │                  │                  │
     │                  │                  │                  │
     ▼                  ▼                  ▼                  ▼
Individual         Combines           Allocates          Risk Caps
Strategies         Strategies         Capital            Vol Targeting
(trend, MR)        + Gates            (InvVol, RP)       Leverage
```

### Data Flow

```
Raw Data (OHLCV)
    │
    ▼
Strategy Layer: Generate signals per strategy
    │ (trend_raw_ret, meanrev_raw_ret)
    ▼
Meta Layer: Combine strategies + apply gates
    │ (meta_raw_ret per asset)
    ▼
Allocator Layer: Compute portfolio weights
    │ (weights per asset)
    ▼
Portfolio Layer: Apply caps + vol targeting
    │ (final_weights, leverage)
    ▼
Portfolio Returns (daily_ret, equity_curve)
```

---

## Key Design Decisions

### 1. **MetaConfig Separation**

**Decision**: Separate `MetaConfig` from `StrategyConfig` and `AllocatorConfig`

**Rationale**:
- Meta layer combines multiple strategies (trend + meanrev)
- Applies regime gates AFTER strategy signals
- Distinct from portfolio allocation (which operates on meta returns)
- Allows single-strategy configs (gates only, no combination)

**Flow**: `Strategy → Meta → Allocator → Portfolio`

### 2. **ScheduleConfig as Single Source of Truth**

**Decision**: All frequencies in `ScheduleConfig`, not in individual layer configs

**Rationale**:
- Prevents redundancy (e.g., `AllocatorConfig.rebalance_freq` vs `ScheduleConfig.allocator_rebalance_freq`)
- Centralizes temporal decisions
- Easier to reason about walkforward schedule
- Consistent pattern across all layers

**Frequencies**:
- `strategy_train_freq`: ML strategy retraining
- `meta_rebalance_freq`: Meta allocation updates
- `allocator_rebalance_freq`: Portfolio weight recomputation
- `portfolio_rebalance_freq`: Daily mechanics (vol targeting)

### 3. **Validation at Config Level**

**Decision**: Use Pydantic `@model_validator` for cross-field validation

**Example**: MinVar + risk_caps incompatibility
```python
@model_validator(mode="after")
def validate_allocator_portfolio_compatibility(self):
    if self.allocator.type == "min_variance_v1" and self.portfolio.use_risk_caps:
        raise ValueError("MinVar already incorporates risk caps as constraints")
    return self
```

**Rationale**:
- Fail fast at config creation
- Clear error messages
- Prevents invalid backtests
- UI can use validation for dynamic field enabling/disabling

### 4. **Lazy Directory Creation**

**Decision**: Don't call `initialize_directories()` on module import

**Rationale**:
- Prevents `PermissionError` in read-only environments
- Safe for Docker, CI/CD, site-packages
- Directories created on-demand via `ensure_dir()`
- Explicit initialization available for dev setup

### 5. **WalkforwardResult as Dataclass**

**Decision**: Use `@dataclass` instead of Pydantic for results

**Rationale**:
- Performance: No validation overhead (results are outputs)
- Simplicity: Results don't need validation
- Flexibility: Easy to store pandas objects
- Validation in `__post_init__` for integrity checks

---

## Config Model Design

### Nested Structure

```python
SystemConfig
├── StrategyConfig
│   ├── strategies: List[Literal["trend_v1", "meanrev_v1"]]
│   └── params: Dict[str, Any]
│
├── MetaConfig
│   ├── combination_method: Literal["hard_v1", "soft_v1"]
│   ├── use_gates: bool
│   ├── gate_params: Dict[str, Any]
│   └── meta_params: Dict[str, Any]
│
├── AllocatorConfig
│   ├── type: Literal["inverse_vol_v1", "min_variance_v1", "risk_parity_v1"]
│   ├── lookback: int
│   └── extra_params: Dict[str, Any]
│
├── PortfolioConfig
│   ├── use_risk_caps: bool
│   ├── max_weight_per_asset: float
│   ├── vol_targeting_enabled: bool
│   └── ...
│
└── ScheduleConfig
    ├── strategy_train_freq
    ├── meta_rebalance_freq
    ├── allocator_rebalance_freq
    └── portfolio_rebalance_freq
```

### Key Features

1. **Type Safety**: Literal types prevent typos
2. **Validation**: Pydantic checks types, ranges, formats
3. **Serialization**: `to_dict()`, `to_json()`, `from_dict()`, `from_json()`
4. **Extensibility**: `extra_params` for strategy-specific parameters
5. **Self-Documenting**: Field descriptions explain every parameter

---

## Caching Strategy

### Config-Based Caching

```python
config_hash = hashlib.sha256(config.to_json().encode()).hexdigest()[:16]
cache_dir = CACHE_SYSTEMS_DIR / config_hash
```

**Cache Structure**:
```
cache/systems/
└── a41bc2d9e3f4ab12/
    ├── config.json
    ├── equity.parquet
    ├── daily_returns.parquet
    ├── weights.parquet
    ├── yearly_summary.parquet
    └── meta.json
```

**Benefits**:
- Automatic deduplication
- Fast iteration (reuse results)
- Disk-based (no DB needed for v1)
- Cleanup-friendly (delete by hash)

---

## Path Management

### Centralized Paths

All paths defined in `sage_core/utils/paths.py`:
- `PROJECT_ROOT`: Auto-detected from module location
- `DATA_DIR`, `CACHE_DIR`, `CONFIG_DIR`: Derived from root
- Helper functions: `get_processed_data_path()`, `get_system_cache_dir()`

**Benefits**:
- No hardcoded paths
- Cross-platform (pathlib)
- Easy to override for testing
- Single source of truth

---

## Testing Strategy

### Fixture-Based Testing

`tests/conftest.py` provides:
- **Config fixtures**: `default_system_config`, `minvar_system_config`
- **Data fixtures**: `sample_returns`, `sample_prices`, `sample_weights`
- **Result fixtures**: `sample_walkforward_result`

**Benefits**:
- Reusable test data
- Consistent across tests
- Fast test execution
- Reproducible (seeded RNG)

---

## Future Extensions

### Phase 1+
- DataLoader implementation
- Strategy implementations (trend_v1, meanrev_v1)
- Allocator implementations (InvVol, MinVar, RP)
- Walkforward engine

### Phase 2+
- Streamlit UI
- Multi-config comparison
- Interactive visualization

### Phase 3+
- ML strategies with training
- Transaction cost models
- Additional asset classes

---

## Design Patterns

### 1. **Protocol-Based Interfaces**
```python
class Strategy(Protocol):
    def run(self, data, schedule, cfg) -> dict[str, pd.DataFrame]:
        ...
```

### 2. **Factory Pattern**
```python
def get_allocator(config: AllocatorConfig) -> PortfolioAllocator:
    if config.type == "inverse_vol_v1":
        return InverseVolAllocator(config)
    elif config.type == "min_variance_v1":
        return MinVarianceAllocator(config)
    ...
```

### 3. **Builder Pattern**
```python
result = (WalkforwardEngineBuilder()
    .with_config(config)
    .with_data(data)
    .build()
    .run())
```

---

## Conclusion

Sage's architecture prioritizes:
- **Correctness** (no lookahead)
- **Flexibility** (pluggable components)
- **Usability** (config-driven)
- **Production-readiness** (robust, testable)

Every design decision supports these goals while maintaining simplicity and clarity.
