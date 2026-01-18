# Sage

**Sage: Systematic Trading Research Platform and Walkforward Backtesting Engine**

Sage is a production-grade research platform for designing, testing, and comparing systematic trading strategies. Built under the Rosemary brand (parent company/strategy), Sage provides a rigorous, config-driven framework for walkforward backtesting with strict no-lookahead guarantees.

---

## Overview

Sage enables you to:
- **Design & test** systematic trading strategies (trend, mean reversion, multi-strategy combinations)
- **Run walkforward backtests** with configurable frequencies per layer (strategy training, allocator rebalancing, portfolio mechanics)
- **Compare systems** side-by-side with comprehensive performance and risk metrics
- **Visualize results** interactively via Streamlit UI
- **Enforce rigor** with paranoid lookahead bias prevention and live-trading feasibility focus

---

## Philosophy

Sage is built with these core principles:

1. **No Lookahead Bias**: Strict train/test splits, rolling/expanding windows, explicit data availability at each decision point
2. **Live Trading Feasibility**: Focus on drawdowns, leverage, turnover, risk concentration—not just pretty equity curves
3. **Robustness Over Optimization**: Simple, justifiable methods; interpretability over "max Sharpe at all costs"
4. **Config-Driven**: All systems defined via `SystemConfig` (Pydantic models), enabling reproducibility and caching
5. **Pluggable Architecture**: Strategies, allocators, and portfolio mechanics are modular and extensible
6. **Production-Grade**: Type hints, clean module boundaries, comprehensive testing, designed for eventual commercial use

---

## Architecture

Sage is organized as a monorepo with two main packages:

### `sage_core` - Core Engine
The backtesting engine and research library:
- **Data**: Ingestion, cleaning, validation, loading
- **Strategies**: Trend, mean reversion, multi-strategy combinations
- **Meta Layer**: Regime detection, strategy gating, signal combination
- **Allocators**: Inverse volatility, minimum variance, risk parity
- **Portfolio**: Weight construction, risk caps, volatility targeting
- **Walkforward**: Orchestration engine with configurable frequencies
- **Cache**: Config-based result caching for fast iteration

### `sage_viz` - Visualization UI
Streamlit-based interactive research interface:
- Define up to 5 system configurations simultaneously
- Edit configs via dynamic sidebar controls
- Run backtests with automatic caching
- Compare equity curves, yearly metrics, risk statistics
- Export results and configurations

---

## Project Structure

```
sage/
├── sage_core/              # Core backtesting engine
│   ├── data/              # Data ingestion & loading
│   ├── config/            # System configuration models
│   ├── strategies/        # Trading strategies
│   ├── meta/              # Meta-layer (regime, gating)
│   ├── allocators/        # Portfolio allocators
│   ├── portfolio/         # Portfolio construction & risk
│   ├── walkforward/       # Walkforward engine
│   ├── cache/             # Result caching
│   └── utils/             # Shared utilities
├── sage_viz/              # Streamlit visualization app
│   ├── app.py            # Main Streamlit entry point
│   └── ui/               # UI components
├── configs/               # Configuration files
│   └── presets/          # Preset system configs (TOML)
├── data/                  # Market data
│   ├── raw/              # Raw downloaded data
│   └── processed/        # Cleaned & validated data
├── cache/                 # Cached backtest results
│   └── systems/          # Per-system result storage
├── tests/                 # Test suite
├── scripts/               # Utility scripts
└── docs/                  # Documentation
```

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd sage

# Install in development mode
pip install -e ".[dev]"
```

### Running the Streamlit App

```bash
# Launch the visualization interface
streamlit run sage_viz/app.py

# Or use the convenience script
python scripts/run_app.py
```

### Running a Single Backtest (CLI)

```bash
# Run a preset configuration
python scripts/run_single_backtest.py --config configs/presets/baseline_invvol.toml
```

---

## Development Status

**Current Phase**: Phase 0 - Repository Bootstrap

### Roadmap

- [x] **Phase 0**: Repository structure, packaging, core models
- [ ] **Phase 1**: Basic engine with simple strategy and inverse-vol allocator
- [ ] **Phase 2**: Streamlit UI v1 (single then multi-config comparison)
- [ ] **Phase 3**: Integrate real strategies & allocators from legacy phases
- [ ] **Phase 4**: Configurable frequencies & schedules (annual/quarterly rebalancing)
- [ ] **Phase 5**: Risk metrics, UX enhancements, "Hall of Fame" top systems

---

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sage_core --cov=sage_viz

# Run specific test file
pytest tests/test_config.py
```

---

## Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy sage_core sage_viz
```

---

## License

MIT License - See LICENSE file for details

---

## Contact

Part of the **Rosemary** systematic trading project.

For questions or collaboration: [Your contact info]
