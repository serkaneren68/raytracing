#ifndef BVH_H
#define BVH_H

#include "aabb.h"
#include "hittable.h"

#include <algorithm>
#include <iostream>
#include <vector>

class bvh_node : public hittable {
    public:
        bvh_node(std::vector<shared_ptr<hittable>>& objects)
            : bvh_node(objects, 0, objects.size()) {}

        bvh_node(std::vector<shared_ptr<hittable>>& objects, size_t start, size_t end) {
            aabb global_box;
            bool first_box = true;

            for (size_t object_index = start; object_index < end; ++object_index) {
                aabb object_box;
                if (!objects[object_index]->bounding_box(object_box)) {
                    std::cerr << "No bounding box in bvh_node constructor.\n";
                    continue;
                }
                global_box = first_box ? object_box : surrounding_box(global_box, object_box);
                first_box = false;
            }

            bbox = global_box;
            auto axis = bbox.longest_axis();

            auto comparator = [axis](const shared_ptr<hittable>& a, const shared_ptr<hittable>& b) {
                aabb box_a;
                aabb box_b;

                if (!a->bounding_box(box_a) || !b->bounding_box(box_b))
                    std::cerr << "No bounding box in bvh_node comparator.\n";

                return box_a.axis_interval(axis).min < box_b.axis_interval(axis).min;
            };

            auto object_span = end - start;

            if (object_span == 1) {
                left = right = objects[start];
            } else if (object_span == 2) {
                if (comparator(objects[start], objects[start + 1])) {
                    left = objects[start];
                    right = objects[start + 1];
                } else {
                    left = objects[start + 1];
                    right = objects[start];
                }
            } else {
                std::sort(objects.begin() + start, objects.begin() + end, comparator);

                auto mid = start + object_span / 2;
                left = make_shared<bvh_node>(objects, start, mid);
                right = make_shared<bvh_node>(objects, mid, end);
            }
        }

        bool hit(const ray& r, interval ray_t, hit_record& rec) const override {
            if (!bbox.hit(r, ray_t))
                return false;

            bool hit_left = left->hit(r, ray_t, rec);
            bool hit_right = right->hit(r, interval(ray_t.min, hit_left ? rec.t : ray_t.max), rec);

            return hit_left || hit_right;
        }

        bool bounding_box(aabb& output_box) const override {
            output_box = bbox;
            return true;
        }

    private:
        shared_ptr<hittable> left;
        shared_ptr<hittable> right;
        aabb bbox;
};

#endif
