import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class BoardSpec:
    pattern_type: str
    cols: int
    rows: int
    square_mm: float
    marker_mm: float | None = None


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def load_images(pattern: str) -> list[Path]:
    paths = sorted(Path().glob(pattern))
    if not paths:
        raise FileNotFoundError(f"No images matched pattern: {pattern}")
    return paths


def create_charuco_board(spec: BoardSpec):
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    board = cv2.aruco.CharucoBoard(
        (spec.cols, spec.rows),
        spec.square_mm,
        spec.marker_mm,
        dictionary,
    )
    return board, dictionary


def create_chessboard_object_points(spec: BoardSpec) -> np.ndarray:
    grid = np.zeros((spec.rows * spec.cols, 3), np.float32)
    grid[:, :2] = np.mgrid[0:spec.cols, 0:spec.rows].T.reshape(-1, 2)
    grid *= spec.square_mm
    return grid


def detect_charuco(image: np.ndarray, spec: BoardSpec):
    board, dictionary = create_charuco_board(spec)
    detector = cv2.aruco.CharucoDetector(board)
    charuco_corners, charuco_ids, marker_corners, marker_ids = detector.detectBoard(image)
    return board, charuco_corners, charuco_ids, marker_corners, marker_ids


def detect_chessboard(image: np.ndarray, spec: BoardSpec):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    found, corners = cv2.findChessboardCorners(
        gray,
        (spec.cols, spec.rows),
        cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE,
    )
    if not found:
        return False, None
    refined = cv2.cornerSubPix(
        gray,
        corners,
        (11, 11),
        (-1, -1),
        (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001),
    )
    return True, refined


def save_json(path: str | Path, payload: dict) -> None:
    ensure_parent(path)
    Path(path).write_text(json.dumps(payload, indent=2))


def load_intrinsics(path: str | Path):
    data = json.loads(Path(path).read_text())
    camera_matrix = np.array(data["camera_matrix"], dtype=np.float64)
    dist_coeffs = np.array(data["dist_coeffs"], dtype=np.float64)
    return data, camera_matrix, dist_coeffs


def draw_pose_axes(
    image: np.ndarray,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
    rvec: np.ndarray,
    tvec: np.ndarray,
    axis_length: float,
) -> np.ndarray:
    axis = np.float32(
        [
            [0, 0, 0],
            [axis_length, 0, 0],
            [0, axis_length, 0],
            [0, 0, -axis_length],
        ]
    )
    imgpts, _ = cv2.projectPoints(axis, rvec, tvec, camera_matrix, dist_coeffs)
    pts = imgpts.reshape(-1, 2).astype(int)
    origin = tuple(pts[0])
    out = image.copy()
    cv2.line(out, origin, tuple(pts[1]), (0, 0, 255), 3)
    cv2.line(out, origin, tuple(pts[2]), (0, 255, 0), 3)
    cv2.line(out, origin, tuple(pts[3]), (255, 0, 0), 3)
    return out
