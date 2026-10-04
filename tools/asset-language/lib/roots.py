"""Asset-language adapter to the shared Node Project-root authority."""
from pathlib import Path
import sys

INSTALL_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(INSTALL_ROOT))
from tools.shared.project_paths import default_project_root, project_root as resolve_project
PROJECT_ENV = 'SECOND_RITE_PROJECT'
DEFAULT_PROJECT_ROOT = default_project_root()


def project_root(env=None, default_project_root=None):
    return resolve_project(env=env, default_project_root=default_project_root)
