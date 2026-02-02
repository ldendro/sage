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

---

## Project Structure

```
sage/
├── sage_core/              # Core backtesting engine
│   ├── config/            # Configuration models
│   ├── data/              # Data ingestion & loading
│   ├── strategies/        # Trading strategies
│   ├── meta/              # Meta-allocation layer
│   ├── allocators/        # Portfolio allocators
│   ├── portfolio/         # Portfolio construction
│   ├── walkforward/       # Walkforward engine
│   ├── cache/             # Result caching
│   └── utils/             # Shared utilities
│
├── sage_viz/              # Streamlit visualization app
│   ├── app.py            # Main entry point
│   └── ui/               # UI components
│
├── tests/                 # Test suite
│   ├── conftest.py       # Shared fixtures
│   ├── test_config.py    # Config tests
│   ├── test_utils.py     # Utility tests
│   └── test_fixtures.py  # Fixture tests
│
├── configs/presets/       # Preset configurations
├── data/                  # Market data
├── cache/                 # Cached results
├── docs/                  # Documentation
└── scripts/               # Utility scripts
```

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

### 3. **Run Tests**

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run with coverage
pytest --cov=sage_core --cov=sage_viz

# Run with verbose output
pytest -v
```

### 4. **Format Code**

```bash
# Format with black
black .

# Lint with ruff
ruff check .

# Type check with mypy
mypy sage_core sage_viz
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

---

## Adding New Components

### Adding a New Strategy

1. **Create strategy file**: `sage_core/strategies/my_strategy_v1.py`

```python
from typing import Protocol
import pandas as pd

class Strategy(Protocol):
    name: str
    
    def run(
        self,
        asset_data: dict[str, pd.DataFrame],
        schedule: "ScheduleConfig",
        cfg: "StrategyConfig",
    ) -> dict[str, pd.DataFrame]:
        """Run strategy and return signals."""
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
        DataFrame with signals and meta_raw_ret
    """
    # Your logic here
    ...
```

3. **Add to config**: Update `StrategyConfig` in `system_config.py`
```python
strategies: List[Literal["trend_v1", "meanrev_v1", "my_strategy_v1"]]
```

4. **Write tests**: `tests/test_strategies.py`

### Adding a New Allocator

Similar process to strategies. See `docs/ARCHITECTURE.md` for allocator interface.

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
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Pandas Docs**: https://pandas.pydata.org/docs/
- **Streamlit Docs**: https://docs.streamlit.io/

---

## Getting Help

- **Issues**: Open a GitHub issue
- **Questions**: Use GitHub Discussions
- **Slack**: [Your Slack channel]

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
