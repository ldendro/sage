"""Reusable header component for Streamlit pages."""

from __future__ import annotations

from pathlib import Path
import streamlit as st


def render_header(
    title: str,
    subtitle: str | None = None,
    icon_path: str | Path | None = None,
) -> None:
    """Render a compact header with icon, title, and subtitle."""
    st.markdown(
        """
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&display=swap');
          .sage-hero-title{font:700 2.2rem 'Merriweather',Georgia,'Times New Roman',serif;margin:0}
          .sage-hero-subtitle{font:400 1rem 'Merriweather',Georgia,'Times New Roman',serif;margin:4px 0 0;opacity:.9}
          .element-container:has(.sage-hero-sentinel)+.element-container [data-testid="stHorizontalBlock"]{background:linear-gradient(120deg,#0c5f2f 0%,#1f7a3a 45%,#5fbf7f 100%);border-radius:16px;padding:6px 10px;margin-bottom:8px;align-items:center;gap:10px}
          .element-container:has(.sage-hero-sentinel)+.element-container img{width:200px;height:auto;display:block}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sage-hero-sentinel"></div>', unsafe_allow_html=True)
    col_icon, col_text = st.columns([1, 3], gap="small")
    with col_icon:
        if icon_path:
            st.image(icon_path, use_container_width=True)
    with col_text:
        subtitle_html = (
            f'<div class="sage-hero-subtitle">{subtitle}</div>' if subtitle else ""
        )
        st.markdown(
            f'<div class="sage-hero-title">{title}</div>{subtitle_html}',
            unsafe_allow_html=True,
        )
