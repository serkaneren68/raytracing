import argparse

import cv2
import numpy as np

from common import (
    BoardSpec,
    create_chessboard_object_points,
    detect_charuco,
    detect_chessboard,
    draw_pose_axes,
    ensure_parent,
    load_intrinsics,
    read_image,
    save_json,
)


def solve_charuco_pose(image, spec: BoardSpec, camera_matrix, dist_coeffs):
    board, charuco_corners, charuco_ids, marker_corners, marker_ids = detect_charuco(image, spec)
    if charuco_ids is None or len(charuco_ids) < 6:
        raise RuntimeError("Not enough ChArUco corners found in pose image")

    ok, rvec, tvec = cv2.aruco.estimatePoseCharucoBoard(
        charuco_corners,
        charuco_ids,
        board,
        camera_matrix,
        dist_coeffs,
        None,
        None,
    )
    if not ok:
        raise RuntimeError("Failed to estimate ChArUco pose")

    overlay = image.copy()
    if marker_ids is not None and len(marker_ids) > 0:
        cv2.aruco.drawDetectedMarkers(overlay, marker_corners, marker_ids)
    cv2.aruco.drawDetectedCornersCharuco(overlay, charuco_corners, charuco_ids)
    return rvec, tvec, overlay


def solve_chessboard_pose(image, spec: BoardSpec, camera_matrix, dist_coeffs):
    found, corners = detect_chessboard(image, spec)
    if not found:
        raise RuntimeError("Chessboard not found in pose image")

    object_points = create_chessboard_object_points(spec)
    ok, rvec, tvec = cv2.solvePnP(
        object_points,
        corners,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_IPPE,
    )
    if not ok:
        raise RuntimeError("Failed to estimate chessboard pose")

    overlay = image.copy()
    cv2.drawChessboardCorners(overlay, (spec.cols, spec.rows), corners, True)
    return rvec, tvec, overlay


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate camera pose relative to the tablet board.")
    parser.add_argument("--type", choices=["charuco", "chessboard"], default="charuco")
    parser.add_argument("--image", required=True)
    parser.add_argument("--cols", type=int, required=True)
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--square-mm", type=float, required=True)
    parser.add_argument("--marker-mm", type=float, default=15.0)
    parser.add_argument("--intrinsics", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overlay")
    args = parser.parse_args()

    spec = BoardSpec(args.type, args.cols, args.rows, args.square_mm, args.marker_mm)
    _, camera_matrix, dist_coeffs = load_intrinsics(args.intrinsics)
    try:
        image = read_image(args.image)
    except RuntimeError as e:
        raise RuntimeError(f"{e} Failing image: {args.image}") from e
    if image is None:
        raise FileNotFoundError(
            f"Could not decode image: {args.image}. If this is a HEIC file, "
            "install the Python dependencies from requirements.txt first."
        )

    if args.type == "charuco":
        rvec, tvec, overlay = solve_charuco_pose(image, spec, camera_matrix, dist_coeffs)
    else:
        rvec, tvec, overlay = solve_chessboard_pose(image, spec, camera_matrix, dist_coeffs)

    axis_length = spec.square_mm * 2.0
    overlay = draw_pose_axes(overlay, camera_matrix, dist_coeffs, rvec, tvec, axis_length)

    pose = {
        "pattern_type": args.type,
        "image": args.image,
        "rvec": rvec.reshape(-1).tolist(),
        "tvec_mm": tvec.reshape(-1).tolist(),
        "camera_matrix": camera_matrix.tolist(),
        "dist_coeffs": dist_coeffs.reshape(-1).tolist(),
    }
    save_json(args.output, pose)
    print(f"Wrote {args.output}")

    if args.overlay:
        ensure_parent(args.overlay)
        cv2.imwrite(args.overlay, overlay)
        print(f"Wrote {args.overlay}")


if __name__ == "__main__":
    main()
