"""Plotly chart utilities for the Streamlit app."""

import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Optional

def create_weight_allocation_chart(
    weights_df: pd.DataFrame,
    title: str = "Portfolio Allocation Over Time",
    height: int = 825,
) -> go.Figure:
    """
    Create a stacked area chart showing portfolio weight allocation over time.
    
    Args:
        weights_df: DataFrame with dates as index and assets as columns, 
                   values as weights (decimals, e.g., 0.25 for 25%)
        title: Chart title
        height: Chart height in pixels
    
    Returns:
        Plotly figure with stacked area chart
    """
    if weights_df.empty:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No weight data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#9ca3af")
        )
        fig.update_layout(
            title=title,
            height=height,
            plot_bgcolor='white',
            paper_bgcolor='white',
        )
        return fig
    
    # Convert weights to percentages for display
    weights_pct = weights_df * 100
    
    # Sort columns alphabetically for consistent legend order
    weights_pct = weights_pct[sorted(weights_pct.columns)]
    
    # Generate color palette - using a diverse, visually distinct palette
    colors = [
        '#2E86AB',  # Blue
        '#A23B72',  # Purple
        '#F18F01',  # Orange
        '#C73E1D',  # Red
        '#6A994E',  # Green
        '#BC4B51',  # Dark Red
        '#4EA8DE',  # Light Blue
        '#5E548E',  # Dark Purple
        '#F4A261',  # Peach
        '#2A9D8F',  # Teal
        '#E76F51',  # Coral
        '#264653',  # Dark Teal
    ]
    
    # Extend colors if needed by cycling through the palette
    while len(colors) < len(weights_pct.columns):
        colors.extend(colors)
    
    fig = go.Figure()
    
    # Add traces for each asset (in reverse order so legend matches stack order)
    for i, asset in enumerate(weights_pct.columns):
        fig.add_trace(go.Scatter(
            x=weights_pct.index,
            y=weights_pct[asset].values,
            mode='lines',
            name=asset,
            line=dict(width=0.5, color=colors[i % len(colors)]),
            fillcolor=colors[i % len(colors)],
            stackgroup='one',  # This creates the stacking effect
            hovertemplate=(
                f'<b>{asset}</b><br>'
                '<b>Date:</b> %{x|%Y-%m-%d}<br>'
                '<b>Weight:</b> %{y:.2f}%<br>'
                '<extra></extra>'
            )
        ))
    
    # Update layout
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, color='#1f2937'),
            xanchor="center",
            x=0.5,
        ),
        xaxis=dict(
            title=dict(text="Date", font=dict(color="#374151", size=12)),
            tickfont=dict(color="#374151", size=11),
            showgrid=True,
            gridcolor='#e5e7eb',
            showline=True,
            linecolor='#9ca3af',
            linewidth=1,
        ),
        yaxis=dict(
            title=dict(text="Allocation (%)", font=dict(color="#374151", size=12)),
            tickfont=dict(color="#374151", size=11),
            showgrid=True,
            gridcolor='#e5e7eb',
            showline=True,
            linecolor='#9ca3af',
            linewidth=1,
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=height,
        margin=dict(l=60, r=30, t=60, b=60),
        font=dict(family='Inter, system-ui, sans-serif', size=12),
        legend=dict(
            title=dict(text="Legend", font=dict(color="#374151", size=10), side="top center"),
            font=dict(color="#374151", size=10),
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#9ca3af",
            borderwidth=1,
        ),
    )
    
    # Add range selector buttons
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(label="ALL", step="all")
            ]),
            bgcolor='#9ca3af',
            activecolor='#2E86AB',
            x=-0.08,
            y=1.07,
        ),
        rangeslider=dict(visible=False)
    )
    
    return fig


def create_multi_equity_curve_chart(
    equity_curves: Dict[str, pd.Series],
    colors: Dict[str, str],
    title: str = "Portfolio Equity Curves",
    height: int = 500,
) -> go.Figure:
    """
    Create an equity curve chart with multiple portfolios.
    """
    fig = go.Figure()

    for name, series in equity_curves.items():
        if series is None or series.empty:
            continue
        fig.add_trace(go.Scatter(
            x=series.index,
            y=series.values,
            mode='lines',
            name=name,
            line=dict(color=colors.get(name, '#2E86AB'), width=2),
            hovertemplate=(
                '<b>Portfolio:</b> %{meta}<br>'
                '<b>Date:</b> %{x|%Y-%m-%d}<br>'
                '<b>Value:</b> %{y:.2f}<br>'
                '<extra></extra>'
            ),
            meta=name,
        ))

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, color='#1f2937'),
            xanchor="center",
            x=0.5,
        ),
        xaxis=dict(
            title=dict(text="Date", font=dict(color="#374151", size=12)),
            tickfont=dict(color="#374151", size=11),
            showgrid=True,
            gridcolor='#e5e7eb',
            showline=True,
            linecolor='#9ca3af',
            linewidth=1,
        ),
        yaxis=dict(
            title=dict(text="Portfolio Value", font=dict(color="#374151", size=12)),
            tickfont=dict(color="#374151", size=11),
            showgrid=True,
            gridcolor='#e5e7eb',
            showline=True,
            linecolor='#9ca3af',
            linewidth=1,
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=height,
        margin=dict(l=60, r=180, t=60, b=60),
        font=dict(family='Inter, system-ui, sans-serif', size=12),
        legend=dict(
            title=dict(text="Legend", font=dict(color="#374151", size=10), side="top center"),
            font=dict(color="#374151", size=10),
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#9ca3af",
            borderwidth=1,
        ),
    )

    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(label="ALL", step="all")
            ]),
            bgcolor='#9ca3af',
            activecolor='#2E86AB',
            x=-0.08,
            y=1.07,
        ),
        rangeslider=dict(visible=False)
    )

    return fig


def create_multi_drawdown_chart(
    drawdown_series: Dict[str, pd.Series],
    colors: Dict[str, str],
    title: str = "Drawdown Analysis",
    height: int = 400,
) -> go.Figure:
    """
    Create a drawdown chart with multiple portfolios.
    """
    fig = go.Figure()

    for name, series in drawdown_series.items():
        if series is None or series.empty:
            continue
        fig.add_trace(go.Scatter(
            x=series.index,
            y=series.values * 100,
            mode='lines',
            name=name,
            line=dict(color=colors.get(name, '#DC2626'), width=2),
            hovertemplate=(
                '<b>Portfolio:</b> %{meta}<br>'
                '<b>Date:</b> %{x|%Y-%m-%d}<br>'
                '<b>Drawdown:</b> %{y:.2f}%<br>'
                '<extra></extra>'
            ),
            meta=name,
        ))

    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, color='#1f2937'),
            xanchor="center",
            x=0.5,
        ),
        xaxis=dict(
            title=dict(text="Date", font=dict(color="#374151", size=12)),
            tickfont=dict(color="#374151", size=11),
            showgrid=True,
            gridcolor='#e5e7eb',
            showline=True,
            linecolor='#9ca3af',
            linewidth=1,
        ),
        yaxis=dict(
            title=dict(text="Drawdown (%)", font=dict(color="#374151", size=12)),
            tickfont=dict(color="#374151", size=11),
            showgrid=True,
            gridcolor='#e5e7eb',
            showline=True,
            linecolor='#9ca3af',
            linewidth=1,
            zeroline=True,
            zerolinecolor='#9ca3af',
            zerolinewidth=2,
        ),
        hovermode='x unified',
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=height,
        margin=dict(l=60, r=30, t=60, b=60),
        font=dict(family='Inter, system-ui, sans-serif', size=12),
        legend=dict(
            title=dict(text="Legend", font=dict(color="#374151", size=10), side="top center"),
            font=dict(color="#374151", size=10),
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#9ca3af",
            borderwidth=1,
        ),
    )

    return fig
