import runpy
from pathlib import Path


if __name__ == "__main__":
    script_path = Path(__file__).resolve().with_name("generate_scene.py")
    runpy.run_path(script_path, run_name="__main__")
