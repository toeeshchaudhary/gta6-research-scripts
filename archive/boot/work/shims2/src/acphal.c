/* acphal.c -- substitute AcpHal.dll : 9 opaque audio-HAL entry points.
 *
 * No ABI truth is available for these, so behaviour is deliberately minimal:
 * allocate a stable token (or S_OK), and log the first call of every API with
 * its raw register arguments. Nothing here is validated; the point is to learn
 * the call order and the shapes from a live run.
 */
#include "shims2.h"

/* HRESULT-shaped: log and succeed. */
#define S2_OK_ONLY(dllname)                                        \
    S2_LOG_ONCE(dllname);                                          \
    (void)a; (void)b; (void)c; (void)d;                            \
    return 0

/* Handle-shaped: return a unique opaque token. */
#define S2_TOKEN(dllname)                                          \
    S2_LOG_ONCE(dllname);                                          \
    (void)a; (void)b; (void)c; (void)d;                            \
    return s2_new_token()

long AcpHalAllocateShapeContexts(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("AcpHal.dll!AcpHalAllocateShapeContexts");
    (void)a; (void)b; (void)c; (void)d;
    /* Xbox APU shape contexts: nothing desktop-side to validate. */
    return 0;                                   /* S_OK */
}

long AcpHalCreate(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("AcpHal.dll!AcpHalCreate");
    (void)b; (void)c; (void)d;
    if (a) *(void**)a = s2_new_token();
    return 0;
}

long AcpHalReleaseShapeContexts(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_OK_ONLY("AcpHal.dll!AcpHalReleaseShapeContexts");
}

void* ApuAlloc(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_TOKEN("AcpHal.dll!ApuAlloc");
}

long ApuCreateHeap(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("AcpHal.dll!ApuCreateHeap");
    (void)b; (void)c; (void)d;
    if (a) *(void**)a = s2_new_token();
    return 0;
}

long ApuFree(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_OK_ONLY("AcpHal.dll!ApuFree");
}

/* Query: 1 = "yes, valid" so a caller's assertion path is not taken. */
long ApuIsVirtualAddressValid(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("AcpHal.dll!ApuIsVirtualAddressValid");
    (void)a; (void)b; (void)c; (void)d;
    return 1;
}

long ApuMapApuAddress(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("AcpHal.dll!ApuMapApuAddress");
    (void)b; (void)c; (void)d;
    if (a) *(void**)a = s2_new_token();
    return 0;
}

long ApuMapVirtualAddress(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("AcpHal.dll!ApuMapVirtualAddress");
    (void)b; (void)c; (void)d;
    if (a) *(void**)a = s2_new_token();
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r)
{
    (void)h; (void)reason; (void)r;
    return TRUE;
}
