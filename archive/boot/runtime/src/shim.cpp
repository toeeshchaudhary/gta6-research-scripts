// shim.cpp -- hand-written shim tables for Xbox/GDK-only imports, plus
// runtime-generated logging miss-thunks.
//
// A real Xbox host runtime would implement these against the GDK. Here each
// entry is either a thin real implementation (memory, forwarding, HRESULT
// stubs) or an auto-generated thunk that logs the miss and returns a chosen
// value so a mapped image can still be exercised.
#include "shim.h"

#include <atomic>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <unordered_map>

namespace peload {
namespace {

// ---------------------------------------------------------------------------
// Real handlers (deliberately tiny; enough to let mapped code proceed).
// ---------------------------------------------------------------------------

extern "C" {

// --- xmem.dll : Xbox memory manager ---------------------------------------
void* XMemAlloc(SIZE_T size, DWORD /*attributes*/) {
    return ::HeapAlloc(::GetProcessHeap(), HEAP_ZERO_MEMORY, size ? size : 1);
}
void* XMemAllocDefault(SIZE_T size, DWORD attributes) { return XMemAlloc(size, attributes); }
void  XMemFree(void* p, DWORD /*attributes*/) {
    if (p) ::HeapFree(::GetProcessHeap(), 0, p);
}
void  XMemFreeDefault(void* p, DWORD attributes) { XMemFree(p, attributes); }
void* XMemGetBaseAddress(DWORD /*attributes*/) { return (void*)0x10000000ull; }
SIZE_T XMemGetSize(const void* /*p*/) { return 0; }

// --- xgame / xsystem : identity -------------------------------------------
long XGameGetXboxTitleId(uint32_t* id) { if (id) *id = 0; return 0; }
long XSystemGetConsoleId(char* buf, size_t* len) { if (len) *len = 0; if (buf && len && *len) buf[0] = 0; return 0; }

// --- xuser -----------------------------------------------------------------
long XUserGetId(void* /*handle*/, uint64_t* id) { if (id) *id = 0; return 0; }

// --- d3d12_xs : forward the device-creation entry to real d3d12.dll --------
using PFN_D3D12CreateDevice = long(__stdcall*)(void*, unsigned, const GUID&, void**);
long D3D12CreateDevice(void* adapter, unsigned min_feature_level, const GUID& riid, void** device) {
    HMODULE real = ::GetModuleHandleW(L"d3d12.dll");
    if (!real) real = ::LoadLibraryW(L"d3d12.dll");
    if (!real) return (long)0x8007007E; // HRESULT_FROM_WIN32(ERROR_MOD_NOT_FOUND)
    auto fn = (PFN_D3D12CreateDevice)::GetProcAddress(real, "D3D12CreateDevice");
    if (!fn) return (long)0x80004001;   // E_NOTIMPL
    return fn(adapter, min_feature_level, riid, device);
}

} // extern "C"

struct Table {
    const char* fn;
    void* addr;
};

#define REAL(f) { #f, (void*)&f }

const std::unordered_map<std::string, std::vector<Table>>& Tables() {
    static const std::unordered_map<std::string, std::vector<Table>> t = {
        {"xmem.dll", {REAL(XMemAlloc), REAL(XMemAllocDefault), REAL(XMemFree),
                      REAL(XMemFreeDefault), REAL(XMemGetBaseAddress), REAL(XMemGetSize)}},
        {"xgame.dll", {REAL(XGameGetXboxTitleId)}},
        {"xsystem.dll", {REAL(XSystemGetConsoleId)}},
        {"xuser.dll", {REAL(XUserGetId)}},
        {"d3d12_xs.dll", {REAL(D3D12CreateDevice)}},
    };
    return t;
}

std::string Lower(const char* s) {
    std::string r(s ? s : "");
    for (auto& c : r) c = (char)::tolower((unsigned char)c);
    return r;
}

// ---------------------------------------------------------------------------
// Miss-thunk machinery
// ---------------------------------------------------------------------------

std::mutex                         g_mu;
FILE*                              g_log = nullptr;
std::vector<ShimMiss>              g_misses;
std::atomic<uint64_t>              g_miss_calls{0};
std::vector<uint8_t*>              g_pages;
uint8_t*                           g_bump = nullptr;
size_t                             g_bump_left = 0;

void* ArenaAlloc(size_t n, size_t align) {
    std::lock_guard<std::mutex> lk(g_mu);
    if (g_bump_left < n) {
        auto* p = (uint8_t*)::VirtualAlloc(nullptr, 65536, MEM_COMMIT | MEM_RESERVE, PAGE_EXECUTE_READWRITE);
        if (!p) return nullptr;
        g_pages.push_back(p);
        g_bump = p;
        g_bump_left = 65536;
    }
    uintptr_t cur = (uintptr_t)g_bump;
    uintptr_t aligned = (cur + align - 1) & ~(uintptr_t)(align - 1);
    size_t pad = (size_t)(aligned - cur);
    if (g_bump_left < n + pad) {
        // Waste the tail; grab a fresh page on the next call.
        g_bump_left = 0;
        return ArenaAlloc(n, align);
    }
    g_bump += pad + n;
    g_bump_left -= pad + n;
    return (void*)aligned;
}

extern "C" USHORT __stdcall RtlCaptureStackBackTrace(ULONG, ULONG, PVOID*, PULONG);

extern "C" void ShimMissHit(const char* dll, const char* fn) {
    g_miss_calls.fetch_add(1, std::memory_order_relaxed);
    FILE* f = g_log ? g_log : stderr;
    ::fprintf(f, "SHIM-MISS %s!%s\n", dll, fn);
    // GTA6_SHIM_TRACE: report the image-side return address. The miss thunk is
    // `sub rsp,0x28; ...; call ShimMissHit; add rsp,0x28; ret`, so the caller's
    // return address sits 0x30 above the current return address slot.
    if (::getenv("GTA6_SHIM_TRACE")) {
        auto* ra = (uintptr_t*)_AddressOfReturnAddress();
        ::fprintf(f, "  MISS-RET thunk=0x%llX caller=0x%llX\n",
                  (unsigned long long)ra[0], (unsigned long long)ra[6]);
        void* frames[24] = {};
        USHORT n = RtlCaptureStackBackTrace(0, 24, frames, nullptr);
        for (USHORT i = 0; i < n; ++i)
            ::fprintf(f, "  CALLSTACK [%u] %p\n", i, frames[i]);
    }
    ::fflush(f);
}

} // namespace

void ShimSetLogFile(FILE* f) { g_log = f; }

const std::vector<ShimMiss>& ShimMisses() { return g_misses; }
size_t ShimMissCallCount() { return (size_t)g_miss_calls.load(); }

bool ShimHasTable(const char* dll) {
    return Tables().count(Lower(dll)) != 0;
}

void* ShimLookup(const char* dll, const char* fn) {
    // GTA6_USE_DLLS: prefer the real substitute DLL on the search path over the
    // built-in mini implementations. This is what lets the surface live in
    // .\work\shims2\bin and be exercised by the mapped image.
    static int useDlls = -1;
    if (useDlls < 0) useDlls = ::getenv("GTA6_USE_DLLS") ? 1 : 0;
    if (useDlls) {
        HMODULE h = ::GetModuleHandleA(dll);
        if (!h) h = ::LoadLibraryA(dll);
        if (h) {
            void* p = nullptr;
            if (fn && fn[0] == '#')
                p = (void*)::GetProcAddress(h, MAKEINTRESOURCEA((WORD)::strtoul(fn + 1, nullptr, 10)));
            else
                p = (void*)::GetProcAddress(h, fn);
            if (p) return p;
        }
    }

    auto it = Tables().find(Lower(dll));
    if (it == Tables().end()) return nullptr;
    for (const auto& t : it->second)
        if (::strcmp(t.fn, fn) == 0) return t.addr;
    return nullptr;
}

// Emit: sub rsp,0x28 ; mov rcx,name ; mov edx,idx ; mov rax,handler ;
//       call rax ; add rsp,0x28 ; mov eax,retval ; xorps xmm0,xmm0 ; ret
void* ShimMakeMissThunk(const char* dll, const char* fn, uintptr_t retval) {
    {
        std::lock_guard<std::mutex> lk(g_mu);
        g_misses.push_back({dll ? dll : "?", fn ? fn : "?"});
    }
    char* dll_copy = _strdup(dll ? dll : "?");
    char* fn_copy  = _strdup(fn ? fn : "?");
    if (!dll_copy || !fn_copy) return nullptr;

    uint8_t* code = (uint8_t*)ArenaAlloc(64, 16);
    if (!code) return nullptr;

    size_t i = 0;
    using fn_t = void (*)(const char*, const char*);
    uintptr_t handler = (uintptr_t)(fn_t)&ShimMissHit;

    auto emit = [&](uint8_t b) { code[i++] = b; };

    // sub rsp, 0x28
    emit(0x48); emit(0x83); emit(0xEC); emit(0x28);
    // mov rcx, imm64
    emit(0x48); emit(0xB9);
    uintptr_t n1 = (uintptr_t)dll_copy;
    ::memcpy(code + i, &n1, 8); i += 8;
    // mov rdx, imm64  (function name, 2nd argument)
    emit(0x48); emit(0xBA);
    uintptr_t n2 = (uintptr_t)fn_copy;
    ::memcpy(code + i, &n2, 8); i += 8;
    // mov rax, imm64
    emit(0x48); emit(0xB8);
    ::memcpy(code + i, &handler, 8); i += 8;
    // call rax
    emit(0xFF); emit(0xD0);
    // add rsp, 0x28
    emit(0x48); emit(0x83); emit(0xC4); emit(0x28);
    // mov eax, imm32
    emit(0xB8);
    uint32_t rv = (uint32_t)retval;
    ::memcpy(code + i, &rv, 4); i += 4;
    // xorps xmm0, xmm0  (zero the float return register)
    emit(0x0F); emit(0x57); emit(0xC0);
    // ret
    emit(0xC3);

    ::FlushInstructionCache(::GetCurrentProcess(), code, i);
    return code;
}

} // namespace peload
