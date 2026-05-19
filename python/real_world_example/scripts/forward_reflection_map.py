import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from scene_utils import TabletSpec, FrustumSpec, camera_ray_to_tablet, load_scene


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def intersect_frustum_side(
    ray_origin: np.ndarray,
    ray_dir: np.ndarray,
    frustum: FrustumSpec,
) -> tuple[np.ndarray, np.ndarray] | None:
    local_origin = ray_origin.copy()
    local_origin[0] -= frustum.base_center_xy_mm[0]
    local_origin[1] -= frustum.base_center_xy_mm[1]
    local_dir = ray_dir.copy()

    r0 = frustum.bottom_radius_mm
    slope = (frustum.top_radius_mm - frustum.bottom_radius_mm) / frustum.height_mm

    ox, oy, oz = local_origin
    dx, dy, dz = local_dir

    a = dx * dx + dy * dy - (slope * dz) * (slope * dz)
    b = 2.0 * (ox * dx + oy * dy - (r0 + slope * oz) * slope * dz)
    c = ox * ox + oy * oy - (r0 + slope * oz) * (r0 + slope * oz)

    roots = []
    if abs(a) < 1e-9:
        if abs(b) < 1e-9:
            return None
        roots = [-c / b]
    else:
        disc = b * b - 4.0 * a * c
        if disc < 0.0:
            return None
        sqrt_disc = np.sqrt(disc)
        roots = [
            (-b - sqrt_disc) / (2.0 * a),
            (-b + sqrt_disc) / (2.0 * a),
        ]

    best_t = None
    best_hit = None
    best_normal = None
    for t in roots:
        if t <= 1e-6:
            continue
        hit = local_origin + t * local_dir
        if hit[2] < 0.0 or hit[2] > frustum.height_mm:
            continue
        radius_here = r0 + slope * hit[2]
        normal_local = np.array(
            [hit[0], hit[1], -slope * radius_here],
            dtype=np.float64,
        )
        normal_norm = np.linalg.norm(normal_local)
        if normal_norm < 1e-9:
            continue
        normal_local /= normal_norm
        if best_t is None or t < best_t:
            best_t = t
            best_hit = hit
            best_normal = normal_local

    if best_hit is None or best_normal is None:
        return None

    hit_world = np.array(
        [
            best_hit[0] + frustum.base_center_xy_mm[0],
            best_hit[1] + frustum.base_center_xy_mm[1],
            best_hit[2],
        ],
        dtype=np.float64,
    )
    return hit_world, best_normal


def reflect(direction: np.ndarray, normal: np.ndarray) -> np.ndarray:
    return direction - 2.0 * np.dot(direction, normal) * normal


def intersect_tablet_plane(ray_origin: np.ndarray, ray_dir: np.ndarray, tablet: TabletSpec) -> np.ndarray | None:
    if abs(ray_dir[2]) < 1e-9:
        return None
    t = -ray_origin[2] / ray_dir[2]
    if t <= 1e-6:
        return None
    hit = ray_origin + t * ray_dir
    if hit[0] < -tablet.width_mm or hit[0] > 0.0:
        return None
    if hit[1] < 0.0 or hit[1] > tablet.height_mm:
        return None
    return hit


def tablet_to_canvas(point: np.ndarray, tablet: TabletSpec, pixels_per_mm: float) -> tuple[int, int]:
    width_px = int(round(tablet.width_mm * pixels_per_mm))
    height_px = int(round(tablet.height_mm * pixels_per_mm))
    x_px = int(round((tablet.width_mm + point[0]) * pixels_per_mm))
    y_px = int(round(point[1] * pixels_per_mm))
    x_px = max(0, min(width_px - 1, x_px))
    y_px = max(0, min(height_px - 1, y_px))
    return x_px, y_px


def make_tablet_canvas(tablet: TabletSpec, frustum: FrustumSpec, pixels_per_mm: float) -> np.ndarray:
    width_px = int(round(tablet.width_mm * pixels_per_mm))
    height_px = int(round(tablet.height_mm * pixels_per_mm))
    canvas = np.full((height_px, width_px, 3), 245, dtype=np.uint8)
    cv2.rectangle(canvas, (0, 0), (width_px - 1, height_px - 1), (120, 120, 120), 2)
    center_px = tablet_to_canvas(
        np.array([frustum.base_center_xy_mm[0], frustum.base_center_xy_mm[1], 0.0]),
        tablet,
        pixels_per_mm,
    )
    base_radius_px = int(round(frustum.bottom_radius_mm * pixels_per_mm))
    cv2.circle(canvas, center_px, base_radius_px, (80, 80, 80), 2)
    return canvas


def build_forward_map(scene_path: str, sample_step: int, pixels_per_mm: float, output_dir: str) -> None:
    _, tablet, frustum, calibration = load_scene(scene_path)

    footprint = make_tablet_canvas(tablet, frustum, pixels_per_mm)
    camera_overlay = np.zeros((calibration.image_height, calibration.image_width, 3), dtype=np.uint8)

    total_samples = 0
    frustum_hits = 0
    screen_hits = 0
    tablet_hits = []

    for py in range(0, calibration.image_height, sample_step):
        for px in range(0, calibration.image_width, sample_step):
            total_samples += 1
            ray_origin, ray_dir = camera_ray_to_tablet(px, py, calibration, tablet)

            side_hit = intersect_frustum_side(ray_origin, ray_dir, frustum)
            if side_hit is None:
                continue
            frustum_hits += 1
            hit_point, normal = side_hit

            reflected = reflect(ray_dir, normal)
            reflected /= np.linalg.norm(reflected)

            tablet_hit = intersect_tablet_plane(hit_point, reflected, tablet)
            if tablet_hit is None:
                cv2.circle(camera_overlay, (px, py), 1, (0, 0, 180), -1)
                continue

            screen_hits += 1
            tablet_hits.append(tablet_hit)
            cv2.circle(camera_overlay, (px, py), 1, (0, 220, 0), -1)
            footprint_px = tablet_to_canvas(tablet_hit, tablet, pixels_per_mm)
            cv2.circle(footprint, footprint_px, 1, (20, 90, 220), -1)

    bounds = None
    if tablet_hits:
        hits = np.array(tablet_hits, dtype=np.float64)
        bounds = {
            "min_x_mm": float(np.min(hits[:, 0])),
            "max_x_mm": float(np.max(hits[:, 0])),
            "min_y_mm": float(np.min(hits[:, 1])),
            "max_y_mm": float(np.max(hits[:, 1])),
        }

    summary = {
        "scene": scene_path,
        "sample_step_px": sample_step,
        "camera_image_size": {
            "width": calibration.image_width,
            "height": calibration.image_height,
        },
        "camera_origin_in_tablet_mm": calibration.camera_origin_tablet_mm.tolist(),
        "cezve_base_center_in_tablet_mm": frustum.base_center_xy_mm.tolist(),
        "cezve_spec": {
            "height_mm": frustum.height_mm,
            "bottom_radius_mm": frustum.bottom_radius_mm,
            "top_radius_mm": frustum.top_radius_mm,
        },
        "sample_counts": {
            "total_camera_samples": total_samples,
            "frustum_hits": frustum_hits,
            "tablet_reflection_hits": screen_hits,
        },
        "tablet_reflection_bounds_mm": bounds,
    }

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "forward_map_summary.json"
    footprint_path = output_dir / "forward_map_footprint.png"
    camera_overlay_path = output_dir / "forward_map_camera_overlay.png"

    summary_path.write_text(json.dumps(summary, indent=2))
    cv2.imwrite(str(footprint_path), footprint)
    cv2.imwrite(str(camera_overlay_path), camera_overlay)

    print(f"Wrote {summary_path}")
    print(f"Wrote {footprint_path}")
    print(f"Wrote {camera_overlay_path}")
    if bounds is not None:
        print("Tablet reflection bounds (mm):", bounds)
    else:
        print("No valid tablet reflection hits found.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a forward reflection map for the real-world setup.")
    parser.add_argument(
        "--scene",
        default="python/real_world_example/config/scene.json",
        help="Path to the real-world scene JSON file.",
    )
    parser.add_argument(
        "--sample-step",
        type=int,
        default=8,
        help="Camera pixel sampling stride in pixels.",
    )
    parser.add_argument(
        "--pixels-per-mm",
        type=float,
        default=4.0,
        help="Tablet footprint rendering scale.",
    )
    parser.add_argument(
        "--output-dir",
        default="python/real_world_example/output",
        help="Output directory for generated forward-map artifacts.",
    )
    args = parser.parse_args()

    build_forward_map(args.scene, args.sample_step, args.pixels_per_mm, args.output_dir)


if __name__ == "__main__":
    main()
