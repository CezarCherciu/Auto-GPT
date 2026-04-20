"""Render a preview PNG from mysore_palace.blend."""

from __future__ import annotations

import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
BLEND = os.path.join(HERE, "mysore_palace.blend")
OUT = os.path.join(HERE, "mysore_palace_preview.png")

bpy.ops.wm.open_mainfile(filepath=BLEND)

scene = bpy.context.scene
scene.render.resolution_x = 1600
scene.render.resolution_y = 750
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = OUT

# Use Cycles for reliable headless rendering with bpy pip package
scene.render.engine = "CYCLES"
scene.cycles.samples = 64
scene.cycles.use_denoising = True
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "NONE"
except Exception:
    pass
scene.cycles.device = "CPU"

print(f"Rendering to {OUT} ...")
bpy.ops.render.render(write_still=True)
print("Done.")
