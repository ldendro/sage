# Sage Architecture

## Overview

Sage is a production-grade systematic trading research platform designed for rigorous walkforward backtesting with strict no-lookahead guarantees. The system is architected as a layered pipeline where **strategies produce intent**, the **execution module enforces timing**, **allocators construct portfolios**, and **run artifacts ensure reproducibility**.

This document explains the key architectural decisions, design patterns, and planned extensions as defined in the [ROADMAP](./ROADMAP.md).

---

## Core Principles

### 1. **No Lookahead Bias**
- Strict train/test splits at every layer
- Explicit data availability windows
- Rolling vs expanding window support
- Validation of temporal dependencies
- **Engine owns the shift** — strategies never see future data (system invariant, not convention)

### 2. **Intent-Based Design**
- Strategies output *intent* (signals or scores), never positions or returns
- The `ExecutionModule` is the only component that converts intent → positions
- Clear terminology: **intent → target weights → held weights**
- This separation makes ML integration clean and timing guarantees universal

### 3. **Config-Driven Everything**
- All systems defined via `SystemConfig`
- Reproducible via serialization
- Cacheable by config hash
- Version-controlled presets

### 4. **Pluggable Components**
- Strategies, allocators, meta layers, features are interfaces
- Easy to add new implementations
- Testable in isolation
- Composable via config

### 5. **Reproducibility as Infrastructure**
- Every run produces a self-contained artifact directory
- Two data modes: `live` (speed) vs `snapshot` (science)
- Run manifests with schema versioning for provenance tracking
- Deterministic re-run validation

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
│  Feature     │  │   Strategy   │  │     Meta     │  │  Execution   │
│  Store       │─▶│    Layer     │─▶│    Layer     │─▶│   Module     │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
     │                  │                  │                  │
     │                  │                  │                  │
     ▼                  ▼                  ▼                  ▼
Feature            Individual         Combines           Timing +
Extraction         Strategies         Strategies         Exposure
(indicators)       (trend, MR)        + Gates            Mapping
                                                              │
                    ┌─────────────────────────────────────────┘
                    │
                    ▼
             ┌──────────────┐  ┌──────────────┐
             │  Allocator   │─▶│  Portfolio    │
             │    Layer     │  │    Layer      │
             └──────────────┘  └──────────────┘
                    │                  │
                    ▼                  ▼
              Allocates           Risk Caps
              Capital             Vol Targeting
              (InvVol, RP,        Leverage
               MeanVar)
```

### Data Flow (Current Implementation)

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

### Data Flow (Target Architecture — per ROADMAP)

```
Raw Data (OHLCV)
    │
    ▼
Feature Store: Extract indicators (pure functions of historical data)
    │ (FeatureMatrixBuilder → X matrix: time × asset × feature)
    ▼
Strategy Layer: Generate intent per strategy
    │ Rule-based: discrete {-1, 0, +1} per asset
    │ ML models:  continuous scores/probabilities per asset
    ▼
Meta Layer: Combine strategies + apply gates
    │ (combined intent per asset)
    ▼
ExecutionModule: Timing enforcement + exposure mapping
    │ - Applies ExecutionPolicy (shift signals to execution time)
    │ - Maps score → target weights (rank_then_normalize, zscore_then_clip, etc.)
    │ - Enforces gross_exposure_cap, net_exposure_target, per_asset_cap
    ▼
Allocator Layer: Portfolio weight construction
    │ - AssetAllocator ABC with output contract
    │ - Weights sum to 1.0, no NaNs, per-asset bounds respected
    │ - Fallback to inverse-vol or equal-weight on solver failure
    ▼
Portfolio Layer: Apply caps + vol targeting
    │ (held_weights, leverage)
    ▼
Cost Model: Deduct transaction costs from returns
    │ (gross_returns → net_returns, cost_components)
    ▼
Run Artifacts: Persist all outputs for reproducibility
    │ (run_manifest.json, equity_curve.parquet, weights.parquet, etc.)
```

### Terminology Invariant

These terms have precise meanings throughout the codebase:

| Term | Definition | Who produces it |
|---|---|---|
| **Intent** | Model or rule output (scores or discrete signals) | Strategy |
| **Target weights** | Desired portfolio weights after exposure mapping | ExecutionModule |
| **Held weights** | Actual portfolio weights after execution, drift, and costs | Portfolio Layer |

> **Only the engine may transform: intent → target weights → held weights.**
> This is enforced structurally, not by convention.

---

## Key Design Decisions

### 1. **MetaConfig Separation**

**Decision**: Separate `MetaConfig` from `StrategyConfig` and `AllocatorConfig`

**Rationale**:
- Meta layer combines multiple strategies (trend + meanrev)
- Applies regime gates AFTER strategy signals
- Distinct from portfolio allocation (which operates on meta returns)
- Allows single-strategy configs (gates only, no combination)

**Flow**: `Strategy → Meta → ExecutionModule → Allocator → Portfolio`

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
- `allocator_rebalance_freq`: Portfolio weight recomputation (with explicit `ScheduleConfig`)
- `portfolio_rebalance_freq`: Daily mechanics (vol targeting)

**Rebalance Schedule** (planned):
```yaml
rebalance:
  frequency: monthly
  day: last_trading_day
```

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

### 6. **Engine Owns the Shift** (Planned — ROADMAP Week 1)

**Decision**: Strategies return raw intent at time *t*. The `ExecutionModule` applies `ExecutionPolicy` to produce lagged positions at *t+1*.

**Rationale**:
- Upgrades "no lookahead" from convention to **system invariant**
- Removes burden from strategy authors
- Makes timing guarantees universal across rule-based and ML strategies
- Strategies structurally cannot return positions — only the `ExecutionModule` can

### 7. **Allocator Output Contract** (Planned — ROADMAP Week 3)

**Decision**: `compute_weights()` must satisfy a strict output contract validated automatically by `_validate_output()`.

**Contract**:
- Weights sum to 1.0 (or target gross exposure)
- Per-asset bounds respected
- No NaN values in output
- Must never raise in production mode — fallback to inverse-vol or equal-weight on solver failure
- Warnings written to `warnings.log` in run artifacts

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
├── ScheduleConfig
│   ├── strategy_train_freq
│   ├── meta_rebalance_freq
│   ├── allocator_rebalance_freq
│   └── portfolio_rebalance_freq
│
├── ExecutionPolicy (planned)           # signal_time, execution_time, price_used
├── CostModelConfig (planned)           # spread_bps, slippage_bps, impact_model
└── FeatureConfig (planned)             # registered features, warmup periods
```

### Key Features

1. **Type Safety**: Literal types prevent typos
2. **Validation**: Pydantic checks types, ranges, formats
3. **Serialization**: `to_dict()`, `to_json()`, `from_dict()`, `from_json()`
4. **Extensibility**: `extra_params` for strategy-specific parameters
5. **Self-Documenting**: Field descriptions explain every parameter

---

## Run Artifacts (Planned — ROADMAP Week 5)

Every run produces a self-contained artifact directory:

```
runs/{run_id}/
├── run_manifest.json        # run_id, git hash, timestamp, mode, config hash,
│                            # python_version, platform, seed, deterministic,
│                            # artifact_schema_version
├── config.yaml              # Frozen SystemConfig
├── data_snapshot_manifest.json
├── metrics.json             # All computed metrics
├── equity_curve.parquet
├── weights.parquet
├── returns_gross.parquet
├── returns_net.parquet
├── cost_components.parquet
├── predictions.parquet      # ML: per-timestamp scores, labels, fold IDs
├── warnings.log             # Solver fallbacks, constraint hits, edge cases
└── env.txt                  # Python version, dependency lock hash
```

**Data Modes**:

| Mode | Purpose | Data Source | Expiry |
|---|---|---|---|
| `mode="live"` | Convenience / exploration | YFinance API → 24h-expiry cache | 24 hours |
| `mode="snapshot"` | Research truth / reproducibility | Pinned parquet files | Never |

---

## Feature Store (Planned — ROADMAP Week 6)

### Architecture

Features are extracted from strategy classes into standalone, pure-function generators:

```python
class FeatureGenerator(ABC):
    required_columns: list[str]    # e.g., ["close", "volume"]
    output_names: list[str]        # e.g., ["trend.momentum_20d"]
    warmup_period: int
    scope: Literal["time_series", "cross_sectional"]

    def generate(self, data: pd.DataFrame) -> pd.DataFrame: ...
```

### Key Rules

- **Immutability**: Features are pure functions of historical data — no internal state, no access to predictions or portfolio state
- **Namespacing**: `{strategy}.{indicator}_{param}` (e.g., `trend.momentum_20d`, `meanrev.rsi_14`)
- **Collision detection**: Registry rejects duplicate feature names (hard error)
- **Canonical shape**: Panel tensor `(time × asset × feature)` with `.to_long()` and `.to_sklearn()` helpers

---

## Cost Model (Planned — ROADMAP Week 2)

Transaction costs as regularization — zero-cost environments are pathological.

**Components**: spread cost, slippage cost, impact cost per day

**Turnover definition**:
- Computed on *target weights* (not held weights)
- Formula: `sum(abs(w_t - w_{t-1}))` (full round-trip, not halved)
- Cash / residual excluded

**Return series maintained**:
- `gross_returns`: pre-cost portfolio returns
- `net_returns`: post-cost portfolio returns
- `cost_components`: per-day breakdown

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

### Invariant Test Suite (Planned — ROADMAP Week 4)

Critical invariants that prove system correctness:

| Invariant | What it catches |
|---|---|
| Zero signals ⇒ zero returns | Signal propagation bugs |
| Equal-weight ⇒ 1/N constant | Allocator logic errors |
| Cost-free ⇒ gross = net | Cost integration bugs |
| Cost monotonicity ⇒ higher cost = lower net return | Cost accounting errors |
| Execution delay ⇒ different performance | Silent same-bar execution |
| No-silent-alignment ⇒ explicit error on index mismatch | Pandas `.reindex()` / `join()` bugs |
| Illegal future-access ⇒ error on reading future prices | `.shift(-1)` leakage |
| Attribution conservation ⇒ components sum to gross | Double-counting in attribution |

---

## Design Patterns

### 1. **Intent-Based Strategy Interface**

Strategies return intent (signals or scores), never positions:

```python
class Strategy(Protocol):
    def run(self, data, schedule, cfg) -> dict[str, pd.DataFrame]:
        """Return intent: raw signals/scores at time t (unshifted)."""
        ...
```

ML strategies additionally implement:
```python
class ModelWrapperStrategy:
    def fit(self, train_data: pd.DataFrame) -> None: ...
    def predict(self, test_data: pd.DataFrame) -> pd.DataFrame: ...
    def generate_scores(self) -> pd.DataFrame: ...  # continuous output
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

### 4. **ABC with Output Contract** (Planned)
```python
class AssetAllocator(ABC):
    @abstractmethod
    def compute_weights(self, ...) -> pd.Series: ...

    def _validate_output(self, weights: pd.Series) -> pd.Series:
        """Auto-called after compute_weights(). Validates contract."""
        assert abs(weights.sum() - 1.0) < tolerance
        assert not weights.isna().any()
        assert (weights <= self.config.per_asset_cap).all()
        return weights
```

---

## Planned Extensions (per ROADMAP)

### Phase 1: Foundation & Rigor (Weeks 1–4)
- ExecutionModule with timing enforcement
- Transaction cost model as regularization
- AssetAllocator ABC with output contracts
- Formal invariant test suite

### Phase 2: Data as Research Object (Weeks 5–8)
- Run artifact system with schema versioning
- Feature store with extraction, registry, and matrix builder
- Stationarity and representation experiments

### Phase 3: ML as Controlled Decision Component (Weeks 9–11)
- ModelWrapperStrategy with fit/predict lifecycle
- Experiment tracking (MLflow/W&B)
- Error analysis with reproducible regime classification

### Phase 4: Professionalization (Weeks 12–14)
- Research-grade documentation
- 5-minute demo narrative
- Interview mapping (ML Engineer + Quant Research)

---

## Conclusion

Sage's architecture prioritizes:
- **Correctness** (no lookahead — enforced structurally)
- **Reproducibility** (run artifacts, data snapshots, schema versioning)
- **Flexibility** (pluggable components via ABCs and factories)
- **Usability** (config-driven, demo-runnable)
- **Production-readiness** (robust fallbacks, invariant testing)

Every design decision supports these goals while maintaining simplicity and clarity.
