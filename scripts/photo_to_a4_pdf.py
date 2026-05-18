#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import sys

from PIL import Image


A4_LANDSCAPE_CM = (29.7, 21.0)
CM_PER_INCH = 2.54
LANCZOS = getattr(Image, "Resampling", Image).LANCZOS


def read_print_info(path: Path) -> dict[str, float]:
    data: dict[str, float] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "=" not in line:
                continue
            key, value = line.split("=", 1)
            try:
                data[key] = float(value.split(",")[0])
            except ValueError:
                continue
    return data


def load_p3_ppm(path: Path) -> Image.Image:
    with path.open("r", encoding="utf-8") as f:
        tokens: list[str] = []
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tokens.extend(line.split())

    if len(tokens) < 4 or tokens[0] != "P3":
        raise ValueError(f"Unsupported or invalid PPM: {path}")

    width = int(tokens[1])
    height = int(tokens[2])
    max_value = int(tokens[3])
    values = list(map(int, tokens[4:]))
    if len(values) != width * height * 3:
        raise ValueError(f"Unexpected pixel count in {path}")

    if max_value != 255:
        values = [int(round(v * 255 / max_value)) for v in values]

    image = Image.new("RGB", (width, height))
    image.putdata([tuple(values[i:i + 3]) for i in range(0, len(values), 3)])
    return image


def cm_to_px(cm: float, dpi: int) -> int:
    return max(1, int(round(cm / CM_PER_INCH * dpi)))


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print(
            "Usage: python3 scripts/photo_to_a4_pdf.py <generated/photo.ppm> <generated/photo_print_info.txt> [output.pdf]",
            file=sys.stderr,
        )
        return 1

    photo_path = Path(sys.argv[1])
    info_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3]) if len(sys.argv) == 4 else Path("outputs/photo_a4_tiled.pdf")

    image = load_p3_ppm(photo_path)
    info = read_print_info(info_path)
    active_width_cm = info.get("active_width_cm")
    active_height_cm = info.get("active_height_cm")
    if not active_width_cm or not active_height_cm:
        raise ValueError("photo_print_info.txt is missing active_width_cm/active_height_cm.")

    dpi = 300
    page_w_cm, page_h_cm = A4_LANDSCAPE_CM
    cols = max(1, int(math.ceil(active_width_cm / page_w_cm)))
    rows = max(1, int(math.ceil(active_height_cm / page_h_cm)))
    total_w_cm = cols * page_w_cm
    total_h_cm = rows * page_h_cm

    poster_w_px = cm_to_px(active_width_cm, dpi)
    poster_h_px = cm_to_px(active_height_cm, dpi)
    page_w_px = cm_to_px(page_w_cm, dpi)
    page_h_px = cm_to_px(page_h_cm, dpi)

    resized = image.resize((poster_w_px, poster_h_px), LANCZOS)
    poster = Image.new("RGB", (cols * page_w_px, rows * page_h_px), (255, 255, 255))
    offset_x = (poster.width - poster_w_px) // 2
    offset_y = (poster.height - poster_h_px) // 2
    poster.paste(resized, (offset_x, offset_y))

    pages: list[Image.Image] = []
    for row in range(rows):
        for col in range(cols):
            left = col * page_w_px
            top = row * page_h_px
            page = poster.crop((left, top, left + page_w_px, top + page_h_px))
            pages.append(page)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(
        output_path,
        "PDF",
        resolution=dpi,
        save_all=True,
        append_images=pages[1:],
    )

    print(f"Wrote {output_path}")
    print(f"Poster size: {active_width_cm:.2f} cm x {active_height_cm:.2f} cm")
    print(f"Layout: {cols} x {rows} A4 landscape pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
