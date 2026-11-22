// Minimal column-major 4x4 / vec3 math. Right-handed, Vulkan clip depth 0..1.
#pragma once
#include <cmath>

struct Vec3 {
    float x, y, z;
    Vec3() : x(0), y(0), z(0) {}
    Vec3(float a, float b, float c) : x(a), y(b), z(c) {}
    Vec3 operator+(const Vec3& o) const { return Vec3(x + o.x, y + o.y, z + o.z); }
    Vec3 operator-(const Vec3& o) const { return Vec3(x - o.x, y - o.y, z - o.z); }
    Vec3 operator*(float s) const { return Vec3(x * s, y * s, z * s); }
    float dot(const Vec3& o) const { return x * o.x + y * o.y + z * o.z; }
    Vec3 cross(const Vec3& o) const {
        return Vec3(y * o.z - z * o.y, z * o.x - x * o.z, x * o.y - y * o.x);
    }
    float length() const { return std::sqrt(dot(*this)); }
    Vec3 normalize() const {
        float l = length();
        return l > 1e-12f ? Vec3(x / l, y / l, z / l) : Vec3(0, 0, 0);
    }
};

struct Mat4 {
    float m[16]; // column-major: m[col*4+row]

    static Mat4 identity() {
        Mat4 r;
        for (int i = 0; i < 16; ++i) r.m[i] = 0.0f;
        r.m[0] = r.m[5] = r.m[10] = r.m[15] = 1.0f;
        return r;
    }
    static Mat4 scale(float s) {
        Mat4 r = identity();
        r.m[0] = r.m[5] = r.m[10] = s;
        return r;
    }
    static Mat4 translate(const Vec3& t) {
        Mat4 r = identity();
        r.m[12] = t.x; r.m[13] = t.y; r.m[14] = t.z;
        return r;
    }
    static Mat4 rotateY(float a) {
        Mat4 r = identity();
        float c = std::cos(a), s = std::sin(a);
        r.m[0] = c; r.m[8] = s; r.m[2] = -s; r.m[10] = c;
        return r;
    }
    static Mat4 rotateX(float a) {
        Mat4 r = identity();
        float c = std::cos(a), s = std::sin(a);
        r.m[5] = c; r.m[9] = -s; r.m[6] = s; r.m[10] = c;
        return r;
    }
    Mat4 operator*(const Mat4& o) const {
        Mat4 r;
        for (int c = 0; c < 4; ++c) {
            for (int row = 0; row < 4; ++row) {
                float sum = 0.0f;
                for (int k = 0; k < 4; ++k) sum += m[k * 4 + row] * o.m[c * 4 + k];
                r.m[c * 4 + row] = sum;
            }
        }
        return r;
    }
    // Transform a point (w = 1).
    Vec3 transformPoint(const Vec3& p) const {
        return Vec3(m[0] * p.x + m[4] * p.y + m[8] * p.z + m[12],
                    m[1] * p.x + m[5] * p.y + m[9] * p.z + m[13],
                    m[2] * p.x + m[6] * p.y + m[10] * p.z + m[14]);
    }
};

// Vulkan-style perspective: z in [0, 1], y flipped so +Y is up on screen.
inline Mat4 perspective(float fovYRad, float aspect, float zn, float zf) {
    float f = 1.0f / std::tan(fovYRad * 0.5f);
    Mat4 r;
    for (int i = 0; i < 16; ++i) r.m[i] = 0.0f;
    r.m[0] = f / aspect;
    r.m[5] = -f; // flip Y (Vulkan viewport has +Y down)
    r.m[10] = zf / (zn - zf);
    r.m[11] = -1.0f;
    r.m[14] = (zn * zf) / (zn - zf);
    return r;
}

inline Mat4 lookAt(const Vec3& eye, const Vec3& target, const Vec3& up) {
    Vec3 f = (target - eye).normalize();
    Vec3 s = f.cross(up).normalize();
    Vec3 u = s.cross(f);
    Mat4 r = Mat4::identity();
    r.m[0] = s.x; r.m[4] = s.y; r.m[8] = s.z;
    r.m[1] = u.x; r.m[5] = u.y; r.m[9] = u.z;
    r.m[2] = -f.x; r.m[6] = -f.y; r.m[10] = -f.z;
    r.m[12] = -s.dot(eye);
    r.m[13] = -u.dot(eye);
    r.m[14] = f.dot(eye);
    return r;
}
