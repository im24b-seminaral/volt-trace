# Volt Trace

## Prerequisites (Windows)

Install [Python 3.14](https://www.python.org/downloads/windows/) with **Add Python to PATH**, and [Node.js 24 LTS](https://nodejs.org/en/download) (includes npm). Reopen PowerShell afterwards.

## Install dependencies

Open PowerShell in the repository root (`volt-trace`, containing `python` and `nextjs`):

```powershell
python -m venv python/.venv
.\python\.venv\Scripts\python -m pip install -r python/requirements.txt
npm --prefix nextjs ci
```

## Start

From the same repository root:

```powershell
npm --prefix nextjs run dev
```

Open [localhost:3000](http://localhost:3000) and select XML files or a folder. Keep the terminal open; press **Ctrl+C** to stop.

Next.js uses `python/.venv` automatically. No environment activation or separate Python server is needed.
