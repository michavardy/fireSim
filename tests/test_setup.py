import os
import subprocess
from distutils.version import LooseVersion
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENE_SCRIPT = REPO_ROOT / "scripts" / "generate_tree_scene.py"
OUTPUT_BLEND = REPO_ROOT / "output" / "tree.blend"
OUTPUT_PNG = REPO_ROOT / "output" / "tree.png"


def _run(command, env=None):
    return subprocess.run(command, capture_output=True, text=True, env=env)


def blender_cmd(*args, timeout_seconds: int = 120):
    return ["timeout", str(timeout_seconds), "blender", *args]


@pytest.fixture(scope="session")
def generated_scene():
    command = blender_cmd("--background", "--python", str(SCENE_SCRIPT))
    env = os.environ.copy()
    env["FIRE_SIM_FAST_RENDER"] = "1"
    result = _run(command, env=env)
    print(result.stdout)
    if result.returncode != 0:
        print("Scene generation stderr:\n", result.stderr)
    assert result.returncode == 0, "Scene generation script failed"
    return result


def test_blender_version():
    result = _run(blender_cmd("--version"))
    print("Blender version output:\n", result.stdout)
    assert result.returncode == 0, result.stderr

    first_line = result.stdout.splitlines()[0] if result.stdout else ""
    assert first_line, "blender --version did not produce any output"

    parts = first_line.split()
    assert len(parts) >= 2, "Unable to parse Blender version"
    version_text = parts[1]
    assert LooseVersion(version_text) >= LooseVersion("5.0"), (
        f"Blender version {version_text} is older than 5.0"
    )


def test_blender_python_executes():
    result = _run(
        blender_cmd("--background", "--python-expr", "print('BLENDER_PYTHON_OK')")
    )
    print(result.stdout)
    assert result.returncode == 0, result.stderr
    assert "BLENDER_PYTHON_OK" in result.stdout


def test_scene_script_runs(generated_scene):
    assert generated_scene.returncode == 0


def test_output_files_exist(generated_scene):
    assert OUTPUT_BLEND.exists(), "Blender scene file is missing"
    assert OUTPUT_PNG.exists(), "Render image is missing"


def test_blend_contains_tree_and_ground(generated_scene):
    check = _run(
        blender_cmd(
            "--background",
            str(OUTPUT_BLEND),
            "--python-expr",
            "import bpy; names = {obj.name for obj in bpy.data.objects}; assert 'Ground' in names and 'RealisticTree' in names; print('objects verified')",
        )
    )
    print(check.stdout)
    if check.returncode != 0:
        print("Blend validation stderr:\n", check.stderr)
    assert check.returncode == 0, "Loaded blend did not contain the expected objects"
