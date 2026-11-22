#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include "math3d.h"

struct MeshVertex {
    Vec3 pos; // object space; true game units unless the loader was asked to normalise
    Vec3 nrm; // smooth normal, computed from triangle area-weighted sums
    float u, v;
};

struct Mesh {
    std::vector<MeshVertex> vertices;
    std::vector<uint32_t> indices;
    uint32_t srcPositions = 0;
    uint32_t srcUvs = 0;
    uint32_t srcFaces = 0;
    uint32_t degenerate = 0;
    // Bounds of the stored vertices, in the same space they were stored in.
    Vec3 bmin{0, 0, 0}, bmax{0, 0, 0};
    float radius = 1.0f; // half the bbox diagonal
    float sizeX() const { return bmax.x - bmin.x; }
    float sizeY() const { return bmax.y - bmin.y; }
    float sizeZ() const { return bmax.z - bmin.z; }

    uint32_t triangleCount() const { return (uint32_t)(indices.size() / 3); }
};

// Loads an OBJ with v / vt / f v/vt indices, de-duplicates (position,uv) pairs,
// fan-triangulates polygons and computes smooth normals.
//
// normalize = true reproduces the old M1-M3 behaviour: every model is cencred
// and rescaled to a unit sphere, which throws the true size away. normalize =
// false keeps the export's own units (metres), which is what a scene of real
// buildings needs.
//
// ground = true translates the model so its lowest point sits at local z = 0.
// The exports are chunk geometry whose vertical origin is the chunk's mid
// height, not its base, so without this buildings half-sink into the ground.
bool loadObj(const std::string& path, Mesh& out, std::string& err, bool normalize = true,
             bool ground = false);
