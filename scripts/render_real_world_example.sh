#!/bin/sh
set -eu

quality="${1:-preview}"
target_png="${2:-assets/images/yg5.png}"

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
