# Volt Trace

Run these commands from the repository root in PowerShell.

**Setup**

```powershell
cd python
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
cd ..\nextjs
npm install
```

**Start (from `nextjs`)**

```powershell
npm run dev
```

Open <http://localhost:3000>. Select the XML files or a folder in the app.
Next.js runs the Python processing directly; no separate API server is needed.
