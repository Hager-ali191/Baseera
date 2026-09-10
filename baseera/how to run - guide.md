# **To run it:**

- `python -m venv venv` at the project root
- `venv\Scripts\activate` to activate it.
- 
- `pip install -r backend/requirements.txt`
- `pip install -r frontend/requirements.txt`

- Terminal 1: 
    - `cd backend`
    - `uvicorn main:app --reload --port 8000` — wait for "All models loaded".

- Terminal 2: 
    - `cd frontend`
    - `streamlit run app.py` — opens in your browser.