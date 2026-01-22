#!/usr/bin/env python
"""
Run a single backtest using the Sage backtesting engine.

This script provides a command-line interface for running backtests with
configurable parameters. Results are displayed in the console and optionally
saved to files.

Example Usage:
    Basic:
        python scripts/run_single_backtest.py \\
            --universe SPY QQQ IWM \\
            --start-date 2020-01-01 \\
            --end-date 2020-12-31

    Advanced:
        python scripts/run_single_backtest.py \\
            --universe SPY QQQ IWM XLF XLK \\
            --start-date 2020-01-01 \\
            --end-date 2021-12-31 \\
            --max-weight-per-asset 0.30 \\
            --max-sector-weight 0.60 \\
            --target-vol 0.15 \\
            --max-leverage 1.5 \\
            --output-dir results/backtest_001 \\
            --verbose
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sage_core.walkforward.engine import run_system_walkforward


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a single backtest using the Sage backtesting engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Required arguments
    parser.add_argument(
        "--universe", "-u",
        nargs="+",
        required=True,
        help="List of symbols to trade (e.g., SPY QQQ IWM)"
    )
    parser.add_argument(
        "--start-date",
        required=True,
        help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end-date",
        required=True,
        help="End date in YYYY-MM-DD format"
    )
    
    # Risk cap arguments
    risk_group = parser.add_argument_group("Risk Caps")
    risk_group.add_argument(
        "--max-weight-per-asset",
        type=float,
        default=0.25,
        help="Maximum weight per asset (default: 0.25)"
    )
    risk_group.add_argument(
        "--max-sector-weight",
        type=float,
        default=None,
        help="Maximum weight per sector (default: None)"
    )
    risk_group.add_argument(
        "--min-assets-held",
        type=int,
        default=1,
        help="Minimum number of assets to hold (default: 1)"
    )
    
    # Vol targeting arguments
    vol_group = parser.add_argument_group("Volatility Targeting")
    vol_group.add_argument(
        "--target-vol",
        type=float,
        default=0.10,
        help="Target annual volatility (default: 0.10)"
    )
    vol_group.add_argument(
        "--vol-lookback",
        type=int,
        default=60,
        help="Lookback period for vol targeting in days (default: 60)"
    )
    vol_group.add_argument(
        "--min-leverage",
        type=float,
        default=0.0,
        help="Minimum leverage (default: 0.0)"
    )
    vol_group.add_argument(
        "--max-leverage",
        type=float,
        default=2.0,
        help="Maximum leverage (default: 2.0)"
    )
    
    # Allocator arguments
    alloc_group = parser.add_argument_group("Allocator")
    alloc_group.add_argument(
        "--vol-window",
        type=int,
        default=60,
        help="Window for inverse vol calculation in days (default: 60)"
    )
    
    # Output arguments
    output_group = parser.add_argument_group("Output")
    output_group.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help="Directory to save results (optional)"
    )
    output_group.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed output"
    )
    
    return parser.parse_args()


def validate_arguments(args):
    """Validate command-line arguments."""
    # Validate date formats
    try:
        start = datetime.strptime(args.start_date, "%Y-%m-%d")
        end = datetime.strptime(args.end_date, "%Y-%m-%d")
        
        if start >= end:
            raise ValueError(
                f"start_date ({args.start_date}) must be before end_date ({args.end_date})"
            )
    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError(
                "Dates must be in YYYY-MM-DD format"
            )
        raise
    
    # Validate universe
    if not args.universe or len(args.universe) == 0:
        raise ValueError("Universe cannot be empty")
    
    # Validate numeric parameters
    if args.max_weight_per_asset <= 0 or args.max_weight_per_asset > 1:
        raise ValueError("max_weight_per_asset must be between 0 and 1")
    
    if args.max_sector_weight is not None:
        if args.max_sector_weight <= 0 or args.max_sector_weight > 1:
            raise ValueError("max_sector_weight must be between 0 and 1")
    
    if args.target_vol <= 0:
        raise ValueError("target_vol must be positive")
    
    if args.min_leverage < 0:
        raise ValueError("min_leverage must be non-negative")
    
    if args.max_leverage < args.min_leverage:
        raise ValueError("max_leverage must be >= min_leverage")


def display_results(result, args, verbose=False):
    """Display backtest results to console."""
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    
    # Configuration
    print("\nConfiguration:")
    print(f"  Universe: {', '.join(args.universe)}")
    print(f"  Period: {args.start_date} to {args.end_date}")
    print(f"  Trading Days: {len(result['returns'])}")
    
    # Performance Metrics
    metrics = result['metrics']
    print("\nPerformance Metrics:")
    print(f"  Total Return: {metrics['total_return']:.2%}")
    print(f"  CAGR: {metrics['cagr']:.2%}")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Max Drawdown: {metrics['max_drawdown_pct']:.2%}")
    print(f"  Volatility (Annual): {metrics['volatility']:.2%}")
    
    # Turnover
    print("\nTurnover:")
    print(f"  Average Daily: {metrics['avg_daily_turnover']:.2%}")
    print(f"  Total: {metrics['total_turnover']:.2%}")
    
    # Verbose output
    if verbose:
        print("\nDetailed Metrics:")
        print(f"  Max Drawdown ($): ${metrics['max_drawdown']:.2f}")
        print(f"  Peak Date: {metrics.get('peak_date', 'N/A')}")
        print(f"  Trough Date: {metrics.get('trough_date', 'N/A')}")
        print(f"  Recovery Date: {metrics.get('recovery_date', 'N/A')}")
        
        print("\nYearly Summary:")
        if 'yearly_summary' in metrics and not metrics['yearly_summary'].empty:
            print(metrics['yearly_summary'].to_string())
        
        print("\nFinal Weights:")
        final_weights = result['weights'].iloc[-1]
        for symbol, weight in final_weights.items():
            print(f"  {symbol}: {weight:.2%}")
    
    print("\n" + "=" * 60)


def save_results(result, args, output_dir):
    """Save backtest results to files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f"\nSaving results to {output_path}...")
    
    # Save metadata and metrics to JSON
    metadata = {
        "universe": args.universe,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "trading_days": len(result['returns']),
        "parameters": {
            "max_weight_per_asset": args.max_weight_per_asset,
            "max_sector_weight": args.max_sector_weight,
            "min_assets_held": args.min_assets_held,
            "target_vol": args.target_vol,
            "vol_lookback": args.vol_lookback,
            "min_leverage": args.min_leverage,
            "max_leverage": args.max_leverage,
            "vol_window": args.vol_window,
        },
        "metrics": {
            k: float(v) if isinstance(v, (int, float)) else str(v)
            for k, v in result['metrics'].items()
            if k != 'yearly_summary'  # Exclude DataFrame
        }
    }
    
    with open(output_path / "results.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    # Save time series to CSV
    result['equity_curve'].to_csv(output_path / "equity_curve.csv", header=True)
    result['returns'].to_csv(output_path / "returns.csv", header=True)
    result['weights'].to_csv(output_path / "weights.csv")
    result['asset_returns'].to_csv(output_path / "asset_returns.csv")
    
    # Save yearly summary if available
    if 'yearly_summary' in result['metrics'] and not result['metrics']['yearly_summary'].empty:
        result['metrics']['yearly_summary'].to_csv(output_path / "yearly_summary.csv")
    
    print(f"  ✓ results.json")
    print(f"  ✓ equity_curve.csv")
    print(f"  ✓ returns.csv")
    print(f"  ✓ weights.csv")
    print(f"  ✓ asset_returns.csv")
    if 'yearly_summary' in result['metrics']:
        print(f"  ✓ yearly_summary.csv")


def main():
    """Main entry point."""
    try:
        # Parse and validate arguments
        args = parse_arguments()
        validate_arguments(args)
        
        # Run backtest
        print(f"\nRunning backtest for {', '.join(args.universe)}...")
        print(f"Period: {args.start_date} to {args.end_date}")
        
        result = run_system_walkforward(
            universe=args.universe,
            start_date=args.start_date,
            end_date=args.end_date,
            max_weight_per_asset=args.max_weight_per_asset,
            max_sector_weight=args.max_sector_weight,
            min_assets_held=args.min_assets_held,
            target_vol=args.target_vol,
            vol_lookback=args.vol_lookback,
            min_leverage=args.min_leverage,
            max_leverage=args.max_leverage,
            vol_window=args.vol_window,
        )
        
        # Display results
        display_results(result, args, verbose=args.verbose)
        
        # Save results if output directory specified
        if args.output_dir:
            save_results(result, args, args.output_dir)
        
        print("\n✓ Backtest completed successfully!\n")
        return 0
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: Data file not found", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        print(f"\nMake sure data files exist in data/processed/ directory", file=sys.stderr)
        return 1
        
    except ValueError as e:
        print(f"\n✗ Error: Invalid parameter", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        return 1
        
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        if args.verbose if 'args' in locals() else False:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
