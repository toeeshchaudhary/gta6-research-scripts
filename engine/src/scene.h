// M3 scene: places thousands of instances at their true world transforms.
//
// The scene file is data (--scene), the transform is a real TRS matrix built
// from the instance's translation / quaternion / scale. Nothing about the scene
// is compiled in: the archetype hash only picks a representative model out of
// the --pool list.
//
// This is a deliberately small JSON reader: it understands exactly the shape
// work\world\scene_streets.json has (an object with an "instances" array of
// {archetype, hash, pos[3], rot[4], scale[3], resource}). It skips unknown
// members, tolerates missing ones (identity), and does not try to be general.
#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "math3d.h"

struct Quat {
    float x = 0.0f, y = 0.0f, z = 0.0f, w = 1.0f;
};

struct SceneInstance {
    Vec3 pos;         // world translation, true game units
    Quat rot;         // world rotation, true game quaternion
    Vec3 scl{1, 1, 1}; // world scale (per axis), true game scale
    uint32_t hash = 0;
    std::string modelPath; // per-instance model file ("" = fall back to hash % pool)
    int model = 0;    // index into the model pool
    Mat4 world;       // T * R * S, built once at load
};

struct Scene {
    std::vector<SceneInstance> instances;
    Vec3 lo{1e30f, 1e30f, 1e30f};
    Vec3 hi{-1e30f, -1e30f, -1e30f};
    Vec3 centroid;
    Vec3 focus;              // centre of the densest clump (camera target)
    float focusExtent = 0.0f;
    float extentX = 0.0f; // horizontal extents, x/y
    float extentY = 0.0f;
    float extentZ = 0.0f; // vertical
    uint32_t distinctHashes = 0;
    uint32_t badInstances = 0;
    uint32_t identityRot = 0;
    uint32_t identityScale = 0;

    bool empty() const { return instances.empty(); }
};

// ---------------------------------------------------------------- reader

namespace scenejson {

inline const char* skipWs(const char* p, const char* e) {
    while (p < e && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n' || *p == ',')) ++p;
    return p;
}

inline bool readNumber(const char*& p, const char* e, float& out) {
    p = skipWs(p, e);
    if (p >= e) return false;
    char buf[64];
    size_t n = 0;
    while (p < e && n + 1 < sizeof(buf) &&
           (*p == '-' || *p == '+' || *p == '.' || *p == 'e' || *p == 'E' || (*p >= '0' && *p <= '9')))
        buf[n++] = *p++;
    if (!n) return false;
    buf[n] = 0;
    out = (float)atof(buf);
    return true;
}

inline bool readString(const char*& p, const char* e, std::string& out) {
    p = skipWs(p, e);
    if (p >= e || *p != '"') return false;
    ++p;
    out.clear();
    while (p < e && *p != '"') {
        if (*p == '\\' && p + 1 < e) ++p;
        out.push_back(*p++);
    }
    if (p < e) ++p;
    return true;
}

// Reads "key" then colon; returns true if the next member is that key.
inline bool readKey(const char*& p, const char* e, char* key, size_t cap) {
    p = skipWs(p, e);
    if (p >= e || *p != '"') return false;
    std::string s;
    if (!readString(p, e, s)) return false;
    snprintf(key, cap, "%s", s.c_str());
    p = skipWs(p, e);
    if (p < e && *p == ':') ++p;
    return true;
}

inline int countChar(const char* p, const char* e, char c) {
    int n = 0;
    for (; p < e; ++p)
        if (*p == c) ++n;
    return n;
}

} // namespace scenejson

// Parses the scene. `limit` keeps an evenly spread subset (0 = all).
// Returns false with `err` set on a hard error.
inline bool loadScene(const std::string& path, int limit, Scene& out, std::string& err) {
    FILE* f = nullptr;
    if (fopen_s(&f, path.c_str(), "rb") != 0 || !f) {
        err = "cannot open scene json";
        return false;
    }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (size <= 0) {
        fclose(f);
        err = "empty scene json";
        return false;
    }
    std::vector<char> buf((size_t)size + 1);
    size_t got = fread(buf.data(), 1, (size_t)size, f);
    fclose(f);
    buf[got] = 0;
    const char* e = buf.data() + got;

    const char* arr = strstr(buf.data(), "\"instances\"");
    if (!arr) {
        err = "no \"instances\" array";
        return false;
    }
    arr = strchr(arr, '[');
    if (!arr) {
        err = "\"instances\" is not an array";
        return false;
    }

    std::vector<SceneInstance> all;
    const char* p = arr + 1;
    while (p < e && *p != ']') {
        p = scenejson::skipWs(p, e);
        if (p >= e || *p == ']') break;
        if (*p != '{') {
            ++p;
            continue;
        }
        // Find this object's extent so a malformed member cannot run away.
        int depth = 0;
        const char* q = p;
        const char* objEnd = e;
        for (; q < e; ++q) {
            if (*q == '{') ++depth;
            else if (*q == '}') {
                if (--depth == 0) {
                    objEnd = q;
                    break;
                }
            }
        }

        SceneInstance in;
        char key[64];
        const char* m = p + 1;
        bool havePos = false;
        while (m < objEnd) {
            if (!scenejson::readKey(m, objEnd, key, sizeof(key))) {
                ++m;
                continue;
            }
            if (!strcmp(key, "pos") || !strcmp(key, "rot") || !strcmp(key, "scale")) {
                m = scenejson::skipWs(m, objEnd);
                if (m < objEnd && *m == '[') {
                    ++m;
                    float v[4] = {0, 0, 0, 1};
                    int n = 0;
                    while (m < objEnd && *m != ']' && n < 4) {
                        if (!scenejson::readNumber(m, objEnd, v[n])) {
                            ++m;
                            continue;
                        }
                        ++n;
                        m = scenejson::skipWs(m, objEnd);
                    }
                    if (!strcmp(key, "pos") && n >= 3) {
                        in.pos = Vec3(v[0], v[1], v[2]);
                        havePos = true;
                    } else if (!strcmp(key, "rot") && n >= 4) {
                        in.rot = Quat{v[0], v[1], v[2], v[3]};
                    } else if (!strcmp(key, "scale") && n >= 3) {
                        in.scl = Vec3(v[0], v[1], v[2]);
                    }
                }
                p = m; // `m` is only used for scanning members here
            } else if (!strcmp(key, "hash")) {
                std::string s;
                if (scenejson::readString(m, objEnd, s))
                    in.hash = (uint32_t)strtoul(s.c_str(), nullptr, 0);
                m = scenejson::skipWs(m, objEnd);
            } else if (!strcmp(key, "model")) {
                std::string s;
                if (scenejson::readString(m, objEnd, s)) in.modelPath = s;
                m = scenejson::skipWs(m, objEnd);
            } else {
                std::string s;
                if (!scenejson::readString(m, objEnd, s)) ++m;
            }
        }
        if (havePos) all.push_back(in);
        else ++out.badInstances;
        p = objEnd < e ? objEnd + 1 : e;
    }

    if (all.empty()) {
        err = "scene has no usable instance";
        return false;
    }

    // Optional even sub-sampling: keep spatial coverage rather than a prefix.
    if (limit > 0 && (size_t)limit < all.size()) {
        std::vector<SceneInstance> pick;
        pick.reserve((size_t)limit);
        double step = (double)all.size() / (double)limit;
        for (int i = 0; i < limit; ++i) {
            size_t idx = (size_t)(i * step);
            if (idx < all.size()) pick.push_back(all[idx]);
        }
        all.swap(pick);
    }

    // Quaternions may be in either order/convention; normalise and keep the
    // true values. Count how many are actually identity so the report can say
    // whether the quaternion path is exercised by the data or only by --spin.
    for (auto& in : all) {
        float l = std::sqrt(in.rot.x * in.rot.x + in.rot.y * in.rot.y + in.rot.z * in.rot.z +
                            in.rot.w * in.rot.w);
        if (l > 1e-6f) {
            in.rot.x /= l;
            in.rot.y /= l;
            in.rot.z /= l;
            in.rot.w /= l;
        } else {
            in.rot = Quat{};
        }
        if (std::fabs(in.rot.x) < 1e-6f && std::fabs(in.rot.y) < 1e-6f && std::fabs(in.rot.z) < 1e-6f)
            ++out.identityRot;
        if (std::fabs(in.scl.x - 1.0f) < 1e-6f && std::fabs(in.scl.y - 1.0f) < 1e-6f &&
            std::fabs(in.scl.z - 1.0f) < 1e-6f)
            ++out.identityScale;
        out.lo.x = in.pos.x < out.lo.x ? in.pos.x : out.lo.x;
        out.lo.y = in.pos.y < out.lo.y ? in.pos.y : out.lo.y;
        out.lo.z = in.pos.z < out.lo.z ? in.pos.z : out.lo.z;
        out.hi.x = in.pos.x > out.hi.x ? in.pos.x : out.hi.x;
        out.hi.y = in.pos.y > out.hi.y ? in.pos.y : out.hi.y;
        out.hi.z = in.pos.z > out.hi.z ? in.pos.z : out.hi.z;
    }
    out.centroid = (out.lo + out.hi) * 0.5f;
    out.extentX = out.hi.x - out.lo.x;
    out.extentY = out.hi.y - out.lo.y;
    out.extentZ = out.hi.z - out.lo.z;

    // The instance mass is not uniform, so the global centroid easily lands in
    // empty space. Use the centroid of the densest horizontal 100-unit cell as
    // the camera focus instead. (z is up in this data: the ground plane is x/y.)
    {
        const float binW = 100.0f;
        int nbx = (int)(out.extentX / binW) + 1;
        int nby = (int)(out.extentY / binW) + 1;
        std::vector<int> bins((size_t)nbx * nby, 0);
        auto cellOf = [&](const Vec3& p, int& bx, int& by) {
            bx = (int)((p.x - out.lo.x) / binW);
            by = (int)((p.y - out.lo.y) / binW);
            return bx >= 0 && bx < nbx && by >= 0 && by < nby;
        };
        int best = 0, bestCount = -1;
        for (auto& in : all) {
            int bx, by;
            if (!cellOf(in.pos, bx, by)) continue;
            int& c = bins[(size_t)by * nbx + bx];
            if (++c > bestCount) {
                bestCount = c;
                best = by * nbx + bx;
            }
        }
        if (bestCount > 0) {
            int bx = best % nbx, by = best / nbx;
            Vec3 sum;
            int n = 0;
            for (auto& in : all) {
                int cx, cy;
                if (!cellOf(in.pos, cx, cy)) continue;
                if (cx == bx && cy == by) {
                    sum = sum + in.pos;
                    ++n;
                }
            }
            out.focus = n ? sum * (1.0f / (float)n) : out.centroid;
            out.focusExtent = binW;
        } else {
            out.focus = out.centroid;
            out.focusExtent = std::max(out.extentX, out.extentY);
        }
    }

    std::vector<uint32_t> hashes;
    hashes.reserve(all.size());
    for (auto& in : all) hashes.push_back(in.hash);
    // Small, dependency-free distinct count.
    std::sort(hashes.begin(), hashes.end());
    out.distinctHashes = (uint32_t)(std::unique(hashes.begin(), hashes.end()) - hashes.begin());

    out.instances.swap(all);
    return true;
}

// ---------------------------------------------------------------- transforms

// Quaternion -> rotation matrix (column-major, as Mat4 everywhere else).
inline Mat4 quatToMat(const Quat& q) {
    float xx = q.x * q.x, yy = q.y * q.y, zz = q.z * q.z;
    float xy = q.x * q.y, xz = q.x * q.z, yz = q.y * q.z;
    float wx = q.w * q.x, wy = q.w * q.y, wz = q.w * q.z;
    Mat4 m;
    m.m[0] = 1.0f - 2.0f * (yy + zz);
    m.m[1] = 2.0f * (xy + wz);
    m.m[2] = 2.0f * (xz - wy);
    m.m[3] = 0.0f;
    m.m[4] = 2.0f * (xy - wz);
    m.m[5] = 1.0f - 2.0f * (xx + zz);
    m.m[6] = 2.0f * (yz + wx);
    m.m[7] = 0.0f;
    m.m[8] = 2.0f * (xz + wy);
    m.m[9] = 2.0f * (yz - wx);
    m.m[10] = 1.0f - 2.0f * (xx + yy);
    m.m[11] = 0.0f;
    m.m[12] = 0.0f;
    m.m[13] = 0.0f;
    m.m[14] = 0.0f;
    m.m[15] = 1.0f;
    return m;
}

// World matrix of one instance: T * R * S. `extra` uniformly scales the model
// on top of the instance's own scale (only used to make the overview legible).
inline Mat4 composeInstance(const SceneInstance& in, float extra) {
    Mat4 s = Mat4::identity();
    s.m[0] = in.scl.x * extra;
    s.m[5] = in.scl.y * extra;
    s.m[10] = in.scl.z * extra;
    Mat4 r = quatToMat(in.rot);
    Mat4 t = Mat4::translate(in.pos);
    return t * r * s;
}

inline float instanceRadius(const SceneInstance& in, float meshRadius, float extra) {
    float m = in.scl.x;
    if (in.scl.y > m) m = in.scl.y;
    if (in.scl.z > m) m = in.scl.z;
    return m * extra * meshRadius;
}

// ---------------------------------------------------------------- frustum

// Six planes of a view-projection matrix (Gribb/Hartmann), column-major m.
inline void frustumPlanes(const Mat4& vp, float pl[6][4]) {
    const float* m = vp.m;
    float rows[4][4];
    for (int i = 0; i < 4; ++i)
        for (int c = 0; c < 4; ++c) rows[i][c] = m[c * 4 + i];
    for (int c = 0; c < 4; ++c) {
        pl[0][c] = rows[3][c] + rows[0][c]; // left
        pl[1][c] = rows[3][c] - rows[0][c]; // right
        pl[2][c] = rows[3][c] + rows[1][c]; // bottom
        pl[3][c] = rows[3][c] - rows[1][c]; // top
        // Vulkan clip depth is 0..w: near plane is the z row itself.
        pl[4][c] = rows[2][c];              // near
        pl[5][c] = rows[3][c] - rows[2][c]; // far
    }
    // Normalise so the radius argument is in world units.
    for (int i = 0; i < 6; ++i) {
        float l = std::sqrt(pl[i][0] * pl[i][0] + pl[i][1] * pl[i][1] + pl[i][2] * pl[i][2]);
        if (l > 1e-9f)
            for (int c = 0; c < 4; ++c) pl[i][c] /= l;
    }
}

inline bool sphereVisible(const float pl[6][4], const Vec3& c, float r) {
    for (int i = 0; i < 6; ++i) {
        float d = pl[i][0] * c.x + pl[i][1] * c.y + pl[i][2] * c.z + pl[i][3];
        if (d < -r) return false;
    }
    return true;
}
