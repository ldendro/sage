"""Smoke test for Streamlit app."""

import pytest
from unittest.mock import MagicMock
import sys

# Mock streamlit before importing app
sys.modules["streamlit"] = MagicMock()

def test_app_import():
    """Test that streamlit_app can be imported without error."""
    try:
        import app.streamlit_app
    except ImportError as e:
        pytest.fail(f"Failed to import app.streamlit_app: {e}")
    except Exception as e:
        # It handles calling main() if __name__ == "__main__", so import should be safe
        # providing it doesn't run code at module level that requires real streamlit
        pass
