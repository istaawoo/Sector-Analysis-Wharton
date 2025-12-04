# streamlit_app.py — robust loader for Streamlit Cloud
import sys
import os
import traceback
import importlib

# Ensure repo root is on sys.path so imports like "from src import ..." or "import sector_analysis_app" work.
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# Also explicitly add package folders (defensive)
sys.path.insert(0, os.path.join(ROOT, "sector_analysis_app"))
sys.path.insert(0, os.path.join(ROOT, "sector_analysis_app", "src"))

try:
    # Try importing the app submodule directly (this avoids ambiguous package-level imports)
    _app = importlib.import_module("sector_analysis_app.app")
except Exception as exc:
    # If import fails, show a clear error in Streamlit (if available) and print traceback
    try:
        import streamlit as st

        st.set_page_config(page_title="Sector Analysis — Load Error", layout="centered")
        st.title("Failed to load Sector Analysis app")
        st.error("An error occurred while loading the app. See traceback below.")
        st.exception(exc)
        st.text("Full traceback:")
        st.text(traceback.format_exc())
    except Exception:
        # If Streamlit isn't importable (unlikely on Cloud), print traceback to stderr
        print("Error while importing app:", file=sys.stderr)
        traceback.print_exc()
    # Re-raise so the container log has the stacktrace as well
    raise