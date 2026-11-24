#pragma once
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

// Minimal PNG writer: 8-bit RGB, no interlacing, single IDAT using stored
// (uncompressed) deflate blocks. Enough to persist a frame with no dependencies.
bool writePngRgb(const std::string& path, const uint8_t* rgb, uint32_t width, uint32_t height);
