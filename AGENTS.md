# fireSim Repository Memory

- FireSim uses Blender 5.0+ to generate simple synthetic scenes from Python scripts.
- Added `scripts/generate_scene.py` as the canonical scene builder and updated `scripts/test.py` to delegate to it.
- Introduced `scripts/setup_dev_linux.sh` to install Blender, ensure pip availability, install Python deps, and validate `generate_scene.py`.
- Added `tests/test_setup.py` to verify Blender version, its embedded Python, and the scene script.
- Added procedural grass blade generation governed by a new `[grass]` config section; the generator scatters hundreds of blades for the green ground and logs the final blade count alongside exported assets.

- Assets and output directories are expected within the repo root for future renders.
- `scripts/generate_scene.py` now loads `config/config.toml`, builds procedural tree/ground/shrub/rock assets exported under `assets/`, and exports the final scene/render to `output/` for reproducibility.

