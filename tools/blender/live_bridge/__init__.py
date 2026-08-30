"""Thestra's opt-in bridge to an already-open Blender authoring session.

Blender imports the package root when an add-on ZIP is installed, so the
registration hooks and metadata must live at this boundary.  Keeping the
implementation in :mod:`addon` still lets protocol-only tests import the
package without duplicating any Blender registration logic.
"""

# Blender's legacy add-on discovery reads this literal from the package root
# before it imports the module.  Do not move it behind an import or condition.
bl_info = {
    "name": "Thestra Live Bridge",
    "author": "Second Rite",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "3D View > Sidebar > Thestra",
    "description": "Opt-in authenticated co-authoring bridge",
    "category": "Development",
}

from .server import LiveBridgeServer

try:
    import bpy  # noqa: F401 - presence selects Blender's registration surface
except ImportError:
    # Importing protocol/client modules through this package must remain usable
    # in the ordinary Python test runner, where bpy is intentionally absent.
    __all__ = ["LiveBridgeServer"]
else:
    from .addon import register, unregister

    __all__ = ["LiveBridgeServer", "bl_info", "register", "unregister"]
