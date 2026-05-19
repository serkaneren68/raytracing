#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Find the center of the dashed circle near the image center, then mirror "
            "all non-purple pixels around that vertical axis onto the same image."
        )
    )
    parser.add_argument("input_image", type=Path, help="Input image path, e.g. real_world_example_photo.ppm")
    parser.add_argument("output_image", type=Path, help="Output image path")
    parser.add_argument(
        "--bg-threshold",
        type=float,
        default=45.0,
        help="Color-distance threshold used to classify the purple background (default: 45)",
    )
    parser.add_argument(
        "--center-search-scale",
        type=float,
        default=0.35,
        help="Central crop ratio used while looking for the dashed circle (default: 0.35)",
    )
    parser.add_argument(
        "--center-x",
        type=float,
        default=None,
        help="Optional mirror center x. If given, auto-detection is skipped for x.",
    )
    parser.add_argument(
        "--center-y",
        type=float,
        default=None,
        help="Optional mirror center y. If given, auto-detection is skipped for y.",
    )
    return parser.parse_args()


def sample_background_color(image: Image.Image) -> tuple[int, int, int]:
    width, height = image.size
    patch = max(2, min(width, height) // 40)
    samples: list[tuple[int, int, int]] = []
    corners = (
        (0, 0),
        (width - patch, 0),
        (0, height - patch),
        (width - patch, height - patch),
    )

    for x0, y0 in corners:
        for y in range(y0, y0 + patch):
            for x in range(x0, x0 + patch):
                samples.append(image.getpixel((x, y)))

    channels = list(zip(*samples))
    return tuple(int(sorted(channel)[len(channel) // 2]) for channel in channels)


def color_distance_sq(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum((ca - cb) * (ca - cb) for ca, cb in zip(a, b))


def build_non_background_mask(
    image: Image.Image,
    bg_color: tuple[int, int, int],
    threshold: float,
) -> list[list[bool]]:
    width, height = image.size
    threshold_sq = threshold * threshold
    mask: list[list[bool]] = [[False] * width for _ in range(height)]

    for y in range(height):
        row = mask[y]
        for x in range(width):
            row[x] = color_distance_sq(image.getpixel((x, y)), bg_color) > threshold_sq
    return mask


def is_edge_pixel(mask: list[list[bool]], x: int, y: int, width: int, height: int) -> bool:
    if not mask[y][x]:
        return False

    has_foreground_neighbor = False
    has_background_neighbor = False
    for ny in range(max(0, y - 1), min(height, y + 2)):
        for nx in range(max(0, x - 1), min(width, x + 2)):
            if nx == x and ny == y:
                continue
            if mask[ny][nx]:
                has_foreground_neighbor = True
            else:
                has_background_neighbor = True
    return has_foreground_neighbor and has_background_neighbor


def solve_3x3(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, rhs)]

    for pivot in range(3):
        best_row = max(range(pivot, 3), key=lambda row: abs(augmented[row][pivot]))
        if abs(augmented[best_row][pivot]) < 1e-9:
            raise ValueError("Circle fit became singular")
        augmented[pivot], augmented[best_row] = augmented[best_row], augmented[pivot]

        scale = augmented[pivot][pivot]
        for col in range(pivot, 4):
            augmented[pivot][col] /= scale

        for row in range(3):
            if row == pivot:
                continue
            factor = augmented[row][pivot]
            for col in range(pivot, 4):
                augmented[row][col] -= factor * augmented[pivot][col]

    return [augmented[row][3] for row in range(3)]


def estimate_circle_center(mask: list[list[bool]], width: int, height: int, crop_scale: float) -> tuple[float, float]:
    half_crop_w = max(10, int(width * crop_scale * 0.5))
    half_crop_h = max(10, int(height * crop_scale * 0.5))
    cx0 = width // 2
    cy0 = height // 2

    points: list[tuple[float, float]] = []
    for y in range(max(0, cy0 - half_crop_h), min(height, cy0 + half_crop_h)):
        for x in range(max(0, cx0 - half_crop_w), min(width, cx0 + half_crop_w)):
            if is_edge_pixel(mask, x, y, width, height):
                points.append((float(x), float(y)))

    if len(points) < 12:
        return (width - 1) / 2.0, (height - 1) / 2.0

    n = float(len(points))
    sum_x = sum(x for x, _ in points)
    sum_y = sum(y for _, y in points)
    sum_x2 = sum(x * x for x, _ in points)
    sum_y2 = sum(y * y for _, y in points)
    sum_xy = sum(x * y for x, y in points)
    sum_x3 = sum(x * x * x for x, _ in points)
    sum_y3 = sum(y * y * y for _, y in points)
    sum_x1y2 = sum(x * y * y for x, y in points)
    sum_x2y1 = sum(x * x * y for x, y in points)

    matrix = [
        [sum_x2, sum_xy, sum_x],
        [sum_xy, sum_y2, sum_y],
        [sum_x, sum_y, n],
    ]
    rhs = [
        -(sum_x3 + sum_x1y2),
        -(sum_x2y1 + sum_y3),
        -(sum_x2 + sum_y2),
    ]

    try:
        a, b, _ = solve_3x3(matrix, rhs)
        center_x = -a / 2.0
        center_y = -b / 2.0
    except ValueError:
        center_x = (width - 1) / 2.0
        center_y = (height - 1) / 2.0

    if not (0 <= center_x < width and 0 <= center_y < height):
        return (width - 1) / 2.0, (height - 1) / 2.0
    return center_x, center_y


def mirror_foreground(
    image: Image.Image,
    non_bg_mask: list[list[bool]],
    center_x: float,
) -> Image.Image:
    width, height = image.size
    output = image.copy()

    for y in range(height):
        for x in range(width):
            if not non_bg_mask[y][x]:
                continue

            relative_x = x - center_x
            mirrored_x = int(round(center_x - relative_x))
            if not (0 <= mirrored_x < width):
                continue

            output.putpixel((mirrored_x, y), image.getpixel((x, y)))

    return output


def main() -> int:
    args = parse_args()

    image = Image.open(args.input_image).convert("RGB")
    width, height = image.size

    bg_color = sample_background_color(image)
    non_bg_mask = build_non_background_mask(image, bg_color, args.bg_threshold)

    auto_center_x, auto_center_y = estimate_circle_center(
        non_bg_mask,
        width,
        height,
        args.center_search_scale,
    )
    center_x = args.center_x if args.center_x is not None else auto_center_x
    center_y = args.center_y if args.center_y is not None else auto_center_y

    output = mirror_foreground(image, non_bg_mask, center_x)

    args.output_image.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.output_image)

    print(f"Input: {args.input_image}")
    print(f"Output: {args.output_image}")
    print(f"Background color: {bg_color}")
    print(f"Detected mirror center: ({center_x:.2f}, {center_y:.2f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
