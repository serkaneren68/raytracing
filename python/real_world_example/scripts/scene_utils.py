import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np


@dataclass
class TabletSpec:
    width_mm: float
    height_mm: float


@dataclass
class FrustumSpec:
    height_mm: float
    bottom_radius_mm: float
    top_radius_mm: float
    base_center_xy_mm: np.ndarray


@dataclass
class CalibrationBundle:
    camera_matrix: np.ndarray
    dist_coeffs: np.ndarray
    image_width: int
    image_height: int
    camera_origin_tablet_mm: np.ndarray
    rotation_board_to_camera: np.ndarray
    translation_board_to_camera_mm: np.ndarray
    tablet_top_right_in_board_mm: np.ndarray


def load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def resolve_repo_path(scene_path: str | Path, candidate: str) -> Path:
    scene_dir = Path(scene_path).resolve().parent
    path = Path(candidate)
    if path.is_absolute():
        return path
    repo_root = scene_dir.parents[2]
    return (repo_root / path).resolve()


def load_scene(scene_path: str | Path) -> tuple[dict, TabletSpec, FrustumSpec, CalibrationBundle]:
    scene_path = Path(scene_path)
    scene = load_json(scene_path)

    tablet = TabletSpec(
        width_mm=float(scene["tablet"]["width_mm"]),
        height_mm=float(scene["tablet"]["height_mm"]),
    )

    cezve_center = scene["cezve"]["base_center_in_tablet_mm"]
    if cezve_center["x_mm"] is None or cezve_center["y_mm"] is None:
        raise RuntimeError(
            "Scene is missing cezve.base_center_in_tablet_mm. "
            "Fill x_mm and y_mm in python/real_world_example/config/scene.json."
        )

    frustum = FrustumSpec(
        height_mm=float(scene["cezve"]["height_mm"]),
        bottom_radius_mm=float(scene["cezve"]["bottom_diameter_mm"]) * 0.5,
        top_radius_mm=float(scene["cezve"]["top_diameter_mm"]) * 0.5,
        base_center_xy_mm=np.array(
            [float(cezve_center["x_mm"]), float(cezve_center["y_mm"])],
            dtype=np.float64,
        ),
    )

    intrinsics_path = resolve_repo_path(scene_path, scene["calibration_inputs"]["intrinsics_file"])
    pose_path = resolve_repo_path(scene_path, scene["calibration_inputs"]["reference_pose_file"])
    tablet_ref_path = resolve_repo_path(scene_path, scene["calibration_inputs"]["tablet_reference_file"])

    intrinsics = load_json(intrinsics_path)
    pose = load_json(pose_path)
    tablet_ref = load_json(tablet_ref_path)

    camera_matrix = np.array(pose["camera_matrix"], dtype=np.float64)
    dist_coeffs = np.array(pose["dist_coeffs"], dtype=np.float64).reshape(-1, 1)
    rvec = np.array(pose["rvec"], dtype=np.float64).reshape(3, 1)
    tvec = np.array(pose["tvec_mm"], dtype=np.float64).reshape(3, 1)
    rotation_board_to_camera, _ = cv2.Rodrigues(rvec)

    tablet_top_right_in_board_mm = np.array(
        [
            tablet_ref["board_to_tablet_reference"]["tablet_top_right_in_board_frame"]["x_mm"],
            tablet_ref["board_to_tablet_reference"]["tablet_top_right_in_board_frame"]["y_mm"],
            0.0,
        ],
        dtype=np.float64,
    )

    camera_origin_board = (-rotation_board_to_camera.T @ tvec).reshape(3)
    camera_origin_tablet = board_point_to_tablet(
        camera_origin_board,
        tablet,
        tablet_top_right_in_board_mm,
    )

    calibration = CalibrationBundle(
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs,
        image_width=int(intrinsics["image_size"]["width"]),
        image_height=int(intrinsics["image_size"]["height"]),
        camera_origin_tablet_mm=camera_origin_tablet,
        rotation_board_to_camera=rotation_board_to_camera,
        translation_board_to_camera_mm=tvec.reshape(3),
        tablet_top_right_in_board_mm=tablet_top_right_in_board_mm,
    )
    return scene, tablet, frustum, calibration


def board_point_to_tablet(point_board: np.ndarray, tablet: TabletSpec, top_right_board: np.ndarray) -> np.ndarray:
    x_board, y_board, z_board = point_board
    x_tablet = x_board - top_right_board[0]
    y_tablet = y_board - top_right_board[1]
    z_tablet = -z_board
    return np.array([x_tablet, y_tablet, z_tablet], dtype=np.float64)


def board_direction_to_tablet(direction_board: np.ndarray) -> np.ndarray:
    return np.array(
        [direction_board[0], direction_board[1], -direction_board[2]],
        dtype=np.float64,
    )


def pixel_to_camera_ray(
    px: float,
    py: float,
    camera_matrix: np.ndarray,
    dist_coeffs: np.ndarray,
) -> np.ndarray:
    points = np.array([[[px, py]]], dtype=np.float64)
    undistorted = cv2.undistortPoints(points, camera_matrix, dist_coeffs)
    x_norm, y_norm = undistorted[0, 0]
    ray = np.array([x_norm, y_norm, 1.0], dtype=np.float64)
    return ray / np.linalg.norm(ray)


def camera_ray_to_tablet(
    px: float,
    py: float,
    calibration: CalibrationBundle,
    tablet: TabletSpec,
) -> tuple[np.ndarray, np.ndarray]:
    ray_camera = pixel_to_camera_ray(px, py, calibration.camera_matrix, calibration.dist_coeffs)
    ray_board = calibration.rotation_board_to_camera.T @ ray_camera
    ray_tablet = board_direction_to_tablet(ray_board)
    ray_tablet = ray_tablet / np.linalg.norm(ray_tablet)
    return calibration.camera_origin_tablet_mm.copy(), ray_tablet
