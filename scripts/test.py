import bpy
import os

# --------------------------
# 1️⃣ Clear existing objects
# --------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)

# --------------------------
# 2️⃣ Create ground plane (5x5 m)
# --------------------------
bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 0, 0))
ground = bpy.context.object
ground.name = "Ground"

# Grass material (Blender 6 compatible)
mat_grass = bpy.data.materials.new(name="Grass_Mat")
mat_grass.use_nodes = True  # still allowed in 6.x with a warning
bsdf = mat_grass.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.1, 0.6, 0.1, 1)  # green
ground.data.materials.append(mat_grass)

# --------------------------
# 3️⃣ Add a single tree
# --------------------------
# Trunk (cylinder)
bpy.ops.mesh.primitive_cylinder_add(radius=0.1, depth=1.5, location=(0, 0, 0.75))
trunk = bpy.context.object
trunk.name = "Trunk"

mat_trunk = bpy.data.materials.new(name="Trunk_Mat")
mat_trunk.use_nodes = True
bsdf = mat_trunk.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.4, 0.2, 0.05, 1)
trunk.data.materials.append(mat_trunk)

# Foliage (cone)
bpy.ops.mesh.primitive_cone_add(radius1=0.5, depth=1, location=(0, 0, 2))
leaves = bpy.context.object
leaves.name = "Leaves"

mat_leaves = bpy.data.materials.new(name="Leaves_Mat")
mat_leaves.use_nodes = True
bsdf = mat_leaves.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs["Base Color"].default_value = (0.0, 0.5, 0.0, 1)
leaves.data.materials.append(mat_leaves)

print("✅ Simple scene created: 5x5 m grass plane with single tree")

# --------------------------
# 4️⃣ Save the scene
# --------------------------
# Ensure the folder exists

save_path = '.blender/simple_scene.blend'
bpy.ops.wm.save_as_mainfile(filepath=save_path)
print(f"Saved .blend file to: {save_path}")