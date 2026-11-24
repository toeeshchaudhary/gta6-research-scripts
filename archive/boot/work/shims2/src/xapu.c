/* xapu.c -- substitute xapu.dll : 5 entry points of the Xbox APU command queue.
 *
 * Opaque tokens + S_OK, with the first call of each API logged for ABI study.
 */
#include "shims2.h"

long XApuConnect(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xapu.dll!XApuConnect");
    (void)b; (void)c; (void)d;
    if (a) *(void**)a = s2_new_token();
    return 0;
}

long XApuDisconnect(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xapu.dll!XApuDisconnect");
    (void)a; (void)b; (void)c; (void)d;
    return 0;
}

long XApuEnqueueCommand(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xapu.dll!XApuEnqueueCommand");
    (void)a; (void)b; (void)c; (void)d;
    return 0;
}

/* Both result paths report "one result available" so a polling caller makes
 * forward progress instead of spinning.
 */
long XApuGetResultCount(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xapu.dll!XApuGetResultCount");
    (void)b; (void)c; (void)d;
    if (a) *(uint32_t*)a = 1;
    return 0;
}

long XApuDequeueResult(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xapu.dll!XApuDequeueResult");
    (void)a; (void)b; (void)c; (void)d;
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r)
{
    (void)h; (void)reason; (void)r;
    return TRUE;
}
