#!/usr/bin/env bash
cd "$(dirname "$0")/frontend"
source ../venv/bin/activate
streamlit run app.py
