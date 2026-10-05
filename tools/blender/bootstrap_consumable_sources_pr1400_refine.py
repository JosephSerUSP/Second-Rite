"""Silhouette refinement for the one-shot PR #1400 first-save bootstrap.

Temporary by design. Imports the source-construction vocabulary from the first
bootstrap, changes two authored forms, then performs the first saves. Both
bootstrap scripts are deleted once the resulting .blend documents are adopted.
"""
from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import bootstrap_consumable_sources_pr1400 as base


def _revolve(child):
    return next((modifier for modifier in child.modifiers if modifier.type == "SCREW"), None)


def build_hi_potion(root):
    base.build_hi_potion(root)
    # The old round-family relationship was still too visible at item-view
    # scale. Keep the editable bottle profile, but make the medicinal phial a
    # deliberately four-sided fabrication. The four live gold ribs now align
    # with the vessel's corners rather than decorating another round bottle.
    for child in root.children_recursive:
        screw = _revolve(child)
        if screw is not None:
            screw.steps = 4
            screw.render_steps = 4


def build_mega_potion(root):
    base.build_mega_potion(root)
    # A field canteen should not share the reliquary's radial mass. Flatten the
    # entire authored assembly in depth; this stays as editable object transforms
    # in the source, so the body profile and handles remain live construction.
    for child in root.children_recursive:
        child.scale.y *= 0.58


base.BUILDERS["hi_potion"] = ("Hi-Potion", build_hi_potion)
base.BUILDERS["mega_potion"] = ("Mega-Potion", build_mega_potion)

if __name__ == "__main__":
    base.main()
