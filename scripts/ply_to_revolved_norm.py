#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import sys


def load_ascii_ply_points(path: Path) -> list[tuple[float, float, float]]:
    with path.open("r", encoding="utf-8") as f:
        line = f.readline().strip()
        if line != "ply":
            raise ValueError(f"Not a PLY file: {path}")

        vertex_count = 0
        for line in f:
            line = line.strip()
            if line.startswith("element vertex "):
                vertex_count = int(line.split()[-1])
            elif line == "end_header":
                break

        if vertex_count <= 0:
            raise ValueError(f"No vertices found in PLY header: {path}")

        points: list[tuple[float, float, float]] = []
        for _ in range(vertex_count):
            parts = f.readline().split()
            if len(parts) < 3:
                raise ValueError(f"Invalid vertex row in {path}")
            x, y, z = map(float, parts[:3])
            points.append((x, y, z))
        return points


def percentile(sorted_values: list[float], q: float) -> float:
    if not sorted_values:
        raise ValueError("percentile of empty list")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    i0 = int(math.floor(pos))
    i1 = min(len(sorted_values) - 1, i0 + 1)
    t = pos - i0
    return sorted_values[i0] * (1.0 - t) + sorted_values[i1] * t


def moving_average(values: list[float], radius: int) -> list[float]:
    out: list[float] = []
    n = len(values)
    for i in range(n):
        a = max(0, i - radius)
        b = min(n, i + radius + 1)
        out.append(sum(values[a:b]) / (b - a))
    return out


def build_profile(
    points: list[tuple[float, float, float]],
    bins: int,
    outer_quantile: float,
) -> list[tuple[float, float]]:
    heights = [p[2] for p in points]
    min_h = min(heights)
    max_h = max(heights)
    eps = 1e-9

    profile: list[tuple[float, float]] = []
    fallback_radii = sorted(math.hypot(x, y) for x, y, _ in points)
    fallback_radius = percentile(fallback_radii, outer_quantile)

    for i in range(bins):
        h0 = min_h + (max_h - min_h) * i / bins
        h1 = min_h + (max_h - min_h) * (i + 1) / bins
        rs = sorted(
            math.hypot(x, y)
            for x, y, z in points
            if h0 <= z < (h1 + eps if i == bins - 1 else h1)
        )
        height = 0.5 * (h0 + h1)
        radius = percentile(rs, outer_quantile) if rs else fallback_radius
        profile.append((height, radius))

    radii = moving_average([r for _, r in profile], radius=2)
    return [(profile[i][0], radii[i]) for i in range(len(profile))]


def build_vertex_normal(profile: list[tuple[float, float]], i: int, theta: float) -> tuple[float, float, float]:
    if i == 0:
        dh = profile[1][0] - profile[0][0]
        dr = profile[1][1] - profile[0][1]
    elif i == len(profile) - 1:
        dh = profile[-1][0] - profile[-2][0]
        dr = profile[-1][1] - profile[-2][1]
    else:
        dh = profile[i + 1][0] - profile[i - 1][0]
        dr = profile[i + 1][1] - profile[i - 1][1]

    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    tx = dr * cos_t
    ty = dh
    tz = dr * sin_t
    sx = -profile[i][1] * sin_t
    sy = 0.0
    sz = profile[i][1] * cos_t

    nx = ty * sz - tz * sy
    ny = tz * sx - tx * sz
    nz = tx * sy - ty * sx
    length = math.sqrt(nx * nx + ny * ny + nz * nz)
    if length <= 1e-12:
        return (cos_t, 0.0, sin_t)
    return (nx / length, ny / length, nz / length)


def remap_to_world(v: tuple[float, float, float]) -> tuple[float, float, float]:
    x, source_h, z = v
    return (x, source_h, z)


def write_norm(
    output_path: Path,
    profile: list[tuple[float, float]],
    segments: int,
    add_bottom_cap: bool,
) -> None:
    triangles: list[tuple[tuple[float, float, float], tuple[float, float, float],
                          tuple[float, float, float], tuple[float, float, float],
                          tuple[float, float, float], tuple[float, float, float]]] = []

    rings: list[list[tuple[tuple[float, float, float], tuple[float, float, float]]]] = []
    for i, (height, radius) in enumerate(profile):
        ring = []
        for j in range(segments):
            theta = 2.0 * math.pi * j / segments
            px = radius * math.cos(theta)
            pz = radius * math.sin(theta)
            p = remap_to_world((px, height, pz))
            n = remap_to_world(build_vertex_normal(profile, i, theta))
            ring.append((p, n))
        rings.append(ring)

    for i in range(len(rings) - 1):
        for j in range(segments):
            jn = (j + 1) % segments
            p00, n00 = rings[i][j]
            p01, n01 = rings[i][jn]
            p10, n10 = rings[i + 1][j]
            p11, n11 = rings[i + 1][jn]
            triangles.append((p00, n00, p10, n10, p11, n11))
            triangles.append((p00, n00, p11, n11, p01, n01))

    if add_bottom_cap:
        bottom_y = profile[0][0]
        center = remap_to_world((0.0, bottom_y, 0.0))
        center_n = (0.0, -1.0, 0.0)
        for j in range(segments):
            jn = (j + 1) % segments
            p0, _ = rings[0][j]
            p1, _ = rings[0][jn]
            triangles.append((center, center_n, p1, center_n, p0, center_n))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as out:
        out.write(f"{len(triangles)}\n")
        for tri in triangles:
            for vertex, normal in ((tri[0], tri[1]), (tri[2], tri[3]), (tri[4], tri[5])):
                out.write(f"{vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
                out.write(f"{normal[0]:.6f} {normal[1]:.6f} {normal[2]:.6f}\n")
            out.write("\n")


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: python3 scripts/ply_to_revolved_norm.py <input.ply> <output.norm>",
            file=sys.stderr,
        )
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    points = load_ascii_ply_points(input_path)
    profile = build_profile(points, bins=96, outer_quantile=0.94)
    write_norm(output_path, profile, segments=160, add_bottom_cap=True)
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
