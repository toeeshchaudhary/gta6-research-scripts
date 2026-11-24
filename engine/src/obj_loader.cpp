#include "obj_loader.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <unordered_map>

namespace {

struct Key {
    uint32_t p, u;
    bool operator==(const Key& o) const { return p == o.p && u == o.u; }
};
struct KeyHash {
    size_t operator()(const Key& k) const {
        return (size_t)k.p * 1000003ull ^ ((size_t)k.u + 0x9e3779b9ull + (k.p << 6));
    }
};

inline void splitToken(const char* tok, const char* end, long& vi, long& ti) {
    vi = 0; ti = 0;
    const char* slash = (const char*)memchr(tok, '/', (size_t)(end - tok));
    const char* vEnd = slash ? slash : end;
    vi = strtol(tok, nullptr, 10);
    if (slash) {
        const char* t = slash + 1;
        const char* tEnd = (const char*)memchr(t, '/', (size_t)(end - t));
        if (!tEnd) tEnd = end;
        if (tEnd > t) ti = strtol(t, nullptr, 10);
    }
}

} // namespace

bool loadObj(const std::string& path, Mesh& out, std::string& err, bool normalize, bool ground) {
    FILE* f = nullptr;
    if (fopen_s(&f, path.c_str(), "rb") != 0 || !f) {
        err = "cannot open OBJ";
        return false;
    }
    fseek(f, 0, SEEK_END);
    long size = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (size <= 0) {
        fclose(f);
        err = "empty OBJ";
        return false;
    }
    std::vector<char> buf((size_t)size + 1);
    size_t got = fread(buf.data(), 1, (size_t)size, f);
    fclose(f);
    buf[got] = 0;

    std::vector<Vec3> positions;
    std::vector<float> uvs; // 2 floats per entry
    positions.reserve(65536);
    uvs.reserve(65536);
    std::unordered_map<Key, uint32_t, KeyHash> vmap;
    out.vertices.clear();
    out.indices.clear();
    vmap.reserve(131072);

    const char* p = buf.data();
    const char* endBuf = buf.data() + got;
    uint32_t degenerate = 0;
    uint32_t skippedFaces = 0;
    long faceVerts[64];

    while (p < endBuf) {
        const char* eol = (const char*)memchr(p, '\n', (size_t)(endBuf - p));
        if (!eol) eol = endBuf;
        const char* lineEnd = eol;
        if (lineEnd > p && lineEnd[-1] == '\r') --lineEnd;
        if (lineEnd - p > 1) {
            if (p[0] == 'v' && p[1] == ' ') {
                const char* q = p + 2;
                float x = strtof(q, (char**)&q);
                float y = strtof(q, (char**)&q);
                float z = strtof(q, (char**)&q);
                positions.push_back(Vec3(x, y, z));
            } else if (p[0] == 'v' && p[1] == 't' && p[2] == ' ') {
                const char* q = p + 3;
                float u = strtof(q, (char**)&q);
                float v = strtof(q, (char**)&q);
                uvs.push_back(u);
                uvs.push_back(v);
            } else if (p[0] == 'f' && p[1] == ' ') {
                const char* q = p + 2;
                long n = 0;
                while (q < lineEnd && n < 64) {
                    while (q < lineEnd && (*q == ' ' || *q == '\t')) ++q;
                    if (q >= lineEnd) break;
                    const char* tok = q;
                    while (q < lineEnd && *q != ' ' && *q != '\t') ++q;
                    long vi = 0, ti = 0;
                    splitToken(tok, q, vi, ti);
                    long np = (long)positions.size();
                    long nt = (long)(uvs.size() / 2);
                    if (vi < 0) vi = np + vi + 1;
                    if (ti < 0) ti = nt + ti + 1;
                    if (vi < 1 || vi > np) { ++skippedFaces; n = 0; break; }
                    if (ti < 1 || ti > nt) ti = 0;
                    Key key{(uint32_t)vi, (uint32_t)(ti ? ti : 0)};
                    auto it = vmap.find(key);
                    uint32_t idx;
                    if (it == vmap.end()) {
                        MeshVertex mv;
                        mv.pos = positions[(size_t)vi - 1];
                        if (ti) {
                            mv.u = uvs[(size_t)(ti - 1) * 2];
                            mv.v = uvs[(size_t)(ti - 1) * 2 + 1];
                        } else {
                            mv.u = mv.v = 0.0f;
                        }
                        mv.nrm = Vec3(0, 0, 0);
                        idx = (uint32_t)out.vertices.size();
                        out.vertices.push_back(mv);
                        vmap.emplace(key, idx);
                    } else {
                        idx = it->second;
                    }
                    faceVerts[n++] = (long)idx;
                }
                for (long i = 1; i + 1 < n; ++i) {
                    uint32_t a = (uint32_t)faceVerts[0];
                    uint32_t b = (uint32_t)faceVerts[i];
                    uint32_t c = (uint32_t)faceVerts[i + 1];
                    if (a == b || b == c || a == c) { ++degenerate; continue; }
                    out.indices.push_back(a);
                    out.indices.push_back(b);
                    out.indices.push_back(c);
                }
            }
        }
        p = eol + 1;
    }

    out.srcPositions = (uint32_t)positions.size();
    out.srcUvs = (uint32_t)(uvs.size() / 2);
    out.srcFaces = (uint32_t)(out.indices.size() / 3);
    out.degenerate = degenerate;
    if (out.vertices.empty() || out.indices.empty()) {
        err = "no usable triangles";
        return false;
    }

    // Area-weighted smooth normals.
    for (size_t i = 0; i + 2 < out.indices.size(); i += 3) {
        uint32_t a = out.indices[i], b = out.indices[i + 1], c = out.indices[i + 2];
        const Vec3& pa = out.vertices[a].pos;
        const Vec3& pb = out.vertices[b].pos;
        const Vec3& pc = out.vertices[c].pos;
        Vec3 n = (pb - pa).cross(pc - pa); // length proportional to 2 * area
        out.vertices[a].nrm = out.vertices[a].nrm + n;
        out.vertices[b].nrm = out.vertices[b].nrm + n;
        out.vertices[c].nrm = out.vertices[c].nrm + n;
    }

    // Bounds of what was actually parsed.
    Vec3 lo(1e30f, 1e30f, 1e30f), hi(-1e30f, -1e30f, -1e30f);
    for (const auto& v : out.vertices) {
        lo.x = v.pos.x < lo.x ? v.pos.x : lo.x;
        lo.y = v.pos.y < lo.y ? v.pos.y : lo.y;
        lo.z = v.pos.z < lo.z ? v.pos.z : lo.z;
        hi.x = v.pos.x > hi.x ? v.pos.x : hi.x;
        hi.y = v.pos.y > hi.y ? v.pos.y : hi.y;
        hi.z = v.pos.z > hi.z ? v.pos.z : hi.z;
    }

    if (ground) {
        // Sit the model on z = 0 (see the header: the export origin is mid height).
        const float dz = lo.z;
        for (auto& v : out.vertices) v.pos.z -= dz;
        hi.z -= dz;
        lo.z = 0.0f;
    }

    if (normalize) {
        // Old behaviour: fit into a unit sphere so camera framing is model independent.
        Vec3 center = (lo + hi) * 0.5f;
        float radius = 0.0f;
        for (const auto& v : out.vertices)
            radius = (v.pos - center).length() > radius ? (v.pos - center).length() : radius;
        if (radius <= 1e-9f) radius = 1.0f;
        float inv = 1.0f / radius;
        for (auto& v : out.vertices) v.pos = (v.pos - center) * inv;
        lo = Vec3(-1, -1, -1);
        hi = Vec3(1, 1, 1);
        out.radius = 1.0f;
    } else {
        out.radius = 0.5f * std::sqrt((hi.x - lo.x) * (hi.x - lo.x) + (hi.y - lo.y) * (hi.y - lo.y) +
                                      (hi.z - lo.z) * (hi.z - lo.z));
        if (!(out.radius > 1e-6f)) out.radius = 1e-3f;
    }
    out.bmin = lo;
    out.bmax = hi;
    for (auto& v : out.vertices) {
        v.nrm = v.nrm.normalize();
        if (v.nrm.length() < 0.5f) v.nrm = Vec3(0, 1, 0);
    }
    (void)skippedFaces;
    return true;
}
