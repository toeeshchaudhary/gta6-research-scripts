/* xg_xs.c -- substitute xg_xs.dll : 2 entry points of the Xbox texture
 * swizzle/compression helper. Specified behaviour: E_NOTIMPL / 0.
 */
#include "shims2.h"

long XGCreateTextureComputer(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xg_xs.dll!XGCreateTextureComputer");
    (void)a; (void)b; (void)c; (void)d;
    return S2_E_NOTIMPL;
}

/* Unknown swizzle mode: 0 is the identity/linear answer. */
long XGSuggestSwizzleMode(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    S2_LOG_ONCE("xg_xs.dll!XGSuggestSwizzleMode");
    (void)a; (void)b; (void)c; (void)d;
    return 0;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r)
{
    (void)h; (void)reason; (void)r;
    return TRUE;
}
