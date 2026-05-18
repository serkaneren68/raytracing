#!/bin/sh
set -eu

quality="${1:-medium}"

case "$quality" in
  preview)
    width=960
    samples=24
    depth=18
    tex_w=1024
    tex_h=1024
    ;;
  medium)
    width=1600
    samples=96
    depth=28
    tex_w=2048
    tex_h=2048
    ;;
  final)
    width=2200
    samples=256
    depth=36
    tex_w=3072
    tex_h=3072
    ;;
  *)
    echo "Usage: sh scripts/render_glass_mesh.sh [preview|medium|final]" >&2
    exit 1
    ;;
esac

mkdir -p generated outputs

python3 scripts/png_to_ppm.py "assets/images/yg.png" "generated/yg.ppm"
python3 scripts/ply_to_revolved_norm.py \
  "assets/pointclouds/glass.ply" \
  "generated/glass_revolved.norm"

RT_SCENE_CONFIG="config/presets/scene_glass_mesh.cfg" \
RT_TARGET_IMAGE="generated/yg.ppm" \
RT_IMAGE_WIDTH="$width" \
RT_SAMPLES="$samples" \
RT_MAX_DEPTH="$depth" \
RT_TEXTURE_WIDTH="$tex_w" \
RT_TEXTURE_HEIGHT="$tex_h" \
./build/raytracing > "outputs/glass_mesh_yg_${quality}.ppm"

echo "Wrote outputs/glass_mesh_yg_${quality}.ppm"
