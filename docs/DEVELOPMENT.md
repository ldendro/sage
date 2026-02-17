# Sage Development Guide

## Getting Started

### Prerequisites

- **Python 3.10+** (for modern type hints)
- **Git** (for version control)
- **pip** (for package management)

### Initial Setup

```bash
# Clone the repository
git clone <repo-url>
cd sage

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Verify installation
python -m pytest tests/ -v
```

### Quick Demo Run (Planned — ROADMAP Week 5)

Once the run artifact system is implemented:

```bash
# Produce a full run artifact end-to-end
python -m sage_core.scripts.run_demo --config configs/presets/demo.yaml --mode snapshot
```

This ships with a small demo snapshot (few tickers, short date range) and proves
"clone → run → verify" in under 60 seconds.

---

## Project Structure

```
sage/
├── sage_core/              # Core backtesting engine
│   ├── config/            # Configuration models (SystemConfig, Pydantic)
│   ├── data/              # Data ingestion & loading
│   ├── strategies/        # Trading strategies (intent output only)
│   ├── meta/              # Meta-allocation layer (combination + gates)
│   ├── allocators/        # Portfolio allocators (InvVol, EqualWeight, MeanVar*)
│   ├── portfolio/         # Portfolio construction (risk caps, vol targeting)
│   ├── walkforward/       # Walkforward engine
│   ├── metrics/           # Performance metrics (Sharpe, DD, CAGR, turnover)
│   ├── cache/             # Result caching (config hash → artifacts)
│   ├── utils/             # Shared utilities (paths, warmup, logging)
│   ├── execution/         # ExecutionModule + ExecutionPolicy (planned)
│   ├── features/          # Feature store + FeatureMatrixBuilder (planned)
│   ├── costs/             # Transaction cost model (planned)
│   ├── analysis/          # Regime classifier, error analysis (planned)
│   ├── tracking/          # Experiment tracking - MLflow/W&B (planned)
│   └── scripts/           # run_demo, validate_reproducibility (planned)
│
├── app/                   # Streamlit visualization app
│   ├── streamlit_app.py  # Main entry point
│   └── ui/               # UI components
│
├── tests/                 # Test suite (27 files)
│   ├── conftest.py       # Shared fixtures
│   ├── test_config.py    # Config tests
│   ├── test_utils.py     # Utility tests
│   ├── test_fixtures.py  # Fixture tests
│   └── test_invariants.py # Invariant test suite (planned)
│
├── configs/presets/       # Preset configurations
├── data/                  # Market data (+ snapshots for reproducibility)
├── cache/                 # Cached results
├── docs/                  # Documentation
│   ├── ARCHITECTURE.md   # System design & decisions
│   ├── DEVELOPMENT.md    # This file
│   └── ROADMAP.md        # 14-week execution plan
│
├── runs/                  # Run artifacts (planned)
└── scripts/               # Utility scripts
```

> Items marked *(planned)* are defined in `ROADMAP.md` and do not yet exist in the codebase.

---

## Development Workflow

### 1. **Create a Feature Branch**

```bash
git checkout -b feature/your-feature-name
```

### 2. **Make Changes**

Follow these guidelines:
- Use type hints everywhere
- Write docstrings for all public functions/classes
- Keep functions focused and testable
- Follow existing code style
- **Strategies must return intent (signals/scores), never positions or returns**
- **Features must be pure functions of historical data** (no internal state)

### 3. **Run Tests**

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run with coverage
pytest --cov=sage_core --cov=app

# Run with verbose output
pytest -v

# Run invariant tests only (once implemented)
pytest tests/test_invariants.py -v
```

### 4. **Format Code**

```bash
# Format with black
black .

# Lint with ruff
ruff check .

# Type check with mypy
mypy sage_core app
```

### 5. **Commit Changes**

```bash
git add .
git commit -m "feat: add new feature"
```

**Commit Message Format**:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

### 6. **Push and Create PR**

```bash
git push origin feature/your-feature-name
```

---

## Testing Guidelines

### Writing Tests

**Location**: `tests/test_<module>.py`

**Structure**:
```python
def test_feature_name():
    """Test that feature works correctly."""
    # Arrange
    config = SystemConfig(...)

    # Act
    result = some_function(config)

    # Assert
    assert result.some_property == expected_value
```

### Using Fixtures

```python
def test_with_fixture(default_system_config):
    """Test using a fixture from conftest.py."""
    assert default_system_config.name == "Test System"
```

### Test Coverage Goals

- **Config models**: 100% coverage
- **Core logic**: >90% coverage
- **UI components**: >70% coverage
- **Invariants**: Must all pass (zero tolerance)

### Invariant Tests (Planned — ROADMAP Week 4)

These tests prove system correctness and must never be skipped:

```python
# tests/test_invariants.py

def test_zero_signals_zero_returns():
    """Zero signals must produce zero returns."""
    ...

def test_cost_free_gross_equals_net():
    """When costs = 0, gross_returns must equal net_returns."""
    ...

def test_cost_monotonicity():
    """Increasing costs should decrease avg daily net return.
    Scoped to PassthroughStrategy + equal-weight allocator."""
    ...

def test_execution_delay_changes_performance():
    """Delaying execution by +k days must produce different results.
    If identical, same-bar execution is happening silently."""
    ...

def test_no_silent_alignment():
    """Mismatched timestamps between signals and prices must error.
    Catches silent .reindex() / join() behavior."""
    ...

def test_attribution_conservation():
    """gross_returns ≈ signal + allocation + leverage components.
    net_returns = gross - cost_total. Within tolerance."""
    ...
```

---

## Code Style

### Type Hints

**Always use type hints**:
```python
def calculate_sharpe(returns: pd.Series, annual_factor: float = 252.0) -> float:
    """Calculate annualized Sharpe ratio."""
    return float(np.sqrt(annual_factor) * returns.mean() / returns.std())
```

### Docstrings

**Use Google-style docstrings**:
```python
def align_returns(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Align returns across multiple assets.

    Args:
        data: Dictionary mapping symbols to DataFrames with returns

    Returns:
        Wide DataFrame with index=date, columns=symbols, values=returns

    Raises:
        ValueError: If data is empty or misaligned
    """
    ...
```

### Naming Conventions

- **Functions/methods**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private**: `_leading_underscore`
- **Feature columns**: `{strategy}.{indicator}_{param}` (e.g., `trend.momentum_20d`, `meanrev.rsi_14`)

### Terminology

Use these terms consistently throughout the codebase:

| Term | Meaning | Example |
|---|---|---|
| **Intent** | Raw strategy output (signals or scores) | `{"SPY": +1, "TLT": -1}` |
| **Target weights** | Desired weights after exposure mapping | `{"SPY": 0.6, "TLT": 0.4}` |
| **Held weights** | Actual weights after execution + drift | `{"SPY": 0.58, "TLT": 0.42}` |
| **Gross returns** | Pre-cost portfolio returns | — |
| **Net returns** | Post-cost portfolio returns | — |

---

## Adding New Components

### Adding a New Strategy

Strategies output **intent** (signals or scores), never positions or returns.
The engine handles timing and exposure mapping.

1. **Create strategy file**: `sage_core/strategies/my_strategy_v1.py`

```python
import pandas as pd

class Strategy:
    """Strategy Protocol — all strategies must conform to this interface."""
    name: str

    def run(
        self,
        asset_data: dict[str, pd.DataFrame],
        schedule: "ScheduleConfig",
        cfg: "StrategyConfig",
    ) -> dict[str, pd.DataFrame]:
        """
        Generate intent (signals/scores) at time t.

        Returns:
            Dict mapping asset symbols to DataFrames with raw signals.
            Signals are UNSHIFTED — the engine applies ExecutionPolicy
            to produce lagged positions at t+1.
        """
        ...
```

2. **Implement strategy**:
```python
def run_my_strategy_v1(
    df: pd.DataFrame,
    train_df: pd.DataFrame,
    params: dict,
) -> pd.DataFrame:
    """
    My custom strategy implementation.

    Args:
        df: Test period data
        train_df: Training period data
        params: Strategy parameters

    Returns:
        DataFrame with raw signals (intent).
        Do NOT shift signals — the engine handles timing.
        Do NOT compute returns — the engine handles that.
    """
    # Your signal logic here
    signals = ...
    return signals
```

3. **Add to config**: Update `StrategyConfig` in `system_config.py`
```python
strategies: List[Literal["trend_v1", "meanrev_v1", "my_strategy_v1"]]
```

4. **Write tests**: `tests/test_strategies.py`
   - Test signal output shape and values
   - Test that strategy does NOT return shifted signals
   - Test warmup period handling

### Adding a New Allocator

Allocators take validated signals and produce portfolio weights.
All allocators must satisfy the **output contract** (see `ARCHITECTURE.md`).

1. **Create allocator file**: `sage_core/allocators/my_allocator_v1.py`

```python
# Current pattern (bare functions):
def compute_my_weights(
    returns: pd.DataFrame,
    lookback: int,
    **kwargs,
) -> pd.Series:
    """
    Compute portfolio weights.

    Output contract (enforced by AssetAllocator ABC once implemented):
    - Weights sum to 1.0 (or target gross exposure)
    - Per-asset bounds respected
    - No NaN values
    - Must never raise — return fallback weights on failure
    """
    ...
```

2. **Planned ABC pattern** (ROADMAP Week 3):
```python
from sage_core.allocators.base import AssetAllocator

class MyAllocator(AssetAllocator):
    def validate_params(self) -> None: ...
    def get_warmup_period(self) -> int: ...
    def compute_weights(self, returns: pd.DataFrame) -> pd.Series:
        """_validate_output() is called automatically after this."""
        ...
```

3. **Add to config**: Update `AllocatorConfig` in `system_config.py`
4. **Write tests**: Verify output contract compliance

### Adding a New Feature Generator (Planned — ROADMAP Week 6)

Features are pure functions of historical data — no internal state, no access
to predictions or portfolio state.

```python
from sage_core.features.base import FeatureGenerator

class MyFeature(FeatureGenerator):
    required_columns = ["close"]
    output_names = ["mystrategy.my_indicator_20d"]  # namespaced!
    warmup_period = 20
    scope = "time_series"  # or "cross_sectional"

    def generate(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Pure function: same input → same output (always).
        No internal state between calls.
        """
        ...
```

**Testing**: Call `generate()` twice with the same input — assert identical output.

---

## Common Tasks

### Running the Streamlit App

```bash
streamlit run app/streamlit_app.py
```

### Generating Sample Data

```python
from tests.conftest import sample_returns, sample_prices

# Use fixtures in scripts
returns = sample_returns(...)
```

### Creating a Preset Config

1. Create TOML file: `configs/presets/my_preset.toml`

```toml
name = "My Preset"
universe = ["SPY", "QQQ", "IWM"]
start_date = "2020-01-01"
end_date = "2024-12-31"

[strategy]
strategies = ["trend_v1", "meanrev_v1"]

[meta]
combination_method = "hard_v1"
use_gates = true

[allocator]
type = "risk_parity_v1"
lookback = 126

[portfolio]
use_risk_caps = true
vol_targeting_enabled = true
```

2. Load in code:
```python
from sage_core.utils.paths import get_preset_config_path
import toml

config_path = get_preset_config_path("my_preset")
config_dict = toml.load(config_path)
config = SystemConfig.from_dict(config_dict)
```

---

## Debugging

### Verbose Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
```

### Interactive Debugging

```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use ipdb (install with: pip install ipdb)
import ipdb; ipdb.set_trace()
```

### Pytest Debugging

```bash
# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Print output (disable capture)
pytest -s
```

---

## Performance Profiling

### Line Profiler

```bash
pip install line_profiler

# Add @profile decorator to function
# Run with:
kernprof -l -v script.py
```

### Memory Profiler

```bash
pip install memory_profiler

# Add @profile decorator
# Run with:
python -m memory_profiler script.py
```

---

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'sage_core'`

**Solution**: Install in development mode:
```bash
pip install -e .
```

### Test Failures

**Problem**: Tests fail after changes

**Solution**:
1. Check if fixtures need updating
2. Verify config changes are backward compatible
3. Run single test to isolate issue: `pytest tests/test_file.py::test_name -v`

### Permission Errors

**Problem**: `PermissionError` when running tests

**Solution**: Ensure directories are writable, or use `tmp_path` fixture for tests

---

## Release Process

### Version Bumping

1. Update version in `pyproject.toml`
2. Update `__version__` in `sage_core/__init__.py`
3. Update `CHANGELOG.md`
4. Commit: `git commit -m "chore: bump version to X.Y.Z"`
5. Tag: `git tag vX.Y.Z`
6. Push: `git push && git push --tags`

---

## Resources

- **Architecture**: See `docs/ARCHITECTURE.md`
- **Roadmap**: See `docs/ROADMAP.md`
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Pandas Docs**: https://pandas.pydata.org/docs/
- **Streamlit Docs**: https://docs.streamlit.io/

---

## Getting Help

- **Issues**: Open a GitHub issue
- **Questions**: Use GitHub Discussions

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Ensure all tests pass
6. Submit a pull request

**Code Review Checklist**:
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted (black)
- [ ] No linting errors (ruff)
- [ ] Type hints added
- [ ] Docstrings complete
- [ ] Strategies return intent only (no positions/returns)
- [ ] Features are pure functions (no internal state)
- [ ] Feature names are namespaced (`{strategy}.{indicator}_{param}`)
