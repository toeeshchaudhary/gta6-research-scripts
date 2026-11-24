/* xmem.c -- substitute xmem.dll : 12 exported GDK memory entry points.
 *
 * Behaviour: real pages via VirtualAlloc / VirtualQuery, exactly like the
 * original 4-function proof stub in ..\..\..\src\xmem.c whose verified free
 * heuristics are reused here. Every non-trivial entry logs its raw register
 * arguments once so the MEM_ATTR_* bitfield and the page-mapping ABI can be
 * learned from a live run instead of assumed.
 *
 * XMemVirtualQuery / XMemGetBaseAddress / XMemGetSize are kept as extras: a
 * bundled importer (XboxBvhBuilder.dll) needs XMemVirtualQuery.
 */
#include "shims2.h"

#include <psapi.h>
#pragma comment(lib, "psapi.lib")

static volatile LONG64 g_attrSeen[64];
static volatile LONG  g_attrSeenCount = 0;
static volatile LONG64 g_allocCount = 0;
static volatile LONG64 g_freeCount = 0;

static void s2_record_attr(uint64_t attributes)
{
    LONG slot = InterlockedIncrement(&g_attrSeenCount) - 1;
    if (slot >= 0 && slot < 64) g_attrSeen[slot] = (LONG64)attributes;
}

/* ---- allocation ---------------------------------------------------------- */

static void* s2_alloc(size_t size, uint64_t attributes)
{
    s2_record_attr(attributes);
    InterlockedIncrement64(&g_allocCount);
    if (size == 0) size = 1;                 /* GDK-legal: unique & freeable */
    if (size > (size_t)0x00007FFFFFFF0000ull) {
        SetLastError(ERROR_NOT_ENOUGH_MEMORY);
        return NULL;
    }
    /* 64 KiB granularity satisfies every GDK alignment promise. */
    return VirtualAlloc(NULL, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
}

void* XMemAlloc(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xmem.dll!XMemAlloc");
    (void)c; (void)d;
    return s2_alloc((size_t)a, (uint64_t)b);
}

void* XMemAllocDefault(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xmem.dll!XMemAllocDefault");
    (void)c; (void)d;
    return s2_alloc((size_t)a, (uint64_t)b);
}

/* Observed ABI (RVA 0x1E1CFEA of the image, first call at startup):
 *   rcx = hProcess-ish (0), rdx = size, r8d = 0x20402000, r9d = 0x21,
 *   5th arg = 4.
 * That is VirtualAlloc's shape exactly, with MEM_LARGE_PAGES|MEM_PHYSICAL set
 * and PAGE_READWRITE|PAGE_NOCACHE as protection. Desktop VirtualAlloc rejects
 * MEM_PHYSICAL and usually MEM_LARGE_PAGES here, so both are stripped. */
void* XMemVirtualAlloc(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    DWORD type = (DWORD)c & ~(DWORD)0x20400000u;   /* drop PHYSICAL|LARGE_PAGES */
    DWORD protect = (DWORD)d;
    void* p;
    S2_LOG_ONCE("xmem.dll!XMemVirtualAlloc");
    /* 0x21 as passed is not a Win32 protection value (VirtualAlloc -> 87), and
     * 0x20402000 also carries MEM_PHYSICAL|MEM_LARGE_PAGES, which the desktop
     * allocator rejects. Keep a protection-looking value, else default. */
    switch (protect & 0xFF) {
    case 0x01: case 0x02: case 0x04: case 0x08:
    case 0x10: case 0x20: case 0x40: case 0x80: break;
    default: protect = PAGE_READWRITE; break;
    }
    if (type == 0) type = MEM_COMMIT | MEM_RESERVE;
    if (b == 0) b = 1;
    {   /* Experiment switch: reserve only, to see whether the commit choice is
         * what the startup path is unhappy about. */
        static int reserveOnly = -1;
        if (reserveOnly < 0) reserveOnly = getenv("GTA6_XMEM_RESERVE_ONLY") ? 1 : 0;
        if (reserveOnly)
            return VirtualAlloc(NULL, (SIZE_T)b, MEM_RESERVE, PAGE_READWRITE);
    }
    /* The descriptor asks for a 24 GiB region. Commit it all so no later touch
     * faults; if the commit charge is short, fall back to a bare reservation. */
    p = VirtualAlloc(NULL, (SIZE_T)b, type | MEM_COMMIT, protect);
    if (!p && (type & MEM_COMMIT) == 0)
        p = VirtualAlloc(NULL, (SIZE_T)b, type | MEM_RESERVE, protect);
    return p;
}

void* XMemAllocatePhysicalPages(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xmem.dll!XMemAllocatePhysicalPages");
    (void)c; (void)d;
    /* Physical class: same pages; contents are never trusted to be readable
     * from the GPU side, which is the honest desktop behaviour. */
    return s2_alloc((size_t)a, (uint64_t)b);
}

/* ---- freeing ------------------------------------------------------------- */

void XMemFree(void* p, uintptr_t attributes, uintptr_t c, uintptr_t d)
{
    MEMORY_BASIC_INFORMATION mbi;
    (void)attributes; (void)c; (void)d;
    InterlockedIncrement64(&g_freeCount);
    if (p == NULL) return;
    if (VirtualQuery(p, &mbi, sizeof(mbi)) == 0) return;
    if (mbi.State == MEM_FREE) return;                       /* double free */
    if ((const void*)mbi.BaseAddress == p && mbi.Type == MEM_PRIVATE &&
        (mbi.State == MEM_COMMIT || mbi.State == MEM_RESERVE)) {
        VirtualFree(p, 0, MEM_RELEASE);
    }
    /* anything foreign (CRT heap, image, mapped file, interior) is leaked
     * rather than mis-released. */
}

void XMemFreeDefault(void* p, uintptr_t attributes, uintptr_t c, uintptr_t d)
{
    uintptr_t a = (uintptr_t)p, b = attributes;
    S2_LOG_ONCE("xmem.dll!XMemFreeDefault");
    XMemFree(p, attributes, c, d);
}

void XMemFreePhysicalPages(void* p, uintptr_t attributes, uintptr_t c, uintptr_t d)
{
    uintptr_t a = (uintptr_t)p, b = attributes;
    S2_LOG_ONCE("xmem.dll!XMemFreePhysicalPages");
    XMemFree(p, attributes, c, d);
}

/* ---- queries ------------------------------------------------------------- */

SIZE_T XMemVirtualQuery(const void* address, MEMORY_BASIC_INFORMATION* info,
                        SIZE_T length, uintptr_t d)
{
    (void)d;
    return VirtualQuery(address, info, length);
}

void* XMemGetBaseAddress(DWORD attributes, uintptr_t b, uintptr_t c, uintptr_t d)
{
    (void)attributes; (void)b; (void)c; (void)d;
    return (void*)(uintptr_t)0x10000000ull;
}

SIZE_T XMemGetSize(const void* p, uintptr_t b, uintptr_t c, uintptr_t d)
{
    MEMORY_BASIC_INFORMATION mbi;
    (void)b; (void)c; (void)d;
    if (!p || VirtualQuery(p, &mbi, sizeof(mbi)) == 0) return 0;
    return mbi.RegionSize;
}

long XMemGetWorkingSetStatistics(void* stats, uintptr_t b, uintptr_t c, uintptr_t d)
{
    PROCESS_MEMORY_COUNTERS pmc;
    (void)b; (void)c; (void)d;
    if (stats == NULL) return S2_E_INVALIDARG;
    memset(stats, 0, 64);                    /* documented minimum is 32 */
    memset(&pmc, 0, sizeof(pmc));
    if (GetProcessMemoryInfo(GetCurrentProcess(), &pmc, sizeof(pmc))) {
        uint64_t ws = (uint64_t)pmc.WorkingSetSize;
        memcpy(stats, &ws, sizeof(ws));
    }
    return 0;                                /* S_OK */
}

/* Specified as 0: no tools/debug memory on this host. */
long XMemIsToolsMemAvailable(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xmem.dll!XMemIsToolsMemAvailable");
    (void)a; (void)b; (void)c; (void)d;
    return 0;
}

/* ---- mapping / copy ------------------------------------------------------ */

/* XMemMapPhysicalPages(physDesc*, count, &outPtr, ...) is the likely shape;
 * without the real header the first slot is used as a byte size. */
long XMemMapPhysicalPages(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xmem.dll!XMemMapPhysicalPages");
    (void)d;
    void* p = s2_alloc((size_t)a, 0);
    if (!p) return (long)0x8007000EL;
    if (c) *(void**)c = p;
    return 0;
}

long XMemMapPhysicalPagesScatter(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xmem.dll!XMemMapPhysicalPagesScatter");
    (void)b; (void)d;
    void* p = s2_alloc((size_t)a, 0);
    if (!p) return (long)0x8007000EL;
    if (c) *(void**)c = p;
    return 0;
}

void* XMemTransferMemory(void* dst, const void* src, size_t size, uintptr_t d)
{
    (void)d;
    if (dst && src && size) memmove(dst, src, size);
    return dst;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r)
{
    (void)h; (void)r;
    if (reason == DLL_PROCESS_ATTACH) {
        g_attrSeenCount = 0; g_allocCount = 0; g_freeCount = 0;
    }
    return TRUE;
}
