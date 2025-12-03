# streamlit_app.py
# Thin wrapper for Streamlit Cloud that safely imports the app and shows errors

import os
import sys
import traceback

# Add the project root to PYTHONPATH
root = os.path.dirname(os.path.abspath(__file__))
if root not in sys.path:
	sys.path.insert(0, root)

try:
	# Import the app module. If it raises, catch and display an error in Streamlit.
	from sector_analysis_app import app as _app
except Exception as exc:
	try:
		import streamlit as st

		st.set_page_config(page_title="Sector Analysis — Load Error", layout="centered")
		st.title("Failed to load Sector Analysis app")
		st.error("An error occurred while loading the app. See traceback below.")
		st.exception(exc)
		st.text("Full traceback:")
		st.text(traceback.format_exc())
	except Exception:
		# If Streamlit isn't available or another error occurs, print to stderr
		print("Error while importing app:", file=sys.stderr)
		traceback.print_exc()
