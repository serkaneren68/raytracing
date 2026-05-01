#ifndef QUAD_H
#define QUAD_H

#include "hittable.h"

class quad : public hittable {
    public:
        quad(const point3& q, const vec3& u, const vec3& v, shared_ptr<material> mat)
            : q(q), u(u), v(v), mat(mat) {
            auto n = cross(u, v);
            normal = unit_vector(n);
            d = dot(normal, q);
            u_length_squared = u.length_squared();
            v_length_squared = v.length_squared();
        }

        bool hit(const ray& r, interval ray_t, hit_record& rec) const override {
            auto denom = dot(normal, r.direction());
            if (std::fabs(denom) < 1e-8)
                return false;

            auto root = (d - dot(normal, r.origin())) / denom;
            if (!ray_t.surrounds(root))
                return false;

            auto p = r.at(root);
            auto planar_hitpt = p - q;
            auto alpha = dot(planar_hitpt, u) / u_length_squared;
            auto beta = dot(planar_hitpt, v) / v_length_squared;

            if (!interval(0, 1).contains(alpha) || !interval(0, 1).contains(beta))
                return false;

            rec.t = root;
            rec.p = p;
            rec.u = alpha;
            rec.v = beta;
            rec.mat = mat;
            rec.set_face_normal(r, normal);
            return true;
        }

    private:
        point3 q;
        vec3 u;
        vec3 v;
        shared_ptr<material> mat;
        vec3 normal;
        double d;
        double u_length_squared;
        double v_length_squared;
};

#endif
