#pragma once
#include <cstdint>
#include <string>
#include <vector>
#include <vulkan/vulkan.h>

struct DdsImage {
    uint32_t width = 0;
    uint32_t height = 0;
    uint32_t mipLevels = 0;
    VkFormat format = VK_FORMAT_UNDEFINED;
    bool srgb = false;
    uint32_t dxgiFormat = 0;
    std::vector<std::vector<uint8_t>> mips; // raw blocks per mip, tightly packed
    size_t totalBytes = 0;
};

// Maps a DXGI format to the VkFormat used for upload. Returns VK_FORMAT_UNDEFINED
// for formats this build does not support, so the caller can count them.
VkFormat dxgiToVkFormat(uint32_t dxgi);

// Parses a DX10-header DDS produced by rpf9dump. Compressed blocks are kept as-is.
bool loadDds(const std::string& path, DdsImage& out, std::string& err);
