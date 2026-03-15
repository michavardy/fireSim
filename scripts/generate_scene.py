import bpy
import math
import random
from pathlib import Path
from math import radians
from mathutils import Vector
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = REPO_ROOT / "config" / "config.toml"
ASSETS_DIR = REPO_ROOT / "assets"
TREE_DIR = ASSETS_DIR / "trees"
SHRUB_DIR = ASSETS_DIR / "shrubs"
ROCK_DIR = ASSETS_DIR / "rocks"
TERRAIN_DIR = ASSETS_DIR / "terrain"
OUTPUT_DIR = REPO_ROOT / "output"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")
    with open(CONFIG_PATH, "rb") as handle:
        return tomllib.load(handle)


def ensure_directories() -> None:
    for path in (TREE_DIR, SHRUB_DIR, ROCK_DIR, TERRAIN_DIR, OUTPUT_DIR):
        path.mkdir(parents=True, exist_ok=True)


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def smooth_object(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.shade_smooth()
    obj.select_set(False)


def align_object_to_vector(obj: bpy.types.Object, direction: Vector) -> None:
    direction = direction.normalized()
    up = Vector((0.0, 0.0, 1.0))
    if direction.length == 0:
        return
    rot_quat = up.rotation_difference(direction)
    obj.rotation_euler = rot_quat.to_euler()


def create_procedural_material(
    name: str,
    color_low: list[float],
    color_high: list[float],
    noise_scale: float,
    bump_strength: float,
    roughness: float = 0.8,
    metallic: float = 0.0,
    specular: float = 0.3,
    subsurface: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name=name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputMaterial")
    output.location = (400, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)

    def set_input(name: str, value: float) -> None:
        socket = bsdf.inputs.get(name)
        if socket is not None:
            socket.default_value = value

    set_input("Metallic", metallic)
    set_input("Specular", specular)
    set_input("Subsurface", subsurface)
    set_input("Roughness", roughness)

    noise = nodes.new(type="ShaderNodeTexNoise")
    noise.location = (-400, 120)
    noise.inputs["Scale"].default_value = noise_scale
    noise.inputs["Detail"].default_value = 5.2

    ramp = nodes.new(type="ShaderNodeValToRGB")
    ramp.location = (-200, 120)
    ramp.color_ramp.elements[0].color = color_low
    ramp.color_ramp.elements[1].color = color_high

    bump = nodes.new(type="ShaderNodeBump")
    bump.location = (-100, -120)
    bump.inputs["Strength"].default_value = bump_strength
    bump.inputs["Distance"].default_value = 0.25

    rough_noise = nodes.new(type="ShaderNodeTexNoise")
    rough_noise.location = (-400, -120)
    rough_noise.inputs["Scale"].default_value = noise_scale * 1.5
    rough_noise.inputs["Detail"].default_value = 3.5

    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(rough_noise.outputs["Fac"], bsdf.inputs["Roughness"])
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    return material


def create_ground(config: dict, material: bpy.types.Material) -> bpy.types.Object:
    scene_cfg = config["scene"]
    ground_cfg = config["ground"]
    scene_size = float(scene_cfg["size"])
    subdivisions = int(ground_cfg["subdivisions"])

    bpy.ops.mesh.primitive_grid_add(
        size=scene_size,
        x_subdivisions=subdivisions,
        y_subdivisions=subdivisions,
        location=(0, 0, 0),
    )
    ground = bpy.context.object
    ground.name = "Ground"
    ground.data.materials.append(material)

    disp_mod = ground.modifiers.new("GroundDisplace", type="DISPLACE")
    disp_tex = bpy.data.textures.new("GroundNoise", type="CLOUDS")
    disp_tex.noise_scale = ground_cfg["noise_scale"]
    disp_tex.noise_depth = 2
    disp_mod.texture = disp_tex
    disp_mod.strength = ground_cfg["displacement_strength"]

    bpy.context.view_layer.objects.active = ground
    bpy.ops.object.modifier_apply(modifier=disp_mod.name)
    smooth_object(ground)

    return ground



def create_leaf_plane(
    position: Vector,
    direction: Vector,
    radius: float,
    leaf_material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_plane_add(size=1, location=position)
    leaf = bpy.context.object
    vertical_tilt = math.radians(90) + random.uniform(-0.18, 0.18)
    leaf.rotation_euler = (
        vertical_tilt,
        random.uniform(-0.15, 0.15),
        0.0,
    )
    horizontal = Vector((direction.x, direction.y, 0.0))
    if horizontal.length == 0:
        heading = random.uniform(0, math.tau)
    else:
        heading = math.atan2(horizontal.y, horizontal.x)
    leaf.rotation_euler[2] = heading + random.uniform(-0.6, 0.6)
    leaf.scale = (
        radius * random.uniform(0.6, 0.85),
        radius * random.uniform(0.9, 1.2),
        1.0,
    )
    leaf.location.z += random.uniform(-radius * 0.05, radius * 0.1)
    leaf.data.materials.clear()
    leaf.data.materials.append(leaf_material)
    return leaf


def create_leaf_cluster(
    position: Vector,
    direction: Vector,
    tree_cfg: dict,
    leaf_material: bpy.types.Material,
    tree_objects: list[bpy.types.Object],
) -> None:
    cluster_size = tree_cfg.get("leaf_cluster_size", 4)
    for _ in range(cluster_size):
        offset = Vector(
            (
                random.uniform(-0.35, 0.35),
                random.uniform(-0.35, 0.35),
                random.uniform(-0.15, 0.35),
            )
        )
        leaf_pos = position + offset
        radius = tree_cfg["leaf_radius"] * random.uniform(0.55, 1.2)
        if random.random() < 0.55:
            bpy.ops.mesh.primitive_ico_sphere_add(
                subdivisions=2,
                radius=radius,
                location=leaf_pos,
            )
            leaf = bpy.context.object
            leaf.name = f"Leaf_{len(tree_objects)}"
            leaf.data.materials.clear()
            leaf.data.materials.append(leaf_material)
            leaf.rotation_euler = (
                random.uniform(0, math.tau),
                random.uniform(0, math.tau),
                random.uniform(0, math.tau),
            )
            leaf.scale *= random.uniform(0.75, 1.1)
            smooth_object(leaf)
        else:
            leaf = create_leaf_plane(
                leaf_pos,
                direction,
                radius * random.uniform(0.7, 1.0),
                leaf_material,
            )
            leaf.name = f"LeafPlane_{len(tree_objects)}"
        tree_objects.append(leaf)


def create_tree(config: dict, materials: dict[str, bpy.types.Material]) -> list[bpy.types.Object]:
    tree_cfg = config["tree"]
    tree_objects: list[bpy.types.Object] = []

    def grow_branch(origin: Vector, direction: Vector, length: float, radius: float, depth: int) -> None:
        if length < 0.12 or radius < 0.015:
            return

        bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, location=(0, 0, 0))
        branch = bpy.context.object
        branch.name = f"TreeBranch_{depth}_{len(tree_objects)}"
        align_object_to_vector(branch, direction)
        branch.location = origin + direction * (length * 0.5)
        branch.data.materials.clear()
        branch.data.materials.append(materials["bark"])
        smooth_object(branch)
        tree_objects.append(branch)

        tip = origin + direction * length
        if depth >= tree_cfg["leaf_start_depth"]:
            create_leaf_cluster(tip, direction, tree_cfg, materials["leaf"], tree_objects)
        if depth >= tree_cfg["branch_depth"]:
            return

        for _ in range(tree_cfg["branch_factor"]):
            jitter = Vector(
                (
                    random.uniform(-0.4, 0.4),
                    random.uniform(-0.4, 0.4),
                    random.uniform(0.2, 1.0),
                )
            )
            new_direction = (direction + jitter).normalized()
            grow_branch(
                tip,
                new_direction,
                length * tree_cfg["branch_length_factor"],
                radius * tree_cfg["branch_radius_factor"],
                depth + 1,
            )

    grow_branch(
        Vector((0, 0, 0)),
        Vector((0, 0, 1)),
        tree_cfg["height"],
        tree_cfg["trunk_radius"],
        0,
    )

    return tree_objects


def export_objects(objects: list[bpy.types.Object], target_path: Path) -> None:
    if not objects:
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(
        filepath=str(target_path),
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_apply=True,
    )
    bpy.ops.object.select_all(action="DESELECT")


def sample_ground_height(scene: bpy.types.Scene, depsgraph, x: float, y: float, config: dict) -> float:
    origin_height = config["scene"]["size"]
    origin = Vector((x, y, origin_height))
    direction = Vector((0.0, 0.0, -1.0))
    hit, location, *_ = scene.ray_cast(depsgraph, origin, direction)
    if hit:
        return location.z
    return 0.0


def random_ground_position(
    config: dict,
    min_distance: float | None = None,
    max_distance: float | None = None,
) -> tuple[float, float]:
    scene_size = config["scene"]["size"]
    margin = config["scene"].get("margin", 0.5)
    half = scene_size / 2 - margin
    clearance = config["scene"].get("tree_clearance", 1.2)
    min_dist = max(clearance, min_distance) if min_distance is not None else clearance
    max_dist = half if max_distance is None else min(max_distance, half)
    if max_dist < min_dist:
        max_dist = min_dist
    while True:
        x = random.uniform(-half, half)
        y = random.uniform(-half, half)
        dist = math.hypot(x, y)
        if dist < min_dist or dist > max_dist:
            continue
        return x, y



def create_grass_blade(
    x: float,
    y: float,
    z: float,
    index: int,
    config: dict,
    material: bpy.types.Material,
) -> bpy.types.Object:
    grass_cfg = config["grass"]
    height = random.uniform(*grass_cfg["blade_height_range"])
    width = grass_cfg.get("blade_width", 0.035)
    location = (
        x + random.uniform(-0.02, 0.02),
        y + random.uniform(-0.02, 0.02),
        z + height * 0.5,
    )
    bpy.ops.mesh.primitive_plane_add(size=1, location=location)
    blade = bpy.context.object
    blade.name = f"GrassBlade_{index}"
    tilt = math.radians(90) + random.uniform(-0.18, 0.18)
    blade.rotation_euler = (
        tilt,
        random.uniform(-0.3, 0.3),
        random.uniform(0, math.tau),
    )
    blade.scale = (
        width * random.uniform(0.6, 1.0),
        height,
        1.0,
    )
    blade.data.materials.clear()
    blade.data.materials.append(material)
    return blade


def scatter_grass(
    config: dict,
    scene: bpy.types.Scene,
    depsgraph,
    grass_material: bpy.types.Material,
) -> list[bpy.types.Object]:
    grass_cfg = config["grass"]
    blades: list[bpy.types.Object] = []
    for idx in range(grass_cfg["count"]):
        x, y = random_ground_position(config)
        z = sample_ground_height(scene, depsgraph, x, y, config)
        blade = create_grass_blade(x, y, z, idx + 1, config, grass_material)
        blades.append(blade)
    return blades


def create_shrub(
    x: float,
    y: float,
    z: float,
    index: int,
    config: dict,
    material: bpy.types.Material,
) -> bpy.types.Object:
    shrubs_cfg = config["shrubs"]
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=shrubs_cfg["detail"], radius=1, location=(x, y, z))
    shrub = bpy.context.object
    shrub.name = f"Shrub_{index}"
    scale_x = random.uniform(*shrubs_cfg["scale_range"])
    scale_y = scale_x * random.uniform(0.8, 1.2)
    scale_z = random.uniform(*shrubs_cfg["height_range"])
    shrub.scale = (scale_x, scale_y, scale_z)
    shrub.location.z = z + scale_z * 0.4
    shrub.rotation_euler[2] = random.uniform(0, math.tau)
    shrub.data.materials.clear()
    shrub.data.materials.append(material)

    subdiv = shrub.modifiers.new("ShrubSubdiv", type="SUBSURF")
    subdiv.levels = 2
    subdiv.render_levels = 2

    disp = shrub.modifiers.new("ShrubDisplace", type="DISPLACE")
    disp_tex = bpy.data.textures.new(f"ShrubNoise_{index}", type="CLOUDS")
    disp_tex.noise_scale = shrubs_cfg["noise_scale"]
    disp.texture = disp_tex
    disp.strength = shrubs_cfg["displace_strength"]

    bpy.context.view_layer.objects.active = shrub
    bpy.ops.object.modifier_apply(modifier=subdiv.name)
    bpy.ops.object.modifier_apply(modifier=disp.name)
    smooth_object(shrub)

    return shrub


def scatter_shrubs(
    config: dict,
    scene: bpy.types.Scene,
    depsgraph,
    shrub_material: bpy.types.Material,
) -> list[Path]:
    shrubs_cfg = config["shrubs"]
    exported: list[Path] = []
    for idx in range(shrubs_cfg["count"]):
        x, y = random_ground_position(config)
        z = sample_ground_height(scene, depsgraph, x, y, config)
        shrub = create_shrub(x, y, z, idx + 1, config, shrub_material)
        asset_path = SHRUB_DIR / f"shrub_{idx + 1}.glb"
        export_objects([shrub], asset_path)
        exported.append(asset_path)
    return exported


def create_rock(
    x: float,
    y: float,
    z: float,
    index: int,
    config: dict,
    material: bpy.types.Material,
) -> bpy.types.Object:
    rocks_cfg = config["rocks"]
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=1, location=(x, y, z))
    rock = bpy.context.object
    rock.name = f"Rock_{index}"
    scale = random.uniform(*rocks_cfg["scale_range"])
    flatten = rocks_cfg.get("flatten", 0.7)
    rock.scale = (
        scale,
        scale * random.uniform(0.6, 1.0),
        scale * flatten,
    )
    rock.rotation_euler = (
        random.uniform(0, math.tau),
        random.uniform(0, math.tau),
        random.uniform(0, math.tau),
    )
    rock.location.z = z + scale * 0.35
    rock.data.materials.clear()
    rock.data.materials.append(material)

    subdiv = rock.modifiers.new("RockSubdiv", type="SUBSURF")
    subdiv.levels = 2
    subdiv.render_levels = 2

    disp = rock.modifiers.new("RockDisplace", type="DISPLACE")
    disp_tex = bpy.data.textures.new(f"RockNoise_{index}", type="CLOUDS")
    disp_tex.noise_scale = rocks_cfg["noise_scale"]
    disp.texture = disp_tex
    disp.strength = rocks_cfg["displace_strength"]

    bpy.context.view_layer.objects.active = rock
    bpy.ops.object.modifier_apply(modifier=subdiv.name)
    bpy.ops.object.modifier_apply(modifier=disp.name)
    smooth_object(rock)

    return rock


def scatter_rocks(
    config: dict,
    scene: bpy.types.Scene,
    depsgraph,
    rock_material: bpy.types.Material,
) -> list[Path]:
    rocks_cfg = config["rocks"]
    scene_cfg = config["scene"]
    half = scene_cfg["size"] / 2 - scene_cfg.get("margin", 0.5)
    clearance = scene_cfg.get("tree_clearance", 1.2)
    cluster_count = rocks_cfg.get("cluster_count", 2)
    centers: list[tuple[float, float]] = []
    for _ in range(cluster_count):
        centers.append(
            random_ground_position(
                config,
                min_distance=clearance + 0.45,
                max_distance=half - 0.35,
            )
        )
    exported: list[Path] = []
    for idx in range(rocks_cfg["count"]):
        ring_min = rocks_cfg.get("min_distance_from_tree", clearance + 0.25)
        ring_max = rocks_cfg.get("max_distance_from_tree", half)
        if centers and random.random() < 0.65:
            base_x, base_y = random.choice(centers)
            x = base_x + random.uniform(-0.6, 0.6)
            y = base_y + random.uniform(-0.6, 0.6)
            if math.hypot(x, y) > half:
                x, y = random_ground_position(config, min_distance=ring_min, max_distance=ring_max)
        else:
            x, y = random_ground_position(config, min_distance=ring_min, max_distance=ring_max)
        z = sample_ground_height(scene, depsgraph, x, y, config)
        rock = create_rock(x, y, z, idx + 1, config, rock_material)
        asset_path = ROCK_DIR / f"rock_{idx + 1}.glb"
        export_objects([rock], asset_path)
        exported.append(asset_path)
    return exported


def setup_scene_settings(scene: bpy.types.Scene, config: dict) -> None:
    render_cfg = config["render"]
    scene.render.engine = "CYCLES"
    scene.cycles.samples = render_cfg["samples"]
    scene.cycles.device = "CPU"
    scene.cycles.use_adaptive_sampling = True
    view_layer = scene.view_layers[0]
    view_layer.cycles.use_denoising = True
    scene.render.resolution_x = render_cfg["resolution_x"]
    scene.render.resolution_y = render_cfg["resolution_y"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.use_file_extension = True


def configure_world(config: dict) -> None:
    render_cfg = config["render"]
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("ProceduralWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    output = nodes.new(type="ShaderNodeOutputWorld")
    output.location = (200, 0)

    background = nodes.new(type="ShaderNodeBackground")
    background.inputs["Strength"].default_value = render_cfg.get("world_strength", 1.0)

    sky = nodes.new(type="ShaderNodeTexSky")
    sky.location = (-200, 0)
    sky.sun_direction = (0.3, -0.4, 0.8)
    sky.turbidity = 3.5

    links.new(sky.outputs["Color"], background.inputs["Color"])
    links.new(background.outputs["Background"], output.inputs["Surface"])


def setup_camera(scene: bpy.types.Scene, config: dict) -> bpy.types.Object:
    render_cfg = config["render"]
    distance = render_cfg["camera_distance"]
    height = render_cfg["camera_height"]
    target_height = render_cfg.get("camera_target_height", 1.3)

    bpy.ops.object.camera_add(location=(0, -distance, height))
    camera = bpy.context.object
    target = Vector((0, 0, target_height))
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = render_cfg.get("camera_lens", 35)
    camera.data.clip_end = 30.0
    scene.camera = camera
    return camera


def setup_sun(config: dict) -> bpy.types.Object:
    render_cfg = config["render"]
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 5))
    sun = bpy.context.object
    sun.data.energy = render_cfg.get("sun_strength", 6.5)
    sun.rotation_euler = (
        radians(render_cfg.get("sun_elevation", 45)),
        0,
        radians(render_cfg.get("sun_rotation", -25)),
    )
    sun.data.shadow_soft_size = 0.8
    return sun


def render_scene(scene: bpy.types.Scene, config: dict) -> Path:
    render_cfg = config["render"]
    render_path = OUTPUT_DIR / render_cfg["image_name"]
    render_path.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(render_path)
    bpy.ops.render.render(write_still=True)
    return render_path


def save_scene(blend_path: Path) -> None:
    blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))


def main() -> None:
    config = load_config()
    random.seed(config["scene"].get("seed", 0))
    ensure_directories()
    clear_scene()

    scene = bpy.context.scene
    setup_scene_settings(scene, config)
    configure_world(config)

    ground_material = create_procedural_material(
        "GroundMat",
        config["ground"]["color_low"],
        config["ground"]["color_high"],
        config["ground"]["noise_scale"],
        config["ground"]["bump_strength"],
        roughness=config["ground"].get("roughness", 0.85),
    )
    ground = create_ground(config, ground_material)
    depsgraph = bpy.context.evaluated_depsgraph_get()

    bark_material = create_procedural_material(
        "BarkMat",
        config["tree"]["bark_color_low"],
        config["tree"]["bark_color_high"],
        config["tree"].get("bark_noise", 3.0),
        config["tree"].get("bark_bump", 0.8),
        roughness=0.9,
    )
    leaf_material = create_procedural_material(
        "LeafMat",
        config["tree"]["leaf_color_low"],
        config["tree"]["leaf_color_high"],
        config["tree"].get("leaf_noise", 6.0),
        config["tree"].get("leaf_bump", 0.4),
        roughness=0.65,
        specular=0.2,
        subsurface=0.4,
    )
    tree_objects = create_tree(config, {"bark": bark_material, "leaf": leaf_material})
    tree_asset = TREE_DIR / "tree_main.glb"
    export_objects(tree_objects, tree_asset)

    terrain_asset = TERRAIN_DIR / "terrain_main.glb"
    export_objects([ground], terrain_asset)

    shrub_material = create_procedural_material(
        "ShrubMat",
        config["shrubs"]["color_low"],
        config["shrubs"]["color_high"],
        config["shrubs"].get("noise_scale", 3.5),
        config["shrubs"].get("bump_strength", 0.38),
        roughness=0.7,
    )
    rock_material = create_procedural_material(
        "RockMat",
        config["rocks"]["color_low"],
        config["rocks"]["color_high"],
        config["rocks"].get("noise_scale", 1.8),
        config["rocks"].get("bump_strength", 0.9),
        roughness=0.6,
        metallic=0.0,
    )
    grass_material = create_procedural_material(
        "GrassMat",
        config["grass"]["color_low"],
        config["grass"]["color_high"],
        config["grass"].get("noise_scale", 4.5),
        config["grass"].get("bump_strength", 0.3),
        roughness=0.6,
        subsurface=0.2,
    )
    grass_blades = scatter_grass(config, scene, depsgraph, grass_material)

    shrub_assets = scatter_shrubs(config, scene, depsgraph, shrub_material)
    rock_assets = scatter_rocks(config, scene, depsgraph, rock_material)

    setup_camera(scene, config)
    setup_sun(config)

    render_path = render_scene(scene, config)
    blend_path = OUTPUT_DIR / config["render"]["blend_name"]
    save_scene(blend_path)

    print("Scene generation complete:")
    print(f"  Blend file: {blend_path}")
    print(f"  Render: {render_path}")
    print(f"  Tree asset: {tree_asset}")
    print(f"  Terrain asset: {terrain_asset}")
    print(f"  Grass blades: {len(grass_blades)} objects")

    print(f"  Shrub assets: {len(shrub_assets)} files")
    print(f"  Rock assets: {len(rock_assets)} files")


if __name__ == "__main__":
    main()
