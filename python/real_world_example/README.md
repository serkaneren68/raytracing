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

## Tablet frame convention

- origin: tablet screen **top-right corner**
- +x: toward the **right**, so visible screen points have negative `x`
- +y: toward the **bottom** edge of the screen
- +z: screen normal, pointing toward the camera side

For the real setup, the short screen edge is treated as the `x` span and the long screen edge as the `y` span.

Valid ranges for points on the screen: `x_mm in [-180, 0]`, `y_mm in [0, 310]`.

Reference points:

- top-right corner: `(0, 0)`
- top-left corner: `(-180, 0)`
- bottom-right corner: `(0, 310)`
- bottom-left corner: `(-180, 310)`
- top-edge midpoint: `(-90, 0)`
- screen center: `(-90, 155)`

## Next step

Update `cezve.base_center_in_tablet_mm` using the convention above, then build the forward reflection map on top of this scene file.

## Forward Reflection Map

Once the cezve base center is filled in, generate the first geometric reflection map with:

```bash
python3 python/real_world_example/scripts/forward_reflection_map.py \
  --scene python/real_world_example/config/scene.json
```

Outputs are written to `python/real_world_example/output/`.
