#!/bin/sh
set -eu

photo_file="${1:-generated/photo.ppm}"
info_file="${2:-generated/photo_print_info.txt}"
output_file="${3:-outputs/photo_a4_tiled.pdf}"

mkdir -p outputs
python3 scripts/photo_to_a4_pdf.py "$photo_file" "$info_file" "$output_file"
