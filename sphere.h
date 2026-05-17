#ifndef SPHERE_H
#define SPHERE_H

#include "aabb.h"
#include "hittable.h"

class sphere : public hittable {
    public:
        sphere(const point3& center, double radius, shared_ptr<material> mat) : center(center), radius(std::fmax(0,radius)), mat(mat) {}
        bool hit(const ray& r, interval ray_t, hit_record& rec) const override {
            vec3 oc = center - r.origin();
            auto a = r.direction().length_squared();
            auto h = dot(r.direction(), oc);
            auto c = oc.length_squared() - radius*radius ;

            auto discriminant = h*h - a*c ;
            if(discriminant < 0 ) return false;

            auto sqrtd = std::sqrt(discriminant);

            //find the neares root that lies in aceptable range
            auto root = (h-sqrtd) / a ;
            if(!ray_t.surrounds(root)){
                root = (h+sqrtd) / a ;
               if (!ray_t.surrounds(root)) return false;
            }
            
            

            rec.t = root;
            rec.p = r.at(rec.t);
            rec.normal = (rec.p - center) / radius;
            vec3 outward_normal = (rec.p - center) / radius ;
            rec.set_face_normal(r, outward_normal);
            rec.mat = mat;
            return true;
        }

        bool bounding_box(aabb& output_box) const override {
            auto rvec = vec3(radius, radius, radius);
            output_box = aabb(center - rvec, center + rvec);
            return true;
        }

    private:
        point3 center;
        double radius;
        shared_ptr<material> mat;

};
#endif
