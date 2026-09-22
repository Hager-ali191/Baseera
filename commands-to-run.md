### make the project environment
`python -m venv venv`

### activate it
- for cmd.exe  :  `venv\Scripts\activate`  
- for PowerShell (may need: Set-ExecutionPolicy -Scope Process RemoteSigned)  :  `.\venv\Scripts\Activate.ps1`
- for Git Bash  :  `source venv/Scripts/activate`
---

### install requirements of frontend(nicegui or streamlit) and backend (fastapi)
`pip install -r backend/requirements.txt`
`pip install -r NiceGUI/requirements.txt`
`pip install -r Streamlit/requirements.txt`

---

### backend terminal
#### access folder
`cd backend`
#### grok api for siara bot
`setx GROQ_API_KEY "paste grok api"`
#### make the run lighter for your device
`set BASEERA_CPU_THREADS=2`
`set BASEERA_LLM_MODEL=Qwen/Qwen2.5-0.5B-Instruct`
`set BASEERA_WHISPER_MODEL=tiny`
#### actual running
`uvicorn main:app --port 8000`

---

### frontend terminal
#### activate the environment
- for cmd.exe  :  `venv\Scripts\activate`  
- for PowerShell (may need: Set-ExecutionPolicy -Scope Process RemoteSigned)  :  `.\venv\Scripts\Activate.ps1`
- for Git Bash  :  `source venv/Scripts/activate`
#### access folder
`cd NiceGUI`
#### actual running
`python app.py`
