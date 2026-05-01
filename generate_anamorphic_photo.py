#!/usr/bin/env python3
import math
from pathlib import Path

import cv2
import numpy as np

# Scene values from main.cc. The generated texture is meant for this setup.
EYE = np.array([0.0, 2.0, 4.2], dtype=np.float64)
CYL_CENTER = np.array([0.02, -0.02, -2.99], dtype=np.float64)
CYL_RADIUS = 0.17
CYL_HEIGHT = 1.6
PLANE_Y = -0.82

# Current quad:
# q=(10,-0.82,-11.0), u=(-20.0,0,0), v=(0,0,18.0)
X_MIN, X_MAX = -10.0, 10.0
Z_MIN, Z_MAX = -11.0, 7.0
OUT_W, OUT_H = 2400, 2160

# Visible/front half of the cylinder. theta=pi/2 faces the camera (+Z side).
THETA_MIN = math.radians(18)
THETA_MAX = math.radians(162)
Y_MIN = CYL_CENTER[1] - CYL_HEIGHT / 2
Y_MAX = CYL_CENTER[1] + CYL_HEIGHT / 2

CHECK_COLS = 8
CHECK_ROWS = 8


def checker_color(u, v):
    col = np.floor(u * CHECK_COLS).astype(np.int32)
    row = np.floor(v * CHECK_ROWS).astype(np.int32)
    checker = (col + row) % 2
    light = np.array([245, 245, 235], dtype=np.uint8)
    dark = np.array([20, 28, 36], dtype=np.uint8)
    return np.where(checker[..., None] == 0, light, dark)


def main():
    canvas = np.full((OUT_H, OUT_W, 3), 255, dtype=np.uint8)
    mask = np.zeros((OUT_H, OUT_W), dtype=np.uint8)

    theta = np.linspace(THETA_MIN, THETA_MAX, 3000)
    y = np.linspace(Y_MIN + 0.02, Y_MAX - 0.02, 2000)
    theta_grid, y_grid = np.meshgrid(theta, y)

    normals = np.stack(
        [np.cos(theta_grid), np.zeros_like(theta_grid), np.sin(theta_grid)],
        axis=-1,
    )
    surface = CYL_CENTER + CYL_RADIUS * normals
    surface[..., 1] = y_grid

    incident = surface - EYE
    incident /= np.linalg.norm(incident, axis=-1, keepdims=True)
    ndot = np.sum(incident * normals, axis=-1, keepdims=True)
    reflected = incident - 2.0 * ndot * normals

    # Intersect reflected rays with the horizontal photo plane.
    denom = reflected[..., 1]
    valid = denom < -1e-6
    t = (PLANE_Y - surface[..., 1]) / denom
    valid &= t > 0

    plane_hit = surface + reflected * t[..., None]
    x = plane_hit[..., 0]
    z = plane_hit[..., 2]
    valid &= (X_MIN <= x) & (x <= X_MAX) & (Z_MIN <= z) & (z <= Z_MAX)

    # Convert world hit point to texture pixel. This matches the current quad orientation:
    # q=(10,-.82,-11.0), u=(-20,0,0), v=(0,0,18.0)
    tex_u = (X_MAX - x) / (X_MAX - X_MIN)
    tex_v = (z - Z_MIN) / (Z_MAX - Z_MIN)
    px = np.rint(tex_u * (OUT_W - 1)).astype(np.int32)
    py = np.rint((1.0 - tex_v) * (OUT_H - 1)).astype(np.int32)

    # Target image coordinates as they should appear on the visible cylinder.
    target_u = (theta_grid - THETA_MIN) / (THETA_MAX - THETA_MIN)
    target_v = (y_grid - Y_MIN) / (Y_MAX - Y_MIN)
    colors = checker_color(target_u, 1.0 - target_v)

    pxv = px[valid]
    pyv = py[valid]
    colv = colors[valid]
    print(f'mapped samples: {len(pxv)}')

    # Forward mapping can leave tiny holes, so splat each sample into a
    # small neighborhood. Do not dilate the white canvas itself, or the
    # white background will erase the dark checker cells.
    for dy in range(-1, 2):
        for dx in range(-1, 2):
            sx = np.clip(pxv + dx, 0, OUT_W - 1)
            sy = np.clip(pyv + dy, 0, OUT_H - 1)
            canvas[sy, sx] = colv
            mask[sy, sx] = 255

    # Slight antialiasing on the generated texture itself.
    blurred = cv2.GaussianBlur(canvas, (3, 3), 0)
    canvas[mask > 0] = blurred[mask > 0]

    out = Path('photo.ppm')
    with out.open('wb') as f:
        f.write(f'P6\n{OUT_W} {OUT_H}\n255\n'.encode('ascii'))
        f.write(canvas.tobytes())

    print(f'wrote {out} ({OUT_W}x{OUT_H})')


if __name__ == '__main__':
    main()
