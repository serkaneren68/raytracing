#ifndef IMAGE_H
#define IMAGE_H

#include <fstream>
#include <string>
#include <vector>

#include "color.h"

class image {
    public:
        image() : image_width(0), image_height(0) {}
        image(const std::string& filename) {
            load(filename);
        }

        bool load(const std::string& filename) {
            std::ifstream in(filename, std::ios::binary);
            if (!in)
                return false;

            auto magic = read_token(in);
            if (magic != "P3" && magic != "P6")
                return false;

            image_width = std::stoi(read_token(in));
            image_height = std::stoi(read_token(in));
            auto max_value = std::stoi(read_token(in));

            if (image_width <= 0 || image_height <= 0 || max_value <= 0)
                return false;

            pixels.assign(image_width * image_height, color(0, 0, 0));

            if (magic == "P3") {
                for (auto& pixel : pixels) {
                    auto r = std::stod(read_token(in)) / max_value;
                    auto g = std::stod(read_token(in)) / max_value;
                    auto b = std::stod(read_token(in)) / max_value;
                    pixel = gamma_to_linear(color(r, g, b));
                }
            } else {
                in.get();
                for (auto& pixel : pixels) {
                    unsigned char rgb[3];
                    in.read(reinterpret_cast<char*>(rgb), 3);
                    auto r = double(rgb[0]) / max_value;
                    auto g = double(rgb[1]) / max_value;
                    auto b = double(rgb[2]) / max_value;
                    pixel = gamma_to_linear(color(r, g, b));
                }
            }

            return true;
        }

        int width() const {
            return image_width;
        }

        int height() const {
            return image_height;
        }

        color pixel_color(double u, double v) const {
            if (pixels.empty())
                return color(1, 0, 1);

            u = interval(0, 1).clamp(u);
            v = 1.0 - interval(0, 1).clamp(v);

            auto i = int(u * image_width);
            auto j = int(v * image_height);

            if (i >= image_width) i = image_width - 1;
            if (j >= image_height) j = image_height - 1;

            return pixels[j * image_width + i];
        }

    private:
        int image_width;
        int image_height;
        std::vector<color> pixels;

        static std::string read_token(std::istream& in) {
            std::string token;
            while (in >> token) {
                if (!token.empty() && token[0] == '#') {
                    std::string rest_of_line;
                    std::getline(in, rest_of_line);
                    continue;
                }
                return token;
            }
            return "";
        }

        static color gamma_to_linear(const color& c) {
            return color(c.x() * c.x(), c.y() * c.y(), c.z() * c.z());
        }
};

#endif
