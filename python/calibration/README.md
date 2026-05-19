# Calibration Pipeline

This folder contains the real-world camera/tablet calibration workflow for the anamorphic setup.

The first milestone is:

1. show a known pattern on the tablet,
2. capture multiple iPhone photos into a folder,
3. estimate camera intrinsics and distortion,
4. estimate the camera pose relative to the tablet from a single reference image.

## Layout

- `captures/intrinsics/`: photos used for intrinsic calibration
- `captures/pose/`: single or few photos used for pose estimation
- `output/`: calibration outputs, overlays, and JSON files
- `scripts/`: Python tools

## Recommended Pattern

The tools support both chessboard and ChArUco boards.
For tablet-based calibration, ChArUco is recommended because corner detection is usually more robust.

## Quick Start

Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r python/calibration/requirements.txt
```

Generate a board image:

```bash
python3 python/calibration/scripts/generate_board.py \
  --type charuco \
  --cols 10 \
  --rows 6 \
  --square-mm 20 \
  --marker-mm 15 \
  --output python/calibration/output/charuco_board.png
```

Estimate intrinsics from photos placed in `captures/intrinsics/`:

```bash
python3 python/calibration/scripts/calibrate_intrinsics.py \
  --type charuco \
  --images "python/calibration/captures/intrinsics/*" \
  --cols 10 \
  --rows 6 \
  --square-mm 20 \
  --marker-mm 15 \
  --output python/calibration/output/intrinsics.json
```

Estimate pose from one reference frame:

```bash
python3 python/calibration/scripts/estimate_pose.py \
  --type charuco \
  --image python/calibration/captures/pose/reference.jpg \
  --cols 10 \
  --rows 6 \
  --square-mm 20 \
  --marker-mm 15 \
  --intrinsics python/calibration/output/intrinsics.json \
  --output python/calibration/output/reference_pose.json \
  --overlay python/calibration/output/reference_pose_overlay.jpg
```

## Notes

- Tablet size is currently tracked separately from the calibration board definition.
- The board dimensions must match the image shown on the tablet.
- For highest accuracy, keep the iPhone lens mode fixed while collecting all photos.
