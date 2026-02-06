"""Streamlit Backtesting App - Main Entry Point."""

import streamlit as st
import sys
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import components
from app.components.header import render_header
from app.components import universe, portfolios, execution, results
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
    if "portfolio_results" not in st.session_state:
        st.session_state.portfolio_results = {}
    if "portfolio_configs" not in st.session_state:
        st.session_state.portfolio_configs = {}
    if "portfolio_errors" not in st.session_state:
        st.session_state.portfolio_errors = {}

    # ==================== SIDEBAR CONFIGURATION ====================
    
    # 1. Universe Selection
    univ_config = universe.render()
    
    # 2. Portfolio Systems
    portfolio_state = portfolios.render(univ_config['universe'])
    
    # 6. Execution (Run Button)
    all_errors = (
        univ_config['errors'] +
        portfolio_state['errors']
    )
    
    run_clicked = execution.render(all_errors)
    
    # 7. Advanced Settings
    execution.render_advanced_settings()
    
    # ==================== BACKTEST EXECUTION ====================
    if run_clicked and not all_errors:
        # Build composite config
        with st.spinner("Running backtest... This may take a moment."):
            try:
                portfolio_results = {}
                portfolio_configs = {}
                portfolio_errors = {}

                for portfolio in portfolio_state['portfolios']:
                    config = portfolio_state['configs'].get(portfolio['id'], {})
                    current_config = {
                        **univ_config,
                        **config,
                        "portfolio_name": portfolio["name"],
                        "portfolio_color": portfolio["color"],
                    }
                    portfolio_configs[portfolio['id']] = current_config

                    try:
                        results_data = run_system_walkforward(
                            universe=univ_config['universe'],
                            start_date=univ_config['start_date'],
                            end_date=univ_config['end_date'],
                            strategies=config['strategies'],
                            meta_allocator=config['meta_allocator'],
                            # Risk Params
                            max_weight_per_asset=config['max_weight_per_asset'],
                            max_sector_weight=config['max_sector_weight'],
                            min_assets_held=config['min_assets_held'],
                            cap_mode=config['cap_mode'],
                            # Vol Params
                            target_vol=config['target_vol'],
                            vol_lookback=config['vol_lookback'],
                            min_leverage=config['min_leverage'],
                            max_leverage=config['max_leverage'],
                            vol_window=config['vol_window'],
                        )
                        portfolio_results[portfolio['id']] = results_data
                    except Exception as e:
                        logger.error(
                            f"Backtest failed for {portfolio['name']}: {str(e)}",
                            exc_info=True,
                        )
                        portfolio_errors[portfolio['id']] = str(e)

                st.session_state.portfolio_results = portfolio_results
                st.session_state.portfolio_configs = portfolio_configs
                st.session_state.portfolio_errors = portfolio_errors
                
            except Exception as e:
                logger.error(f"Backtest failed: {str(e)}", exc_info=True)
                st.session_state.portfolio_results = {}
                st.session_state.portfolio_errors = {"system": str(e)}

    # ==================== RESULTS DISPLAY ====================
    if st.session_state.portfolio_results or st.session_state.portfolio_errors:
        results.render(
            st.session_state.portfolio_results,
            st.session_state.portfolio_configs,
            portfolio_state['portfolios'],
            st.session_state.portfolio_errors,
        )
    else:
        st.info("👈 Configure parameters in the sidebar and click 'Run Backtest' to begin")

    # Footer
    st.markdown("---")
    st.caption("Sage Backtesting Engine v2.0 | Modularized Streamlit App")

if __name__ == "__main__":
    main()
