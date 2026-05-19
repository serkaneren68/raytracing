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
