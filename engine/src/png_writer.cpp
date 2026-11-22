#include "png_writer.h"

#include <cstring>

namespace {

uint32_t kCrcTable[256];
bool kCrcReady = false;

void initCrc() {
    for (uint32_t n = 0; n < 256; ++n) {
        uint32_t c = n;
        for (int k = 0; k < 8; ++k) c = (c & 1) ? 0xEDB88320u ^ (c >> 1) : c >> 1;
        kCrcTable[n] = c;
    }
    kCrcReady = true;
}

uint32_t crc32Update(uint32_t crc, const uint8_t* data, size_t len) {
    if (!kCrcReady) initCrc();
    uint32_t c = crc ^ 0xFFFFFFFFu;
    for (size_t i = 0; i < len; ++i) c = kCrcTable[(c ^ data[i]) & 0xFF] ^ (c >> 8);
    return c ^ 0xFFFFFFFFu;
}

void putBE32(std::vector<uint8_t>& v, uint32_t x) {
    v.push_back((uint8_t)(x >> 24));
    v.push_back((uint8_t)(x >> 16));
    v.push_back((uint8_t)(x >> 8));
    v.push_back((uint8_t)x);
}

void chunk(FILE* f, const char* type, const std::vector<uint8_t>& data) {
    std::vector<uint8_t> len;
    putBE32(len, (uint32_t)data.size());
    fwrite(len.data(), 1, 4, f);
    fwrite(type, 1, 4, f);
    if (!data.empty()) fwrite(data.data(), 1, data.size(), f);
    uint32_t crc = crc32Update(0, (const uint8_t*)type, 4);
    if (!data.empty()) crc = crc32Update(crc, data.data(), data.size());
    std::vector<uint8_t> tail;
    putBE32(tail, crc);
    fwrite(tail.data(), 1, 4, f);
}

} // namespace

bool writePngRgb(const std::string& path, const uint8_t* rgb, uint32_t width, uint32_t height) {
    FILE* f = nullptr;
    if (fopen_s(&f, path.c_str(), "wb") != 0 || !f) return false;

    static const uint8_t sig[8] = {0x89, 'P', 'N', 'G', '\r', '\n', 0x1A, '\n'};
    fwrite(sig, 1, 8, f);

    std::vector<uint8_t> ihdr;
    putBE32(ihdr, width);
    putBE32(ihdr, height);
    ihdr.push_back(8); // bit depth
    ihdr.push_back(2); // color type: truecolor RGB
    ihdr.push_back(0); // deflate
    ihdr.push_back(0); // adaptive filtering
    ihdr.push_back(0); // no interlace
    chunk(f, "IHDR", ihdr);

    // Raw scanlines with filter type 0.
    std::vector<uint8_t> raw;
    raw.reserve((size_t)(width * 3 + 1) * height);
    for (uint32_t y = 0; y < height; ++y) {
        raw.push_back(0);
        raw.insert(raw.end(), rgb + (size_t)y * width * 3, rgb + (size_t)(y + 1) * width * 3);
    }

    // zlib stream: header, stored deflate blocks, adler32.
    std::vector<uint8_t> z;
    z.reserve(raw.size() + raw.size() / 65535 * 5 + 16);
    z.push_back(0x78);
    z.push_back(0x01);
    size_t off = 0;
    while (off < raw.size()) {
        size_t n = raw.size() - off;
        if (n > 65535) n = 65535;
        bool last = off + n >= raw.size();
        z.push_back(last ? 1 : 0);
        z.push_back((uint8_t)(n & 0xFF));
        z.push_back((uint8_t)(n >> 8));
        z.push_back((uint8_t)(~n & 0xFF));
        z.push_back((uint8_t)((~n >> 8) & 0xFF));
        z.insert(z.end(), raw.begin() + off, raw.begin() + off + n);
        off += n;
    }
    uint32_t a = 1, b = 0;
    for (size_t i = 0; i < raw.size(); ++i) {
        a = (a + raw[i]) % 65521;
        b = (b + a) % 65521;
    }
    putBE32(z, (b << 16) | a);
    chunk(f, "IDAT", z);
    chunk(f, "IEND", std::vector<uint8_t>());
    fclose(f);
    return true;
}
