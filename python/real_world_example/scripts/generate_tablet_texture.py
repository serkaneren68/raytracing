import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from forward_reflection_map import intersect_frustum_side, intersect_tablet_plane, reflect
from scene_utils import TabletSpec, FrustumSpec, camera_ray_to_tablet, load_scene


def make_canvas_dimensions(tablet: TabletSpec, pixels_per_mm: float) -> tuple[int, int]:
    width_px = int(round(tablet.width_mm * pixels_per_mm))
    height_px = int(round(tablet.height_mm * pixels_per_mm))
    return width_px, height_px


def tablet_to_canvas(point: np.ndarray, tablet: TabletSpec, pixels_per_mm: float) -> tuple[int, int]:
    width_px, height_px = make_canvas_dimensions(tablet, pixels_per_mm)
    x_px = int(round((tablet.width_mm + point[0]) * pixels_per_mm))
    y_px = int(round(point[1] * pixels_per_mm))
    x_px = max(0, min(width_px - 1, x_px))
    y_px = max(0, min(height_px - 1, y_px))
    return x_px, y_px


def create_target_frame(target_image: np.ndarray, camera_width: int, camera_height: int) -> np.ndarray:
    if target_image.shape[1] == camera_width and target_image.shape[0] == camera_height:
        return target_image
    return cv2.resize(target_image, (camera_width, camera_height), interpolation=cv2.INTER_AREA)


def splat_color(
    accum: np.ndarray,
    counts: np.ndarray,
    x: int,
    y: int,
    color: np.ndarray,
    radius: int,
) -> None:
    height, width = counts.shape
    r2 = radius * radius
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > r2:
                continue
            xx = x + dx
            yy = y + dy
            if xx < 0 or xx >= width or yy < 0 or yy >= height:
                continue
            accum[yy, xx] += color
            counts[yy, xx] += 1


def fill_holes(image: np.ndarray, counts: np.ndarray) -> np.ndarray:
    mask = (counts == 0).astype(np.uint8) * 255
    if np.all(mask == 0):
        return image
    image_u8 = np.clip(image, 0, 255).astype(np.uint8)
    return cv2.inpaint(image_u8, mask, 3, cv2.INPAINT_TELEA)


def generate_texture(
    scene_path: str,
    target_image_path: str,
    output_image_path: str,
    output_summary_path: str,
    output_camera_preview_path: str,
    sample_step: int,
    pixels_per_mm: float,
    splat_radius: int,
) -> None:
    _, tablet, frustum, calibration = load_scene(scene_path)

    target_image = cv2.imread(target_image_path, cv2.IMREAD_COLOR)
    if target_image is None:
        raise FileNotFoundError(f"Could not read target image: {target_image_path}")
    target_frame = create_target_frame(target_image, calibration.image_width, calibration.image_height)

    width_px, height_px = make_canvas_dimensions(tablet, pixels_per_mm)
    accum = np.zeros((height_px, width_px, 3), dtype=np.float64)
    counts = np.zeros((height_px, width_px), dtype=np.int32)
    camera_preview = np.zeros((calibration.image_height, calibration.image_width, 3), dtype=np.uint8)

    total_samples = 0
    frustum_hits = 0
    tablet_hits = 0

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
                continue

            tablet_hits += 1
            color = target_frame[py, px].astype(np.float64)
            tx, ty = tablet_to_canvas(tablet_hit, tablet, pixels_per_mm)
            splat_color(accum, counts, tx, ty, color, splat_radius)
            camera_preview[py, px] = target_frame[py, px]

    tablet_image = np.zeros_like(accum)
    valid = counts > 0
    tablet_image[valid] = accum[valid] / counts[valid, None]
    tablet_image = fill_holes(tablet_image, counts)

    output_image = np.clip(tablet_image, 0, 255).astype(np.uint8)
    Path(output_image_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_summary_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_camera_preview_path).parent.mkdir(parents=True, exist_ok=True)

    cv2.imwrite(output_image_path, output_image)
    cv2.imwrite(output_camera_preview_path, camera_preview)

    summary = {
        "scene": scene_path,
        "target_image": target_image_path,
        "camera_image_size": {
            "width": calibration.image_width,
            "height": calibration.image_height,
        },
        "tablet_canvas_size": {
            "width_px": width_px,
            "height_px": height_px,
            "pixels_per_mm": pixels_per_mm,
        },
        "sampling": {
            "sample_step_px": sample_step,
            "splat_radius_px": splat_radius,
        },
        "sample_counts": {
            "total_camera_samples": total_samples,
            "frustum_hits": frustum_hits,
            "tablet_hits": tablet_hits,
            "filled_tablet_pixels": int(np.count_nonzero(counts)),
        },
        "cezve_base_center_in_tablet_mm": frustum.base_center_xy_mm.tolist(),
        "camera_origin_in_tablet_mm": calibration.camera_origin_tablet_mm.tolist(),
    }
    Path(output_summary_path).write_text(json.dumps(summary, indent=2))

    print(f"Wrote {output_image_path}")
    print(f"Wrote {output_camera_preview_path}")
    print(f"Wrote {output_summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the distorted tablet texture for the real-world scene.")
    parser.add_argument(
        "--scene",
        default="python/real_world_example/config/scene.json",
        help="Path to the real-world scene JSON file.",
    )
    parser.add_argument("--target-image", required=True, help="Desired image to be seen by the camera.")
    parser.add_argument(
        "--output-image",
        default="python/real_world_example/output/tablet_texture.png",
        help="Output tablet texture path.",
    )
    parser.add_argument(
        "--output-summary",
        default="python/real_world_example/output/tablet_texture_summary.json",
        help="Output JSON summary path.",
    )
    parser.add_argument(
        "--output-camera-preview",
        default="python/real_world_example/output/tablet_texture_camera_preview.png",
        help="Camera-space colored hit preview path.",
    )
    parser.add_argument("--sample-step", type=int, default=8, help="Camera pixel sampling stride.")
    parser.add_argument("--pixels-per-mm", type=float, default=6.0, help="Tablet output resolution scale.")
    parser.add_argument("--splat-radius", type=int, default=3, help="Tablet-space splat radius in pixels.")
    args = parser.parse_args()

    generate_texture(
        scene_path=args.scene,
        target_image_path=args.target_image,
        output_image_path=args.output_image,
        output_summary_path=args.output_summary,
        output_camera_preview_path=args.output_camera_preview,
        sample_step=args.sample_step,
        pixels_per_mm=args.pixels_per_mm,
        splat_radius=args.splat_radius,
    )


if __name__ == "__main__":
    main()
