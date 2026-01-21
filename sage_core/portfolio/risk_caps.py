"""
Risk cap utilities for portfolio construction.

This module applies various risk constraints to portfolio weights:
- Per-asset weight caps
- Per-sector weight caps
- Minimum number of assets held
"""

import pandas as pd
from typing import Dict, Optional


def apply_all_risk_caps(
    weights_df: pd.DataFrame,
    sector_map: Dict[str, str],
    max_weight_per_asset: float = 0.25,
    max_sector_weight: Optional[float] = None,
    min_assets_held: int = 1,
) -> pd.DataFrame:
    """
    Apply all risk caps to portfolio weights.
    
    Applies constraints in order:
    1. Per-asset weight caps
    2. Per-sector weight caps (if enabled)
    3. Minimum assets held constraint
    
    After each constraint, weights are renormalized to sum to 1.
    
    Args:
        weights_df: Wide DataFrame of weights (dates × symbols)
        sector_map: Dictionary mapping symbols to sectors
        max_weight_per_asset: Maximum weight per asset (default: 0.25 = 25%)
        max_sector_weight: Maximum weight per sector (default: None = no cap)
        min_assets_held: Minimum number of assets to hold (default: 1)
    
    Returns:
        Wide DataFrame of capped weights (dates × symbols), normalized to sum to 1
    
    Raises:
        ValueError: If constraints are infeasible
    
    Example:
        >>> capped = apply_all_risk_caps(
        ...     weights_df,
        ...     sector_map={"SPY": "Broad", "XLF": "Financials"},
        ...     max_weight_per_asset=0.25,
        ...     max_sector_weight=0.40,
        ...     min_assets_held=3,
        ... )
    """
    # Validate inputs
    n_assets = len(weights_df.columns)
    
    if min_assets_held < 1:
        raise ValueError(f"min_assets_held must be >= 1, got {min_assets_held}")
    
    if min_assets_held > n_assets:
        raise ValueError(
            f"min_assets_held ({min_assets_held}) cannot exceed "
            f"number of assets ({n_assets})"
        )
    
    if max_weight_per_asset <= 0 or max_weight_per_asset > 1:
        raise ValueError(
            f"max_weight_per_asset must be in (0, 1], got {max_weight_per_asset}"
        )
    
    # Validate max_sector_weight if provided
    if max_sector_weight is not None:
        if max_sector_weight <= 0 or max_sector_weight > 1:
            raise ValueError(
                f"max_sector_weight must be in (0, 1], got {max_sector_weight}"
            )
        
        # Check sector weight feasibility
        # Find minimum number of sectors needed
        unique_sectors = set(sector_map.get(symbol, "Unknown") for symbol in weights_df.columns)
        n_sectors = len(unique_sectors)
        
        # If all assets are in one sector, max_sector_weight must be 1.0
        # More generally: max_sector_weight * n_sectors >= 1.0
        if n_sectors * max_sector_weight < 1.0:
            raise ValueError(
                f"Infeasible sector constraint: {n_sectors} sector(s) * "
                f"max_sector_weight ({max_sector_weight:.4f}) = "
                f"{n_sectors * max_sector_weight:.4f} < 1.0. "
                f"With {n_sectors} sector(s), max_sector_weight must be >= "
                f"{1.0 / n_sectors:.4f} to ensure weights can sum to 1."
            )
    
    # Check feasibility: min_assets_held * max_weight_per_asset >= 1
    # This check is conservative - it ensures that IF we only use min_assets,
    # we can still reach 100% allocation. However, if we have more assets available,
    # we can use them, so we only enforce this when min_assets == n_assets.
    if min_assets_held == n_assets and min_assets_held * max_weight_per_asset < 1.0:
        raise ValueError(
            f"Infeasible constraints: min_assets_held ({min_assets_held}) * "
            f"max_weight_per_asset ({max_weight_per_asset}) = "
            f"{min_assets_held * max_weight_per_asset:.2f} < 1.0. "
            f"With only {n_assets} assets available and all required to be held, "
            f"cannot satisfy both constraints simultaneously."
        )
    
    # Apply per-asset caps
    capped_weights = apply_per_asset_caps(weights_df, max_weight_per_asset)
    
    # Apply per-sector caps (if enabled)
    if max_sector_weight is not None:
        capped_weights = apply_per_sector_caps(
            capped_weights,
            sector_map,
            max_sector_weight,
        )
    
    # Apply minimum assets constraint
    capped_weights = apply_min_assets_constraint(capped_weights, min_assets_held)
    
    return capped_weights


def apply_per_asset_caps(
    weights_df: pd.DataFrame,
    max_weight: float,
) -> pd.DataFrame:
    """
    Apply per-asset weight caps.
    
    Caps each asset's weight and renormalizes to sum to 1.
    
    Args:
        weights_df: Wide DataFrame of weights (dates × symbols)
        max_weight: Maximum weight per asset
    
    Returns:
        Capped and renormalized weights
    """
    def cap_row(row):
        """Cap and renormalize a single row."""
        if row.isna().any():
            return row
        
        # Iteratively cap and renormalize
        for _ in range(100):
            if (row <= max_weight).all():
                break
            
            exceeds = row > max_weight
            capped = row.copy()
            capped[exceeds] = max_weight
            
            total_capped = capped[exceeds].sum()
            total_uncapped = row[~exceeds].sum()
            remaining = 1.0 - total_capped
            
            if total_uncapped > 0:
                capped[~exceeds] = row[~exceeds] / total_uncapped * remaining
            
            row = capped
        
        return row
    
    return weights_df.apply(cap_row, axis=1)


def apply_per_sector_caps(
    weights_df: pd.DataFrame,
    sector_map: Dict[str, str],
    max_sector_weight: float,
) -> pd.DataFrame:
    """
    Apply per-sector weight caps.
    
    Ensures no sector exceeds max_sector_weight by scaling down
    assets within over-weighted sectors.
    
    Args:
        weights_df: Wide DataFrame of weights (dates × symbols)
        sector_map: Dictionary mapping symbols to sectors
        max_sector_weight: Maximum weight per sector
    
    Returns:
        Sector-capped and renormalized weights
    """
    def cap_sectors_row(row):
        """Cap sectors and renormalize a single row."""
        if row.isna().any():
            return row
        
        new_row = row.copy()
        
        # Iterate until all sectors are within cap
        for _ in range(100):
            # Calculate sector weights
            sector_weights = {}
            for symbol in new_row.index:
                sector = sector_map.get(symbol, "Unknown")
                sector_weights[sector] = sector_weights.get(sector, 0) + new_row[symbol]
            
            # Find sectors that exceed cap
            over_sectors = {s: w for s, w in sector_weights.items() if w > max_sector_weight}
            
            if not over_sectors:
                break  # All sectors within cap
            
            # Scale down assets in over-weighted sectors
            for sector, sector_weight in over_sectors.items():
                # Find assets in this sector
                sector_assets = [s for s in new_row.index if sector_map.get(s, "Unknown") == sector]
                
                # Scale down proportionally
                scale_factor = max_sector_weight / sector_weight
                for asset in sector_assets:
                    new_row[asset] *= scale_factor
            
            # Renormalize to sum to 1
            if new_row.sum() > 0:
                new_row = new_row / new_row.sum()
        
        return new_row
    
    return weights_df.apply(cap_sectors_row, axis=1)


def apply_min_assets_constraint(
    weights_df: pd.DataFrame,
    min_assets: int,
) -> pd.DataFrame:
    """
    Apply minimum assets held constraint.
    
    Ensures at least min_assets have non-zero weights.
    If fewer than min_assets have weight, keeps the top min_assets by weight.
    
    Args:
        weights_df: Wide DataFrame of weights (dates × symbols)
        min_assets: Minimum number of assets to hold
    
    Returns:
        Weights with at least min_assets non-zero
    """
    def apply_min_assets_row(row):
        """Apply min assets constraint to a single row."""
        if row.isna().any():
            return row
        
        # Count non-zero weights (using small threshold)
        non_zero_count = (row > 1e-6).sum()
        
        if non_zero_count >= min_assets:
            return row  # Already satisfies constraint
        
        # Need to add more assets - keep top min_assets by weight
        top_assets = row.nlargest(min_assets).index
        new_row = pd.Series(0.0, index=row.index)
        new_row[top_assets] = row[top_assets]
        
        # Renormalize
        if new_row.sum() > 0:
            new_row = new_row / new_row.sum()
        
        return new_row
    
    return weights_df.apply(apply_min_assets_row, axis=1)
