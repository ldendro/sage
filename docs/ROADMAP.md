# Sage: ML Systems Research Platform — Execution Roadmap

**Vision**: Sage is a professional-grade machine learning systems research platform for
decision-making under uncertainty, using quantitative finance as the primary domain.

**Core Principles** (these govern every week):
- No feature ships without an evaluation story
- No ML before baselines and invariants
- Every major component gets a written justification
- Depth > breadth — features earn their existence
- If something feels "obvious," write why

**Platform Emphasis**:
- Rigorous offline evaluation
- Reproducibility
- Clear separation of data, models, and decisions
- Engineering discipline over model hype

---

## Current State (as of Feb 2026)

### What Is Built ✅

| Component | Location | Status |
|---|---|---|
| Walk-forward engine | `walkforward/engine.py` | Production |
| Strategy ABC + factory | `strategies/base.py`, `strategies/__init__.py` | Production |
| TrendStrategy (3 indicators) | `strategies/trend.py` | Production |
| MeanRevStrategy (3 indicators) | `strategies/meanrev.py` | Production |
| PassthroughStrategy (benchmark) | `strategies/passthrough.py` | Production |
| MetaAllocator ABC + factory | `meta/base.py`, `meta/__init__.py` | Production |
| FixedWeight meta allocator | `meta/fixed_weight.py` | Production |
| RiskParity meta allocator | `meta/risk_parity.py` | Production |
| Inverse vol asset allocator | `allocators/inverse_vol_v1.py` | Production |
| Equal-weight allocator function | `allocators/inverse_vol_v1.py` | Production |
| Risk caps (asset, sector, min-hold) | `portfolio/risk_caps.py` | Production |
| Vol targeting | `portfolio/vol_targeting.py` | Production |
| Portfolio constructor | `portfolio/constructor.py` | Production |
| Metrics (Sharpe, DD, CAGR, Calmar, turnover) | `metrics/performance.py` | Production |
| WalkforwardResult dataclass | `walkforward/results.py` | Production |
| SystemConfig (Pydantic) | `config/system_config.py` | Production |
| Warmup calculation system | `utils/warmup.py` | Production |
| Data loader (YFinance + parquet) | `data/loader.py` | Production |
| Data cache (disk, expiry-based) | `data/cache.py` | Production |
| Streamlit UI (5-system comparison) | `app/` | Production |
| 27 test files | `tests/` | Extensive |

### What Is NOT Built ❌

- No `ExecutionPolicy` — timing is enforced by `shift(1)` convention, not system-level guardrails
- No `CostModel` — zero-cost environment
- No asset-level allocator abstraction — allocators are bare functions, not classes
- No mean-variance optimizer — `cvxpy` not in dependencies
- No run/result cache — `sage_core/cache/__init__.py` is empty despite architecture doc describing it
- No `run_id` system — no reproducibility artifacts
- No invariant tests — no formal correctness proofs
- No attribution analysis — no signal vs allocation vs cost decomposition
- No Sortino, hit-rate, or stability-across-folds metrics
- No feature store — indicators embedded in strategy classes
- No label engineering — no triple-barrier or horizon-aware targets
- No ML integration — no `ModelWrapperStrategy`
- No experiment tracking — no MLflow/W&B

---

## PHASE 1: TRUST, TEMPORAL CORRECTNESS, AND ENGINE LEGITIMACY

**Theme**: "Can this system be wrong, and would I know?"

**Gate**: Phase 1 is DONE when you can say:
*"If Sage produces a result, I can explain why it's correct."*

---

### Week 1 — Execution Timing & Market Clock (40h)

**Why**: The #1 silent failure mode. Sage currently relies on informal `shift(1)` scattered
across `trend.py`, `meanrev.py`, `inverse_vol_v1.py`, `vol_targeting.py`, and `risk_parity.py`.
A new strategy or allocator can easily break timing with no guardrail.

#### Key Design Decision

> **The engine owns the shift, not strategies.**
>
> Strategies output raw signals/scores at time *t* (unshifted intent).
> The engine applies `ExecutionPolicy` to convert intent into positions/returns
> at *t+1* (or the next execution time). This is the strongest guardrail because
> it removes the burden from strategy authors and upgrades "no lookahead" from
> convention → **system invariant**.

#### Hard Architectural Constraint

> **Strategies return intent only — never positions or returns.**
>
> The `ExecutionModule` is the *only* component allowed to produce
> positions and trades. This is enforced structurally: the `Strategy` ABC
> returns signals/scores, and the engine pipeline passes them through
> `ExecutionModule` before any downstream component sees them.
>
> **Intent** = per-asset target exposure. For a multi-asset universe:
> - Discrete: `{"SPY": +1, "TLT": -1, "GLD": 0}` (long/short/flat per asset)
> - Continuous: `{"SPY": 0.72, "TLT": -0.35, "GLD": 0.12}` (scores per asset)
>
> `ExecutionModule` converts intent into positions with a defined rule
> (e.g., normalize, clip, map score → exposure). This distinction matters
> when cross-sectional models produce relative scores across assets.
>
> This makes "can't bypass" a **design invariant**, not a runtime check.
> Document this rule explicitly in `docs/execution_model.md` and in the
> `Strategy` ABC docstring.

#### Build (≈30h)

- [ ] **Introduce `ExecutionPolicy`** (`sage_core/execution/policy.py`)
    - `signal_time`: when signals are computed
    - `execution_time`: when trades execute
    - `price_used`: which price is used for fills
- [ ] **Introduce `ExecutionModule`** (`sage_core/execution/module.py`)
    - The *only* component that converts intent → positions/trades
    - Strategies output raw signals/scores at time *t*
    - `ExecutionModule` applies `ExecutionPolicy` to produce lagged positions at *t+1*
    - Engine pipeline: `Strategy.generate_signals()` → `ExecutionModule.apply()` → downstream
    - **Pipeline boundary clarification**:
        - `ExecutionModule`: handles timing (shift) + intent validation
        - `Allocator`: handles weight construction from validated signals
        - Exposure mapping (score → target weights) lives in `ExecutionModule`
          as a pre-allocator step. This keeps a clean separation:
          `intent → [ExecutionModule: timing + exposure mapping] → target_weights → [Allocator: portfolio construction] → held_weights`
        - This distinction matters because "positions" can mean target weights
          vs held weights once allocators are introduced
    - **Default score → exposure mapping** (configurable):
        - `score_to_exposure`: e.g., `"rank_then_normalize"`, `"zscore_then_clip"`, `"passthrough"`
        - Constraints: `gross_exposure_cap`, `net_exposure_target`, `per_asset_cap`
        - Default: `"rank_then_normalize"` with `gross_exposure_cap=1.0`
        - Cross-sectional ML models will force this decision — making it explicit now prevents ambiguity
- [ ] **Refactor existing strategies to return intent only**
    - Remove existing `shift(1)` calls from `trend.py`, `meanrev.py`,
      `inverse_vol_v1.py`, `vol_targeting.py`, `risk_parity.py`
    - Strategies no longer compute returns — they compute signals
- [ ] **Add unit tests for timing**
    - Test: strategy that emits unshifted signals ⇒ engine correctly shifts via `ExecutionModule`
    - Test: attempting to return positions from a strategy ⇒ structural error
    - Test: valid flow ⇒ passes
    - **Illegal future-access invariant**: a strategy or feature that attempts
      to read prices at or after `execution_time` must raise an error.
      Implementation: inject a sentinel/masked future window during tests;
      assert access raises or returns NaN. Catches `.shift(-1)`, future
      leakage in feature refactors, and subtle pandas alignment bugs.
    - **No-silent-alignment invariant**: if signals are missing a timestamp
      that prices have (or vice versa), the engine must explicitly error.
      Rule: "Any merge across time must be explicit + tested."
      Catches silent `.reindex()` / `join()` behavior that can make two
      series "look" shifted when they're not. Prevents "my backtest changed
      when I added a column."
- [ ] **Update `SystemConfig`** to include `ExecutionPolicy` settings

#### Write (≈10h)

- [ ] `docs/execution_model.md`
    - Timeline diagram of legal vs illegal data access
    - **Terminology invariant** (lock the language system-wide):
        - *Intent*: model or rule output (scores or discrete signals)
        - *Target weights*: desired portfolio weights after exposure mapping
        - *Held weights*: actual portfolio weights after execution, drift, and costs
        - Only the engine may transform: intent → target weights → held weights
    - Why this matters for ML/RL downstream
    - Map data leakage concepts (Hands-On ML) to execution timing

**Outcome**: Sage can *prove* it doesn't cheat.

---

### Week 2 — Transaction Costs as Regularization (40h)

**Why**: Quant rigor and ML rigor intersect here. Zero-cost environments are pathological.

**Prerequisite**: Week 1 (`ExecutionPolicy` must exist so costs apply at the correct time).

#### Build (≈30h)

- [ ] **Implement `CostModel`** (`sage_core/costs/model.py`)
    - Bid–ask spread
    - Slippage ∝ turnover
    - Simple market impact proxy
- [ ] **Wire `CostModel` into the engine**
    - Costs deducted from portfolio returns at the correct execution time
    - Costs are a config option (default: zero for backward compatibility)
- [ ] **Maintain three distinct return series throughout the engine**
    - `gross_returns`: pre-cost portfolio returns
    - `net_returns`: post-cost portfolio returns
    - `cost_components`: per-day breakdown (spread, slippage, impact)
    - All three recorded in `WalkforwardResult`
- [ ] **Cost attribution per rebalance**
    - Break down: spread cost, slippage cost, impact cost per day
- [ ] **Human-readable cost summaries**
    - `cost_bps_per_day`: daily cost drag in basis points
    - `annualized_cost_bps`: annualized cost drag
    - Turnover-weighted cost summary ("Average cost drag was ~X bps/day at Y turnover")
- [ ] **Cost-free regression test** (invariant: `gross_returns == net_returns` when costs = 0)
- [ ] **Cost monotonicity invariant**: increasing costs should decrease average
    daily net return (not Sharpe — Sharpe can paradoxically improve if costs
    dampen turnover noise). Scoped to `PassthroughStrategy` + equal-weight
    allocator where behavior is fully predictable. This avoids false failures
    while still catching cost integration bugs.
- [ ] **Update `SystemConfig`** with cost model parameters
- [ ] **Update `WalkforwardResult`** with `gross_returns`, `net_returns`, `cost_components`
- [ ] ~~Compute turnover~~ *(already implemented in `metrics/performance.py`)*

> **Re-scoped from original plan**: Turnover calculation already exists. The ~4h
> originally budgeted for it should go to cost attribution and engine integration.

#### Write (≈10h)

- [ ] `docs/cost_modeling.md`
    - Why zero-cost environments are pathological
    - Parallels to ML regularization (overfitting ↔ over-trading)
    - Limitations of the cost model
    - Map regularization intuition (Hands-On ML) to cost modeling
    - **Turnover definition** (surprisingly non-standard — interview trap):
        - Computed on *target weights* (not held weights)
        - Formula: `sum(abs(w_t - w_{t-1}))` (full round-trip, not halved)
        - Cash / residual excluded from the sum
        - Document explicitly because the cost model depends on this choice
    - **Cost calibration section**:
        - Plausible ranges for spread, slippage, and impact by asset class
        - Why Sage does not claim real execution precision
        - How sensitivity to costs is evaluated (sweep costs ×0.5–×2.0, check Sharpe stability)
        - Protects against "is this realistic?" objections

**Outcome**: Unrealistic strategies fail early.

---

### Week 3 — Allocator Abstraction & Convex Optimization (40h)

**Why**: ML must beat math, not vibes. But first, the allocator layer needs an abstraction.

**Critical prerequisite identified in gap analysis**: Asset-level allocators (`sage_core/allocators/`)
have no base class — they are bare functions. The meta allocators (`sage_core/meta/`) have a clean
ABC. Before adding MeanVariance, the asset allocator layer must match.

#### Build (≈32h)

**Part A — Allocator Abstraction (~10h)**

- [ ] **Create `AssetAllocator` ABC** (`sage_core/allocators/base.py`)
    - `validate_params()`, `get_warmup_period()`, `compute_weights()`
    - `rebalance_frequency`: daily / weekly / monthly (or accepts `ScheduleConfig`)
    - **`ScheduleConfig`** (define the abstraction explicitly):
        ```yaml
        rebalance:
          frequency: monthly
          day: last_trading_day
        ```
        - Makes allocator behavior explainable
        - Prevents confusion when ML models train daily but trade monthly
        - Sets up cleanly for transaction cost realism
        - No exotic schedules needed now — just name the abstraction
    - Covariance update frequency can match rebalance frequency
    - Mirror the pattern in `meta/base.py`
    - **Output contract** — `compute_weights()` must return weights that satisfy:
        - Weights sum to 1.0 (or to target gross exposure if leveraged)
        - Per-asset bounds respected (within configured caps)
        - No NaN values in output (NaN inputs are handled internally)
        - Fallback always yields valid weights (never an exception)
        - **Hard rule**: `compute_weights()` must never raise in production mode.
          It must return valid weights or a fallback — a failed optimizer
          must not crash the entire run.
    - Contract is validated by a base-class `_validate_output()` method
      called automatically after every `compute_weights()` invocation
    - **Tests must assert**:
        - Solver failure → weights still valid (fallback returned)
        - Warning emitted → written to `warnings.log` (Week 5 artifact)
- [ ] **Refactor `inverse_vol_v1.py`** into `InverseVolAllocator` class
- [ ] **Refactor `compute_equal_weights`** into `EqualWeightAllocator` class
- [ ] **Create allocator factory** (`sage_core/allocators/__init__.py`)
    - Registry + `get_allocator()` function
- [ ] **Wire factory through `engine.py`**
    - Replace direct function call with allocator instantiation from config
- [ ] **Update existing tests** (`test_allocators.py`) for new class-based interface

**Part B — Mean-Variance Optimizer (~14h)**

- [ ] **Add `cvxpy` to `pyproject.toml`** dependencies
- [ ] **Implement `MeanVarianceAllocator`** (`sage_core/allocators/mean_variance.py`)
    - Long-only, box constraints, optional sector constraints
    - Deterministic solver settings for reproducibility
    - Warmup logic (requires sufficient return history for covariance estimation)
    - **Leakage-safe covariance**: covariance is computed using returns
      *strictly prior* to the rebalance/execution date — never including
      same-day or future returns. This is a classic failure point.
    - Constraints documented with failure modes
- [ ] **Solver failure fallback policy**
    - If solver fails to converge: fall back to inverse-vol (or equal-weight)
    - Log a warning with solver status — never fail silently
    - Configurable fallback preference in `AllocatorConfig`
- [ ] **Add constraint diagnostics** — log when solver hits constraints
- [ ] **Compare allocators** under identical signals (EqualWeight vs InvVol vs MeanVar)

**Part C — Cross-Cutting (~8h)**

- [ ] **Update `SystemConfig.AllocatorConfig`** to support new allocator types
- [ ] **Update Streamlit UI** allocator selection dropdown
- [ ] **Sync `ARCHITECTURE.md`** — it references allocator types that now actually exist

#### Write (≈8h)

- [ ] `docs/allocators.md`
    - Assumptions and failure modes of each allocator
    - When optimization beats heuristics (and vice versa)

**Outcome**: Sage has defensible baselines with a clean, extensible allocator layer.

---

### Week 4 — Evaluation Framework & Invariants (40h)

**Why**: Pure engineering credibility. If you can't prove correctness, nothing else matters.

**Re-scoped from original plan**: The metrics layer (Sharpe, DD, CAGR, Calmar, turnover, yearly
summaries) already exists in `metrics/performance.py`. This week focuses on what's *missing*:
attribution, expanded metrics, runnable baselines, and formal invariant tests.

#### Build (≈28h)

**Part A — Expanded Metrics (~6h)**

- [ ] **Sortino ratio** (downside deviation only)
- [ ] **Hit rate** (% of positive-return days)
- [ ] **Fold-level stability metrics**
    - Define "fold" explicitly: yearly non-overlapping windows (Jan–Dec)
    - `mean_sharpe_across_folds / std_sharpe_across_folds` (stability ratio)
    - `pct_folds_positive` (% of yearly folds with Sharpe > 0)
    - `worst_fold_sharpe` (minimum yearly Sharpe — stress test)
- [ ] Add all new metrics to `calculate_all_metrics()`

**Part B — Runnable Baselines (~8h)**

- [ ] **Buy-and-hold baseline system**
    - Passthrough strategy + equal-weight allocator, no vol targeting
    - Runnable as a single config via the engine (not a separate script)
- [ ] **Equal-weight baseline system**
    - Passthrough strategy + equal-weight allocator + vol targeting
- [ ] **Preset configs** for each baseline in `configs/presets/`

**Part C — Attribution Analysis (~8h)**

- [ ] **Signal attribution**: Returns from signal alone (strategy returns vs raw returns)
- [ ] **Allocation attribution**: Returns from allocation vs equal-weight
- [ ] **Cost attribution**: Gross returns vs net returns (requires Week 2 `CostModel`)
- [ ] **Leverage attribution**: Pre-vol-targeting vs post-vol-targeting returns

**Part D — Invariant Test Suite (~6h)**

- [ ] `tests/test_invariants.py`
    - Zero signals ⇒ zero returns
    - Equal-weight allocation ⇒ 1/N weights constant
    - No rebalance ⇒ weights drift with returns only
    - Cost-free ⇒ gross = net
    - Leverage 1.0 ⇒ raw weights unchanged
    - **Execution delay invariant**: delaying execution by +k days
      (e.g., `next_open` vs `next_close`) produces *different* performance.
      If delaying execution yields identical results, same-bar execution is
      happening silently. This catches timing regressions.
    - **Attribution conservation invariant**:
      `gross_returns ≈ signal_component + allocation_component + leverage_component`
      (within tolerance), and `net_returns = gross_returns - cost_total`.
      Even if attribution isn't perfect early, this test forces honest accounting
      and catches double-counting bugs.

#### Write (≈12h)

- [ ] `docs/evaluation.md` — metric definitions, baseline rationale
- [ ] `docs/invariants.md` — what each invariant tests and why

**Outcome**: Every result is explainable. Phase 1 gate is passed.

> [!TIP]
> **Sequencing note**: If you find yourself needing run artifacts before Week 5
> (e.g., for invariant test output or baseline comparison), start writing the
> artifact directory structure at the end of Week 4. The schema is simple and
> having it early prevents ad-hoc file patterns from taking root.

---

## PHASE 2: DATA AS A FIRST-CLASS RESEARCH OBJECT

**Theme**: "ML does not consume strategies — it consumes datasets."

---

### Week 5 — Reproducibility & Run Artifacts (40h)

**Why**: Reproducibility separates research from demos.

**Gap identified**: `ARCHITECTURE.md` describes a config-hash result cache
(`cache/systems/{hash}/`) but `sage_core/cache/__init__.py` is empty. The data
cache (`data/cache.py`) works but expires after 24h — the opposite of deterministic.

#### Data Mode Philosophy

> Two distinct modes with different purposes:
>
> | Mode | Purpose | Data Source | Expiry |
> |---|---|---|---|
> | `mode="live"` | Convenience / exploration | YFinance API → 24h-expiry cache | 24 hours |
> | `mode="snapshot"` | Research truth / reproducibility | Pinned parquet files | Never |
>
> The data cache (`data/cache.py`) is for speed. Data snapshots are for science.
> Every experiment that claims a result must be backed by a snapshot.

#### Run Artifact Schema

> Every run produces a self-contained artifact directory:
>
> ```
> runs/{run_id}/
> ├── run_manifest.json                # run_id, git hash, timestamp, mode, config hash
> ├── config.yaml                      # Frozen SystemConfig
> ├── data_snapshot_manifest.json       # Symbols, date range, data hash
> ├── metrics.json                      # All computed metrics
> ├── equity_curve.parquet              # Daily equity
> ├── weights.parquet                   # Daily asset weights
> ├── returns_gross.parquet             # Pre-cost returns
> ├── returns_net.parquet               # Post-cost returns
> ├── cost_components.parquet           # Per-day cost breakdown
> ├── warnings.log                      # Solver fallbacks, constraint hits, edge cases
> └── env.txt                           # Python version, dependency lock hash
> ```
>
> `run_manifest.json` fields: `run_id`, `git_commit_hash` (if available),
> `timestamp`, `mode` (live/snapshot), `config_hash`, `python_version`,
> `platform`, `seed` (even if unused — future-proofs for stochastic models),
> `deterministic` (true/false, derived from mode + solver settings),
> `artifact_schema_version` (starts at `1` — makes old runs readable forever
> and avoids "why did this field disappear?" pain as artifacts evolve).
> This makes debugging and provenance tracking trivial.

#### Build (≈30h)

- [ ] **`run_id` system** — UUID per backtest run
- [ ] **Run artifact writer** — save all artifacts in the schema above
- [ ] **Result cache** (`sage_core/cache/result_cache.py`)
    - Implement the architecture described in `ARCHITECTURE.md`:
      config hash → `cache/systems/{hash}/` with equity, returns, weights, config snapshot
    - Add cache lookup before engine execution
- [ ] **Two data modes: `live` vs `snapshot`**
    - `live`: pulls latest from YFinance, uses 24h-expiry cache (current behavior)
    - `snapshot`: replays from pinned parquet, bypasses YFinance entirely
    - Pin data to parquet at experiment time (separate from the API cache)
    - Save data hash alongside run artifacts
    - Mode is a config option in `SystemConfig`
- [ ] **Save execution policy + cost model config** with each run
- [ ] **Environment capture** — record Python version and dependency lock hash in `env.txt`
- [ ] **Deterministic re-run validation**
    - `scripts/validate_reproducibility.py`: re-run from snapshot, assert identical results
- [ ] **Demo run command** — one-liner that produces a full run artifact:
    ```
    python -m sage_core.scripts.run_demo --config configs/presets/demo.yaml --mode snapshot
    ```
    - Ships with a small demo snapshot (few tickers, short date range)
    - Proves "clone → run → verify" in under 60 seconds
    - Massive hiring signal — interviewers can validate the system immediately

#### Write (≈10h)

- [ ] `docs/reproducibility.md`
    - Why YFinance is non-deterministic (adjusted close changes over time)
    - Data snapshot strategy
    - How `run_id` connects config → data → results
    - Artifact schema reference
    - Demo run walkthrough

**Outcome**: Every result can be re-created.

---

### Week 6 — Feature Store Architecture (40h)

**Why**: Bridge from quant systems → ML systems.

**Gap identified**: This is a **refactor**, not a greenfield build. The indicators already exist
inside strategy classes (6 indicator methods across `TrendStrategy` and `MeanRevStrategy`).
They must be extracted without breaking 27 existing test files.

#### Build (≈30h)

**Part A — Extract Indicators (~15h)**

- [ ] **Create `sage_core/features/` module**
- [ ] **Extract from `TrendStrategy`**:
    - `calculate_momentum_signal` → `MomentumFeature`
    - `calculate_ma_crossover_signal` → `MACrossoverFeature`
    - `calculate_breakout_signal` → `BreakoutFeature`
- [ ] **Extract from `MeanRevStrategy`**:
    - `calculate_rsi_signal` → `RSIFeature`
    - `calculate_bb_signal` → `BollingerBandFeature`
    - `calculate_zscore_signal` → `ZScoreFeature`
- [ ] **Create `FeatureGenerator` ABC** with `generate()`, `get_warmup_period()`
    - **Feature contract** — every generator must declare:
        - `required_columns`: which raw OHLCV columns it reads
        - `output_names`: column name(s) it produces
        - `warmup_period`: minimum history needed
        - `scope`: `"time_series"` (per-asset) or `"cross_sectional"` (across assets)
    - Contract is validated at registration time, not runtime
    - **Immutability rule** — features must be pure functions of historical data:
        - No internal state between calls
        - No access to previous predictions or model outputs
        - No dependence on portfolio state (weights, positions, PnL)
        - This prevents "feature leakage via strategy logic," makes features
          reusable across ML + non-ML, and makes testing trivial
        - Enforced via assertion: `generate()` called twice with the same input
          must produce identical output
- [ ] **Rewire strategies** to call feature generators (strategies become thin orchestrators)
- [ ] **Migrate tests** — ensure all 27 existing test files still pass

**Part B — Feature Registry (~10h)**

- [ ] **Feature registry** — config-driven definition of available features
- [ ] **Lookahead enforcement** at the feature level (centralized, not per-strategy)
- [ ] **Feature lineage** — which raw columns does each feature depend on?
- [ ] **Contract validation** — registry rejects generators with incomplete contracts
- [ ] **Feature namespacing** — column names must be globally unique and namespaced:
    - Convention: `{strategy}.{indicator}_{param}`, e.g.,
      `trend.momentum_20d`, `meanrev.rsi_14`, `xsec.rank_20d`
    - Registry enforces collision detection (hard error on duplicate names)
    - Prevents slow death by "two features both called `rsi`"

**Part C — Feature Matrix Builder (~5h)**

- [ ] **`FeatureMatrixBuilder`** (`sage_core/features/matrix_builder.py`)
    - Produces aligned `X` matrix from registered generators
    - **Canonical shape convention**: panel tensor `(time × asset × feature)`
        - Internal storage: 3D panel (time × asset × feature)
        - Helper `.to_long()` → long-format DataFrame `(timestamp, asset, feature…)`
        - Helper `.to_sklearn()` → 2D `(time*asset, feature)` flattened for sklearn
        - Naming the canonical format now avoids endless refactors later
    - Handles NaNs from warmup periods consistently (mask, don't fill)
    - Standard alignment rules for cross-sectional vs time-series features
    - Validates no lookahead in the assembled matrix
    - This is the bridge to Week 9 ML integration — models consume `X`, not raw DataFrames

**Part D — Infrastructure (~3h)**

- [ ] Add features to `SystemConfig`
- [ ] Feature generation as a discrete engine step (before strategy execution)

#### Write (≈10h)

- [ ] `docs/feature_store.md`
    - Lineage diagram
    - Feature contracts (inputs, outputs, warmup)
    - `FeatureMatrixBuilder` usage and alignment rules
    - Failure modes

**Outcome**: Features are reusable across strategies and ML models. The `FeatureMatrixBuilder`
makes Week 9 ML integration clean — models receive a well-formed `X` matrix, not ad-hoc DataFrames.

---

### Week 7 — Stationarity & Representation Experiments (40h)

**Why**: You learn when sophistication is justified — empirically, not by assumption.

#### Build (≈30h)

- [ ] **Implement representation transforms**:
    - Raw returns (baseline)
    - Volatility-scaled returns
    - Rolling z-scores
    - Fractional differentiation (optional, if time permits)
- [ ] **OOS stability comparison** — which transforms produce more stable features?
- [ ] **Integrate transforms into feature store** as configurable options

#### Write (≈10h)

- [ ] `experiments/stationarity.md`
    - Results and conclusions
    - When transforms help vs hurt

**Outcome**: Transform choices are justified empirically.

---

### Week 8 — Target Engineering (40h)

**Why**: Targets encode beliefs. They shape learning more than model choice.

#### Build (≈30h)

- [ ] **Triple-barrier labeling** (`sage_core/labels/triple_barrier.py`)
    - Profit take, stop loss, time expiry
- [ ] **Horizon-aware targets**
    - Multiple forecast horizons (1d, 5d, 21d)
    - Volatility-normalized return targets
- [ ] **Label diagnostics**:
    - Class imbalance analysis
    - Label drift over time
    - Distribution visualization

#### Write (≈10h)

- [ ] `docs/labels.md`
    - Why targets matter more than models
    - Triple-barrier explanation with examples
    - Diagnostic interpretation guide

**Outcome**: ML models will train on well-understood, properly constructed targets.

---

## PHASE 3: ML AS A CONTROLLED DECISION COMPONENT

**Theme**: "Models are tools, not magic."

---

### Week 9 — ModelWrapper & Training Discipline (40h)

**Why**: The moment ML enters the pipeline, but under strict discipline.

**Gap identified**: The current `Strategy` ABC enforces `generate_signals()` → discrete
{-1, 0, 1}. ML models may output probabilities or continuous scores. The ABC may need
extension before `ModelWrapperStrategy` can be built.

#### Key Design Decision

> **Strategies output intent, not positions.**
>
> Both rule-based and ML strategies output *intent*:
> - Rule-based: discrete signals ({-1, 0, 1})
> - ML models: continuous scores/probabilities
>
> The engine's `ExecutionPolicy` (from Week 1) converts intent into
> lagged positions. This keeps the timing guarantee universal and
> makes strategy authoring simpler.

#### Build (≈30h)

- [ ] **Extend `Strategy` ABC for intent-based output**
    - Add `generate_scores()` → returns continuous values (probabilities, scores)
    - Existing `generate_signals()` returns discrete {-1, 0, 1} (backward compatible)
    - Engine detects which method is implemented and handles both
    - Thresholding from scores → signals is configurable, not hardcoded
- [ ] **Implement `ModelWrapperStrategy`** (`sage_core/strategies/model_wrapper.py`)
    - Wraps sklearn-compatible models
    - **Explicit `fit` / `predict` lifecycle**:
        - `fit(train_data)`: train on walk-forward training window
        - `predict(test_data)`: generate scores on test window
        - Clear separation makes leakage reasoning easier
    - Train → validate → deploy within walk-forward
    - Consumes `X` matrix from `FeatureMatrixBuilder` (Week 6)
- [ ] **Train/validation split policy for time series**
    - Expanding window for training (no shuffling — ever)
    - Fixed-length validation tail for hyperparameter tuning
    - Scaler/normalizer fit on training data only — transform applied to val/test
    - Policy is a config option, not hardcoded
    - Document explicitly: walk-forward provides the *outer* split;
      this policy governs the *inner* split within each training window
- [ ] **Baseline models**:
    - Logistic Regression (linear baseline)
    - Random Forest
    - Gradient Boosting / XGBoost
- [ ] **Add `scikit-learn` and `xgboost` to `pyproject.toml`**
- [ ] **Update warmup system** (`utils/warmup.py`) for ML training windows
    - ML strategies need training window + prediction warmup (distinct from indicator warmup)
- [ ] **Prediction persistence** — save per-fold predictions as `predictions.parquet`
    in run artifacts (even before MLflow/W&B in Week 10):
    - Per-timestamp: predicted score/probability
    - Realized label/return
    - Fold ID
    - Enables Week 11 failure slicing without re-running training

#### Write (≈10h)

- [ ] `docs/ml_integration.md`
    - How models fit into the walk-forward loop
    - `fit` / `predict` lifecycle diagram
    - Train/val split policy (inner vs outer splits)
    - Training/validation/deployment lifecycle
    - How `ExecutionPolicy` applies to ML scores (intent → positions)
    - Why linear models come first
    - **Explicit non-goal: online / continual learning**
        - All models are trained only during walk-forward training windows
        - No model updates during live/test windows
        - Avoids leakage ambiguity, hard interview questions, and scope explosion
        - Online learning can be added later as a Phase 5 research extension

**Outcome**: ML enters the pipeline under controlled conditions.

---

### Week 10 — Experiment Tracking (40h)

**Why**: Without tracking, experiments are unreproducible anecdotes.

#### Build (≈30h)

- [ ] **MLflow or W&B integration** (`sage_core/tracking/`)
    - Choose one, implement adapter pattern for future swap
- [ ] **Track per run**:
    - Hyperparameters
    - Metrics (train, validation, test)
    - Fold-level results
    - Feature importance
- [ ] **Persist predictions** alongside model artifacts
- [ ] **Add `mlflow` (or `wandb`) to `pyproject.toml`**

#### Write (≈10h)

- [ ] `docs/experiments.md`
    - Tracking conventions
    - How to compare runs
    - Artifact storage structure

**Outcome**: Every experiment is traceable and comparable.

---

### Week 11 — Error Analysis & Failure Modes (40h)

**Why**: Understanding *when* a model fails matters more than its aggregate Sharpe.

#### Build (≈25h)

- [ ] **Reproducible regime classifier** (`sage_core/analysis/regime.py`)
    - Config-driven regime definitions (not hand-wavy slicing):
        - Rolling return + volatility thresholds, or
        - Moving average slope-based classification
    - Regime classifier config saved with run artifacts
    - Deterministic: same config + same data = same regime labels
- [ ] **Performance slicing**:
    - By market regime (bull/bear/sideways) — using the regime classifier above
    - By volatility state:
        - Primary: `realized_vol_quantiles` — rolling realized vol bucketed
          into terciles (low/medium/high). Data-driven, no external series required.
        - Optional: VIX-based states when equity data includes VIX.
          VIX is convenient but limits generality to US equities.
    - By time period (yearly, quarterly)
- [ ] **Feature drift diagnostics**
    - Distribution shift detection across walk-forward folds
- [ ] **Identify and catalog failure cases**
    - When does the model's edge disappear?

#### Write (≈15h)

- [ ] `docs/error_analysis.md`
    - Failure mode taxonomy
    - How to interpret regime-conditional results
    - Regime classifier configuration reference
    - Connection to model robustness

**Outcome**: You sound like a researcher, not a model user.

---

## PHASE 4: PROFESSIONALIZATION & DUAL-TRACK POSITIONING

**Theme**: "Can this support ML and quant interviews?"

---

### Week 12 — Documentation, Diagrams, and Narrative (40h)

- [ ] **Rewrite README** — research-grade, not project-template
- [ ] **Architecture diagrams** — Mermaid or draw.io, embedded in docs
- [ ] **Sync `ARCHITECTURE.md`** — remove references to unbuilt components, add what exists
- [ ] **Sync `DEVELOPMENT.md`** — update code examples to match actual interfaces
- [ ] **Explicit assumptions & limitations** section in every doc
- [ ] **Write `docs/design_decisions.md`** — why each major decision was made

---

### Week 13 — Resume & Interview Mapping (40h)

- [ ] **Map Sage → ML Engineer stories**
    - Walk-forward as cross-validation
    - Feature store as ML pipeline
    - Cost modeling as regularization
- [ ] **Map Sage → Quant Research stories**
    - No-lookahead guarantees
    - Attribution analysis
    - Robustness over optimization
- [ ] **Prepare explanations**:
    - Walk-forward engine (whiteboard-ready)
    - Cost modeling rationale
    - Why ML comes after baselines
- [ ] **5-minute demo narrative** — a scripted walkthrough:
    1. Clone repo
    2. Run demo command (`python -m sage_core.scripts.run_demo`)
    3. Open Streamlit
    4. Walk through: config → execution → attribution → failure case
    - This is packaging, not new work — and it's gold for interviews
    - Interviewers should be able to follow the script independently

---

### Week 14 — Optional Research Extensions (40h)

**Only if everything else is solid:**

- [ ] Robustness sweeps (parameter sensitivity across strategies)
- [ ] Limited DL baseline (LSTM on feature store data)
- [ ] Streamlit UI polish and new metric visualizations
- [ ] PyTorch integration groundwork

---

## PHASE 5: ADVANCED RESEARCH (Post-Roadmap, Ongoing)

### 5.1 Deep Learning for Time Series
- [ ] PyTorch integration
- [ ] Sequence models: LSTM / GRU, Temporal Fusion Transformers
- [ ] Comparative evaluation vs classical models
- *Rule*: Deep learning must justify its complexity empirically

### 5.2 Reinforcement Learning (Exploratory)
- [ ] OpenAI Gym-style environment wrapper
- [ ] PPO / SAC agents for allocation decisions
- [ ] Realistic cost-aware reward functions
- [ ] Conservative evaluation & ablation studies
- *Rule*: RL is a research extension — not the platform's core identity

---

## Cross-Cutting Concerns (Every Week)

These are recurring tasks not called out in individual weeks but required throughout:

| Concern | Budget | Details |
|---|---|---|
| **`SystemConfig` updates** | ~2h/week | Every engine feature requires config model changes |
| **`WalkforwardResult` updates** | ~1h/week | New metrics and outputs need result model updates |
| **Streamlit UI maintenance** | ~2h/week | New features must be reflected in the UI |
| **Existing test maintenance** | ~2h/week | Refactors will break existing tests |
| **`pyproject.toml` dependencies** | As needed | `cvxpy` (W3), `scikit-learn`/`xgboost` (W9), `mlflow`/`wandb` (W10) |
| **Docs sync** | ~1h/week | Keep ARCHITECTURE.md and DEVELOPMENT.md honest |

---

## Repo Visibility Strategy

**Recommended default**: Public core repo + deterministic demo snapshots.

| Public | Private |
|---|---|
| Engine, configs, docs, tests | API keys, credentials |
| Small demo data snapshots (few tickers, short range) | Heavy production datasets |
| All strategy implementations | "Best" config files (if you care) |
| Reproducibility scripts | |

Include small demo snapshots to prove reproducibility. This maximizes hiring signal —
interviewers can clone, run, and verify.

---

## What This Plan Optimizes For

✅ Research credibility
✅ ML systems maturity
✅ Quant rigor
✅ Transferability
✅ Interview depth

❌ Flashy models
❌ Speed
❌ Feature count
