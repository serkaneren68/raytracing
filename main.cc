#include "rtweekend.h"
#include "camera.h"
#include "hittable.h"
#include "hittable_list.h"
#include "material.h"
#include "sphere.h"
#include "cylinder.h"
#include "quad.h"
#include <iostream>

int main() {
    hittable_list world;

    auto material_ground = make_shared<lambertian>(color(0.55, 0.55, 0.55));
    auto material_cylinder = make_shared<metal>(color(0.98, 0.78, 0.48), 0.0);
    auto material_photo = make_shared<image_light>("photo.ppm", 1.4);

    world.add(make_shared<sphere>(point3(0.0, -100.86, -2.0), 100.0, material_ground));
    world.add(make_shared<cylinder>(point3(0.02, -0.02, -2.99), 0.17, 1.6, vec3(0, 1, 0), material_cylinder));
    world.add(make_shared<quad>(
        point3(10.0, -0.82, -11.0),
        vec3(-20.0, 0, 0),
        vec3(0, 0, 18.0),
        material_photo
    ));

    camera cam;

    cam.aspect_ratio      = 16.0 / 9.0;
    cam.image_width       = 1200;
    cam.samples_per_pixel = 150;
    cam.max_depth         = 30;


    cam.vfov     = 30;
    cam.lookfrom = point3(0,2.0,20.2);
    cam.lookat   = point3(0,-0.25,-2.5);
    cam.vup      = vec3(0,1,0);
    
    cam.defocus_angle = 0.0;
    cam.focus_dist    = 7.1;

    cam.render(world);
}
