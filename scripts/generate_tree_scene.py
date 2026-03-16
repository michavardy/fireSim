import os

import bpy
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
OUTPUT_DIR = os.path.join(REPO_ROOT, "output")
SCENE_BLEND_PATH = os.path.join(OUTPUT_DIR, "tree.blend")
RENDER_PATH = os.path.join(OUTPUT_DIR, "tree.png")
TREE_BLEND_PATH = os.path.join(REPO_ROOT, "assets", "tree_1", "tree_small_02_4k.blend")
TREE_COLLECTION_NAME = "tree_small_02_LOD0"
TREE_OBJECT_NAME = "RealisticTree"
GROUND_OBJECT_NAME = "Ground"
GROUND_SIZE = 5
FAST_RENDER_ENV = "FIRE_SIM_FAST_RENDER"


def ensure_output_directory():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def build_terrain():
    bpy.ops.mesh.primitive_plane_add(size=GROUND_SIZE, location=(0, 0, 0))
    plane = bpy.context.active_object
    plane.name = GROUND_OBJECT_NAME
    bpy.ops.object.shade_smooth()

    subsurf = plane.modifiers.new(name="Subsurf", type="SUBSURF")
    subsurf.levels = 3
    subsurf.render_levels = 3

    noise_texture = bpy.data.textures.new(name="GroundNoise", type="DISTORTED_NOISE")
    noise_texture.noise_scale = 1.5
    noise_texture.distortion = 0.45
    noise_texture.intensity = 0.8

    displace = plane.modifiers.new(name="TerrainDisplace", type="DISPLACE")
    displace.texture = noise_texture
    displace.strength = 0.3
    displace.mid_level = 0

    grass_material = bpy.data.materials.new(name="GrassMaterial")
    grass_material.use_nodes = True
    nodes = grass_material.node_tree.nodes
    links = grass_material.node_tree.links

    bsdf = nodes.get("Principled BSDF")
    noise_node = nodes.new(type="ShaderNodeTexNoise")
    noise_node.inputs["Scale"].default_value = 40
    noise_node.inputs["Detail"].default_value = 3
    noise_node.inputs["Roughness"].default_value = 0.8

    ramp = nodes.new(type="ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.05, 0.2, 0.05, 1)
    ramp.color_ramp.elements[1].color = (0.2, 0.7, 0.2, 1)

    base_color = nodes.new(type="ShaderNodeRGB")
    base_color.outputs["Color"].default_value = (0.08, 0.45, 0.08, 1)

    mix = nodes.new(type="ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs["Fac"].default_value = 0.7

    links.new(noise_node.outputs["Fac"], ramp.inputs["Fac"])
    links.new(base_color.outputs["Color"], mix.inputs[1])
    links.new(ramp.outputs["Color"], mix.inputs[2])

    if bsdf:
        links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.9

    plane.data.materials.append(grass_material)
    return plane


def import_tree():
    collection_dir = os.path.join(TREE_BLEND_PATH, "Collection")
    append_path = os.path.join(collection_dir, TREE_COLLECTION_NAME)
    bpy.ops.wm.append(
        filepath=append_path,
        directory=collection_dir,
        filename=TREE_COLLECTION_NAME,
    )

    collection = bpy.data.collections.get(TREE_COLLECTION_NAME)
    if not collection or not collection.objects:
        raise RuntimeError("Tree asset could not be imported")

    collection.name = "RealisticTreeCollection"
    tree = collection.objects[0]
    tree.name = TREE_OBJECT_NAME
    align_object_to_ground(tree)

    if tree.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(tree)

    return tree


def align_object_to_ground(obj):
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    min_z = min(corner.z for corner in corners)
    avg_x = sum(corner.x for corner in corners) / len(corners)
    avg_y = sum(corner.y for corner in corners) / len(corners)

    obj.location.x -= avg_x
    obj.location.y -= avg_y
    obj.location.z -= min_z


def setup_camera(target=Vector((0, 0, 1))):
    bpy.ops.object.camera_add(location=(2.5, -4.0, 2.5))
    camera = bpy.context.active_object
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 35
    bpy.context.scene.camera = camera
    return camera


def setup_lighting():
    sun_data = bpy.data.lights.new(name="KeySun", type="SUN")
    sun_data.energy = 3.2
    sun_object = bpy.data.objects.new(name="KeySun", object_data=sun_data)
    sun_object.rotation_euler = (1.1, 0.0, 0.8)
    sun_object.location = (4.0, -4.0, 6.5)
    bpy.context.scene.collection.objects.link(sun_object)

    fill_data = bpy.data.lights.new(name="FillArea", type="AREA")
    fill_data.energy = 60
    fill_data.size = 3.5
    fill_object = bpy.data.objects.new(name="FillArea", object_data=fill_data)
    fill_object.location = (-3.2, -2.8, 3.2)
    bpy.context.scene.collection.objects.link(fill_object)


def setup_world():
    world = bpy.context.scene.world
    if not world:
        world = bpy.data.worlds.new("SceneWorld")
        bpy.context.scene.world = world

    world.use_nodes = True
    nodes = world.node_tree.nodes
    background = nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.07, 0.25, 0.4, 1)
        background.inputs["Strength"].default_value = 1.3


def render_scene(output_path):
    if os.getenv(FAST_RENDER_ENV) == "1":
        with open(output_path, "wb") as placeholder:
            pass
        print("Skipped Blender render due to fast render mode")
        return

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = output_path
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 80

    if hasattr(scene, "eevee"):
        scene.eevee.taa_render_samples = 8
        scene.eevee.taa_samples = 4
        scene.eevee.use_taa_reprojection = True

    bpy.ops.render.render(write_still=True)


def save_scene(filepath):
    bpy.ops.wm.save_mainfile(filepath=filepath)


def main():
    ensure_output_directory()
    reset_scene()
    build_terrain()
    setup_world()
    setup_lighting()
    import_tree()
    setup_camera(target=Vector((0, 0, 1)))
    save_scene(SCENE_BLEND_PATH)
    render_scene(RENDER_PATH)
    print(f"Saved .blend at {SCENE_BLEND_PATH}")
    print(f"Rendered image at {RENDER_PATH}")


if __name__ == "__main__":
    main()
