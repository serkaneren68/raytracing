#!/usr/bin/env python3
"""Generate a synthetic point cloud of a drinking glass (truncated cone)."""

import argparse
import math
import struct
from pathlib import Path

import numpy as np


def sample_frustum_lateral(r_bottom, r_top, height, n, jitter=0.0, rng=None):
    """Sample n points on the lateral surface of a frustum.
    Area element scales linearly with r(t), so we sample t with that pdf."""
    rng = rng or np.random.default_rng()
    # CDF for r(t) = r_b + (r_t - r_b) * u, u in [0,1]
    # f(u) ∝ r(u); inverse-CDF via numerical roots of a quadratic
    a = (r_top - r_bottom)
    b = r_bottom
    # F(u) = (a*u^2/2 + b*u) / (a/2 + b); solve for u given uniform v
    v = rng.random(n)
    K = a / 2 + b
    # a/2 * u^2 + b*u - v*K = 0
    if abs(a) < 1e-9:
        u = v.copy()
    else:
        disc = b * b + 2 * a * v * K
        u = (-b + np.sqrt(disc)) / a
    theta = rng.uniform(0, 2 * np.pi, n)
    r = r_bottom + (r_top - r_bottom) * u
    z = height * u
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    if jitter > 0:
        # jitter along outward normal
        slope = (r_top - r_bottom) / height
        nz = -slope / math.sqrt(1 + slope * slope)
        nr = 1 / math.sqrt(1 + slope * slope)
        j = rng.normal(0, jitter, n)
        x += j * nr * np.cos(theta)
        y += j * nr * np.sin(theta)
        z += j * nz
    return np.column_stack([x, y, z])


def sample_disk(radius_outer, radius_inner, z, n, rng=None):
    """Sample n points on an annulus (or disk if inner=0) at fixed z."""
    rng = rng or np.random.default_rng()
    # area-weighted: r = sqrt(uniform(r_i^2, r_o^2))
    r2 = rng.uniform(radius_inner ** 2, radius_outer ** 2, n)
    r = np.sqrt(r2)
    theta = rng.uniform(0, 2 * np.pi, n)
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return np.column_stack([x, y, np.full(n, z)])


def generate_glass(r_bottom=6.5, r_top=7.5, height=9.0, wall=0.2,
                   n_outer=12000, n_inner=8000, n_bottom=2500, n_rim=1500,
                   noise=0.005, seed=42):
    """Build a glass point cloud. All units in cm."""
    rng = np.random.default_rng(seed)

    # Outer lateral surface
    outer = sample_frustum_lateral(r_bottom, r_top, height, n_outer,
                                   jitter=noise, rng=rng)

    # Inner lateral surface (wall thickness offset inward)
    # inner radii are reduced by wall (approx, ignoring slant projection)
    inner_top = max(r_top - wall, 0.01)
    inner_bottom = max(r_bottom - wall, 0.01)
    # inner starts above the bottom by `wall` (glass has a base)
    inner_h = height - wall
    inner = sample_frustum_lateral(inner_bottom, inner_top, inner_h, n_inner,
                                   jitter=noise, rng=rng)
    inner[:, 2] += wall  # lift to sit above base
    # flip normals not stored, just geometry — but we need a slight offset to
    # avoid being co-located with outer surface; sampling at slightly smaller
    # radius is enough.

    # Bottom outer disk (z=0)
    bottom = sample_disk(r_bottom, 0.0, 0.0, n_bottom, rng=rng)
    bottom[:, 2] += rng.normal(0, noise, n_bottom)

    # Inner bottom (sits at z=wall)
    inner_bottom_disk = sample_disk(inner_bottom, 0.0, wall,
                                    n_bottom // 2, rng=rng)
    inner_bottom_disk[:, 2] += rng.normal(0, noise, inner_bottom_disk.shape[0])

    # Top rim annulus
    rim = sample_disk(r_top, inner_top, height, n_rim, rng=rng)
    rim[:, 2] += rng.normal(0, noise, n_rim)

    pts = np.vstack([outer, inner, bottom, inner_bottom_disk, rim])

    # Color by region (for debugging/visualization)
    colors = np.zeros((pts.shape[0], 3), dtype=np.uint8)
    i = 0
    colors[i:i + n_outer] = (180, 200, 230); i += n_outer        # outer: blue-ish
    colors[i:i + n_inner] = (140, 170, 200); i += n_inner        # inner: darker
    colors[i:i + n_bottom] = (120, 120, 120); i += n_bottom      # bottom
    colors[i:i + inner_bottom_disk.shape[0]] = (100, 100, 100)
    i += inner_bottom_disk.shape[0]
    colors[i:i + n_rim] = (220, 220, 220)                        # rim
    return pts, colors


def write_ply(path, points, colors=None, binary=True):
    n = len(points)
    has_color = colors is not None
    header = ["ply"]
    header.append("format binary_little_endian 1.0" if binary else "format ascii 1.0")
    header.append(f"element vertex {n}")
    header += ["property float x", "property float y", "property float z"]
    if has_color:
        header += ["property uchar red", "property uchar green", "property uchar blue"]
    header.append("end_header\n")
    header_str = "\n".join(header)
    with open(path, "wb") as f:
        f.write(header_str.encode("ascii"))
        if binary:
            if has_color:
                buf = bytearray()
                for p, c in zip(points, colors):
                    buf += struct.pack("<fff", *p)
                    buf += struct.pack("<BBB", *c)
                f.write(buf)
            else:
                f.write(points.astype(np.float32).tobytes())
        else:
            for i, p in enumerate(points):
                line = f"{p[0]:.5f} {p[1]:.5f} {p[2]:.5f}"
                if has_color:
                    c = colors[i]
                    line += f" {c[0]} {c[1]} {c[2]}"
                f.write((line + "\n").encode("ascii"))


def write_xyz(path, points):
    np.savetxt(path, points, fmt="%.5f")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--r-bottom", type=float, default=6.5, help="base radius (cm)")
    ap.add_argument("--r-top", type=float, default=7.5, help="top radius (cm)")
    ap.add_argument("--height", type=float, default=9.0, help="height (cm)")
    ap.add_argument("--wall", type=float, default=0.2, help="wall thickness (cm)")
    ap.add_argument("--n-outer", type=int, default=12000)
    ap.add_argument("--n-inner", type=int, default=8000)
    ap.add_argument("--n-bottom", type=int, default=2500)
    ap.add_argument("--n-rim", type=int, default=1500)
    ap.add_argument("--noise", type=float, default=0.005,
                    help="gaussian noise stddev (cm)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path,
                    default=Path("assets/pointclouds/glass.ply"))
    ap.add_argument("--ascii", action="store_true", help="write ASCII PLY")
    ap.add_argument("--also-xyz", action="store_true",
                    help="also dump plain XYZ next to the PLY")
    args = ap.parse_args()

    pts, cols = generate_glass(
        r_bottom=args.r_bottom, r_top=args.r_top, height=args.height,
        wall=args.wall, n_outer=args.n_outer, n_inner=args.n_inner,
        n_bottom=args.n_bottom, n_rim=args.n_rim,
        noise=args.noise, seed=args.seed,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_ply(args.out, pts, cols, binary=not args.ascii)
    print(f"wrote {len(pts)} points -> {args.out}")
    print(f"  bbox  x:[{pts[:,0].min():.2f}, {pts[:,0].max():.2f}] "
          f"y:[{pts[:,1].min():.2f}, {pts[:,1].max():.2f}] "
          f"z:[{pts[:,2].min():.2f}, {pts[:,2].max():.2f}]  (cm)")

    if args.also_xyz:
        xyz = args.out.with_suffix(".xyz")
        write_xyz(xyz, pts)
        print(f"wrote XYZ -> {xyz}")


if __name__ == "__main__":
    main()
