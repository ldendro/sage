# Sage: ML Systems Research Platform Roadmap

**Vision**: Sage is a professional-grade machine learning systems research platform for decision-making under uncertainty, using quantitative finance as the primary domain.

The platform emphasizes:
- **Rigorous offline evaluation**
- **Reproducibility**
- **Clear separation** of data, models, and decisions
- **Engineering discipline** over model hype

Sage serves as a long-term backbone for applied ML, Deep Learning, and Reinforcement Learning research, while remaining a strong standalone demonstration of ML engineering maturity.

---

## Phase 1: Core Simulation & Evaluation Foundation
**Goal**: Build a rigorous, reproducible decision-simulation engine capable of supporting ML-driven strategies.
**Status**: ~80% Complete

### 1.1 Simulation Engine (Complete ✅)
- [x] **Hybrid Event-Driven / Vectorized Architecture**
- [x] **Walk-Forward Cross-Validation Engine**
- [x] **Strategy-level and Meta-level execution loop**
- [x] **Streamlit-based visualization dashboard**

### 1.2 Strategy Architecture & Data Integrity (In Progress 🔄)
**Goal**: Ensure strategies produce clean, ML-safe data.
- [ ] **Strategy Warmup Masking**
    - Each strategy explicitly manages its own warmup period.
    - Prevents leakage into feature/label construction.
- [ ] **Strategy Interface Standardization**
    - Clear contract: inputs, outputs, lifecycle.
- [ ] **Unit Testing**
    - 100% coverage on Strategy and Meta-allocation logic.

### 1.3 Cost & Friction Modeling (Pending ⏳)
**Goal**: Introduce realistic market constraints as a first-class regularizer.
- [ ] **Transaction cost framework**:
    - Bid–ask spread
    - Slippage
    - Market impact (simple + extensible models)
- [ ] **Cost attribution reporting**
- *Rationale*: Zero-cost environments lead to pathological ML and RL behavior. Realistic friction is essential for credibility.

### 1.4 Convex Portfolio Optimization (Pending ⏳)
**Goal**: Establish a mathematically grounded portfolio construction baseline.
- [ ] **Mean–Variance Optimization** (`cvxpy` integration)
- [ ] **Risk parity / constrained optimization extensions**
- [ ] **Allocator abstraction layer**
- *Rationale*: Learn and demonstrate classical optimization before delegating allocation to learned models.

### 1.5 Evaluation & Baseline Framework (NEW — Critical)
**Goal**: Make evaluation and comparison explicit and defensible.
- [ ] **Naive baselines**:
    - Equal-weight
    - Buy-and-hold
    - Volatility targeting
- [ ] **Metric layer**:
    - Sharpe, drawdown, turnover
    - Hit-rate, stability across folds
- [ ] **Attribution analysis**:
    - Signal vs allocation vs leverage effects

*This phase completion marks Sage as a credible ML experimentation platform.*

---

## Phase 2: Data Modeling & Representation
**Goal**: Transition from heuristic strategies to structured features, targets, and datasets.
**Timeline**: ~4–6 weeks

### 2.1 Feature Store & Data Abstractions
- [ ] **Feature Generators**: Decouple indicators from strategies into standalone generators.
- [ ] **Unified feature registry**: Config-driven definition of availble features.
- [ ] **Stationarity transformations**:
    - Fractional differentiation (as one option, not default).
    - Comparative analysis vs simpler transforms.
- [ ] **Macro & cross-asset data integration**:
    - VIX, Interest rates, Market breadth.

### 2.2 Target & Label Engineering
- [ ] **Triple-Barrier Method**: Profit, stop-loss, time-out labels.
- [ ] **Volatility-normalized return targets**
- [ ] **Horizon-aware labeling**
- [ ] **Label diagnostics & distribution checks**
- *Rationale*: Targets define learning behavior more than models.

---

## Phase 3: Model-Driven Decision Systems (Classical ML)
**Goal**: Integrate predictive models into the decision pipeline with strict offline validation.
**Timeline**: ~1–2 months

### 3.1 Scikit-Learn Model Integration
- [ ] **ModelWrapperStrategy abstraction**
- [ ] **Baseline Models**: Random Forest, Gradient Boosting / XGBoost.
- [ ] **Training orchestration**: Train → Validate → Deploy (within walk-forward).
- [ ] **Feature importance & stability analysis**

### 3.2 Experiment Tracking & Reproducibility (MLOps)
- [ ] **MLflow / Weights & Biases integration**
- [ ] **Experiment metadata**: Hyperparameters, Metrics, Fold-level results.
- [ ] **Artifact storage**: Models, predictions.

### 3.3 Error Analysis & Failure Modes (NEW)
- [ ] **Performance slicing by**:
    - Market regime
    - Volatility state
- [ ] **Feature drift diagnostics**
- [ ] **Stability analysis** across time splits

*This phase defines Sage as an ML engineering system, not a modeling demo.*

---

## Phase 4: Advanced Deep Learning & Reinforcement Learning (Research Track)
**Goal**: Explore state-of-the-art methods only where justified.
**Timeline**: Ongoing / Optional

### 4.1 Deep Learning for Time Series
- [ ] **PyTorch integration**
- [ ] **Sequence models**: LSTM / GRU, Temporal Fusion Transformers.
- [ ] **Comparative evaluation** vs classical models.
- *Rule*: Deep learning must justify its complexity empirically.

### 4.2 Reinforcement Learning (Exploratory)
- [ ] **OpenAI Gym-style environment wrapper**
- [ ] **PPO / SAC agents** for allocation decisions.
- [ ] **Realistic cost-aware reward functions**
- [ ] **Conservative evaluation & ablation studies**
- *Rule*: RL is a research extension — not the platform’s core identity.

---

## Immediate Priorities (Next Execution Window)

1.  **Finalize Strategy Warmup Masking** (Step 1.2)
2.  **Implement Cost Modeling** (`sage_core/costs`) (Step 1.3)
3.  **Add Mean–Variance Optimizer** (`sage_core/allocators/mean_variance.py`) (Step 1.4)
4.  **Introduce Baseline & Evaluation Layer** (Step 1.5)

*Completion of these marks Phase 1 Done and unlocks Phase 2.*
