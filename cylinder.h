#ifndef CYLINDER_H
#define CYLINDER_H

#include "hittable.h"

class cylinder : public hittable {
    public:
        cylinder(
            const point3& center,
            double radius,
            double height,
            const vec3& direction,
            shared_ptr<material> mat
        ) : center(center),
            radius(std::fmax(0, radius)),
            half_height(std::fmax(0, height) / 2),
            axis(direction.near_zero() ? vec3(0, 1, 0) : unit_vector(direction)),
            mat(mat) {}

        bool hit(const ray& r, interval ray_t, hit_record& rec) const override {
            if (radius <= 0 || half_height <= 0)
                return false;

            bool hit_anything = false;
            auto closest_so_far = ray_t.max;
            vec3 outward_normal;

            // Check the curved side of the finite cylinder.
            auto oc = r.origin() - center;
            auto ray_axis = dot(r.direction(), axis);
            auto oc_axis = dot(oc, axis);
            auto ray_perp = r.direction() - ray_axis * axis;
            auto oc_perp = oc - oc_axis * axis;

            auto a = ray_perp.length_squared();
            auto h = dot(ray_perp, oc_perp);
            auto c = oc_perp.length_squared() - radius * radius;
            auto discriminant = h * h - a * c;

            if (a > 1e-12 && discriminant >= 0) {
                auto sqrtd = std::sqrt(discriminant);

                auto root = (-h - sqrtd) / a;
                auto axial_offset = dot(r.at(root) - center, axis);

                if (!ray_t.surrounds(root) || root >= closest_so_far || std::fabs(axial_offset) > half_height) {
                    root = (-h + sqrtd) / a;
                    axial_offset = dot(r.at(root) - center, axis);
                }

                if (ray_t.surrounds(root) && root < closest_so_far && std::fabs(axial_offset) <= half_height) {
                    closest_so_far = root;
                    rec.t = root;
                    rec.p = r.at(rec.t);

                    auto axis_point = center + axial_offset * axis;
                    outward_normal = (rec.p - axis_point) / radius;

                    hit_anything = true;
                }
            }

            // Check the two flat caps.
            auto top_center = center + half_height * axis;
            auto bottom_center = center - half_height * axis;

            auto top_denom = dot(r.direction(), axis);
            if (std::fabs(top_denom) > 1e-12) {
                auto root = dot(top_center - r.origin(), axis) / top_denom;
                auto p = r.at(root);

                if (ray_t.surrounds(root) && root < closest_so_far && (p - top_center).length_squared() <= radius * radius) {
                    closest_so_far = root;
                    rec.t = root;
                    rec.p = p;
                    outward_normal = axis;
                    hit_anything = true;
                }
            }

            auto bottom_normal = -axis;
            auto bottom_denom = dot(r.direction(), bottom_normal);
            if (std::fabs(bottom_denom) > 1e-12) {
                auto root = dot(bottom_center - r.origin(), bottom_normal) / bottom_denom;
                auto p = r.at(root);

                if (ray_t.surrounds(root) && root < closest_so_far && (p - bottom_center).length_squared() <= radius * radius) {
                    rec.t = root;
                    rec.p = p;
                    outward_normal = bottom_normal;
                    hit_anything = true;
                }
            }

            if (!hit_anything)
                return false;

            rec.set_face_normal(r, outward_normal);
            rec.mat = mat;
            return true;
        }

    private:
        point3 center;
        double radius;
        double half_height;
        vec3 axis;
        shared_ptr<material> mat;
};

#endif
