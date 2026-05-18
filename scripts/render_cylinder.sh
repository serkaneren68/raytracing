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
    echo "Usage: sh scripts/render_cylinder.sh [preview|medium|final]" >&2
    exit 1
    ;;
esac

mkdir -p outputs

RT_SCENE_CONFIG="config/default.cfg" \
RT_TARGET_IMAGE="assets/targets/checkerboard.ppm" \
RT_IMAGE_WIDTH="$width" \
RT_SAMPLES="$samples" \
RT_MAX_DEPTH="$depth" \
RT_TEXTURE_WIDTH="$tex_w" \
RT_TEXTURE_HEIGHT="$tex_h" \
./build/raytracing > "outputs/cylinder_${quality}.ppm"

echo "Wrote outputs/cylinder_${quality}.ppm"
