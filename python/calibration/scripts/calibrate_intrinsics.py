import argparse
from pathlib import Path

import cv2
import numpy as np

from common import (
    BoardSpec,
    create_chessboard_object_points,
    detect_charuco,
    detect_chessboard,
    load_images,
    save_json,
)


def calibrate_charuco(image_paths: list[Path], spec: BoardSpec):
    all_corners = []
    all_ids = []
    image_size = None
    board = None

    for path in image_paths:
        image = cv2.imread(str(path))
        if image is None:
            continue
        board, charuco_corners, charuco_ids, _, _ = detect_charuco(image, spec)
        if charuco_ids is None or len(charuco_ids) < 6:
            print(f"Skipping {path}: not enough ChArUco corners")
            continue
        all_corners.append(charuco_corners)
        all_ids.append(charuco_ids)
        image_size = (image.shape[1], image.shape[0])
        print(f"Accepted {path}: {len(charuco_ids)} corners")

    if not all_corners or image_size is None or board is None:
        raise RuntimeError("No valid ChArUco detections found")

    retval, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.aruco.calibrateCameraCharuco(
        charucoCorners=all_corners,
        charucoIds=all_ids,
        board=board,
        imageSize=image_size,
        cameraMatrix=None,
        distCoeffs=None,
    )
    return retval, camera_matrix, dist_coeffs, rvecs, tvecs, image_size, len(all_corners)


def calibrate_chessboard(image_paths: list[Path], spec: BoardSpec):
    object_points = []
    image_points = []
    image_size = None
    template_points = create_chessboard_object_points(spec)

    for path in image_paths:
        image = cv2.imread(str(path))
        if image is None:
            continue
        found, corners = detect_chessboard(image, spec)
        if not found:
            print(f"Skipping {path}: chessboard not found")
            continue
        object_points.append(template_points)
        image_points.append(corners)
        image_size = (image.shape[1], image.shape[0])
        print(f"Accepted {path}: {len(corners)} corners")

    if not image_points or image_size is None:
        raise RuntimeError("No valid chessboard detections found")

    retval, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        object_points,
        image_points,
        image_size,
        None,
        None,
    )
    return retval, camera_matrix, dist_coeffs, rvecs, tvecs, image_size, len(image_points)


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate camera intrinsics from a folder of images.")
    parser.add_argument("--type", choices=["charuco", "chessboard"], default="charuco")
    parser.add_argument("--images", required=True)
    parser.add_argument("--cols", type=int, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--square-mm", type=float, required=True)
    parser.add_argument("--marker-mm", type=float, default=15.0)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    spec = BoardSpec(args.type, args.cols, args.rows, args.square_mm, args.marker_mm)
    image_paths = load_images(args.images)

    if args.type == "charuco":
        rms, camera_matrix, dist_coeffs, rvecs, tvecs, image_size, used_views = calibrate_charuco(image_paths, spec)
    else:
        rms, camera_matrix, dist_coeffs, rvecs, tvecs, image_size, used_views = calibrate_chessboard(image_paths, spec)

    result = {
        "pattern_type": args.type,
        "board": {
            "cols": args.cols,
            "rows": args.rows,
            "square_mm": args.square_mm,
            "marker_mm": args.marker_mm,
        },
        "image_size": {
            "width": image_size[0],
            "height": image_size[1],
        },
        "used_views": used_views,
        "rms_reprojection_error": float(rms),
        "camera_matrix": camera_matrix.tolist(),
        "dist_coeffs": dist_coeffs.reshape(-1).tolist(),
        "rvecs": [r.reshape(-1).tolist() for r in rvecs],
        "tvecs": [t.reshape(-1).tolist() for t in tvecs],
    }
    save_json(args.output, result)
    print(f"Wrote {args.output}")
    print(f"RMS reprojection error: {rms:.6f}")


if __name__ == "__main__":
    main()
