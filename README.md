# Hostile Ledger

A web-based financial strategy game for a small group of friends (3 to 10)
playing together in one sitting - start to finish in under an hour, like a
board game night. Everyone builds a company and grows a **Power** score
built from cash, real estate, stock positions, loans, and captured rivals -
not just a single net-worth number. The biggest plays (a Hostile Bid on a
rival's company) usually need allies to pull off, some of your allies might
secretly want you to fail, and every claim anyone makes can be bluffed.
See [`docs/GDD.md`](docs/GDD.md) for the full design.

## Repository structure

- **`docs/`** - all project documentation.
  - [`GDD.md`](docs/GDD.md) - the full game design: the Power system, the
    Building/Conflict phase structure, all six ways to make money, combat
    rules, Power Cards, and the MVP scope for the first playable version.
  - [`GAMEPLAY.md`](docs/GAMEPLAY.md) - the practical companion to the GDD:
    what a player actually sees and does, round by round.
  - [`TABLE_REFERENCE.html`](docs/TABLE_REFERENCE.html) - a print-and-play
    reference card for running a live game: the round loop, rates, combat
    math, and all 7 Power Cards laid out to cut apart and deal privately.
  - [`MARKET_RESEARCH.md`](docs/MARKET_RESEARCH.md) - research into
    competing games (mobile 4X strategy titles, social-deduction/
    negotiation games, and economic-negotiation board games like 18xx and
    Chinatown) that shaped the design decisions in the GDD.
  - [`BALANCE_TESTING.md`](docs/BALANCE_TESTING.md) - results from the
    simulations used to test and tune the game's numbers before building
    anything, including bugs and exploits that were found and fixed along
    the way (loan interest, Hostile Bid math, alliance betrayal payouts).
  - [`ENVIRONMENT_SETUP.md`](docs/ENVIRONMENT_SETUP.md) - how the Python
    dev environment is created and auto-initialized when opening this
    project in VS Code.
- **`sim/`** - the Python simulations behind every finding in
  `BALANCE_TESTING.md`: `power_simulation.py` (the original 6-archetype
  bot pod) and `human_sim.py` (the human-shaped extension, mistakes,
  Power Cards, Hidden Raiders, and everything else validated since).
- **`backend/`** - Python + FastAPI backend, structured as an `app/`
  package per `CLAUDE.md`'s conventions. Currently a minimal scaffold
  (`app/main.py` with a health-check endpoint); this is where round
  resolution and game-state logic will live.
- **`CLAUDE.md`** - coding standards for this project: writing style, code
  quality, docstrings, security practices, folder structure, and the
  linting/pre-commit tooling that enforces them.
- **`frontend/`** - React + Vite frontend. Currently the default scaffold
  from `npm create vite`; this is where the actual game UI will be built.
- **`.vscode/`** - editor settings that auto-select the project's Python
  environment and auto-run its setup task whenever this folder is opened
  in VS Code (see `docs/ENVIRONMENT_SETUP.md` for details).

## Status

Design and balance-testing phase. No gameplay has been built yet - the
current focus is nailing down the rules and numbers (see `docs/GDD.md`
Section 9 for open questions) before writing game code.
