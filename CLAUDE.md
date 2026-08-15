# Project Standards

These rules apply to all code, documentation, commit messages, and chat
responses generated in this repository.

## Writing style

- Never use em dashes or en dashes anywhere: not in code, comments,
  docstrings, commit messages, markdown docs, or chat responses. Use a
  period, comma, colon, or a plain hyphen instead, or restructure the
  sentence. This applies everywhere, no exceptions.
- Never use emojis anywhere, for any reason.
- Write plainly. Prefer short, direct sentences over dense ones.

## Code quality

- Follow standard software engineering fundamentals: single
  responsibility, DRY, meaningful names, no dead code, no commented-out
  code left behind.
- Keep code simple to read over clever. If a simpler version does the same
  job, use it.
- No premature abstraction: do not add configuration, extension points, or
  design patterns for requirements that do not exist yet. Three similar
  lines of code beat a speculative abstraction.
- No unnecessary comments. Code should be self-explanatory through naming;
  a comment is only worth adding when it explains *why*, not *what* (a
  non-obvious constraint, a workaround, an invariant).
- Keep cyclomatic complexity low. If a function is hard to summarize in one
  sentence, it probably needs splitting.

## Docstrings

- Every source file (Python and JS/TS) gets a module-level docstring
  summarizing what the file is for.
- Every public function, class, and method gets a docstring: what it does,
  parameters, return value, and any exceptions it raises. Google-style
  docstrings for Python (enforced by `ruff`'s `D` rules, see
  `backend/pyproject.toml`).
- Private/internal helper functions only need a docstring if their purpose
  is not obvious from the name and signature.

## Security

- No hardcoded secrets, API keys, tokens, or credentials in any file, ever.
  Use environment variables and a `.env` file (gitignored) for local
  config.
- Validate and sanitize input at every trust boundary (API endpoints,
  anything from the client). Never trust client-supplied data for
  authorization decisions.
- No `eval`, `exec`, or equivalent dynamic code execution on
  externally-influenced input.
- Parameterized queries only, never string-built SQL, once a database is
  introduced.
- Run `/security-review` before merging `dev` into `main`.
- Keep dependencies current; do not pin to known-vulnerable versions.

## Folder structure

Backend (FastAPI, Python):
```
backend/
  app/
    __init__.py
    main.py        # FastAPI app instance, mounts routers
    api/            # route handlers, grouped by feature
    core/           # config, settings, shared utilities
    models/         # Pydantic schemas / data models
    services/       # business logic (round resolution, Power calc, etc.)
  requirements.txt
  pyproject.toml
```
As the backend grows, business logic belongs in `services/`, not in route
handlers. Route handlers should stay thin: parse input, call a service,
return the result.

Frontend (React + Vite): follow the existing `src/` scaffold; group
components by feature as the app grows rather than by file type once it
gets big enough to matter. Do not restructure it speculatively before
there is enough code to justify it.

## Tooling and enforcement

- **Backend**: `ruff` for linting, formatting, complexity, security
  (bandit-equivalent `S` rules), and docstring enforcement (`D` rules).
  Config in `backend/pyproject.toml`.
- **Frontend**: `oxlint`. Config in `frontend/.oxlintrc.json`.
- **Pre-commit hooks** (`.pre-commit-config.yaml`) run both automatically
  on every commit, plus basic hygiene checks (trailing whitespace,
  merge-conflict markers, private-key detection, secret scanning). A
  commit that fails these checks should be fixed, not bypassed with
  `--no-verify`.
- Setup: see `docs/ENVIRONMENT_SETUP.md`.

## Before merging `dev` into `main`

Run `/code-review` and `/security-review` on the diff. Do not merge on a
failing pre-commit run.
