"""Print what a baked atlas holds: its size, the fraction of texels that carry light, and their mean.

    blender -b --factory-startup -P atlas_stats_blender.py -- environment.png
"""
import json
import sys

import bpy
import numpy as np

path = sys.argv[sys.argv.index("--") + 1]
image = bpy.data.images.load(path)
image.colorspace_settings.name = "sRGB"
width, height = image.size
pixels = np.array(image.pixels[:], dtype=np.float64).reshape(height, width, 4)[..., :3]
lit = pixels.max(axis=2) > 8 / 255.0
print("ATLAS_STATS " + json.dumps({"size": [width, height], "litFraction": float(lit.mean()),
                                   "meanLit": float(pixels[lit].mean() * 255.0) if lit.any() else 0.0}))
