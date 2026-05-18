#!/usr/bin/env python3
from pathlib import Path
import sys

from PIL import Image


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/png_to_ppm.py <input.png> <output.ppm>", file=sys.stderr)
        return 1

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])

    image = Image.open(src).convert("RGBA")
    rgb = Image.new("RGB", image.size, (255, 0, 255))
    rgb.paste(image, mask=image.getchannel("A"))

    dst.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(dst, format="PPM")
    print(f"Wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
