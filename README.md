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

### `app` - Visualization UI
Streamlit-based interactive research interface:
- Define up to 5 system configurations simultaneously
- Edit configs via dynamic sidebar controls
- Run backtests with automatic caching
- Compare equity curves, yearly metrics, risk statistics
- Export results and configurations


---

## Development Status

**Current Phase**: Phase 1.2 - Strategy Architecture & Data Integrity  
**Goal**: Ensuring reproducible, clean data generation for ML systems.

### Completed (Phase 1.1)
- [x] **Simulation Engine**: Hybrid Event-Driven/Vectorized architecture
- [x] **Walk-Forward Validation**: Cross-validation engine working
- [x] **Visualization**: Streamlit analytics dashboard

### Roadmap: ML Systems Research Platform

Sage is an engineering-first research platform for ML-driven quantitative finance.
See `docs/ROADMAP.md` for the detailed execution plan.

- [ ] **Phase 1**: Core Simulation & Evaluation Foundation (Current)
  - Strategy Warmup Masking (In Progress)
  - Cost & Friction Modeling (Pending)
  - Convex Optimization (`cvxpy` integration)
  - Baseline & Evaluation Framework

- [ ] **Phase 2**: Data Modeling & Representation
  - Feature Store & Data Abstractions
  - Target & Label Engineering (Triple-Barrier Method)
  - Stationarity Transformations

- [ ] **Phase 3**: Model-Driven Decision Systems
  - Scikit-Learn Integration (Random Forest, XGBoost)
  - Experiment Tracking (MLflow/W&B)
  - Error Analysis & Drift Diagnostics

- [ ] **Phase 4**: Advanced Deep Learning & RL
  - PyTorch Sequence Models (LSTM/Transformer)
  - Reinforcement Learning Agents (PPO/SAC)

**Immedate Priorities**:
1. Strategy Warmup Masking (Data Integrity)
2. Transaction Cost Modeling (RL Environment)
3. Mean-Variance Optimizer (Math Foundation)

See `docs/ROADMAP.md` for details.

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
