import subprocess
from distutils.version import LooseVersion
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCENE_SCRIPT = REPO_ROOT / "scripts" / "test.py"


def _run(command):
    return subprocess.run(command, capture_output=True, text=True)


def test_blender_version():
    result = _run(["blender", "--version"])
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
    result = _run([
        "blender",
        "--background",
        "--python-expr",
        "print('BLENDER_PYTHON_OK')",
    ])
    print(result.stdout)
    assert result.returncode == 0, result.stderr
    assert "BLENDER_PYTHON_OK" in result.stdout


def test_scene_script_runs():
    result = _run([
        "blender",
        "--background",
        "--python",
        str(SCENE_SCRIPT),
    ])
    print(result.stdout)
    assert result.returncode == 0, result.stderr
