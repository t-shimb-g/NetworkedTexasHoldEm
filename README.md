# Networked Texas-Hold-Em Poker
## Overview
A completely networked way to play Texas-Hold-Em Poker! Works with up to 9 players.

## Setup
1. Python 3.11 or later is required. Install [here](https://www.python.org/downloads/).
2. In root directory, run `python -m venv .venv` to create Python virtual environment
3. Run the following command to activate the environment:
   - Windows (Command Prompt): `.venv\Scripts\activate`
   - Windows (PowerShell): `.venv\Scripts\Activate.ps1`
   - macOS/Linux: `source .venv/bin/activate`
4. Install `TexasHoldEm` using `pip install texasholdem`

## Using
- `server.py` is the only script that requires [`TexasHoldEm`](https://github.com/SirRender00/texasholdem/tree/v0.11.0/). It accepts all traffic trying to connect.
- `client.py` simply needs to update `HOST, PORT = '<update here>', 8080` to reflect the IP of the server machine.
- Run `server.py` first, connect using `client.py` on different machines, and play poker!