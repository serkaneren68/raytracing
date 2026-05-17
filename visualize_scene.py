#!/usr/bin/env python3
"""
Interactive 3D visualization of the raytracer's scene.cfg.

Shows the table, cylinder, ball, camera position, lookat point, view
direction, and the viewport rectangle / view frustum. Use the mouse to
rotate, pan, and zoom.

Usage:
    python3 visualize_scene.py                # uses scene.cfg
    python3 visualize_scene.py custom.cfg     # uses a custom config

Coordinate convention: scene-space Y is "up". In the plot, Y is mapped to
matplotlib's vertical axis so the world appears upright.
"""

import argparse
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


DEFAULTS = {
    # Camera
    'lookfrom':      [0.0, 0.55, 1.10],
    'lookat':        [0.0, 0.07, 0.0],
    'vup':           [0.0, 1.0, 0.0],
    'vfov':          30.0,
    'aspect_ratio':  16.0 / 9.0,
    'focus_dist':    1.25,
    'defocus_angle': 0.0,
    # Geometry
    'table_y':         0.0,
    'cylinder_center': [0.0, 0.075, 0.0],
    'cylinder_radius': 0.035,
    'cylinder_height': 0.15,
    'cylinder_axis':   [0.0, 1.0, 0.0],
    'ball_enabled':    True,
    'ball_center':     [0.13, 0.05, 0.0],
    'ball_radius':     0.05,
    # Photo plane
    'photo_plane_margin': 0.02,
}

VEC3_KEYS = {
    'lookfrom', 'lookat', 'vup',
    'cylinder_center', 'cylinder_axis', 'ball_center',
    'cylinder_albedo', 'ball_albedo', 'ground_albedo',
}
BOOL_KEYS = {'ball_enabled'}


def parse_value(key, raw):
    if key in BOOL_KEYS:
        return raw.strip().lower() in ('true', 'yes', '1', 'on')
    if key in VEC3_KEYS or ',' in raw:
        parts = [p.strip() for p in raw.split(',')]
        return [float(p) for p in parts]
    return float(raw)


def load_config(path):
    cfg = dict(DEFAULTS)
    if not path.exists():
        print(f"warning: '{path}' not found; using built-in defaults.",
              file=sys.stderr)
        return cfg
    for line_no, raw in enumerate(path.read_text().splitlines(), 1):
        line = raw.split('#', 1)[0].strip()
        if not line or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        if key not in DEFAULTS:
            # silently ignore material-only keys we don't need for viz
            continue
        try:
            cfg[key] = parse_value(key, value)
        except ValueError as e:
            print(f"warning: line {line_no}: '{key}' parse error: {e}",
                  file=sys.stderr)
    return cfg


# ── geometry helpers ──────────────────────────────────────────────────────

def normalize(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def to_plot(p):
    """scene (x, y, z)  ->  matplotlib (x, z, y)   (Y becomes vertical)."""
    p = np.asarray(p, dtype=float)
    return p[..., 0], p[..., 2], p[..., 1]


def cylinder_polys(center, radius, height, axis, n_segments=32):
    center = np.asarray(center, dtype=float)
    axis = normalize(axis)
    ref = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = normalize(np.cross(axis, ref))
    v = np.cross(axis, u)
    half = height / 2.0
    thetas = np.linspace(0.0, 2 * np.pi, n_segments, endpoint=False)
    bot = [center - half * axis + radius * (math.cos(t) * u + math.sin(t) * v) for t in thetas]
    top = [center + half * axis + radius * (math.cos(t) * u + math.sin(t) * v) for t in thetas]

    polys = []
    for i in range(n_segments):
        j = (i + 1) % n_segments
        polys.append([bot[i], bot[j], top[j], top[i]])

    bot_c = center - half * axis
    top_c = center + half * axis
    for i in range(n_segments):
        j = (i + 1) % n_segments
        polys.append([bot[i], bot[j], bot_c])
        polys.append([top[i], top[j], top_c])
    return polys


def sphere_mesh(center, radius, n_lat=18, n_lon=28):
    u = np.linspace(0.0, 2.0 * np.pi, n_lon)
    v = np.linspace(0.0, np.pi, n_lat)
    cx, cy, cz = center
    xs = cx + radius * np.outer(np.cos(u), np.sin(v))
    ys = cy + radius * np.outer(np.ones_like(u), np.cos(v))
    zs = cz + radius * np.outer(np.sin(u), np.sin(v))
    return xs, ys, zs


# ── plotting ──────────────────────────────────────────────────────────────

def draw_polys_swapped(ax, polys, **kwargs):
    swapped = []
    for poly in polys:
        swapped.append([(p[0], p[2], p[1]) for p in poly])
    ax.add_collection3d(Poly3DCollection(swapped, **kwargs))


def main():
    ap = argparse.ArgumentParser(description="Interactive scene.cfg visualizer.")
    ap.add_argument('config', nargs='?', default='scene.cfg',
                    help="path to scene config (default: scene.cfg)")
    args = ap.parse_args()

    cfg = load_config(Path(args.config))

    fig = plt.figure(figsize=(11, 9))
    ax = fig.add_subplot(111, projection='3d')

    # Table surface (gray translucent square around the origin in xz).
    extent = 0.6
    xs = np.array([[-extent, extent], [-extent, extent]])
    zs = np.array([[-extent, -extent], [extent, extent]])
    ys = np.full_like(xs, cfg['table_y'])
    ax.plot_surface(xs, zs, ys, color='lightgray', alpha=0.35,
                    edgecolor='gray', linewidth=0.5)

    # Cylinder
    cyl_polys = cylinder_polys(cfg['cylinder_center'], cfg['cylinder_radius'],
                               cfg['cylinder_height'], cfg['cylinder_axis'])
    draw_polys_swapped(ax, cyl_polys, facecolor='gold',
                       edgecolor='goldenrod', alpha=0.75, linewidth=0.3)

    # Ball
    if cfg['ball_enabled']:
        sx, sy, sz = sphere_mesh(cfg['ball_center'], cfg['ball_radius'])
        ax.plot_surface(sx, sz, sy, color='silver', alpha=0.8,
                        edgecolor='gray', linewidth=0.2)

    # Camera point + lookat point + line between them
    lookfrom = np.asarray(cfg['lookfrom'], float)
    lookat   = np.asarray(cfg['lookat'], float)
    vup      = np.asarray(cfg['vup'], float)

    ax.scatter(*to_plot(lookfrom), color='red',  s=90, label='camera (lookfrom)')
    ax.scatter(*to_plot(lookat),   color='blue', s=90, label='lookat')

    line = np.array([lookfrom, lookat])
    ax.plot(*to_plot(line), color='red', linestyle='--', alpha=0.45)

    # Viewport rectangle and frustum
    forward = normalize(lookat - lookfrom)
    right   = normalize(np.cross(forward, vup))
    up      = np.cross(right, forward)

    focus_dist = cfg['focus_dist']
    vfov_rad   = math.radians(cfg['vfov'])
    vp_h = 2.0 * focus_dist * math.tan(vfov_rad / 2.0)
    vp_w = vp_h * cfg['aspect_ratio']

    vp_center = lookfrom + forward * focus_dist
    tl = vp_center - right * vp_w/2 + up * vp_h/2
    tr = vp_center + right * vp_w/2 + up * vp_h/2
    br = vp_center + right * vp_w/2 - up * vp_h/2
    bl = vp_center - right * vp_w/2 - up * vp_h/2

    draw_polys_swapped(ax, [[tl, tr, br, bl]], facecolor='cyan',
                       alpha=0.20, edgecolor='blue', linewidth=1.2)

    for corner in (tl, tr, br, bl):
        ax.plot(*to_plot(np.array([lookfrom, corner])),
                color='blue', alpha=0.35, linewidth=0.8)

    # vup arrow
    arrow_len = 0.12
    ax.quiver(*to_plot(lookfrom), 0.0, 0.0, arrow_len,
              color='green', label='vup', linewidth=1.5)

    # Axis tunables: equal aspect & framing
    pts = [lookfrom, lookat, tl, tr, br, bl, cfg['cylinder_center']]
    if cfg['ball_enabled']:
        pts.append(cfg['ball_center'])
    pts = np.array(pts, dtype=float)
    mn = pts.min(axis=0) - 0.08
    mx = pts.max(axis=0) + 0.08
    rng = float((mx - mn).max())
    mid = (mn + mx) / 2.0

    # Apply the same swap to the axis limits
    ax.set_xlim(mid[0] - rng/2, mid[0] + rng/2)
    ax.set_ylim(mid[2] - rng/2, mid[2] + rng/2)
    ax.set_zlim(mid[1] - rng/2, mid[1] + rng/2)

    try:
        ax.set_box_aspect((1, 1, 1))
    except AttributeError:
        pass

    ax.set_xlabel('X')
    ax.set_ylabel('Z (depth)')
    ax.set_zlabel('Y (up)')
    ax.set_title(f"Scene: {args.config}\n"
                 f"vfov={cfg['vfov']:.1f}°, focus={cfg['focus_dist']:.2f}m, "
                 f"ball={'on' if cfg['ball_enabled'] else 'off'}")
    ax.legend(loc='upper left', fontsize=9)

    # Initial viewing angle: roughly behind & above the camera, looking forward
    ax.view_init(elev=25, azim=-70)

    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()
