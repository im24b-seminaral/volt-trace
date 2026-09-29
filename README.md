# Volt Trace

Run these commands from the repository root in two PowerShell terminals.

**Terminal 1 — Python API**

```powershell
cd python
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn volt_trace.api:app --port 8000
```

**Terminal 2 — Frontend**

```powershell
cd nextjs
npm install
npm run dev
```

Open <http://localhost:3000>. Select the XML files or a folder in the app.
