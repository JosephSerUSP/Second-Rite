"""Read an environment variable a running process was started too early to see.

``setx`` writes to the user environment in the registry and reaches NEW processes
only, so a shell -- or an agent session -- opened before a key was set inherits
nothing and reports a missing variable that is plainly set. Relaunching fixes it;
so does reading the registry, which is cheaper and does not lose the session.

The value is returned, never printed. Callers should keep it that way: a key that
reaches a log or a transcript has to be reissued.
"""

from __future__ import annotations

import os
import subprocess
import sys

_cache = {}


def get(name, scope="User"):
    """The variable from the process, or from the user environment if absent."""
    value = os.environ.get(name)
    if value:
        return value
    if name in _cache:
        return _cache[name]
    if not sys.platform.startswith("win"):
        return None
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "[System.Environment]::GetEnvironmentVariable('%s','%s')"
             % (name, scope)],
            capture_output=True, text=True, timeout=30)
    except Exception:                                  # noqa: BLE001
        return None
    value = (result.stdout or "").strip() or None
    _cache[name] = value
    if value:
        # Put it back so anything spawned from here inherits it, and so a second
        # lookup costs nothing.
        os.environ[name] = value
    return value


def require(*names):
    """All of them, or a message naming the ones that are genuinely absent."""
    found = {name: get(name) for name in names}
    missing = [name for name, value in found.items() if not value]
    if missing:
        raise SystemExit(
            "missing %s. Set it, or if it was just set with setx, note that setx "
            "reaches new processes only." % " and ".join(missing))
    return [found[name] for name in names]
