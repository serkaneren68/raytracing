#include "rtweekend.h"
#include "camera.h"
#include "hittable.h"
#include "hittable_list.h"
#include "material.h"
#include "sphere.h"
#include "bvh.h"
#include "cylinder.h"
#include "inverse_mapping.h"
#include "quad.h"
#include "scene_config.h"
#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

int main() {
    auto env_int = [](const char* name, int fallback) {
        if (const char* value = std::getenv(name))
            return std::max(1, std::atoi(value));
        return fallback;
    };
    auto env_str = [](const char* name, const char* fallback) {
        if (const char* value = std::getenv(name))
            return std::string(value);
        return std::string(fallback);
    };

    auto scene = load_scene_config(env_str("RT_SCENE_CONFIG", "scene.cfg"));

    hittable_list world_objects;

    auto material_ground   = make_shared<lambertian>(scene.ground_albedo);
    auto material_cylinder = make_shared<metal>(scene.cylinder_albedo, scene.cylinder_fuzz);

    world_objects.add(make_shared<sphere>(
        point3(0.0, scene.table_y - 100.0, 0.0), 100.0, material_ground));

    auto reflective_cylinder = make_shared<cylinder>(
        scene.cylinder_center,
        scene.cylinder_radius,
        scene.cylinder_height,
        scene.cylinder_axis,
        material_cylinder
    );
    world_objects.add(reflective_cylinder);

    if (scene.ball_enabled) {
        auto material_ball = make_shared<metal>(scene.ball_albedo, scene.ball_fuzz);
        world_objects.add(make_shared<sphere>(
            scene.ball_center,
            scene.ball_radius,
            material_ball
        ));
    }

    camera cam;

    cam.aspect_ratio      = scene.aspect_ratio;
    cam.image_width       = env_int("RT_IMAGE_WIDTH", 900);
    cam.samples_per_pixel = env_int("RT_SAMPLES", 64);
    cam.max_depth         = env_int("RT_MAX_DEPTH", 24);

    cam.vfov          = scene.vfov;
    cam.lookfrom      = scene.lookfrom;
    cam.lookat        = scene.lookat;
    cam.vup           = scene.vup;
    cam.defocus_angle = scene.defocus_angle;
    cam.focus_dist    = scene.focus_dist;
    cam.initialize();

    // Print viewport corners so they can be cross-checked against the HTML
    // visualizer. Same math as camera::initialize().
    {
        auto w = unit_vector(scene.lookfrom - scene.lookat);
        auto u = unit_vector(cross(scene.vup, w));
        auto v = cross(w, u);
        auto theta_v = degrees_to_radians(scene.vfov);
        auto vh = 2.0 * std::tan(theta_v / 2.0) * scene.focus_dist;
        auto vw = vh * scene.aspect_ratio;
        auto vp_center = scene.lookfrom - scene.focus_dist * w;
        auto tl = vp_center - u * (vw / 2) + v * (vh / 2);
        auto tr = vp_center + u * (vw / 2) + v * (vh / 2);
        auto br = vp_center + u * (vw / 2) - v * (vh / 2);
        auto bl = vp_center - u * (vw / 2) - v * (vh / 2);
        std::clog
            << "Viewport center: (" << vp_center.x() << ", " << vp_center.y() << ", " << vp_center.z()
            << "), size " << vw << " x " << vh << ".\n"
            << "  TL=(" << tl.x() << ", " << tl.y() << ", " << tl.z() << ")"
            <<  " TR=(" << tr.x() << ", " << tr.y() << ", " << tr.z() << ")\n"
            << "  BL=(" << bl.x() << ", " << bl.y() << ", " << bl.z() << ")"
            <<  " BR=(" << br.x() << ", " << br.y() << ", " << br.z() << ")\n";
    }

    auto target_file = env_str("RT_TARGET_IMAGE", "checkerboard.ppm");
    auto photo_file  = env_str("RT_PHOTO_IMAGE",  "photo.ppm");

    bool photo_on_disk = std::ifstream(photo_file).good();

    if (scene.anamorphic_enabled || photo_on_disk) {
        // Fit the photo plane to where cylinder reflections actually land on
        // the table — needed both for texture generation and for quad placement.
        auto plane_fit = fit_photo_plane_to_reflections(
            cam,
            *reflective_cylinder,
            scene.table_y + 0.001,
            scene.photo_plane_margin
        );
        if (plane_fit.sample_count == 0) {
            std::clog << "No reflections hit the table plane; cannot fit a photo plane.\n";
            return 1;
        }
        std::clog
            << "Fitted photo plane: q=(" << plane_fit.q.x() << ", " << plane_fit.q.z()
            << "), size=(" << plane_fit.u.x() << " x " << std::fabs(plane_fit.v.z())
            << ") from " << plane_fit.sample_count << " reflection samples.\n";

        if (scene.anamorphic_enabled) {
            photo_plane_mapper photo_plane(plane_fit.q, plane_fit.u, plane_fit.v);
            generate_inverse_mapped_photo_texture(
                cam,
                *reflective_cylinder,
                photo_plane,
                target_file,
                photo_file,
                env_int("RT_TEXTURE_WIDTH", 1000),
                env_int("RT_TEXTURE_HEIGHT", 1600),
                scene.target_rect_width_ratio,
                scene.target_rect_height_ratio
            );
        } else {
            std::clog << "Skipping texture generation; reusing existing "
                      << photo_file << ".\n";
        }

        auto material_photo = make_shared<image_light>(photo_file, scene.photo_intensity);
        world_objects.add(make_shared<quad>(
            plane_fit.q,
            plane_fit.u,
            plane_fit.v,
            material_photo
        ));
    } else {
        std::clog << "Anamorphic pipeline disabled and no " << photo_file
                  << " on disk — rendering geometry only.\n";
    }

    auto world = make_shared<bvh_node>(world_objects.objects);
    cam.render(*world);
}
