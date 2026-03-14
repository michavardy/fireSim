# Fire Simulation Dataset Prototype

This project explores a **simple, fully scriptable pipeline for generating synthetic nature scenes** using **Blender and Python**.
The long-term goal is to create realistic environments (terrain, vegetation, fire ignition, smoke, and drone viewpoints) for **synthetic image generation** that can be used to train or evaluate computer vision models for **early forest fire detection**.

The current version intentionally starts with the **simplest possible scene**:

* A **5×5 meter grass plane**
* A **single tree**
* Generated entirely via a **Python script**

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
`python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`

---

# Requirements

* **Blender 5.x or newer**
* Python (included with Blender)

Download Blender from:

https://www.blender.org/download/

---

# Project Structure

```
fire-sim/
│
├─ config/
│  └─ ... config files
|
├─ scripts/
│  └─ generate_scene.py
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

### Run the script

You can also run the script directly from the terminal:

```
python scripts/generate_scene.py
```

---

# Current Scene

The generated environment includes:

| Element      | Description                                |
| ------------ | ------------------------------------------ |
| Ground       | 5×5 meter plane with simple grass material |
| Tree trunk   | Cylinder mesh                              |
| Tree foliage | Cone mesh                                  |
| Lighting     | Default viewport lighting                  |

This minimal configuration ensures the system works before introducing more complex simulation components.

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


