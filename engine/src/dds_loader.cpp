#include "dds_loader.h"

#include <cstdio>
#include <cstring>

namespace {

struct FmtInfo {
    uint32_t dxgi;
    VkFormat vk;
    uint32_t blockBytes; // bytes per 4x4 block, or bytes per pixel for linear formats
    bool blockCompressed;
    bool srgb;
};

const FmtInfo kFormats[] = {
    {71, VK_FORMAT_BC1_RGB_UNORM_BLOCK, 8, true, false},   // BC1_UNORM
    {72, VK_FORMAT_BC1_RGB_SRGB_BLOCK, 8, true, true},     // BC1_UNORM_SRGB
    {77, VK_FORMAT_BC3_UNORM_BLOCK, 16, true, false},      // BC3_UNORM
    {78, VK_FORMAT_BC3_SRGB_BLOCK, 16, true, true},        // BC3_UNORM_SRGB
    {80, VK_FORMAT_BC4_UNORM_BLOCK, 8, true, false},       // BC4_UNORM
    {83, VK_FORMAT_BC5_UNORM_BLOCK, 16, true, false},      // BC5_UNORM
    {95, VK_FORMAT_BC6H_UFLOAT_BLOCK, 16, true, false},    // BC6H_UF16
    {98, VK_FORMAT_BC7_UNORM_BLOCK, 16, true, false},      // BC7_UNORM
    {99, VK_FORMAT_BC7_SRGB_BLOCK, 16, true, true},        // BC7_UNORM_SRGB
    {28, VK_FORMAT_R8G8B8A8_UNORM, 4, false, false},       // R8G8B8A8_UNORM
    {29, VK_FORMAT_R8G8B8A8_SRGB, 4, false, true},         // R8G8B8A8_UNORM_SRGB
    {87, VK_FORMAT_B8G8R8A8_UNORM, 4, false, false},       // B8G8R8A8_UNORM
    {91, VK_FORMAT_B8G8R8A8_SRGB, 4, false, true},         // B8G8R8A8_UNORM_SRGB
    {10, VK_FORMAT_R16G16B16A16_SFLOAT, 8, false, false},  // R16G16B16A16_FLOAT
    {2, VK_FORMAT_R32G32B32A32_SFLOAT, 16, false, false},  // R32G32B32A32_FLOAT
};

const FmtInfo* find(uint32_t dxgi) {
    for (const auto& f : kFormats)
        if (f.dxgi == dxgi) return &f;
    return nullptr;
}

} // namespace

VkFormat dxgiToVkFormat(uint32_t dxgi) {
    const FmtInfo* f = find(dxgi);
    return f ? f->vk : VK_FORMAT_UNDEFINED;
}

bool loadDds(const std::string& path, DdsImage& out, std::string& err) {
    FILE* f = nullptr;
    if (fopen_s(&f, path.c_str(), "rb") != 0 || !f) {
        err = "cannot open DDS";
        return false;
    }
    uint8_t hdr[148];
    if (fread(hdr, 1, sizeof(hdr), f) != sizeof(hdr)) {
        fclose(f);
        err = "short DDS header";
        return false;
    }
    if (memcmp(hdr, "DDS ", 4) != 0) {
        fclose(f);
        err = "bad DDS magic";
        return false;
    }
    uint32_t hdrSize;
    memcpy(&hdrSize, hdr + 4, 4);
    if (hdrSize != 124) {
        fclose(f);
        err = "bad DDS header size";
        return false;
    }
    uint32_t height, width;
    memcpy(&height, hdr + 12, 4);
    memcpy(&width, hdr + 16, 4);
    if (memcmp(hdr + 84, "DX10", 4) != 0) {
        fclose(f);
        err = "not a DX10-header DDS";
        return false;
    }
    uint32_t dxgi, dim, misc, arraySize;
    memcpy(&dxgi, hdr + 128, 4);
    memcpy(&dim, hdr + 132, 4);
    memcpy(&misc, hdr + 136, 4);
    memcpy(&arraySize, hdr + 140, 4);
    long mips = 0;
    memcpy(&mips, hdr + 28, 4); // dwMipMapCount
    if (mips < 1) mips = 1;

    out = DdsImage{};
    out.dxgiFormat = dxgi;
    const FmtInfo* fi = find(dxgi);
    if (!fi) {
        fclose(f);
        err = "unsupported DXGI format " + std::to_string(dxgi);
        return false;
    }
    if ((dim != 3 && dim != 0) || misc != 0 || arraySize > 1) {
        fclose(f);
        err = "only 2D single-layer textures supported";
        return false;
    }
    if (width == 0 || height == 0) {
        fclose(f);
        err = "zero extent";
        return false;
    }
    out.width = width;
    out.height = height;
    out.format = fi->vk;
    out.srgb = fi->srgb;

    uint32_t levels = 0;
    for (uint32_t w = width, h = height; levels < (uint32_t)mips; ++levels) {
        uint32_t bw = fi->blockCompressed ? (w + 3) / 4 : w;
        uint32_t bh = fi->blockCompressed ? (h + 3) / 4 : h;
        size_t bytes = (size_t)bw * bh * fi->blockBytes;
        std::vector<uint8_t> mip(bytes);
        if (fread(mip.data(), 1, bytes, f) != bytes) {
            fclose(f);
            err = "truncated mip level " + std::to_string(levels);
            return false;
        }
        out.mips.push_back(std::move(mip));
        out.totalBytes += bytes;
        w = w > 1 ? w / 2 : 1;
        h = h > 1 ? h / 2 : 1;
    }
    out.mipLevels = levels;
    fclose(f);
    return true;
}
