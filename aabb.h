#ifndef AABB_H
#define AABB_H

#include <algorithm>
#include <cmath>

class aabb {
    public:
        interval x;
        interval y;
        interval z;

        aabb() {}

        aabb(const interval& x, const interval& y, const interval& z)
            : x(x), y(y), z(z) {
            pad_to_minimums();
        }

        aabb(const point3& a, const point3& b) {
            x = interval(std::fmin(a.x(), b.x()), std::fmax(a.x(), b.x()));
            y = interval(std::fmin(a.y(), b.y()), std::fmax(a.y(), b.y()));
            z = interval(std::fmin(a.z(), b.z()), std::fmax(a.z(), b.z()));
            pad_to_minimums();
        }

        const interval& axis_interval(int axis) const {
            if (axis == 1) return y;
            if (axis == 2) return z;
            return x;
        }

        bool hit(const ray& r, interval ray_t) const {
            for (int axis = 0; axis < 3; ++axis) {
                const auto& ax = axis_interval(axis);
                auto ray_origin = r.origin()[axis];
                auto ray_direction = r.direction()[axis];

                if (std::fabs(ray_direction) < 1e-12) {
                    if (!ax.contains(ray_origin))
                        return false;
                    continue;
                }

                auto inv_d = 1.0 / ray_direction;
                auto t0 = (ax.min - ray_origin) * inv_d;
                auto t1 = (ax.max - ray_origin) * inv_d;

                if (inv_d < 0.0)
                    std::swap(t0, t1);

                if (t0 > ray_t.min) ray_t.min = t0;
                if (t1 < ray_t.max) ray_t.max = t1;

                if (ray_t.max <= ray_t.min)
                    return false;
            }
            return true;
        }

        int longest_axis() const {
            if (x.size() > y.size())
                return x.size() > z.size() ? 0 : 2;
            return y.size() > z.size() ? 1 : 2;
        }

    private:
        void pad_to_minimums() {
            auto delta = 0.0001;
            if (x.size() < delta) x = expand(x, delta);
            if (y.size() < delta) y = expand(y, delta);
            if (z.size() < delta) z = expand(z, delta);
        }

        static interval expand(const interval& ax, double delta) {
            auto padding = delta / 2;
            return interval(ax.min - padding, ax.max + padding);
        }
};

inline aabb surrounding_box(const aabb& box0, const aabb& box1) {
    return aabb(
        interval(std::fmin(box0.x.min, box1.x.min), std::fmax(box0.x.max, box1.x.max)),
        interval(std::fmin(box0.y.min, box1.y.min), std::fmax(box0.y.max, box1.y.max)),
        interval(std::fmin(box0.z.min, box1.z.min), std::fmax(box0.z.max, box1.z.max))
    );
}

inline aabb surrounding_points(const point3& a, const point3& b, const point3& c) {
    return aabb(
        interval(std::fmin(a.x(), std::fmin(b.x(), c.x())), std::fmax(a.x(), std::fmax(b.x(), c.x()))),
        interval(std::fmin(a.y(), std::fmin(b.y(), c.y())), std::fmax(a.y(), std::fmax(b.y(), c.y()))),
        interval(std::fmin(a.z(), std::fmin(b.z(), c.z())), std::fmax(a.z(), std::fmax(b.z(), c.z())))
    );
}

#endif
