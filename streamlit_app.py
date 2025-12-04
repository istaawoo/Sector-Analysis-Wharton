import sys
import os
import traceback
import importlib

# Ensure repo root is on sys.path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Explicitly add package folders
sys.path.insert(0, os.path.join(ROOT, "sector_analysis_app"))
sys.path.insert(0, os.path.join(ROOT, "sector_analysis_app", "src"))

try:
    # 1. Import the module
    _app = importlib.import_module("sector_analysis_app.app")
    
    # 2. RELOAD the module to ensure fresh state (Optional but recommended for Streamlit)
    importlib.reload(_app)

    # 3. EXPLICITLY call the main function
    if hasattr(_app, "main"):
        _app.main()
    else:
        # Fallback if main isn't found
        import streamlit as st
        st.error("Module 'sector_analysis_app.app' has no 'main' function.")

except Exception as exc:
    import streamlit as st
    st.set_page_config(page_title="Load Error", layout="centered")
    st.title("Failed to load Sector Analysis app")
    st.exception(exc)
    st.text(traceback.format_exc())