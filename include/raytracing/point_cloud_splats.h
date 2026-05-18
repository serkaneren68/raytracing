#ifndef POINT_CLOUD_SPLATS_H
#define POINT_CLOUD_SPLATS_H

#include "bvh.h"
#include "hittable_list.h"
#include "sphere.h"

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

inline std::vector<point3> load_ascii_ply_vertices(const std::string& filename) {
    std::ifstream in(filename);
    if (!in)
        throw std::runtime_error("Could not open PLY point cloud: " + filename);

    std::string line;
    std::size_t vertex_count = 0;
    bool header_done = false;

    while (std::getline(in, line)) {
        if (line.rfind("element vertex ", 0) == 0) {
            std::istringstream iss(line.substr(15));
            iss >> vertex_count;
        } else if (line == "end_header") {
            header_done = true;
            break;
        }
    }

    if (!header_done || vertex_count == 0)
        throw std::runtime_error("Unsupported or empty PLY header: " + filename);

    std::vector<point3> points;
    points.reserve(vertex_count);

    for (std::size_t i = 0; i < vertex_count; ++i) {
        if (!std::getline(in, line))
            throw std::runtime_error("Unexpected end of PLY vertex data: " + filename);

        std::istringstream iss(line);
        double x, y, z;
        if (!(iss >> x >> y >> z))
            throw std::runtime_error("Invalid PLY vertex row: " + filename);

        points.emplace_back(x, y, z);
    }

    return points;
}

inline void normalize_point_cloud(
    std::vector<point3>& points,
    const point3& target_center,
    double target_height
) {
    if (points.empty())
        return;

    auto minp = points[0];
    auto maxp = points[0];
    for (const auto& p : points) {
        minp[0] = std::fmin(minp[0], p.x());
        minp[1] = std::fmin(minp[1], p.y());
        minp[2] = std::fmin(minp[2], p.z());
        maxp[0] = std::fmax(maxp[0], p.x());
        maxp[1] = std::fmax(maxp[1], p.y());
        maxp[2] = std::fmax(maxp[2], p.z());
    }

    auto source_center = 0.5 * (minp + maxp);
    auto height = maxp.y() - minp.y();
    if (height <= 0)
        height = (maxp - minp).length();
    if (height <= 0)
        height = 1.0;

    auto scale = target_height / height;
    for (auto& p : points)
        p = target_center + scale * (p - source_center);
}

inline shared_ptr<hittable> load_point_cloud_splats(
    const std::string& filename,
    shared_ptr<material> mat,
    const point3& target_center,
    double target_height,
    double point_radius
) {
    auto points = load_ascii_ply_vertices(filename);
    normalize_point_cloud(points, target_center, target_height);

    std::vector<shared_ptr<hittable>> splats;
    splats.reserve(points.size());

    for (const auto& p : points)
        splats.push_back(make_shared<sphere>(p, point_radius, mat));

    return make_shared<bvh_node>(splats);
}

#endif
