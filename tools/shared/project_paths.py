"""Python adapter to tools/semantic-roots.js, the existing Project authority.

Requires Node (also required by staging and Studio). Selection is resolved once
per distinct explicit/env/cwd input in this process. Assets and data are Project
content; tools, contracts and scratch output belong to the installation.
"""
from functools import lru_cache
import json
import os
from pathlib import Path
import subprocess

INSTALL_ROOT = Path(__file__).resolve().parents[2]


class ProjectPathError(RuntimeError):
    pass


@lru_cache(maxsize=32)
def _resolve(configured, default, cwd, node, mode='resolve'):
    request = {}
    request['mode'] = mode
    if configured is not None:
        request['projectRoot'] = configured
    if default is not None:
        request['defaultProjectRoot'] = default
    try:
        result = subprocess.run([node, str(INSTALL_ROOT / 'tools/semantic-roots.js')],
            input=json.dumps(request), capture_output=True, text=True, encoding='utf-8', cwd=cwd,
            timeout=30)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ProjectPathError(f'Cannot resolve Project through Node: {error}') from error
    if result.returncode:
        raise ProjectPathError(result.stderr.strip())
    return json.loads(result.stdout)


def project_root(configured=None, *, env=None, default_project_root=None):
    environment = os.environ if env is None else env
    # Forward the selector; Node owns validation, defaulting and resolution.
    if env is not None and configured is None:
        configured = environment.get('SECOND_RITE_PROJECT', '')
    elif configured is None:
        configured = os.environ.get('SECOND_RITE_PROJECT')
    result = _resolve(os.fspath(configured) if configured is not None else None,
        os.fspath(default_project_root) if default_project_root is not None else None,
        str(Path.cwd()), environment.get('NODE_EXECUTABLE', 'node'))
    return Path(result['projectRoot'])


def default_project_root():
    return Path(_resolve('', None, str(Path.cwd()),
        os.environ.get('NODE_EXECUTABLE', 'node'), 'metadata')['defaultProjectRoot'])


def within(root, *parts):
    """Resolve a filesystem target within its explicit owner, including symlinks."""
    root = Path(root).resolve()
    target = root.joinpath(*parts).resolve()
    if not target.is_relative_to(root):
        raise ProjectPathError(f'Refusing a path outside {root}: {target}')
    return target
