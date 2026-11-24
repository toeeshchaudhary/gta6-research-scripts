/* shims2.h -- common ABI-discovery logging for the substitute GDK DLLs.
 *
 * Every entry point is declared with four uintptr_t register slots (rcx, rdx,
 * r8, r9 on Win64) so an unknown ABI can be *recorded* rather than guessed.
 * Each API logs exactly once: "SHIM-ABI <dll>!<fn> tid=<n> a=<..> b=<..> ...".
 * Output goes to stderr, which is the peload console, so the log is captured
 * with the run. Set GTA6_SHIM_LOG=<path> to tee it into a file as well.
 */
#ifndef SHIMS2_H
#define SHIMS2_H

#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define S2_E_NOTIMPL   ((long)0x80004001L)
#define S2_E_INVALIDARG ((long)0x80070057L)
#define S2_E_OUTOFMEMORY ((long)0x8007000EL)

/* Handle table: opaque counters handed out as fake pointers. */
static volatile LONG64 g_s2_handle_seq = 0x1000;

static void s2_log_init(void)
{
    static LONG once = 0;
    if (InterlockedExchange(&once, 1) != 0)
        return;
    const char* p = getenv("GTA6_SHIM_LOG");
    if (p && *p) {
        FILE* f = fopen(p, "a");
        if (f) {
            fprintf(f, "=== shims2 attached in pid %lu ===\n",
                    (unsigned long)GetCurrentProcessId());
            fclose(f);
        }
    }
}

/* Log the first call of one API with its raw register arguments. */
#define S2_LOG_ONCE(api)                                                    \
    do {                                                                    \
        static LONG s2_once_ = 0;                                           \
        s2_log_init();                                                      \
        if (InterlockedExchange(&s2_once_, 1) == 0) s2_emit((api), (void*)a, \
                                                            (void*)b, (void*)c, (void*)d); \
    } while (0)

static void s2_emit(const char* api, void* a, void* b, void* c, void* d)
{
    const char* path = getenv("GTA6_SHIM_LOG");
    FILE* f = stderr;
    FILE* file = NULL;
    if (path && *path) {
        file = fopen(path, "a");
        if (file) f = file;
    }
    fprintf(f, "SHIM-ABI %s tid=%lu a=%p b=%p c=%p d=%p\n", api,
            (unsigned long)GetCurrentThreadId(), a, b, c, d);
    fflush(f);
    if (file) fclose(file);
    OutputDebugStringA(api);
}

/* Hand out a monotonically increasing, never-dereferenced token. */
static void* s2_new_token(void)
{
    LONG64 n = InterlockedIncrement64(&g_s2_handle_seq);
    return (void*)(uintptr_t)n;
}

/* A stable, page-aligned, freeable block for "opaque" surface calls. */
static void* s2_virtual_alloc(size_t size)
{
    if (size == 0) size = 4096;
    return VirtualAlloc(NULL, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE);
}

#endif /* SHIMS2_H */
