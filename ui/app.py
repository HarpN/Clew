"""
ui/app.py - Desktop Command Center Streamlit Interface
Renders the modern Clew Command Center desktop HTML workspace.
"""

import os
import sys
import streamlit as st
import streamlit.components.v1 as components

# Ensure root repository directory is accessible for imports
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database

# Initialize DB on load
database.init_db()

# Page configuration
st.set_page_config(
    page_title="Clew Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Hide Streamlit default chrome & margins for a clean full-window view
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding: 0rem !important;
        max-width: 100% !important;
    }
    iframe {
        border: none !important;
        width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# Read desktop HTML template
html_path = os.path.join(BASE_DIR, "ui", "index.html")
if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
        desktop_html = f.read()
    components.html(desktop_html, height=920, scrolling=False)
else:
    st.error("Desktop template ui/index.html not found.")
