"""Reusable header component for Streamlit pages."""

from __future__ import annotations

import base64
from pathlib import Path
import streamlit as st


def _encode_image_data(icon_path: str | Path) -> tuple[str, str]:
    path = Path(icon_path)
    mime_type = "image/png"
    if path.suffix:
        mime_type = f"image/{path.suffix.lstrip('.').lower()}"
    data = path.read_bytes()
    return base64.b64encode(data).decode("ascii"), mime_type


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
          .sage-hero{background:linear-gradient(120deg,#0c5f2f 0%,#1f7a3a 45%,#5fbf7f 100%);border-radius:16px;color:#fff;margin-bottom:8px;display:flex;align-items:center;gap:10px;padding:6px 10px}
          .sage-hero img{width:200px;height:auto;display:block}
          .sage-hero-title{font:700 4.2rem 'Merriweather',Georgia,'Times New Roman',serif;margin:0}
          .sage-hero-subtitle{font:400 1.4rem 'Merriweather',Georgia,'Times New Roman',serif;margin:4px 0 0;opacity:.9}
        </style>
        """,
        unsafe_allow_html=True,
    )

    subtitle_html = (
        f'<div class="sage-hero-subtitle">{subtitle}</div>' if subtitle else ""
    )
    icon_html = ""
    if icon_path:
        encoded, mime_type = _encode_image_data(icon_path)
        icon_html = f'<img src="data:{mime_type};base64,{encoded}" alt="Sage icon" />'

    st.markdown(
        f"""
        <div class="sage-hero">
          {icon_html}
          <div>
            <div class="sage-hero-title">{title}</div>
            {subtitle_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
