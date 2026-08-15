"""Run the one-shot A bootstrap with a corrected partial-wrap source profile.

The first materialization proved live Curve+Screw source authority works, but a
partial sweep whose profile touches the axis generates repeated coincident pole
vertices in Blender Screw and therefore zero-area runtime triangles. A wrap is
more truthfully a thin sleeve anyway: use a closed rectangular wall profile and
sweep that part-way around the axis.

This adapter is migration-only and is deleted with the bootstrap.
"""
from __future__ import annotations

from pathlib import Path

path = Path(__file__).with_name("bootstrap_a_item_sources.py")
source = path.read_text(encoding="utf-8")
old = '''def wrap(name, radius, height, *, parent, material, segments=16, sweep=.55):
    return screw_profile(name, [(0.0, radius), (height, radius)], parent=parent,
                         material=material, segments=segments, sweep=sweep, role="wrap_profile")
'''
new = '''def wrap(name, radius, height, *, parent, material, segments=16, sweep=.55, thickness=.04):
    profile = [(0.0, radius-thickness/2), (0.0, radius+thickness/2),
               (height, radius+thickness/2), (height, radius-thickness/2)]
    return screw_profile(name, profile, parent=parent, material=material,
                         segments=segments, sweep=sweep, closed_profile=True,
                         cap_axis=False, role="wrap_profile")
'''
if source.count(old) != 1:
    raise RuntimeError("A wrap helper changed; review migration adapter")
source = source.replace(old, new)
exec(compile(source, str(path), "exec"), {"__name__": "__main__", "__file__": str(path)})
