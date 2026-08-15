# Environment Setup

How the Python environment for this project was created, and how it's kept
initialized automatically every time you open this project in VS Code.

## What environment this project uses
A **conda environment named `consortium`** (Python 3.12), not the base
conda environment and not a standard-library `venv`. It was created with:

```powershell
conda create -n consortium python=3.12
conda activate consortium
pip install fastapi uvicorn
```

Backend dependencies are pinned in `backend/requirements.txt`:
```
fastapi==0.141.1
uvicorn==0.52.3
```

## How it auto-initializes when you open VS Code
Two files in `.vscode/` do this — they're committed to the repo on purpose,
so this keeps working even on a fresh clone/machine (as long as `consortium`
gets created there too):

1. **`.vscode/tasks.json`** — defines a task with `"runOn": "folderOpen"`.
   VS Code runs this automatically whenever you open the project folder. It
   calls `scripts/setup-env.ps1`, which:
   - creates the `consortium` conda environment if it doesn't already exist
     on this machine
   - installs/updates everything in `backend/requirements.txt` into it
   - does nothing (safely) if conda isn't installed at all, or if the
     environment is already fully set up — safe to run every single time
     you open the project, not just the first time
2. **`.vscode/settings.json`** — tells VS Code which Python interpreter to
   use (`consortium`'s `python.exe`) and turns on
   `python.terminal.activateEnvironment`, so any new integrated terminal
   you open in VS Code has `consortium` active automatically — you should
   not need to run `conda activate consortium` by hand anymore.

**One-time prompt to expect:** the first time you open this project after
pulling these files, VS Code will ask *"Do you want to allow automatic
tasks in this workspace?"* — say yes, or the auto-init won't run.

## Manual commands (if you ever need them)
Run the same setup the task runs, by hand:
```powershell
.\scripts\setup-env.ps1
```

Activate the environment yourself in any terminal (VS Code should already
do this for you, this is the fallback):
```powershell
conda activate consortium
```

Run the backend once the environment is active:
```powershell
cd backend
uvicorn main:app --reload
```
Then check `http://127.0.0.1:8000/health` in a browser.

## Why not a `venv` instead of conda?
You already had conda (Miniconda) installed and working before this
project existed — reusing it avoids installing and maintaining a second,
different Python environment tool for no benefit. If that ever changes,
swapping to a standard `venv` only requires rewriting `scripts/setup-env.ps1`
and the interpreter path in `.vscode/settings.json` — nothing else in the
project depends on which tool manages the environment.
