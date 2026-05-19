#include "app.h"

#include "rtweekend.h"
#include "bvh.h"
#include "camera.h"
#include "cylinder.h"
#include "frustum.h"
#include "hittable.h"
#include "hittable_list.h"
#include "inverse_mapping.h"
#include "material.h"
#include "normal_triangle_mesh.h"
#include "point_cloud_splats.h"
#include "quad.h"
#include "scene_config.h"
#include "sphere.h"

#include <algorithm>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

namespace {

int env_int(const char* name, int fallback) {
    if (const char* value = std::getenv(name)) {
        return std::max(1, std::atoi(value));
    }
    return fallback;
}

std::string env_str(const char* name, const char* fallback) {
    if (const char* value = std::getenv(name)) {
        return std::string(value);
    }
    return std::string(fallback);
}

camera make_camera(const scene_config& scene) {
    camera cam;
    cam.aspect_ratio = scene.aspect_ratio;
    cam.image_width = env_int("RT_IMAGE_WIDTH", 900);
    cam.samples_per_pixel = env_int("RT_SAMPLES", 64);
    cam.max_depth = env_int("RT_MAX_DEPTH", 24);
    cam.vfov = scene.vfov;
    cam.lookfrom = scene.lookfrom;
    cam.lookat = scene.lookat;
    cam.vup = scene.vup;
    cam.defocus_angle = scene.defocus_angle;
    cam.focus_dist = scene.focus_dist;
    cam.initialize();
    return cam;
}

void log_viewport(const scene_config& scene) {
    // Same math as camera::initialize(), logged here for the HTML visualizer.
    auto w = unit_vector(scene.lookfrom - scene.lookat);
    auto u = unit_vector(cross(scene.vup, w));
    auto v = cross(w, u);
    auto theta_v = degrees_to_radians(scene.vfov);
    auto viewport_height = 2.0 * std::tan(theta_v / 2.0) * scene.focus_dist;
    auto viewport_width = viewport_height * scene.aspect_ratio;
    auto viewport_center = scene.lookfrom - scene.focus_dist * w;
    auto top_left = viewport_center - u * (viewport_width / 2) + v * (viewport_height / 2);
    auto top_right = viewport_center + u * (viewport_width / 2) + v * (viewport_height / 2);
    auto bottom_right = viewport_center + u * (viewport_width / 2) - v * (viewport_height / 2);
    auto bottom_left = viewport_center - u * (viewport_width / 2) - v * (viewport_height / 2);

    std::clog
        << "Viewport center: (" << viewport_center.x() << ", " << viewport_center.y() << ", "
        << viewport_center.z() << "), size " << viewport_width << " x " << viewport_height << ".\n"
        << "  TL=(" << top_left.x() << ", " << top_left.y() << ", " << top_left.z() << ")"
        << " TR=(" << top_right.x() << ", " << top_right.y() << ", " << top_right.z() << ")\n"
        << "  BL=(" << bottom_left.x() << ", " << bottom_left.y() << ", " << bottom_left.z() << ")"
        << " BR=(" << bottom_right.x() << ", " << bottom_right.y() << ", " << bottom_right.z()
        << ")\n";
}

shared_ptr<hittable> build_reflective_object(
    const scene_config& scene,
    const shared_ptr<material>& reflector_material
) {
    if (scene.reflective_object_type == "mesh") {
        auto mesh = load_normal_triangle_mesh(
            scene.mesh_file,
            reflector_material,
            scene.mesh_center,
            scene.mesh_height,
            scene.mesh_upside_down
        );
        std::clog << "Reflective object: mesh '" << scene.mesh_file
                  << "' centered at (" << scene.mesh_center.x() << ", "
                  << scene.mesh_center.y() << ", " << scene.mesh_center.z()
                  << "), height " << scene.mesh_height << ".\n";
        return mesh;
    }

    if (scene.reflective_object_type == "pointcloud") {
        auto pointcloud = load_point_cloud_splats(
            scene.pointcloud_file,
            reflector_material,
            scene.pointcloud_center,
            scene.pointcloud_height,
            scene.pointcloud_point_radius
        );
        std::clog << "Reflective object: point cloud '" << scene.pointcloud_file
                  << "' centered at (" << scene.pointcloud_center.x() << ", "
                  << scene.pointcloud_center.y() << ", " << scene.pointcloud_center.z()
                  << "), height " << scene.pointcloud_height
                  << ", splat radius " << scene.pointcloud_point_radius << ".\n";
        return pointcloud;
    }

    if (scene.reflective_object_type == "frustum") {
        auto frustum_object = make_shared<frustum>(
            scene.frustum_base_center,
            scene.frustum_bottom_radius,
            scene.frustum_top_radius,
            scene.frustum_height,
            scene.frustum_axis,
            reflector_material
        );
        std::clog << "Reflective object: frustum at base center ("
                  << scene.frustum_base_center.x() << ", "
                  << scene.frustum_base_center.y() << ", "
                  << scene.frustum_base_center.z() << "), height "
                  << scene.frustum_height << ".\n";
        return frustum_object;
    }

    std::clog << "Reflective object: cylinder.\n";
    return make_shared<cylinder>(
        scene.cylinder_center,
        scene.cylinder_radius,
        scene.cylinder_height,
        scene.cylinder_axis,
        reflector_material
    );
}

bool add_photo_plane_if_needed(
    const scene_config& scene,
    const camera& cam,
    const shared_ptr<hittable>& reflective_object,
    hittable_list& world_objects,
    const std::string& target_file,
    const std::string& photo_file,
    const std::string& print_info_file
) {
    bool photo_on_disk = std::ifstream(photo_file).good();
    if (!scene.anamorphic_enabled && !photo_on_disk) {
        std::clog << "Anamorphic pipeline disabled and no " << photo_file
                  << " on disk; rendering geometry only.\n";
        return true;
    }

    photo_plane_fit plane_fit;
    if (scene.explicit_photo_plane_enabled) {
        plane_fit.q = scene.photo_plane_q;
        plane_fit.u = scene.photo_plane_u;
        plane_fit.v = scene.photo_plane_v;
        plane_fit.sample_count = -1;
        std::clog << "Using explicit photo plane from scene config.\n";
    } else {
        plane_fit = fit_photo_plane_to_reflections(
            cam,
            *reflective_object,
            scene.table_y + 0.001,
            scene.photo_plane_margin,
            scene.photo_plane_trim_fraction
        );
        if (plane_fit.sample_count == 0) {
            std::clog << "No reflections hit the table plane; cannot fit a photo plane.\n";
            return false;
        }
        std::clog
            << "Fitted photo plane: q=(" << plane_fit.q.x() << ", " << plane_fit.q.z()
            << "), size=(" << plane_fit.u.x() << " x " << std::fabs(plane_fit.v.z())
            << ") from " << plane_fit.sample_count << " reflection samples.\n";
    }

    if (scene.anamorphic_enabled) {
        photo_plane_mapper photo_plane(plane_fit.q, plane_fit.u, plane_fit.v);
        generate_inverse_mapped_photo_texture(
            cam,
            *reflective_object,
            photo_plane,
            target_file,
            photo_file,
            env_int("RT_TEXTURE_WIDTH", 1000),
            env_int("RT_TEXTURE_HEIGHT", 1600),
            scene.target_rect_width_ratio,
            scene.target_rect_height_ratio,
            scene.target_rect_offset_x,
            scene.target_rect_offset_y,
            scene.photo_plane_solid_empty_background,
            print_info_file
        );
    } else {
        std::clog << "Skipping texture generation; reusing existing "
                  << photo_file << ".\n";
    }

    auto photo_material = make_shared<image_light>(photo_file, scene.photo_intensity);
    world_objects.add(make_shared<quad>(
        plane_fit.q,
        plane_fit.u,
        plane_fit.v,
        photo_material
    ));
    return true;
}

}  // namespace

namespace raytracing_app {

int run() {
    auto scene = load_scene_config(env_str("RT_SCENE_CONFIG", "config/default.cfg"));
    auto target_file = env_str("RT_TARGET_IMAGE", "assets/targets/checkerboard.ppm");
    auto photo_file = env_str("RT_PHOTO_IMAGE", "generated/photo.ppm");
    auto print_info_file = env_str("RT_PRINT_INFO_FILE", "generated/photo_print_info.txt");

    hittable_list world_objects;

    auto ground_material = make_shared<lambertian>(scene.ground_albedo);
    auto reflector_material = make_shared<metal>(scene.cylinder_albedo, scene.cylinder_fuzz);
    if (scene.ground_enabled) {
        world_objects.add(make_shared<sphere>(
            point3(0.0, scene.table_y - 100.0, 0.0), 100.0, ground_material));
    }

    shared_ptr<hittable> reflective_object;
    try {
        reflective_object = build_reflective_object(scene, reflector_material);
    } catch (const std::exception& e) {
        std::clog << "Failed to build reflective object: " << e.what() << "\n";
        return 1;
    }
    world_objects.add(reflective_object);

    if (scene.ball_enabled) {
        auto ball_material = make_shared<metal>(scene.ball_albedo, scene.ball_fuzz);
        world_objects.add(make_shared<sphere>(
            scene.ball_center,
            scene.ball_radius,
            ball_material
        ));
    }

    auto cam = make_camera(scene);
    log_viewport(scene);

    if (!add_photo_plane_if_needed(
            scene,
            cam,
            reflective_object,
            world_objects,
            target_file,
            photo_file,
            print_info_file)) {
        return 1;
    }

    auto world = make_shared<bvh_node>(world_objects.objects);
    cam.render(*world);
    return 0;
}

}  // namespace raytracing_app
