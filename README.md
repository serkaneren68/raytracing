# Raytracing

Small C++ ray tracer plus a Python calibration/tooling workspace for anamorphic reflections on reflective objects such as a cylinder, glass mesh, or a real-world cezve/frustum setup.

## Repo layout

- `src/`, `include/raytracing/`: core ray tracer
- `config/`: scene configs and presets
- `scripts/`: render helpers and image conversion utilities
- `python/calibration/`: camera intrinsics + pose estimation workflow
- `python/real_world_example/`: real tablet + camera scene utilities
- `assets/`: input images, meshes, and point clouds
- `generated/`, `outputs/`: generated textures and rendered images

## Build

```bash
cmake -S . -B build
cmake --build build
```

This produces `build/raytracing`.

## Run the renderer

Default run:

```bash
./build/raytracing > outputs/render.ppm
```

Useful environment variables:

- `RT_SCENE_CONFIG`: scene config file, default `config/default.cfg`
- `RT_TARGET_IMAGE`: target image used for inverse mapping
- `RT_PHOTO_IMAGE`: generated anamorphic texture written to disk
- `RT_PRINT_INFO_FILE`: print/layout metadata for the generated texture
- `RT_IMAGE_WIDTH`, `RT_SAMPLES`, `RT_MAX_DEPTH`: render quality controls
- `RT_TEXTURE_WIDTH`, `RT_TEXTURE_HEIGHT`: generated texture resolution

## Preset scripts

Quick entry points:

```bash
sh scripts/render_cylinder.sh
sh scripts/render_glass_mesh.sh
sh scripts/render_glass_pointcloud.sh
sh scripts/render_real_world_example.sh preview assets/images/yg.png
```

The real-world script converts the input PNG to PPM, generates the tablet texture, and renders the calibrated scene to `outputs/real_world_example_<quality>.ppm`.

## Real-world workflow

1. Estimate intrinsics and reference pose in `python/calibration/`.
2. Store the board-to-tablet anchor in `python/calibration/config/tablet_screen_reference.json`.
3. Keep the real scene definition in `python/real_world_example/config/scene.json`.
4. Render the calibrated setup with `scripts/render_real_world_example.sh`.

More detail lives in:

- [python/calibration/README.md](python/calibration/README.md)
- [python/real_world_example/README.md](python/real_world_example/README.md)

## Utility scripts

- `scripts/png_to_ppm.py`: converts PNG input into magenta-backed PPM
- `scripts/photo_to_a4_pdf.py`: lays out a generated image for printing
- `scripts/mirror_subject_from_left.py`: finds the central circle and mirrors non-purple pixels about that vertical axis

## Notes

- The renderer writes PPM images to stdout, so shell redirection is expected.
- The Python utilities rely on Pillow, and calibration scripts also use OpenCV and NumPy.

## For Demo, RUN :


#!/bin/sh
set -eu

quality="${1:-preview}"
target_png="${2:-assets/images/yg6.png}"

case "$quality" in
  preview)
    width=1200
    samples=32
    depth=18
    tex_w=1550
    tex_h=900
    ;;
  medium)
    width=1800
    samples=96
    depth=28
    tex_w=1860
    tex_h=1080
    ;;
  final)
    width=2400
    samples=256
    depth=40
    tex_w=2480
    tex_h=1440
    ;;
  *)
    echo "Usage: sh scripts/render_real_world_example.sh [preview|medium|final] [target.png]" >&2
    exit 1
    ;;
esac

mkdir -p generated outputs

python3 scripts/png_to_ppm.py "$target_png" "generated/real_world_target.ppm"

RT_SCENE_CONFIG="config/presets/scene_real_world_example.cfg" \
RT_TARGET_IMAGE="generated/real_world_target.ppm" \
RT_PHOTO_IMAGE="generated/real_world_example_photo.ppm" \
RT_PRINT_INFO_FILE="generated/real_world_example_print_info.txt" \
RT_IMAGE_WIDTH="$width" \
RT_SAMPLES="$samples" \
RT_MAX_DEPTH="$depth" \
RT_TEXTURE_WIDTH="$tex_w" \
RT_TEXTURE_HEIGHT="$tex_h" \
./build/raytracing > "outputs/real_world_example_${quality}.ppm"

echo "Wrote outputs/real_world_example_${quality}.ppm"

