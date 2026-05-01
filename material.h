#ifndef MATERIAL_H
#define MATERIAL_H

#include "hittable.h"
#include "image.h"

class material {
    public:
        virtual ~material() = default;

        virtual bool scatter(
            const ray& r_in, const hit_record& rec, color& attenuation, ray& scattered
        ) const {
            return false;
        }

        virtual color emitted(double u, double v, const point3& p) const {
            return color(0, 0, 0);
        }
};

class lambertian : public material {
    public:
        lambertian(const color& albedo): albedo(albedo) {}

        bool scatter(const ray& r_in, const hit_record& rec, color& attenuation, ray& scattered) const override {
            auto scatter_direction = rec.normal + random_unit_vector();

            if(scatter_direction.near_zero())
                scatter_direction = rec.normal;

            scattered = ray(rec.p, scatter_direction);
            attenuation = albedo;
            return true;
        }
    private:
        color albedo;
};

class metal : public material {
    public:
        metal(const color& albedo, double fuzz) : albedo(albedo), fuzz(fuzz < 1 ? fuzz :1) {}

        bool scatter (const ray& r_in, const hit_record& rec, color& attenuation, ray& scattered) const override {
            vec3 reflected = reflect(r_in.direction(), rec.normal);
            reflected = unit_vector(reflected) + (fuzz * random_unit_vector());
            scattered = ray(rec.p, reflected);
            attenuation = albedo ;
            return (dot(scattered.direction(), rec.normal) > 0);
        }
    private:
        color albedo;
        double fuzz ;
};

class image_light : public material {
    public:
        image_light(const std::string& filename, double intensity = 1.0)
            : texture(filename), intensity(intensity) {}

        color emitted(double u, double v, const point3& p) const override {
            return intensity * texture.pixel_color(u, v);
        }

    private:
        image texture;
        double intensity;
};

#endif
