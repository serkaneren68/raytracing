#ifndef SCENE_CONFIG_H
#define SCENE_CONFIG_H

#include "vec3.h"
#include "color.h"

#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

struct scene_config {
    // Camera
    point3 lookfrom      = point3(0.0, 0.55, 1.10);
    point3 lookat        = point3(0.0, 0.07, 0.0);
    vec3   vup           = vec3(0, 1, 0);
    double vfov          = 30.0;
    double aspect_ratio  = 16.0 / 9.0;
    double focus_dist    = 1.25;
    double defocus_angle = 0.0;

    // Geometry
    double table_y         = 0.0;
    point3 cylinder_center = point3(0.0, 0.075, 0.0);
    double cylinder_radius = 0.035;
    double cylinder_height = 0.15;
    vec3   cylinder_axis   = vec3(0, 1, 0);
    bool   ball_enabled    = true;
    point3 ball_center     = point3(0.13, 0.05, 0.0);
    double ball_radius     = 0.05;

    // Materials
    color  cylinder_albedo = color(0.95, 0.88, 0.72);
    double cylinder_fuzz   = 0.0;
    color  ball_albedo     = color(0.92, 0.92, 0.95);
    double ball_fuzz       = 0.0;
    color  ground_albedo   = color(0.55, 0.55, 0.55);
    double photo_intensity = 1.0;

    // Photo plane fitting
    double photo_plane_margin = 0.02;

    // Horizontal fraction of the cylinder's screen-space bounding rect that
    // gets the anamorphic image. The vertical fraction is derived from the
    // target image's own aspect so the image isn't stretched.
    double target_rect_width_ratio  = 0.72;
    // Optional manual override for the vertical fraction. <0 = auto from
    // target image aspect; >=0 = use this value as-is (may distort).
    double target_rect_height_ratio = -1.0;

    // Toggle the whole anamorphic photo-plane pipeline (fit + texture + quad).
    // When false, only the geometry (cylinder + optional ball + ground) is
    // rendered with regular ray tracing.
    bool anamorphic_enabled = true;
};

inline std::string strip(const std::string& s) {
    auto a = s.find_first_not_of(" \t\r\n");
    if (a == std::string::npos) return "";
    auto b = s.find_last_not_of(" \t\r\n");
    return s.substr(a, b - a + 1);
}

inline bool parse_vec3(const std::string& value, vec3& out) {
    std::string s = value;
    for (auto& ch : s) if (ch == ',') ch = ' ';
    std::istringstream iss(s);
    double x, y, z;
    if (!(iss >> x >> y >> z)) return false;
    out = vec3(x, y, z);
    return true;
}

inline bool parse_bool(const std::string& value, bool& out) {
    std::string s;
    for (auto ch : value) s += static_cast<char>(std::tolower(static_cast<unsigned char>(ch)));
    if (s == "true" || s == "yes" || s == "1" || s == "on")  { out = true;  return true; }
    if (s == "false"|| s == "no"  || s == "0" || s == "off") { out = false; return true; }
    return false;
}

inline scene_config load_scene_config(const std::string& path) {
    scene_config cfg;
    std::ifstream in(path);
    if (!in) {
        std::clog << "Scene config: '" << path << "' not found, using defaults.\n";
        return cfg;
    }

    std::string line;
    int line_no = 0;
    while (std::getline(in, line)) {
        ++line_no;

        auto hash = line.find('#');
        if (hash != std::string::npos) line.erase(hash);
        line = strip(line);
        if (line.empty()) continue;

        auto eq = line.find('=');
        if (eq == std::string::npos) {
            std::clog << "Scene config line " << line_no << ": missing '=', skipping.\n";
            continue;
        }
        auto key   = strip(line.substr(0, eq));
        auto value = strip(line.substr(eq + 1));

        try {
            if (key == "lookfrom") {
                vec3 v; if (parse_vec3(value, v)) cfg.lookfrom = v;
            } else if (key == "lookat") {
                vec3 v; if (parse_vec3(value, v)) cfg.lookat = v;
            } else if (key == "vup") {
                vec3 v; if (parse_vec3(value, v)) cfg.vup = v;
            } else if (key == "vfov") {
                cfg.vfov = std::stod(value);
            } else if (key == "aspect_ratio") {
                cfg.aspect_ratio = std::stod(value);
            } else if (key == "focus_dist") {
                cfg.focus_dist = std::stod(value);
            } else if (key == "defocus_angle") {
                cfg.defocus_angle = std::stod(value);

            } else if (key == "table_y") {
                cfg.table_y = std::stod(value);
            } else if (key == "cylinder_center") {
                vec3 v; if (parse_vec3(value, v)) cfg.cylinder_center = v;
            } else if (key == "cylinder_radius") {
                cfg.cylinder_radius = std::stod(value);
            } else if (key == "cylinder_height") {
                cfg.cylinder_height = std::stod(value);
            } else if (key == "cylinder_axis") {
                vec3 v; if (parse_vec3(value, v)) cfg.cylinder_axis = v;
            } else if (key == "ball_enabled") {
                bool b; if (parse_bool(value, b)) cfg.ball_enabled = b;
            } else if (key == "ball_center") {
                vec3 v; if (parse_vec3(value, v)) cfg.ball_center = v;
            } else if (key == "ball_radius") {
                cfg.ball_radius = std::stod(value);

            } else if (key == "cylinder_albedo") {
                vec3 v; if (parse_vec3(value, v)) cfg.cylinder_albedo = v;
            } else if (key == "cylinder_fuzz") {
                cfg.cylinder_fuzz = std::stod(value);
            } else if (key == "ball_albedo") {
                vec3 v; if (parse_vec3(value, v)) cfg.ball_albedo = v;
            } else if (key == "ball_fuzz") {
                cfg.ball_fuzz = std::stod(value);
            } else if (key == "ground_albedo") {
                vec3 v; if (parse_vec3(value, v)) cfg.ground_albedo = v;
            } else if (key == "photo_intensity") {
                cfg.photo_intensity = std::stod(value);

            } else if (key == "photo_plane_margin") {
                cfg.photo_plane_margin = std::stod(value);
            } else if (key == "anamorphic_enabled") {
                bool b; if (parse_bool(value, b)) cfg.anamorphic_enabled = b;
            } else if (key == "target_rect_width_ratio") {
                cfg.target_rect_width_ratio = std::stod(value);
            } else if (key == "target_rect_height_ratio") {
                cfg.target_rect_height_ratio = std::stod(value);

            } else {
                std::clog << "Scene config line " << line_no << ": unknown key '" << key << "'.\n";
            }
        } catch (const std::exception& e) {
            std::clog << "Scene config line " << line_no << ": parse error for '" << key << "': " << e.what() << "\n";
        }
    }

    std::clog << "Scene config loaded from '" << path << "'.\n";
    return cfg;
}

#endif
