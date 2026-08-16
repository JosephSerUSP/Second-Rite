#!/bin/bash
set -e
cd "$(dirname "$0")/../.."

# #646: `editor-screens-actual/` is evidence for this run, not an append-only
# history. Reset it and stamp the run before the harness can write any frame.
python3 tools/golden/actual_run.py g6

# G6 drives the editor server and a headless Chrome from Python; no xvfb needed,
# Chrome runs headless on its own.
python3 tools/golden/editor-screens.py check
