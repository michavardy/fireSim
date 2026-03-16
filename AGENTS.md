# fireSim Repository Memory

- Use AI or procedural generation to create tree, ground, and shrubs
- Minimize manual Blender modeling
- Assemble scene in Blender, assign materials
- Added moto-backed S3 client tests referencing assets/tree_1 and pytest commands in README.
- Added scripts/load_all_assets.py to batch-upload assets/ via S3AssetClient and tests ensure tree_1 uploads can be streamed from moto-backed S3.
- Generated tree scene script now honors the FIRE_SIM_FAST_RENDER flag to skip heavy renders during testing.
- tests/test_setup.py sets FIRE_SIM_FAST_RENDER=1 so pytest stays fast while still creating tree.blend and tree.png placeholders.



- Render image to output/
