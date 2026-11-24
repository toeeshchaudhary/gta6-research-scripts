// pe_classify.cpp -- DLL classification into system / bundled / shim.
#include "pe_image.h"

#include <algorithm>
#include <cctype>
#include <unordered_map>
#include <unordered_set>

namespace peload {
namespace {

std::string Lower(std::string s) {
    for (auto& c : s) c = (char)std::tolower((unsigned char)c);
    return s;
}

// Basename only: import tables sometimes carry a path.
std::string BaseName(const std::string& s) {
    size_t p = s.find_last_of("\\/");
    return p == std::string::npos ? s : s.substr(p + 1);
}

// Names that are shims even if a lookalike exists in System32, because the
// Xbox/GDK build links against an ABI Windows does not ship.
const std::unordered_set<std::string>& ForcedShims() {
    static const std::unordered_set<std::string> s = {
        // Xbox memory manager (WDDM/GDK system module, not in System32)
        "xmem.dll", "xmem",
        // Xbox D3D12 flavour (stock Windows has d3d12.dll, not d3d12_xs.dll)
        "d3d12_xs.dll", "d3d12_xs",
        // GDK audio
        "xaudio2_9.dll", "xaudio2_8.dll", "xaudio2_7.dll",
        // Xbox services / GDK runtime
        "xstore.dll", "xgame.dll", "xuser.dll", "xsystem.dll", "gamechat.dll",
        "gameloop.dll", "xgameruntime.dll", "xsts.dll", "xnet.dll",
        "xboxbvhbuilder.dll", "xcurl.dll",
        // GDK broker-ish
        "xbcp.dll", "xcrypto.dll",
    };
    return s;
}

bool ExistsInSystem32(const std::string& base) {
    static std::unordered_map<std::string, bool> cache;
    auto it = cache.find(base);
    if (it != cache.end()) return it->second;

    wchar_t sys[MAX_PATH] = {};
    UINT n = ::GetSystemDirectoryW(sys, MAX_PATH);
    if (!n || n >= MAX_PATH) { cache[base] = false; return false; }

    std::wstring full(sys);
    full += L"\\";
    full += Widen(base);
    DWORD attr = ::GetFileAttributesW(full.c_str());
    bool ok = (attr != INVALID_FILE_ATTRIBUTES) && !(attr & FILE_ATTRIBUTE_DIRECTORY);
    if (!ok) {
        // Also accept Wow6432Node-style or SysWOW64 presence for completeness.
        wchar_t syswow[MAX_PATH] = {};
        if (::GetSystemWow64DirectoryW(syswow, MAX_PATH)) {
            std::wstring f2(syswow); f2 += L"\\"; f2 += Widen(base);
            DWORD a2 = ::GetFileAttributesW(f2.c_str());
            ok = (a2 != INVALID_FILE_ATTRIBUTES) && !(a2 & FILE_ATTRIBUTE_DIRECTORY);
        }
    }
    cache[base] = ok;
    return ok;
}

bool ExistsInDir(const std::wstring& dir, const std::string& base) {
    if (dir.empty() || base.empty()) return false;
    std::wstring full = dir;
    if (full.back() != L'\\' && full.back() != L'/') full += L'\\';
    full += Widen(base);
    DWORD attr = ::GetFileAttributesW(full.c_str());
    return attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY);
}

bool IsApiSetName(const std::string& lower) {
    return lower.rfind("api-ms-win-", 0) == 0 ||
           lower.rfind("ext-ms-win-", 0) == 0 ||
           lower.rfind("api-ms-onecore-", 0) == 0;
}

} // namespace

DllClass ClassifyDll(const std::string& dll, const std::wstring& gameDir) {
    std::string lower = Lower(BaseName(dll));
    if (lower.empty()) return DllClass::Shim;

    // 1. Bundled: literally shipped in the game folder (wins over everything:
    //    the game's own CRT copies must be used, not System32's).
    if (ExistsInDir(gameDir, lower)) return DllClass::Bundled;

    // 2. API sets are always resolvable through the api-set schema.
    if (IsApiSetName(lower)) return DllClass::System;

    // 3. Known Xbox/GDK-only modules.
    if (ForcedShims().count(lower)) return DllClass::Shim;

    // 4. Present in System32 (or SysWOW64) => system.
    if (ExistsInSystem32(lower)) return DllClass::System;

    // 5. Everything else is presumed an Xbox-side module.
    return DllClass::Shim;
}

} // namespace peload
