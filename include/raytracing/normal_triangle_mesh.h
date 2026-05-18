#ifndef NORMAL_TRIANGLE_MESH_H
#define NORMAL_TRIANGLE_MESH_H

#include "bvh.h"
#include "hittable_list.h"
#include "triangle.h"

#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>

struct normal_triangle_source {
    point3 v0;
    vec3 n0;
    point3 v1;
    vec3 n1;
    point3 v2;
    vec3 n2;
};

inline void normalize_normal_triangle_mesh(
    std::vector<normal_triangle_source>& triangles,
    const point3& target_center,
    double target_height,
    bool upside_down
) {
    if (triangles.empty())
        return;

    auto minp = triangles[0].v0;
    auto maxp = triangles[0].v0;

    auto include = [&](const point3& p) {
        minp[0] = std::fmin(minp[0], p.x());
        minp[1] = std::fmin(minp[1], p.y());
        minp[2] = std::fmin(minp[2], p.z());
        maxp[0] = std::fmax(maxp[0], p.x());
        maxp[1] = std::fmax(maxp[1], p.y());
        maxp[2] = std::fmax(maxp[2], p.z());
    };

    for (const auto& tri : triangles) {
        include(tri.v0);
        include(tri.v1);
        include(tri.v2);
    }

    auto mesh_center = 0.5 * (minp + maxp);
    auto height = maxp.y() - minp.y();
    if (height <= 0)
        height = (maxp - minp).length();

    auto scale = target_height / height;
    for (auto& tri : triangles) {
        auto transform_vertex = [&](point3 p) {
            auto local = p - mesh_center;
            if (upside_down)
                local[1] = -local[1];
            return target_center + scale * local;
        };
        auto transform_normal = [&](vec3 n) {
            if (upside_down)
                n[1] = -n[1];
            return n;
        };

        tri.v0 = transform_vertex(tri.v0);
        tri.v1 = transform_vertex(tri.v1);
        tri.v2 = transform_vertex(tri.v2);
        tri.n0 = transform_normal(tri.n0);
        tri.n1 = transform_normal(tri.n1);
        tri.n2 = transform_normal(tri.n2);
    }
}

inline shared_ptr<hittable> load_normal_triangle_mesh(
    const std::string& filename,
    shared_ptr<material> mat,
    const point3& target_center,
    double target_height,
    bool upside_down = false
) {
    std::ifstream in(filename);
    if (!in)
        throw std::runtime_error("Could not open triangle normal mesh: " + filename);

    int triangle_count = 0;
    in >> triangle_count;
    if (!in || triangle_count <= 0)
        throw std::runtime_error("Invalid triangle normal mesh header: " + filename);

    std::vector<normal_triangle_source> source_triangles;
    source_triangles.reserve(triangle_count);

    for (int i = 0; i < triangle_count; ++i) {
        normal_triangle_source tri;
        in >> tri.v0[0] >> tri.v0[1] >> tri.v0[2];
        in >> tri.n0[0] >> tri.n0[1] >> tri.n0[2];
        in >> tri.v1[0] >> tri.v1[1] >> tri.v1[2];
        in >> tri.n1[0] >> tri.n1[1] >> tri.n1[2];
        in >> tri.v2[0] >> tri.v2[1] >> tri.v2[2];
        in >> tri.n2[0] >> tri.n2[1] >> tri.n2[2];

        if (!in)
            throw std::runtime_error("Unexpected end of triangle normal mesh: " + filename);

        source_triangles.push_back(tri);
    }

    normalize_normal_triangle_mesh(source_triangles, target_center, target_height, upside_down);

    std::vector<shared_ptr<hittable>> triangles;
    triangles.reserve(source_triangles.size());

    for (const auto& tri : source_triangles) {
        auto n0 = tri.n0.near_zero() ? vec3(0, 1, 0) : unit_vector(tri.n0);
        auto n1 = tri.n1.near_zero() ? vec3(0, 1, 0) : unit_vector(tri.n1);
        auto n2 = tri.n2.near_zero() ? vec3(0, 1, 0) : unit_vector(tri.n2);

        triangles.push_back(make_shared<triangle>(
            tri.v0,
            tri.v1,
            tri.v2,
            n0,
            n1,
            n2,
            mat
        ));
    }

    return make_shared<bvh_node>(triangles);
}

#endif
