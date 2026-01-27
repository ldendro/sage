"""Plotly chart utilities for the Streamlit app."""

import plotly.graph_objects as go
import pandas as pd
from typing import Optional


def create_equity_curve_chart(
    equity_curve: pd.Series,
    title: str = "Portfolio Equity Curve",
    height: int = 500,
) -> go.Figure:
    """
    Create an interactive equity curve chart.
    
    Args:
        equity_curve: Series of equity values (indexed by date)
        title: Chart title
        height: Chart height in pixels
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Add equity curve line
    fig.add_trace(go.Scatter(
        x=equity_curve.index,
        y=equity_curve.values,
        mode='lines',
        name='Portfolio Value',
        line=dict(color='#2E86AB', width=2),
        hovertemplate=(
            '<b>Date:</b> %{x|%Y-%m-%d}<br>'
            '<b>Value:</b> %{y:.2f}<br>'
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
        margin=dict(l=60, r=30, t=60, b=60),
        font=dict(family='Inter, system-ui, sans-serif', size=12),
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


def create_drawdown_chart(
    drawdown_series: pd.Series,
    title: str = "Drawdown Analysis",
    height: int = 400,
) -> go.Figure:
    """
    Create an underwater (drawdown) chart.
    
    Args:
        drawdown_series: Series of drawdown values as decimals (e.g., -0.05 for -5%)
        title: Chart title
        height: Chart height in pixels
    
    Returns:
        Plotly figure
    """
    fig = go.Figure()
    
    # Add drawdown area (convert to percentage for display)
    fig.add_trace(go.Scatter(
        x=drawdown_series.index,
        y=drawdown_series.values * 100,  # Convert to percentage
        mode='lines',
        name='Drawdown',
        fill='tozeroy',
        line=dict(color='#DC2626', width=1),
        fillcolor='rgba(220, 38, 38, 0.3)',
        hovertemplate=(
            '<b>Date:</b> %{x|%Y-%m-%d}<br>'
            '<b>Drawdown:</b> %{y:.2f}%<br>'
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
    )
    
    return fig
