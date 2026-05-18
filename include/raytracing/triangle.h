#ifndef TRIANGLE_H
#define TRIANGLE_H

#include "aabb.h"
#include "hittable.h"

class triangle : public hittable {
    public:
        triangle(
            const point3& v0,
            const point3& v1,
            const point3& v2,
            const vec3& n0,
            const vec3& n1,
            const vec3& n2,
            shared_ptr<material> mat
        ) : v0(v0), v1(v1), v2(v2), n0(n0), n1(n1), n2(n2), mat(mat) {
            bbox = surrounding_points(v0, v1, v2);
            face_normal = cross(v1 - v0, v2 - v0);
            face_normal = face_normal.near_zero() ? vec3(0, 1, 0) : unit_vector(face_normal);
        }

        bool hit(const ray& r, interval ray_t, hit_record& rec) const override {
            auto edge1 = v1 - v0;
            auto edge2 = v2 - v0;
            auto h = cross(r.direction(), edge2);
            auto a = dot(edge1, h);

            if (std::fabs(a) < 1e-10)
                return false;

            auto f = 1.0 / a;
            auto s = r.origin() - v0;
            auto u = f * dot(s, h);
            if (u < 0.0 || u > 1.0)
                return false;

            auto q = cross(s, edge1);
            auto v = f * dot(r.direction(), q);
            if (v < 0.0 || u + v > 1.0)
                return false;

            auto root = f * dot(edge2, q);
            if (!ray_t.surrounds(root))
                return false;

            auto w = 1.0 - u - v;
            auto interpolated_normal = w * n0 + u * n1 + v * n2;
            if (interpolated_normal.near_zero())
                interpolated_normal = face_normal;
            else
                interpolated_normal = unit_vector(interpolated_normal);

            rec.t = root;
            rec.p = r.at(rec.t);
            rec.u = u;
            rec.v = v;
            rec.mat = mat;
            rec.set_face_normal(r, interpolated_normal);
            return true;
        }

        bool bounding_box(aabb& output_box) const override {
            output_box = bbox;
            return true;
        }

    private:
        point3 v0;
        point3 v1;
        point3 v2;
        vec3 n0;
        vec3 n1;
        vec3 n2;
        vec3 face_normal;
        shared_ptr<material> mat;
        aabb bbox;
};

#endif
