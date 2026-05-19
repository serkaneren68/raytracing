# Real World Example

This folder is the dedicated workspace for the real tablet + iPhone + cezve setup.

The goal of this example is to keep the real-world scene separate from the older synthetic render presets.

## Current status

Calibration is already available from:

- `python/calibration/output/intrinsics.json`
- `python/calibration/output/reference_pose.json`
- `python/calibration/config/tablet_screen_reference.json`

## Scene file

The main scene definition is:

- `python/real_world_example/config/scene.json`

It collects:

- tablet dimensions
- board-to-tablet reference
- camera intrinsics path
- reference pose path
- cezve frustum dimensions
- cezve placement on the tablet

## Next step

Update `cezve_base_center_in_tablet_mm` once the real tablet position is known, then build the forward reflection map on top of this scene file.

## Forward Reflection Map

Once the cezve base center is filled in, generate the first geometric reflection map with:

```bash
python3 python/real_world_example/scripts/forward_reflection_map.py \
  --scene python/real_world_example/config/scene.json
```

Outputs are written to `python/real_world_example/output/`.
