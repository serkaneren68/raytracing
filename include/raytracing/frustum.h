#ifndef FRUSTUM_H
#define FRUSTUM_H

#include "aabb.h"
#include "hittable.h"

class frustum : public hittable {
    public:
        frustum(
            const point3& base_center,
            double bottom_radius,
            double top_radius,
            double height,
            const vec3& direction,
            shared_ptr<material> mat
        ) : base_center(base_center),
            bottom_radius(std::fmax(0, bottom_radius)),
            top_radius(std::fmax(0, top_radius)),
            height(std::fmax(0, height)),
            axis(direction.near_zero() ? vec3(0, 1, 0) : unit_vector(direction)),
            mat(mat) {
            build_basis();
        }

        bool hit(const ray& r, interval ray_t, hit_record& rec) const override {
            if (height <= 0 || (bottom_radius <= 0 && top_radius <= 0))
                return false;

            auto local_origin = to_local(r.origin());
            auto local_direction = to_local_direction(r.direction());

            double closest_so_far = ray_t.max;
            bool hit_anything = false;
            vec3 outward_normal_world;

            auto try_update = [&](double root, const vec3& outward_normal_local) {
                if (!ray_t.surrounds(root) || root >= closest_so_far)
                    return;
                closest_so_far = root;
                rec.t = root;
                rec.p = r.at(rec.t);
                outward_normal_world = from_local_direction(outward_normal_local);
                hit_anything = true;
            };

            const auto slope = (top_radius - bottom_radius) / height;
            const auto ox = local_origin.x();
            const auto oy = local_origin.y();
            const auto oz = local_origin.z();
            const auto dx = local_direction.x();
            const auto dy = local_direction.y();
            const auto dz = local_direction.z();

            const auto a = dx * dx + dy * dy - (slope * dz) * (slope * dz);
            const auto b = 2.0 * (ox * dx + oy * dy - (bottom_radius + slope * oz) * slope * dz);
            const auto c = ox * ox + oy * oy - (bottom_radius + slope * oz) * (bottom_radius + slope * oz);

            if (std::fabs(a) > 1e-12) {
                const auto discriminant = b * b - 4.0 * a * c;
                if (discriminant >= 0.0) {
                    const auto sqrtd = std::sqrt(discriminant);
                    const auto roots = {
                        (-b - sqrtd) / (2.0 * a),
                        (-b + sqrtd) / (2.0 * a)
                    };

                    for (auto root : roots) {
                        if (!ray_t.surrounds(root) || root >= closest_so_far)
                            continue;
                        const auto hit_local = local_origin + root * local_direction;
                        if (hit_local.z() < 0.0 || hit_local.z() > height)
                            continue;
                        const auto radius_here = bottom_radius + slope * hit_local.z();
                        vec3 normal_local(hit_local.x(), hit_local.y(), -slope * radius_here);
                        if (normal_local.near_zero())
                            continue;
                        try_update(root, unit_vector(normal_local));
                    }
                }
            }

            const auto try_cap = [&](double z_plane, double radius, const vec3& normal_local) {
                if (radius <= 0.0 || std::fabs(dz) < 1e-12)
                    return;
                const auto root = (z_plane - oz) / dz;
                if (!ray_t.surrounds(root) || root >= closest_so_far)
                    return;
                const auto hit_local = local_origin + root * local_direction;
                if (hit_local.x() * hit_local.x() + hit_local.y() * hit_local.y() > radius * radius)
                    return;
                try_update(root, normal_local);
            };

            try_cap(0.0, bottom_radius, vec3(0, 0, -1));
            try_cap(height, top_radius, vec3(0, 0, 1));

            if (!hit_anything)
                return false;

            rec.set_face_normal(r, outward_normal_world);
            rec.mat = mat;
            return true;
        }

        bool bounding_box(aabb& output_box) const override {
            const auto radius = std::fmax(bottom_radius, top_radius);
            const auto top_center = base_center + height * axis;
            const point3 min_point(
                std::fmin(base_center.x(), top_center.x()) - radius,
                std::fmin(base_center.y(), top_center.y()) - radius,
                std::fmin(base_center.z(), top_center.z()) - radius
            );
            const point3 max_point(
                std::fmax(base_center.x(), top_center.x()) + radius,
                std::fmax(base_center.y(), top_center.y()) + radius,
                std::fmax(base_center.z(), top_center.z()) + radius
            );
            output_box = aabb(min_point, max_point);
            return true;
        }

    private:
        point3 base_center;
        double bottom_radius;
        double top_radius;
        double height;
        vec3 axis;
        vec3 basis_u;
        vec3 basis_v;
        shared_ptr<material> mat;

        void build_basis() {
            auto helper = std::fabs(axis.z()) < 0.9 ? vec3(0, 0, 1) : vec3(1, 0, 0);
            basis_u = unit_vector(cross(helper, axis));
            basis_v = cross(axis, basis_u);
        }

        vec3 to_local(const point3& p) const {
            auto d = p - base_center;
            return vec3(dot(d, basis_u), dot(d, basis_v), dot(d, axis));
        }

        vec3 to_local_direction(const vec3& d) const {
            return vec3(dot(d, basis_u), dot(d, basis_v), dot(d, axis));
        }

        vec3 from_local_direction(const vec3& d) const {
            return d.x() * basis_u + d.y() * basis_v + d.z() * axis;
        }
};

#endif
