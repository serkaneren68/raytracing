#!/bin/sh
set -eu

quality="${1:-medium}"

case "$quality" in
  preview)
    width=960
    samples=32
    depth=20
    tex_w=1024
    tex_h=1024
    ;;
  medium)
    width=1600
    samples=128
    depth=28
    tex_w=2048
    tex_h=2048
    ;;
  final)
    width=2400
    samples=384
    depth=40
    tex_w=3072
    tex_h=3072
    ;;
  *)
    echo "Usage: sh scripts/render_cube_on_cylinder.sh [preview|medium|final]" >&2
    exit 1
    ;;
esac

mkdir -p generated outputs

python3 scripts/png_to_ppm.py "assets/images/yg.png" "generated/yg.ppm"

RT_SCENE_CONFIG="config/default.cfg" \
RT_TARGET_IMAGE="generated/yg.ppm" \
RT_IMAGE_WIDTH="$width" \
RT_SAMPLES="$samples" \
RT_MAX_DEPTH="$depth" \
RT_TEXTURE_WIDTH="$tex_w" \
RT_TEXTURE_HEIGHT="$tex_h" \
./build/raytracing > "outputs/yg_on_cylinder_${quality}.ppm"

echo "Wrote outputs/yg_on_cylinder_${quality}.ppm"
