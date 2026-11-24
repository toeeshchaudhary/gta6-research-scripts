/* chad.c -- substitute chad.dll : 5 entry points of the Xbox DSP command layer.
 *
 * Opaque tokens + S_OK. Every API logs its first call with raw register
 * arguments so the DSP command blocks can be identified later.
 */
#include "shims2.h"

long XDspActivate(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("chad.dll!XDspActivate");
    (void)b; (void)c; (void)d;
    if (a) *(void**)a = s2_new_token();
    return 0;
}

long XDspDeactivate(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("chad.dll!XDspDeactivate");
    (void)a; (void)b; (void)c; (void)d;
    return 0;
}

long XDspConnectWithMaximumStreamLimit(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("chad.dll!XDspConnectWithMaximumStreamLimit");
    (void)b; (void)c; (void)d;
    if (a) *(void**)a = s2_new_token();
    return 0;
}

long XDspDisconnect(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("chad.dll!XDspDisconnect");
    (void)a; (void)b; (void)c; (void)d;
    return 0;
}

long XDspSubmitCommand(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("chad.dll!XDspSubmitCommand");
    (void)a; (void)b; (void)c; (void)d;
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r)
{
    (void)h; (void)reason; (void)r;
    return TRUE;
}
