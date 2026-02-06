"""Streamlit Backtesting App - Main Entry Point."""

import streamlit as st
import sys
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import components
from app.components.header import render_header
from app.components import universe, strategies, meta, allocator, risk, execution, results
from sage_core.walkforward.engine import run_system_walkforward

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Sage Backtesting Engine",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # ==================== HEADER ====================
    render_header(
        "Sage Backtesting Engine",
        "Interactive backtesting dashboard for quantitative strategies",
        icon_path=Path(__file__).parent / "images" / "SAGEICON.png",
    )
    
    # ==================== INITIALIZE SESSION STATE ====================
    if "backtest_results" not in st.session_state:
        st.session_state.backtest_results = None
    if "backtest_params" not in st.session_state:
        st.session_state.backtest_params = None
    if "backtest_error" not in st.session_state:
        st.session_state.backtest_error = None

    # ==================== SIDEBAR CONFIGURATION ====================
    
    # 1. Universe Selection
    univ_config = universe.render()
    
    # 2. Strategy Selection
    strat_config = strategies.render()
    
    # 3. Meta Allocator
    meta_config = meta.render(strat_config['selected_strategies'])
    
    # 4. Asset Allocator
    allocator_config = allocator.render()

    # 5. Risk & Volatility Targeting
    risk_config = risk.render(univ_config['universe'])
    
    # 6. Execution (Run Button)
    all_errors = (
        univ_config['errors'] + 
        strat_config['errors'] + 
        meta_config['errors'] + 
        allocator_config['errors'] + 
        risk_config['errors']
    )
    
    run_clicked = execution.render(all_errors)
    
    # 7. Advanced Settings
    execution.render_advanced_settings()
    
    # About Section
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.info("""
    **Sage Backtesting Engine v2.0**
    
    Phase 2: Streamlit App
    - Multi-strategy support
    - Meta-allocator integration
    - Modular architecture
    """)
    
    # ==================== BACKTEST EXECUTION ====================
    if run_clicked and not all_errors:
        # Build composite config
        current_config = {
            **univ_config,
            **strat_config,
            **meta_config,
            **allocator_config,
            **risk_config
        }
        
        with st.spinner("Running backtest... This may take a moment."):
            try:
                # logger.info(f"Starting backtest with {len(univ_config['universe'])} assets")
                
                results_data = run_system_walkforward(
                    universe=univ_config['universe'],
                    start_date=univ_config['start_date'],
                    end_date=univ_config['end_date'],
                    strategies=strat_config['strategies'],
                    meta_allocator=meta_config['meta_allocator'],
                    # Risk Params
                    max_weight_per_asset=risk_config['max_weight_per_asset'],
                    max_sector_weight=risk_config['max_sector_weight'],
                    min_assets_held=risk_config['min_assets_held'],
                    cap_mode=risk_config['cap_mode'],
                    # Vol Params
                    target_vol=risk_config['target_vol'],
                    vol_lookback=risk_config['vol_lookback'],
                    min_leverage=risk_config['min_leverage'],
                    max_leverage=risk_config['max_leverage'],
                    vol_window=allocator_config['vol_window'],
                )
                
                st.session_state.backtest_results = results_data
                st.session_state.backtest_params = current_config
                st.session_state.backtest_error = None
                
            except Exception as e:
                logger.error(f"Backtest failed: {str(e)}", exc_info=True)
                st.session_state.backtest_results = None
                st.session_state.backtest_error = str(e)

    # ==================== RESULTS DISPLAY ====================
    if st.session_state.backtest_error:
        results.render_error(st.session_state.backtest_error)
        
    elif st.session_state.backtest_results:
        results.render(
            st.session_state.backtest_results,
            st.session_state.backtest_params
        )
    else:
        st.info("👈 Configure parameters in the sidebar and click 'Run Backtest' to begin")

    # Footer
    st.markdown("---")
    st.caption("Sage Backtesting Engine v2.0 | Modularized Streamlit App")

if __name__ == "__main__":
    main()
