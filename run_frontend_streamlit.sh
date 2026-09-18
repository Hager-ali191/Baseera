#!/usr/bin/env bash
cd "$(dirname "$0")/Streamlit"
source ../venv/bin/activate
streamlit run app.py
