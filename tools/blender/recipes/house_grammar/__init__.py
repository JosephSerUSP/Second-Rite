"""The St. Maria parametric house grammar.

Pure Python: nothing here imports ``bpy``.  See :mod:`records` for the output
contract and :mod:`recipe` for the input schema.
"""

from .recipe import (  # noqa: F401
    BuildingRecipe, Course, Opening, RoofSection, Wing, build,
)
from .records import GrammarError, MeshBuilder, MeshRecord, ModifierSpec, validate  # noqa: F401
