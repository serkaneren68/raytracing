import argparse

import cv2
import numpy as np

from common import BoardSpec, ensure_parent, create_charuco_board


def generate_charuco(spec: BoardSpec, pixels_per_mm: float) -> np.ndarray:
    board, _ = create_charuco_board(spec)
    width = int(round(spec.cols * spec.square_mm * pixels_per_mm))
    height = int(round(spec.rows * spec.square_mm * pixels_per_mm))
    return board.generateImage((width, height), marginSize=0)


def generate_chessboard(spec: BoardSpec, pixels_per_mm: float) -> np.ndarray:
    width = int(round(spec.cols * spec.square_mm * pixels_per_mm))
    height = int(round(spec.rows * spec.square_mm * pixels_per_mm))
    square_px = int(round(spec.square_mm * pixels_per_mm))
    image = np.ones((height, width), dtype=np.uint8) * 255
    for row in range(spec.rows):
        for col in range(spec.cols):
            if (row + col) % 2 == 0:
                y0 = row * square_px
                x0 = col * square_px
                image[y0:y0 + square_px, x0:x0 + square_px] = 0
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a tablet calibration board image.")
    parser.add_argument("--type", choices=["charuco", "chessboard"], default="charuco")
    parser.add_argument("--cols", type=int, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--square-mm", type=float, required=True)
    parser.add_argument("--marker-mm", type=float, default=15.0)
    parser.add_argument("--pixels-per-mm", type=float, default=10.0)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    spec = BoardSpec(
        pattern_type=args.type,
        cols=args.cols,
        rows=args.rows,
        square_mm=args.square_mm,
        marker_mm=args.marker_mm,
    )

    if args.type == "charuco":
        image = generate_charuco(spec, args.pixels_per_mm)
    else:
        image = generate_chessboard(spec, args.pixels_per_mm)

    ensure_parent(args.output)
    cv2.imwrite(args.output, image)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
