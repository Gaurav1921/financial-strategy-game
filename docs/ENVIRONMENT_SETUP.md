# Environment Setup

How the Python environment for this project was created, how it auto
initializes every time you open this project in VS Code, and how the
code quality tooling (linting, formatting, pre-commit hooks) is set up.

## What environment this project uses
A **conda environment named `consortium`** (Python 3.12), not the base
conda environment and not a standard-library `venv`. It was created with:

```powershell
conda create -n consortium python=3.12
conda activate consortium
pip install fastapi uvicorn
```

Backend runtime dependencies are pinned in `backend/requirements.txt`.
Dev-only tooling (ruff, pre-commit) is pinned separately in
`requirements-dev.txt` at the repo root, since it's not something the
running application needs, only the people working on it.

## How it auto-initializes when you open VS Code
Two files in `.vscode/` handle this, and they are committed to the repo:

1. **`.vscode/tasks.json`** defines a task with `"runOn": "folderOpen"`.
   VS Code runs this automatically whenever you open the project folder.
   It calls `scripts/setup-env.ps1`, which creates the `consortium` conda
   environment if it does not already exist on this machine, and installs
   or updates everything in `backend/requirements.txt` into it. It is
   safe to run every time you open the project, not just the first time.
2. **`.vscode/settings.json`** tells VS Code which Python interpreter to
   use (`consortium`'s `python.exe`) and turns on
   `python.terminal.activateEnvironment`, so any new integrated terminal
   you open in VS Code has `consortium` active automatically. You should
   not need to run `conda activate consortium` by hand.

**`scripts/` is intentionally not tracked in this repo** (see
`.gitignore`). It is local dev-only tooling. This means the auto-init task
only works on machines where `scripts/setup-env.ps1` already exists
locally. On a fresh clone, or a new machine, set that up once by hand
(see "Manual commands" below) before the automatic task has anything to
run.

**One-time prompt to expect:** the first time you open this project, VS
Code will ask *"Do you want to allow automatic tasks in this workspace?"*
Say yes, or the auto-init will not run.

## Manual commands (if you ever need them)
Create the environment and install backend dependencies by hand:
```powershell
conda create -n consortium python=3.12
conda activate consortium
pip install -r backend/requirements.txt
```

Activate the environment yourself in any terminal (VS Code should already
do this for you, this is the fallback):
```powershell
conda activate consortium
```

Run the backend once the environment is active:
```powershell
cd backend
uvicorn app.main:app --reload
```
Then check `http://127.0.0.1:8000/health` in a browser.

## Code quality tooling
Install the dev tools once, into the same `consortium` environment:
```powershell
conda activate consortium
pip install -r requirements-dev.txt
pre-commit install
```

That last command activates the git hook, defined in
`.pre-commit-config.yaml`, so every commit automatically runs:
- `ruff` (lint, format, complexity, security, docstring checks) on the
  backend, configured in `backend/pyproject.toml`
- `oxlint` on the frontend, configured in `frontend/.oxlintrc.json`
- basic hygiene checks: trailing whitespace, merge-conflict markers,
  oversized files, private-key and secret detection (`gitleaks`)

Run the same checks manually at any time:
```powershell
ruff check backend
ruff format backend
npm --prefix frontend run lint
pre-commit run --all-files
```

Coding standards and what these tools enforce are documented in
`CLAUDE.md` at the repo root.

## Why not a `venv` instead of conda?
You already had conda (Miniconda) installed and working before this
project existed, so reusing it avoids installing and maintaining a second,
different Python environment tool for no benefit. If that ever changes,
swapping to a standard `venv` only requires rewriting `scripts/setup-env.ps1`
and the interpreter path in `.vscode/settings.json`. Nothing else in the
project depends on which tool manages the environment.
