/* xcrdapi.c -- substitute XCRDAPI.dll : DStorageGetFactory.
 *
 * Tries the real desktop dstorage.dll first (by explicit System32 path so the
 * game folder cannot hijack it); falls back to E_NOTIMPL when absent or when
 * the export is missing.
 */
#include "shims2.h"

typedef long(__stdcall* PFN_DStorageGetFactory)(const GUID*, void**);

long DStorageGetFactory(uintptr_t a, uintptr_t b, uintptr_t c, uintptr_t d)
{
    static HMODULE cached = NULL;
    static LONG once = 0;
    HMODULE h;
    PFN_DStorageGetFactory fn;

    S2_LOG_ONCE("XCRDAPI.dll!DStorageGetFactory");
    (void)c; (void)d;

    if (InterlockedCompareExchange(&once, 1, 0) == 0) {
        wchar_t sys[MAX_PATH];
        UINT n = GetSystemDirectoryW(sys, MAX_PATH);
        if (n && n < MAX_PATH) {
            wchar_t full[MAX_PATH];
            _snwprintf(full, MAX_PATH, L"%s\\dstorage.dll", sys);
            cached = LoadLibraryExW(full, NULL, LOAD_LIBRARY_SEARCH_SYSTEM32);
        }
        if (!cached) cached = LoadLibraryW(L"dstorage.dll");
    }
    h = cached;
    if (!h) {
        fprintf(stderr, "SHIM-ABI DStorageGetFactory: dstorage.dll absent -> E_NOTIMPL\n");
        return S2_E_NOTIMPL;
    }

    fn = (PFN_DStorageGetFactory)GetProcAddress(h, "DStorageGetFactory");
    if (!fn) {
        fprintf(stderr, "SHIM-ABI DStorageGetFactory: export absent -> E_NOTIMPL\n");
        return S2_E_NOTIMPL;
    }
    return fn((const GUID*)a, (void**)b);
}

BOOL WINAPI DllMain(HINSTANCE hinst, DWORD reason, LPVOID r)
{
    (void)hinst; (void)reason; (void)r;
    return TRUE;
}
