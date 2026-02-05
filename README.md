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

**Current Phase**: Phase 3 - Cycle 1 (Foundation)  
**Current Focus**: Meta Allocation Layer (3C)

### Completed
- [x] **Phase 0**: Repository structure, packaging, core models
- [x] **Phase 1**: Basic engine with inverse-vol allocator
- [x] **Phase 2**: Professional Streamlit UI with multi-tab analytics
- [x] **Phase 3A**: Core system (real data, warmup, risk caps)
- [x] **Phase 3B**: Strategy framework (Trend, Mean Reversion)

### Phase 3: Research Platform - Iterative Cycles

**Approach**: Cyclic development across all system layers

#### Cycle 1: Foundation (Current - 4-6 weeks)
**Goal**: Complete minimum viable research platform

- [x] **3A-3B**: Core system + Strategies ✅
- [ ] **3C**: Meta Allocation Layer (Current)
  - Strategy warmup masking
  - Meta allocator framework
  - Fixed Weight + Risk Parity meta allocators
  - Engine and UI integration
- [ ] **3D**: Asset Allocator Suite
  - Minimum Variance allocator
  - Risk Parity allocator (asset-level)
- [ ] **3E**: Transaction Costs
  - Cost framework (commissions, spread)
  - Engine integration

**Cycle 1 Deliverable**: Production-ready research platform

#### Cycle 2: Enhancement (Future - can run parallel to Phase 4)
- Additional strategies (Carry, Value, Statistical Arbitrage)
- Regime detection and strategy gating
- Advanced meta allocation methods
- Risk contribution analytics
- UI polish and advanced visualizations

#### Cycle 3: Optimization (Future - can run parallel to Phase 5)
- Performance optimization (10x improvement)
- Scalability (100+ assets)
- Parameter optimization framework
- Research workflow tools

**Key Insight**: Complete Cycle 1, then iterate on Cycles 2-3 while building live trading infrastructure (Phase 4+)

### Roadmap to Live Trading

- [ ] **Phase 4** (2-3 months): Pre-Live Trading Infrastructure
  - Paper trading engine
  - Real-time data integration
  - Risk monitoring system
  - *Can run parallel to Cycle 2*

- [ ] **Phase 5** (1-2 months): Broker Integration
  - Broker abstraction layer (Alpaca, IB)
  - Order execution engine
  - Paper trading validation
  - *Can run parallel to Cycle 3*

- [ ] **Phase 6** (1-2 months): Live Trading Launch
  - Pre-launch validation
  - Soft launch → Full deployment
  - *Cycles 2-3 continue as ongoing improvements*

**Timeline**: 
- Cycle 1: 4-6 weeks
- Phase 4-6: 12-18 months (with Cycles 2-3 in parallel)

See `docs/PHASE_3_PLAN.md` for detailed cycle breakdown.

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
