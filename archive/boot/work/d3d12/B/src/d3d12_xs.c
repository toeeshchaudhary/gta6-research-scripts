#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <intrin.h>
/* d3d12_xs.c -- substitute d3d12_xs.dll : 3 exported entry points.
 *
 * The root-signature pair forwards to the real %SystemRoot%\System32\d3d12.dll
 * (proven HRESULT-identical in the earlier 4-function proof; that forwarding is
 * kept verbatim). D3D12ConfigureVirtualMemoryX is a Series-only extension and
 * has no desktop implementation.
 *
 * D3D12XboxCreateDevice is declared with five slots because the Xbox form
 * carries an extra parameter (a D3D12XBOX_CREATE_DEVICE_PARAMETERS*) that the
 * desktop D3D12CreateDevice does not. Both readings are attempted and the one
 * that succeeds is logged, so the real order is learned from the run.
 */
#include "shims2.h"

static HMODULE s2_d3d12(void)
{
    static HMODULE cached = NULL;
    static LONG once = 0;
    if (InterlockedCompareExchange(&once, 1, 0) == 0) {
        wchar_t sys[MAX_PATH];
        UINT n = GetSystemDirectoryW(sys, MAX_PATH);
        if (n && n < MAX_PATH) {
            wchar_t full[MAX_PATH];
            _snwprintf(full, MAX_PATH, L"%s\\d3d12.dll", sys);
            cached = LoadLibraryExW(full, NULL, LOAD_LIBRARY_SEARCH_SYSTEM32);
        }
        if (!cached) cached = LoadLibraryW(L"d3d12.dll");
    }
    return cached;
}

typedef long(__stdcall* PFN_CreateDevice)(void*, unsigned, const GUID*, void**);
typedef long(__stdcall* PFN_Serialize)(const void*, void**, void**);
typedef long(__stdcall* PFN_Deserialize)(const void*, size_t, const GUID*, void**);

static void* s2_export(const char* name)
{
    HMODULE h = s2_d3d12();
    return h ? (void*)GetProcAddress(h, name) : NULL;
}

long D3D12SerializeVersionedRootSignature(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    if(getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL d3d12_xs!D3D12SerializeVersionedRootSignature return_pc=%p\n",_ReturnAddress());fflush(stderr);}
    (void)c; (void)d;
    PFN_Serialize fn = (PFN_Serialize)s2_export("D3D12SerializeVersionedRootSignature");
    if (!fn) return S2_E_NOTIMPL;
    return fn((const void*)a, (void**)b, (void**)c);
}

long D3D12CreateRootSignatureDeserializer(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    if(getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL d3d12_xs!D3D12CreateRootSignatureDeserializer return_pc=%p\n",_ReturnAddress());fflush(stderr);}
    (void)b; (void)c; (void)d;
    PFN_Deserialize fn = (PFN_Deserialize)s2_export("D3D12CreateRootSignatureDeserializer");
    if (!fn) return S2_E_NOTIMPL;
    return fn((const void*)a, (size_t)b, (const GUID*)c, (void**)d);
}

long D3D12ConfigureVirtualMemoryX(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    if(getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL d3d12_xs!D3D12ConfigureVirtualMemoryX return_pc=%p\n",_ReturnAddress());fflush(stderr);}
    S2_LOG_ONCE("d3d12_xs.dll!D3D12ConfigureVirtualMemoryX");
    (void)a; (void)b; (void)c; (void)d;
    return S2_E_NOTIMPL;   /* Xbox virtual-memory reservation; no desktop peer */
}

/* Five slots: e is the caller's stack argument. */
long D3D12XboxCreateDevice(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d, uintptr_t e)
{
    if(getenv("PELOAD_TRACE")) {fprintf(stderr,"CALL d3d12_xs!D3D12XboxCreateDevice return_pc=%p\n",_ReturnAddress());fflush(stderr);}
    PFN_CreateDevice fn;
    long hr;

    s2_log_init();
    {
        static LONG once = 0;
        if (InterlockedExchange(&once, 1) == 0)
            fprintf(stderr, "SHIM-ABI d3d12_xs.dll!D3D12XboxCreateDevice tid=%lu "
                            "a=%p b=%p c=%p d=%p e=%p\n",
                    (unsigned long)GetCurrentThreadId(), (void*)a, (void*)b,
                    (void*)c, (void*)d, (void*)e);
    }

    fn = (PFN_CreateDevice)s2_export("D3D12CreateDevice");
    if (!fn) return S2_E_NOTIMPL;

    /* Reading 1: desktop shape (adapter, level, riid, out) with 5th unused. */
    hr = fn((void*)a, (unsigned)b, (const GUID*)c, (void**)d);
    if (hr == 0) {
        fprintf(stderr, "SHIM-ABI D3D12XboxCreateDevice: desktop 4-arg reading OK\n");
        return hr;
    }

    /* Reading 2: Xbox shape (adapter, level, params, riid, out). */
    if (e) {
        long hr2 = fn((void*)a, (unsigned)b, (const GUID*)d, (void**)e);
        if (hr2 == 0) {
            fprintf(stderr, "SHIM-ABI D3D12XboxCreateDevice: xbox 5-arg reading OK "
                            "(params ignored)\n");
            return hr2;
        }
    }
    fprintf(stderr, "SHIM-ABI D3D12XboxCreateDevice: both readings failed, hr=0x%08lX\n",
            (unsigned long)hr);
    return hr;
}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r)
{
    (void)h; (void)r; (void)reason;
    return TRUE;
}
