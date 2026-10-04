"""Stage the default Project for native St. Maria route verification.

Town content is authored in the Project and shared by every export target.
"""
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[7]
STAGE = ROOT / 'out/st-maria-playtest/game'
subprocess.run(['node', 'tools/ci/stage-project-gates.js', '--output', str(STAGE)], cwd=ROOT, check=True)
print('DEFAULT TOWN PROOF STAGE:', STAGE)
