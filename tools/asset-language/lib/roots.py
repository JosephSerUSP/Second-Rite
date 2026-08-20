"""Semantic roots for the asset-language checker.

The Python mirror of the contract `tools/semantic-roots.js` owns: the
installation root is the checkout, and the Project is a separate root that the
installation merely knows a default location for. #700 moved Second Gate into
`projects/hichaukitoden-game/`, so a tool that reads authored `data/` or
`assets/` from the checkout root is reading the installation and finding
nothing (#827).

Kept deliberately small. This is the one contract the checker needs -- resolve
a Project root, and fail loudly naming the path when it is not a Project --
rather than a second implementation of the whole Node module.
"""

import os
from pathlib import Path

INSTALL_ROOT = Path(__file__).resolve().parents[3]

# Same environment variable and same default as tools/semantic-roots.js.
PROJECT_ENV = "SECOND_RITE_PROJECT"
DEFAULT_PROJECT_ROOT = INSTALL_ROOT / "projects" / "hichaukitoden-game"


def is_project_root(path):
    """A Project is identified by owning authored data, as the Node side does."""
    return (Path(path) / "data").is_dir()


def project_root(env=None, default_project_root=None):
    """Resolve the Project this run measures.

    An explicitly configured root must be a Project; so must the default. A
    wrong root fails here, naming itself, instead of surfacing later as a
    missing file deep inside a snapshot walk.
    """
    env = os.environ if env is None else env
    configured = env.get(PROJECT_ENV)
    default = Path(default_project_root or DEFAULT_PROJECT_ROOT)

    if configured and configured.strip():
        root = Path(configured).expanduser().resolve()
        label = PROJECT_ENV
    else:
        root = default.resolve()
        label = "default Project root"

    if not root.exists():
        raise RuntimeError(f"{label} points at a path that does not exist: {root}")
    if not is_project_root(root):
        raise RuntimeError(f"{label} is not a Project: {root} contains no data/ directory")
    return root
