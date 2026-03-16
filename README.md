# Fire Simulation Dataset Prototype

This project explores a **simple, fully scriptable pipeline for generating synthetic nature scenes** using **Blender and Python**.
The long-term goal is to create realistic environments (terrain, vegetation, fire ignition, smoke, and drone viewpoints) for **synthetic image generation** that can be used to train or evaluate computer vision models for **early forest fire detection**.

### Next Prototype
* 5×5m natural patch
* Single realistic tree
* Realistic ground with rocks and shrubs
* Scene should look photorealistic when rendered
* Assets may be generated externally and imported into Blender

This allows the environment generation pipeline to remain **reproducible, minimal, and easy to extend**.

---

# Project Goals

The broader objectives of this project are:

* Generate **synthetic datasets** for wildfire detection
* Simulate **early fire ignition conditions**
* Render scenes from **drone perspectives**
* Produce both **RGB and infrared-style imagery**
* Automate the pipeline entirely with **Python**

The current implementation focuses only on the **base environment generation**.

---
# Setup

## download and install blender

`sh scripts/install_blender.sh`

## install dependencies
`blender --background --python-expr "import ensurepip, pip install -r requirments.txt"`

---

### Run the script

You can rebuild the photorealistic scene from the terminal:

```bash
timeout 120 blender --background --python scripts/generate_tree_scene.py
```

The script saves the Blender file at `output/tree.blend` and the render at `output/tree.png`.

---

# Project Structure

```
fire-sim/
│
├─ config/
│  └─ ... config files
|
├─ scripts/
│  └─ generate_tree_scene.py
│
├─ assets/                # (future)
│  ├─ trees
│  ├─ shrubs
│  └─ terrain
│
├─ output/                # (future)
│  └─ rendered_images
│
└─ README.md
```




---

# Current Scene

The generated environment includes:

| Element      | Description                                                         |
| ------------ | ------------------------------------------------------------------- |
| Ground       | 5×5 meter terrain with noise-driven displacement and layered grass shader |
| Tree         | Realistic `tree_small_02_4k` asset imported from `assets/tree_1`, centered and grounded |
| Lighting     | Sun lamp combined with an area fill light and a blue-tinted sky background |
| Camera       | 35 mm camera positioned diagonally to frame the tree from a natural angle |

This setup creates a small natural patch with a single realistic tree perched on gently undulating terrain.

---

# Planned Features

Future iterations will extend the environment with:

### Vegetation

* Realistic tree models
* Shrub and ground vegetation
* Procedural foliage scattering

### Terrain

* Procedural hills
* Imported real-world terrain heightmaps

### Fire Simulation

* Ignition sources
* Fire propagation
* Smoke simulation

### Drone Simulation

* Drone-mounted camera
* Path planning
* Multiple viewpoints

### Imaging Simulation

* RGB image simulation
* Infrared image simulation

### Dataset Generation

* RGB renders
* Thermal / infrared-style renders
* Automated dataset export

---

# Future Asset Sources

Potential sources for realistic vegetation and terrain:

* Poly Haven
* Quixel Megascans
* BlenderKit
* Terrain heightmap datasets

These will allow the environment to scale from a single tree to **large forest scenes**.

---
## Testing

1. Install project dependencies and the S3 testing helpers:

   ```bash
   pip install -r requirements.txt
   pip install pytest moto boto3 python-dotenv
   ```

2. Run the dedicated S3 client tests (they rely on `assets/tree_1` for the sample textures):

   ```bash
   pytest tests/test_s3_client.py
   ```

The new test suite uses `moto` to mock S3 so the upload/list/download/stream flows can be exercised without hitting real AWS endpoints.

---



