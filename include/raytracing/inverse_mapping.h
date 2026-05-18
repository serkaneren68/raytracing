#ifndef INVERSE_MAPPING_H
#define INVERSE_MAPPING_H

#include "camera.h"
#include "hittable.h"
#include "image.h"

#include <algorithm>
#include <fstream>
#include <vector>

struct inverse_map_hit {
    bool valid = false;
    int pixel_i = 0;
    int pixel_j = 0;
    point3 surface_point;
    vec3 surface_normal;
    point3 photo_point;
    double photo_u = 0;
    double photo_v = 0;
};

struct target_rect {
    int x0 = 0;
    int y0 = 0;
    int x1 = 0;
    int y1 = 0;

    bool contains(int x, int y) const {
        return x0 <= x && x < x1 && y0 <= y && y < y1;
    }

    double u(int x) const {
        return double(x - x0) / std::fmax(1, x1 - x0 - 1);
    }

    double v(int y) const {
        return double(y - y0) / std::fmax(1, y1 - y0 - 1);
    }
};

class photo_plane_mapper {
    public:
        photo_plane_mapper(const point3& q, const vec3& u, const vec3& v)
            : q(q), u(u), v(v) {
            auto n = cross(u, v);
            normal = unit_vector(n);
            d = dot(normal, q);
            u_length_squared = u.length_squared();
            v_length_squared = v.length_squared();
        }

        bool hit_uv(const ray& r, point3& p, double& out_u, double& out_v) const {
            if (!hit_uv_unbounded(r, p, out_u, out_v))
                return false;

            return interval(0, 1).contains(out_u) && interval(0, 1).contains(out_v);
        }

        bool hit_uv_unbounded(const ray& r, point3& p, double& out_u, double& out_v) const {
            auto denom = dot(normal, r.direction());
            if (std::fabs(denom) < 1e-8)
                return false;

            auto root = (d - dot(normal, r.origin())) / denom;
            if (root <= 1e-4)
                return false;

            p = r.at(root);
            auto planar_hitpt = p - q;
            out_u = dot(planar_hitpt, u) / u_length_squared;
            out_v = dot(planar_hitpt, v) / v_length_squared;

            return true;
        }

        double width() const { return std::sqrt(u_length_squared); }
        double height() const { return std::sqrt(v_length_squared); }

    private:
        point3 q;
        vec3 u;
        vec3 v;
        vec3 normal;
        double d;
        double u_length_squared;
        double v_length_squared;
};

inline bool reflect_camera_ray_to_photo_plane(
    const ray& camera_ray,
    const hittable& reflective_object,
    const photo_plane_mapper& photo_plane,
    double& out_u,
    double& out_v
) {
    hit_record rec;
    if (!reflective_object.hit(camera_ray, interval(0.001, infinity), rec))
        return false;

    auto reflected_direction = reflect(unit_vector(camera_ray.direction()), rec.normal);
    auto reflected_ray = ray(rec.p, reflected_direction);

    point3 photo_point;
    return photo_plane.hit_uv(reflected_ray, photo_point, out_u, out_v);
}

inline inverse_map_hit map_camera_pixel_to_photo_plane(
    const camera& cam,
    const hittable& reflective_object,
    const photo_plane_mapper& photo_plane,
    int pixel_i,
    int pixel_j
) {
    inverse_map_hit result;
    result.pixel_i = pixel_i;
    result.pixel_j = pixel_j;

    auto camera_ray = cam.pixel_center_ray(pixel_i, pixel_j);
    hit_record rec;
    if (!reflective_object.hit(camera_ray, interval(0.001, infinity), rec))
        return result;

    auto reflected_direction = reflect(unit_vector(camera_ray.direction()), rec.normal);
    auto reflected_ray = ray(rec.p, reflected_direction);

    point3 photo_point;
    double photo_u = 0;
    double photo_v = 0;
    if (!photo_plane.hit_uv(reflected_ray, photo_point, photo_u, photo_v))
        return result;

    result.valid = true;
    result.surface_point = rec.p;
    result.surface_normal = rec.normal;
    result.photo_point = photo_point;
    result.photo_u = photo_u;
    result.photo_v = photo_v;
    return result;
}

inline int clamp_to_byte(double x) {
    x = interval(0, 0.999).clamp(x);
    return int(256 * x);
}

inline void write_ppm_p3(
    const std::string& filename,
    const std::vector<color>& pixels,
    int width,
    int height
) {
    std::ofstream out(filename);
    out << "P3\n" << width << ' ' << height << "\n255\n";
    for (const auto& pixel : pixels) {
        out << clamp_to_byte(pixel.x()) << ' '
            << clamp_to_byte(pixel.y()) << ' '
            << clamp_to_byte(pixel.z()) << '\n';
    }
}

inline target_rect centered_rect_inside(const target_rect& bounds, double width_ratio, double height_ratio) {
    auto bounds_w = bounds.x1 - bounds.x0;
    auto bounds_h = bounds.y1 - bounds.y0;
    auto rect_w = std::max(1, int(bounds_w * width_ratio));
    auto rect_h = std::max(1, int(bounds_h * height_ratio));
    auto cx = (bounds.x0 + bounds.x1) / 2;
    auto cy = (bounds.y0 + bounds.y1) / 2;

    return target_rect{
        cx - rect_w / 2,
        cy - rect_h / 2,
        cx - rect_w / 2 + rect_w,
        cy - rect_h / 2 + rect_h
    };
}

struct photo_plane_fit {
    point3 q;
    vec3 u;
    vec3 v;
    int sample_count = 0;
};

struct photo_texture_region {
    bool valid = false;
    double min_u = 0;
    double max_u = 0;
    double min_v = 0;
    double max_v = 0;
    int mapped_samples = 0;

    double width_fraction() const { return valid ? (max_u - min_u) : 0.0; }
    double height_fraction() const { return valid ? (max_v - min_v) : 0.0; }
};

inline photo_plane_fit fit_photo_plane_to_reflections(
    const camera& cam,
    const hittable& reflective_object,
    double plane_y,
    double margin,
    double trim_fraction
) {
    auto image_w = static_cast<int>(cam.image_width);
    auto image_h = cam.image_height_value();

    std::vector<double> xs;
    std::vector<double> zs;
    xs.reserve(image_w * image_h / 8);
    zs.reserve(image_w * image_h / 8);

    for (int j = 0; j < image_h; ++j) {
        for (int i = 0; i < image_w; ++i) {
            auto camera_ray = cam.pixel_center_ray(i, j);
            hit_record rec;
            if (!reflective_object.hit(camera_ray, interval(0.001, infinity), rec))
                continue;

            auto reflected_direction = reflect(unit_vector(camera_ray.direction()), rec.normal);
            if (std::fabs(reflected_direction.y()) < 1e-8)
                continue;

            auto t = (plane_y - rec.p.y()) / reflected_direction.y();
            if (t <= 1e-4)
                continue;

            auto hit_point = rec.p + t * reflected_direction;
            xs.push_back(hit_point.x());
            zs.push_back(hit_point.z());
        }
    }

    photo_plane_fit fit;
    fit.sample_count = static_cast<int>(xs.size());
    if (xs.empty())
        return fit;

    std::sort(xs.begin(), xs.end());
    std::sort(zs.begin(), zs.end());

    auto clamped_trim = interval(0.0, 0.49).clamp(trim_fraction);
    auto trim_count = static_cast<int>(xs.size() * clamped_trim);
    auto last_index = static_cast<int>(xs.size()) - 1 - trim_count;
    if (last_index < trim_count)
        last_index = trim_count;

    auto min_x = xs[trim_count];
    auto max_x = xs[last_index];
    auto min_z = zs[trim_count];
    auto max_z = zs[last_index];

    min_x -= margin; max_x += margin;
    min_z -= margin; max_z += margin;

    fit.q = point3(min_x, plane_y, max_z);
    fit.u = vec3(max_x - min_x, 0, 0);
    fit.v = vec3(0, 0, min_z - max_z);
    return fit;
}

inline bool find_camera_object_bounds(
    const camera& cam,
    const hittable& reflective_object,
    target_rect& bounds
) {
    auto image_w = static_cast<int>(cam.image_width);
    auto image_h = cam.image_height_value();
    bounds = target_rect{image_w, image_h, 0, 0};

    for (int j = 0; j < image_h; ++j) {
        for (int i = 0; i < image_w; ++i) {
            auto camera_ray = cam.pixel_center_ray(i, j);
            hit_record rec;
            if (!reflective_object.hit(camera_ray, interval(0.001, infinity), rec))
                continue;

            bounds.x0 = std::min(bounds.x0, i);
            bounds.y0 = std::min(bounds.y0, j);
            bounds.x1 = std::max(bounds.x1, i + 1);
            bounds.y1 = std::max(bounds.y1, j + 1);
        }
    }

    return bounds.x0 < bounds.x1 && bounds.y0 < bounds.y1;
}

inline photo_texture_region trace_photo_texture_region(
    const camera& cam,
    const hittable& reflective_object,
    const photo_plane_mapper& photo_plane,
    const target_rect& target
) {
    photo_texture_region region;
    region.min_u = infinity;
    region.max_u = -infinity;
    region.min_v = infinity;
    region.max_v = -infinity;

    constexpr int subsamples_per_axis = 10;
    constexpr double subsample_step = 1.0 / subsamples_per_axis;
    constexpr double subsample_origin = subsample_step / 2;

    for (int j = target.y0; j < target.y1; ++j) {
        for (int i = target.x0; i < target.x1; ++i) {
            for (int sj = 0; sj < subsamples_per_axis; ++sj) {
                for (int si = 0; si < subsamples_per_axis; ++si) {
                    auto sub_di = subsample_origin + si * subsample_step - 0.5;
                    auto sub_dj = subsample_origin + sj * subsample_step - 0.5;
                    auto camera_ray = cam.pixel_subsample_ray(i + sub_di, j + sub_dj);

                    double photo_u = 0;
                    double photo_v = 0;
                    if (!reflect_camera_ray_to_photo_plane(camera_ray, reflective_object, photo_plane, photo_u, photo_v))
                        continue;

                    region.min_u = std::min(region.min_u, photo_u);
                    region.max_u = std::max(region.max_u, photo_u);
                    region.min_v = std::min(region.min_v, photo_v);
                    region.max_v = std::max(region.max_v, photo_v);
                    ++region.mapped_samples;
                }
            }
        }
    }

    region.valid = region.mapped_samples > 0;
    return region;
}

inline void write_print_info(
    const std::string& filename,
    const photo_texture_region& region,
    const photo_plane_mapper& photo_plane
) {
    if (!region.valid)
        return;

    std::ofstream out(filename);
    if (!out)
        return;

    out << "active_width_m=" << photo_plane.width() * region.width_fraction() << "\n";
    out << "active_height_m=" << photo_plane.height() * region.height_fraction() << "\n";
    out << "active_width_cm=" << photo_plane.width() * region.width_fraction() * 100.0 << "\n";
    out << "active_height_cm=" << photo_plane.height() * region.height_fraction() * 100.0 << "\n";
    out << "photo_u_range=" << region.min_u << "," << region.max_u << "\n";
    out << "photo_v_range=" << region.min_v << "," << region.max_v << "\n";
    out << "mapped_samples=" << region.mapped_samples << "\n";
}

inline int splat_to_texture(
    std::vector<color>& pixels,
    std::vector<int>& counts,
    int width,
    int height,
    double u,
    double v,
    const color& value,
    int radius
) {
    if (u < 0.0 || u >= 1.0 || v < 0.0 || v >= 1.0)
        return 0;

    auto cx = int(u * width);
    auto cy = int((1.0 - v) * height);
    auto r2 = radius * radius;

    for (int dy = -radius; dy <= radius; ++dy) {
        for (int dx = -radius; dx <= radius; ++dx) {
            if (dx * dx + dy * dy > r2) continue;
            auto x = cx + dx;
            auto y = cy + dy;
            if (x < 0 || x >= width || y < 0 || y >= height) continue;
            auto index = y * width + x;
            pixels[index] += value;
            counts[index] += 1;
        }
    }
    return 1;
}

inline void fill_empty_pixels(
    std::vector<color>& pixels,
    std::vector<int>& counts,
    int width,
    int height,
    int passes
) {
    auto empty_color = pixels.empty() ? color(0,0,0) : pixels[0];
    for (int p = 0; p < passes; ++p) {
        auto previous_pixels = pixels;
        auto previous_counts = counts;
        for (int y = 0; y < height; ++y) {
            for (int x = 0; x < width; ++x) {
                auto idx = y * width + x;
                if (previous_counts[idx] > 0) continue;

                color accum(0, 0, 0);
                int n = 0;
                for (int dy = -1; dy <= 1; ++dy) {
                    for (int dx = -1; dx <= 1; ++dx) {
                        if (dx == 0 && dy == 0) continue;
                        auto nx = x + dx;
                        auto ny = y + dy;
                        if (nx < 0 || nx >= width || ny < 0 || ny >= height) continue;
                        auto nidx = ny * width + nx;
                        if (previous_counts[nidx] <= 0) continue;
                        accum += previous_pixels[nidx] / previous_counts[nidx];
                        ++n;
                    }
                }
                if (n > 0) {
                    pixels[idx] = accum;
                    counts[idx] = n;
                }
            }
        }
    }
    (void)empty_color;
}

inline void generate_inverse_mapped_photo_texture(
    const camera& cam,
    const hittable& reflective_object,
    const photo_plane_mapper& photo_plane,
    const std::string& target_filename,
    const std::string& output_filename,
    int texture_width,
    int texture_height,
    double target_width_ratio = 0.72,
    double target_height_ratio = 0.72,
    const std::string& print_info_filename = "generated/photo_print_info.txt"
) {
    image target_image(target_filename);
    if (target_image.width() <= 0 || target_image.height() <= 0) {
        std::clog << "Inverse texture generation: could not load target image " << target_filename << ".\n";
        return;
    }

    target_rect object_bounds;
    if (!find_camera_object_bounds(cam, reflective_object, object_bounds)) {
        std::clog << "Inverse texture generation: no object bounds found.\n";
        return;
    }

    double effective_height_ratio = target_height_ratio;
    if (effective_height_ratio < 0.0) {
        auto img_aspect = double(target_image.width()) / std::max(1, target_image.height());
        auto bw = std::max(1, object_bounds.x1 - object_bounds.x0);
        auto bh = std::max(1, object_bounds.y1 - object_bounds.y0);
        auto target_w_px = bw * target_width_ratio;
        auto target_h_px = target_w_px / img_aspect;
        effective_height_ratio = std::min(1.0, target_h_px / bh);
    }
    std::clog << "Target rect ratios: w=" << target_width_ratio
              << ", h=" << effective_height_ratio
              << " (image " << target_image.width() << "x" << target_image.height() << ").\n";

    auto target = centered_rect_inside(object_bounds, target_width_ratio, effective_height_ratio);
    auto region = trace_photo_texture_region(cam, reflective_object, photo_plane, target);
    std::vector<color> pixels(texture_width * texture_height, color(1, 0, 1));
    std::vector<int> counts(texture_width * texture_height, 0);

    constexpr int subsamples_per_axis = 10;
    constexpr double subsample_step = 1.0 / subsamples_per_axis;
    constexpr double subsample_origin = subsample_step / 2;

    auto target_w = std::max(1, target.x1 - target.x0);
    auto target_h = std::max(1, target.y1 - target.y0);
    auto radius_x = texture_width / (target_w * subsamples_per_axis);
    auto radius_y = texture_height / (target_h * subsamples_per_axis);
    auto splat_radius = std::max(1, (radius_x + radius_y) / 2);

    int mapped_samples = 0;
    for (int j = target.y0; j < target.y1; ++j) {
        for (int i = target.x0; i < target.x1; ++i) {
            for (int sj = 0; sj < subsamples_per_axis; ++sj) {
                for (int si = 0; si < subsamples_per_axis; ++si) {
                    auto sub_di = subsample_origin + si * subsample_step - 0.5;
                    auto sub_dj = subsample_origin + sj * subsample_step - 0.5;
                    auto camera_ray = cam.pixel_subsample_ray(i + sub_di, j + sub_dj);

                    double photo_u = 0;
                    double photo_v = 0;
                    if (!reflect_camera_ray_to_photo_plane(camera_ray, reflective_object, photo_plane, photo_u, photo_v))
                        continue;

                    auto target_u = (i + sub_di + 0.5 - target.x0) / target_w;
                    auto target_v = (j + sub_dj + 0.5 - target.y0) / target_h;
                    auto c = target_image.pixel_color(target_u, 1.0 - target_v);
                    mapped_samples += splat_to_texture(
                        pixels,
                        counts,
                        texture_width,
                        texture_height,
                        photo_u,
                        photo_v,
                        c,
                        splat_radius
                    );
                }
            }
        }
    }

    for (size_t idx = 0; idx < pixels.size(); ++idx) {
        if (counts[idx] > 0)
            pixels[idx] /= counts[idx];
    }

    fill_empty_pixels(pixels, counts, texture_width, texture_height, 3);

    write_ppm_p3(output_filename, pixels, texture_width, texture_height);
    write_print_info(print_info_filename, region, photo_plane);
    std::clog
        << "Generated inverse texture " << output_filename
        << " using target " << target_filename
        << " from camera target rect ["
        << target.x0 << ", " << target.y0 << " -> "
        << target.x1 << ", " << target.y1 << "], "
        << mapped_samples << " samples reached the photo plane.\n";
}

#endif
