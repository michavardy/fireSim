import bpy
import os
import sys
import importlib.util
from pathlib import Path

addon_folder = Path(r"C:/Program Files/Blender Foundation/Blender 5.0/5.0/scripts/addons_core")
sys.path.append(str(addon_folder))
import tree_gen  

# --------------------------
# 1️⃣ Clear existing objects
# --------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)

# --------------------------
# 2️⃣ Create ground plane (5x5 m)
# --------------------------
bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 0, 0))
# Track objects before adding the plane
objects_before = set(bpy.data.objects)

# Add plane
bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 0, 0))

# Track new objects
objects_after = set(bpy.data.objects)
new_objects = objects_after - objects_before

# Grab the new object (the plane) and rename it
ground = list(new_objects)[0]
ground.name = "Ground"

# Grass material
mat_grass = bpy.data.materials.new(name="Grass_Mat")
mat_grass.use_nodes = True
bsdf = mat_grass.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.1, 0.6, 0.1, 1)
ground.data.materials.append(mat_grass)

# --------------------------
# 3️⃣ Generate a single tree using TreeGen Python API
# --------------------------
# The bpy.ops.treegen.create_tree operator wraps functions in tree_gen
# We can call them directly. Usually the function is called create_tree() or similar
# Check TreeGen source to confirm the function signature
tree = tree_gen.create_tree(
    location=(0, 0, 0),
    trunk_height=2.0,
    trunk_radius=0.15,
    foliage_radius=1.0,
    foliage_height=1.5,
    branch_density=0.5,
    seed=42
)

# Optionally, rename all generated objects
if isinstance(tree, list):
    for i, obj in enumerate(tree):
        obj.name = f"GeneratedTree_{i}"
else:
    tree.name = "GeneratedTree"

print(f"✅ TreeGen tree created: {tree}")

# --------------------------
# 4️⃣ Save the scene
# --------------------------
save_dir = ".blender"
os.makedirs(save_dir, exist_ok=True)
save_path = os.path.join(save_dir, "treegen_scene.blend")
bpy.ops.wm.save_as_mainfile(filepath=save_path)
print(f"✅ Saved scene: {save_path}")