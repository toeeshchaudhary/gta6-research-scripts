// pe_map.cpp -- reserve/commit, section copy, relocation, TLS, import binding,
// unwind registration, protections, entry-point invocation.
#include "pe_image.h"
#include "shim.h"

#include <algorithm>
#include <cstring>
#include <cstring>

namespace peload {

// RtlAddFunctionTable / RtlDeleteFunctionTable / RtlVirtualUnwind
extern "C" {
BOOLEAN NTAPI RtlAddFunctionTable(PRUNTIME_FUNCTION, DWORD, DWORD64);
BOOLEAN NTAPI RtlDeleteFunctionTable(PRUNTIME_FUNCTION);
}

namespace {

uintptr_t g_stub_retval = 0;   // 0, or E_NOTIMPL when --stub-returns-fail
bool      g_verbose     = false;

// Exec guard: a mapped CRT ends with ExitProcess(), which would kill the host
// before it could report. The entry point runs on a private thread and the
// exit calls are redirected to ExitThread, so the exit code survives as the
// thread exit code and the harness keeps running.
bool         g_exit_taken = false;
void*        g_orig_tls_array = nullptr;
uintptr_t    g_ExitProcess_addr = 0;
uintptr_t    g_RtlExitUserProcess_addr = 0;

void WINAPI ExitProcessThunk(UINT code) {
    g_exit_taken = true;
    // Give the TEB back its original TLS array so the loader's thread teardown
    // (which runs from ExitThread) sees the shape it allocated.
    if (g_orig_tls_array) {
        __writegsqword(0x58, (unsigned long long)g_orig_tls_array);
        g_orig_tls_array = nullptr;
    }
    ::ExitThread(code);   // never returns
}

bool AlignUp(uintptr_t v, uintptr_t a) { return (v & (a - 1)) == 0; }

std::wstring JoinPath(const std::wstring& dir, const std::string& file) {
    std::wstring w = dir;
    if (!w.empty() && w.back() != L'\\' && w.back() != L'/') w += L'\\';
    w += Widen(file);
    return w;
}

// Resolve a base-relative pointer inside the mapped image.
void* At(uintptr_t base, uint32_t rva) { return (void*)(base + rva); }

// ---------------------------------------------------------------------------
// Relocations
// ---------------------------------------------------------------------------
bool ApplyRelocations(MappedImage& img, const PeInfo& info) {
    auto& st = img.reloc;
    if (!info.has_reloc()) {
        st.err = "image has no .reloc directory and was mapped away from its ImageBase";
        return false;
    }
    if (!info.rva_in_image(info.dir_reloc_rva, 4)) {
        st.err = ".reloc directory RVA out of image";
        return false;
    }
    const int64_t delta = (int64_t)img.base - (int64_t)info.image_base;
    uint32_t off = 0;
    const uint32_t size = info.dir_reloc_size;

    while (off + sizeof(IMAGE_BASE_RELOCATION) <= size) {
        auto* blk = (const IMAGE_BASE_RELOCATION*)((const uint8_t*)At(img.base, info.dir_reloc_rva) + off);
        if (blk->SizeOfBlock < sizeof(IMAGE_BASE_RELOCATION)) break;
        st.blocks++;
        uint32_t count = (blk->SizeOfBlock - sizeof(IMAGE_BASE_RELOCATION)) / sizeof(WORD);
        auto* e = (const WORD*)(blk + 1);
        for (uint32_t i = 0; i < count; ++i) {
            uint32_t type = e[i] >> 12;
            uint32_t page_off = e[i] & 0x0FFF;
            uintptr_t target = img.base + blk->VirtualAddress + page_off;
            st.entries++;
            if (target + 8 > img.base + img.size) { st.unknown++; continue; }
            switch (type) {
            case IMAGE_REL_BASED_ABSOLUTE: st.skipped_abs++; break;
            case IMAGE_REL_BASED_DIR64:   *(int64_t*)target += delta; st.applied++; break;
            case IMAGE_REL_BASED_HIGHLOW: *(int32_t*)target += (int32_t)delta; st.applied++; break;
            default: st.unknown++; break;
            }
        }
        off += blk->SizeOfBlock;
    }
    st.ok = true;
    return true;
}

// ---------------------------------------------------------------------------
// TLS
// ---------------------------------------------------------------------------
bool SetupTls(MappedImage& img, const PeInfo& info, std::string& err) {
    if (!info.has_tls()) return true;
    if (!info.rva_in_image(info.dir_tls_rva, (uint32_t)sizeof(IMAGE_TLS_DIRECTORY64))) {
        err = "TLS directory RVA out of image";
        return false;
    }
    auto* tls = (IMAGE_TLS_DIRECTORY64*)At(img.base, info.dir_tls_rva);

    // Snapshot the template out of the freshly copied image and rebuild it in
    // a private allocation (real loaders own this block).
    uint64_t start_va = tls->StartAddressOfRawData;
    size_t raw = (size_t)(tls->EndAddressOfRawData - start_va);
    size_t total = raw + (size_t)tls->SizeOfZeroFill;
    img.tls_total = total;
    if (total) {
        void* tpl = ::HeapAlloc(::GetProcessHeap(), HEAP_ZERO_MEMORY, total);
        if (!tpl) { err = "HeapAlloc for TLS template failed"; return false; }
        if (raw && start_va) ::memcpy(tpl, (const void*)(uintptr_t)start_va, raw);
        img.tls_template = tpl;
        tls->StartAddressOfRawData = (uint64_t)(uintptr_t)tpl;
        tls->EndAddressOfRawData   = (uint64_t)(uintptr_t)tpl + raw;
    }

    if (g_verbose) {
        fprintf(stderr, "[tls] start_rva=0x%llX n=%zu zerofill=%u total=%zu tpl[0..8]=%016llX\n",
                start_va - img.base, raw, tls->SizeOfZeroFill, total,
                (total >= 8 && start_va) ? *(const uint64_t*)(uintptr_t)start_va : 0ull);
        fprintf(stderr, "[tls] idx_rva=0x%llX cb_rva=0x%llX\n",
                tls->AddressOfIndex - img.base, tls->AddressOfCallBacks - img.base);
    }
    // The loader's implicit-TLS slot namespace and the TlsAlloc namespace are
    // not the same array here (TEB->ThreadLocalStoragePointer vs ->TlsSlots).
    // Pick a TlsAlloc slot whose TEB array entry is free so filling it cannot
    // clobber another module's implicit TLS record.
    DWORD idx = TLS_OUT_OF_INDEXES;
    void** tp = (void**)__readgsqword(0x58);
    std::vector<DWORD> held;          // TlsAlloc always hands out the lowest
    while (held.size() < 64) {        // free slot, so hold rejects and free later
        DWORD cand = ::TlsAlloc();
        if (cand == TLS_OUT_OF_INDEXES) break;
        held.push_back(cand);
        if (cand >= 64 || !tp || tp[cand] == nullptr) { idx = cand; break; }
    }
    for (DWORD h : held) if (h != idx) ::TlsFree(h);
    if (g_verbose) {
        fprintf(stderr, "[tls] TlsAlloc -> %u (tp=%p)\n", idx, tp);
        for (int k = 0; k < 4; ++k)
            fprintf(stderr, "[tls]   tp[%d]=%p\n", k, tp ? tp[k] : (void*)1);
    }
    if (idx == TLS_OUT_OF_INDEXES) { err = "TlsAlloc failed (no free implicit slot)"; return false; }
    img.tls_index = idx;
    img.tls_active = true;
    if (tls->AddressOfIndex) *(DWORD*)(uintptr_t)tls->AddressOfIndex = idx;
    return true;
}

void ClearTlsIndex(MappedImage& img) {
    if (img.tls_active) { ::TlsFree(img.tls_index); img.tls_active = false; }
    if (img.tls_template) { ::HeapFree(::GetProcessHeap(), 0, img.tls_template); img.tls_template = nullptr; }
}

// ---------------------------------------------------------------------------
// Import binding helpers
// ---------------------------------------------------------------------------

} // namespace

void MapSetStubRetval(uintptr_t v) { g_stub_retval = v; }
void MapSetVerbose(bool v) { g_verbose = v; }

bool MapImage(const PeInfo& info, const std::vector<uint8_t>& file,
              uintptr_t prefer_base, MappedImage& out) {
    uintptr_t preferred = prefer_base ? prefer_base : (uintptr_t)info.image_base;
    if (!AlignUp(preferred, 0x10000)) preferred = (preferred + 0xFFFF) & ~(uintptr_t)0xFFFF;
    out.preferred = preferred;

    if (!info.size_of_image || info.size_of_image > 0x80000000u) {
        out.reloc.err = "implausible SizeOfImage"; return false;
    }

    void* mem = ::VirtualAlloc((void*)preferred, info.size_of_image,
                               MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
    if (!mem) {
        mem = ::VirtualAlloc(nullptr, info.size_of_image, MEM_RESERVE | MEM_COMMIT, PAGE_READWRITE);
        if (!mem) {
            out.reloc.err = "VirtualAlloc failed, GetLastError=" + std::to_string(::GetLastError());
            return false;
        }
    }
    out.base = (uintptr_t)mem;
    out.size = info.size_of_image;
    out.mapped = true;
    std::memset(mem, 0, out.size);

    // PE headers are part of the image (some code reads them at runtime).
    size_t hdr = std::min<size_t>(info.size_of_headers ? info.size_of_headers : 0x1000,
                                  std::min<size_t>(file.size(), out.size));
    if (hdr) std::memcpy(mem, file.data(), hdr);

    for (const auto& s : info.sections) {
        if (!s.va || s.va >= out.size) continue;
        size_t copy = 0;
        if (s.rawsize && s.rawptr < file.size())
            copy = std::min<size_t>(s.rawsize, file.size() - s.rawptr);
        if (s.vsize) copy = std::min<size_t>(copy, s.vsize);
        copy = std::min<size_t>(copy, out.size - s.va);
        if (copy) std::memcpy((uint8_t*)mem + s.va, file.data() + s.rawptr, copy);
        // BSS tail: [copy, max(vsize,rawsize)) must be zero (already is).
    }

    if (out.base != (uintptr_t)info.image_base) {
        out.relocated = true;
        if (!ApplyRelocations(out, info)) {
            ::VirtualFree(mem, 0, MEM_RELEASE);
            out.mapped = false;
            return false;
        }
    } else {
        out.reloc.ok = true;   // mapped at its ImageBase: nothing to do
    }

    std::string err;
    if (!SetupTls(out, info, err)) {
        out.reloc.err = err;
        ::VirtualFree(mem, 0, MEM_RELEASE);
        out.mapped = false;
        return false;
    }

    return true;
}

namespace {

// Bind one thunk slot. Returns true if a usable address was installed.
bool BindOne(MappedImage& img, DllClass cls, HMODULE hmod, const std::string& dll,
             const ImportFn& fn, uint64_t* out, std::string& why) {
    const std::string key = fn.by_ordinal ? ("#" + std::to_string(fn.ordinal)) : fn.name;

    if (cls == DllClass::Shim) {
        if (void* real = ShimLookup(dll.c_str(), key.c_str())) {
            img.bind.shim_real++;
            *out = (uint64_t)real;
            return true;
        }
        void* thunk = ShimMakeMissThunk(dll.c_str(), key.c_str(), g_stub_retval);
        if (!thunk) { why = "thunk alloc failed"; return false; }
        img.bind.shim_stub++;
        *out = (uint64_t)thunk;
        return true;   // a stub is a successful bind
    }

    if (!hmod) { why = "module not loaded"; return false; }

    FARPROC p = fn.by_ordinal ? ::GetProcAddress(hmod, MAKEINTRESOURCEA(fn.ordinal))
                              : ::GetProcAddress(hmod, fn.name.c_str());
    if (!p) {
        why = "GetProcAddress failed, GetLastError=" + std::to_string(::GetLastError());
        // Install a logging stub so the image stays callable, but report it.
        if (void* thunk = ShimMakeMissThunk(dll.c_str(), key.c_str(), g_stub_retval))
            *out = (uint64_t)thunk;
        return false;
    }
    *out = (uint64_t)p;
    return true;
}

DllClass DefaultClass(const std::string& d, const std::wstring& g) { return ClassifyDll(d, g); }

} // namespace

bool BindImports(MappedImage& img, const PeInfo& info, const std::wstring& gameDir,
                 DllClass (*classifier)(const std::string&, const std::wstring&)) {
    if (!classifier) classifier = &DefaultClass;
    img.bind.ok = true;
    if (info.dir_import_rva == 0) return true;
    if (!info.rva_in_image(info.dir_import_rva, (uint32_t)sizeof(IMAGE_IMPORT_DESCRIPTOR))) {
        img.bind.ok = false;
        img.bind.err = "import directory RVA out of image";
        return false;
    }

    const size_t max_desc = 512;
    auto* d = (IMAGE_IMPORT_DESCRIPTOR*)At(img.base, info.dir_import_rva);
    for (size_t di = 0; d->Name && di < max_desc; ++d, ++di) {
        ImportDll meta;
        meta.name = std::string((const char*)At(img.base, d->Name));
        img.bind.descriptors++;

        DllClass cls = classifier(meta.name, gameDir);
        HMODULE hmod = nullptr;
        std::string load_err;

        if (cls != DllClass::Shim) {
            if (cls == DllClass::Bundled) {
                std::wstring full = JoinPath(gameDir, meta.name);
                hmod = ::LoadLibraryExW(full.c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
                if (!hmod) hmod = ::LoadLibraryExW(full.c_str(), nullptr, 0);
            } else {
                std::wstring w = Widen(meta.name);
                hmod = ::GetModuleHandleW(w.c_str());
                if (!hmod) hmod = ::LoadLibraryExW(w.c_str(), nullptr, 0);
            }
            if (!hmod)
                load_err = "LoadLibrary failed, GetLastError=" + std::to_string(::GetLastError());
            else if (g_verbose) {
                char path[MAX_PATH] = {}; ::GetModuleFileNameA(hmod, path, MAX_PATH);
                fprintf(stderr, "[bind] %-28s -> %s%s\n", meta.name.c_str(), path,
                        cls == DllClass::Bundled ? "" : "  (NOTE: resolved outside game dir)");
            }
        }

        uint32_t oiat = d->OriginalFirstThunk ? d->OriginalFirstThunk : d->FirstThunk;
        const uint64_t* names = oiat ? (const uint64_t*)At(img.base, oiat) : nullptr;
        uint64_t* iat = (uint64_t*)At(img.base, d->FirstThunk);

        for (size_t i = 0; i < 65536 && names && names[i]; ++i) {
            ImportFn fn;
            if (names[i] & IMAGE_ORDINAL_FLAG64) {
                fn.by_ordinal = true; fn.ordinal = (uint16_t)(names[i] & 0xFFFF);
            } else {
                fn.name = std::string((const char*)At(img.base, (uint32_t)(names[i] & 0x7FFFFFFF) + 2));
            }
            std::string why = load_err;
            uint64_t addr = 0;
            bool ok = BindOne(img, cls, hmod, meta.name, fn, &addr, why);
            iat[i] = addr;
            if (ok) {
                if (cls != DllClass::Shim) img.bind.bound++;
            } else {
                img.bind.missing++;
                img.bind.unbound.push_back(meta.name + "!" +
                    (fn.by_ordinal ? "#" + std::to_string(fn.ordinal) : fn.name) +
                    "  (" + why + ")");
            }
        }
    }

    // ---- delay-load descriptors -------------------------------------------
    if (info.has_delay() && info.rva_in_image(info.dir_delay_rva,
                                              (uint32_t)sizeof(IMAGE_DELAYLOAD_DESCRIPTOR))) {
        auto* dd = (IMAGE_DELAYLOAD_DESCRIPTOR*)At(img.base, info.dir_delay_rva);
        for (size_t i = 0; i < 128 && dd->DllNameRVA; ++dd, ++i) {
            const bool rva_based = (dd->Attributes.AllAttributes & 1) != 0;
            auto fix = [&](uint32_t v) -> uint32_t {
                return rva_based ? v : (uint32_t)((uint64_t)v - info.image_base);
            };
            img.bind.delay_descriptors++;
            std::string name((const char*)At(img.base, fix(dd->DllNameRVA)));
            DllClass cls = classifier(name, gameDir);
            HMODULE hmod = nullptr;
            if (cls != DllClass::Shim) {
                if (cls == DllClass::Bundled) {
                    std::wstring full = JoinPath(gameDir, name);
                    hmod = ::LoadLibraryExW(full.c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
                } else {
                    std::wstring w = Widen(name);
                    hmod = ::GetModuleHandleW(w.c_str());
                    if (!hmod) hmod = ::LoadLibraryExW(w.c_str(), nullptr, 0);
                }
            }
            if (dd->ModuleHandleRVA) *(HMODULE*)At(img.base, fix(dd->ModuleHandleRVA)) = hmod;

            uint32_t int_rva = fix(dd->ImportNameTableRVA);
            uint32_t iat_rva = fix(dd->ImportAddressTableRVA);
            const uint64_t* names = int_rva ? (const uint64_t*)At(img.base, int_rva) : nullptr;
            uint64_t* iat = iat_rva ? (uint64_t*)At(img.base, iat_rva) : nullptr;
            for (size_t k = 0; names && iat && names[k]; ++k) {
                ImportFn fn;
                if (names[k] & IMAGE_ORDINAL_FLAG64) {
                    fn.by_ordinal = true; fn.ordinal = (uint16_t)(names[k] & 0xFFFF);
                } else {
                    fn.name = std::string((const char*)At(img.base, (uint32_t)(names[k] & 0x7FFFFFFF) + 2));
                }
                std::string why;
                uint64_t addr = 0;
                bool ok = BindOne(img, cls, hmod, name, fn, &addr, why);
                iat[k] = addr;
                if (ok) img.bind.delay_bound++;
                else {
                    img.bind.delay_missing++;
                    img.bind.unbound.push_back("[delay] " + name + "!" +
                        (fn.by_ordinal ? "#" + std::to_string(fn.ordinal) : fn.name) +
                        "  (" + why + ")");
                }
            }
        }
    }
    return true;
}

bool InstallUnwindInfo(const MappedImage& img, const PeInfo& info, std::string& err) {
    if (!info.has_pdata()) return true;
    if (info.dir_pdata_size % sizeof(RUNTIME_FUNCTION) != 0) {
        err = ".pdata size not a multiple of RUNTIME_FUNCTION";
        return false;
    }
    if (!info.rva_in_image(info.dir_pdata_rva, info.dir_pdata_size)) {
        err = ".pdata RVA out of image";
        return false;
    }
    auto* tbl = (PRUNTIME_FUNCTION)At(img.base, info.dir_pdata_rva);
    if (!::RtlAddFunctionTable(tbl, info.dir_pdata_size / sizeof(RUNTIME_FUNCTION),
                               (DWORD64)img.base)) {
        err = "RtlAddFunctionTable failed";
        return false;
    }
    return true;
}

void RemoveUnwindInfo(const MappedImage& img, const PeInfo& info) {
    if (!info.has_pdata() || !info.rva_in_image(info.dir_pdata_rva, 12)) return;
    ::RtlDeleteFunctionTable((PRUNTIME_FUNCTION)At(img.base, info.dir_pdata_rva));
}

bool SealProtections(const MappedImage& img, const PeInfo& info, std::string& err) {
    for (const auto& s : info.sections) {
        if (!s.va || s.va >= img.size) continue;
        SIZE_T len = std::min<SIZE_T>(std::max(s.vsize, s.rawsize), img.size - s.va);
        if (!len) continue;
        DWORD prot = PAGE_READONLY;
        if (s.chars & IMAGE_SCN_MEM_EXECUTE)
            prot = (s.chars & IMAGE_SCN_MEM_WRITE) ? PAGE_EXECUTE_READWRITE : PAGE_EXECUTE_READ;
        else if (s.chars & IMAGE_SCN_MEM_WRITE)
            prot = PAGE_READWRITE;
        if (s.chars & IMAGE_SCN_MEM_DISCARDABLE) prot = PAGE_READONLY;
        DWORD old = 0;
        if (!::VirtualProtect((void*)(img.base + s.va), len, prot, &old)) {
            err = "VirtualProtect failed for section " + s.name +
                  ", GetLastError=" + std::to_string(::GetLastError());
            return false;
        }
    }
    return true;
}

void NotifyTlsCallbacks(const MappedImage& img, const PeInfo& info, bool attach) {
    if (!info.has_tls() || !info.rva_in_image(info.dir_tls_rva, (uint32_t)sizeof(IMAGE_TLS_DIRECTORY64)))
        return;
    auto* tls = (IMAGE_TLS_DIRECTORY64*)At(img.base, info.dir_tls_rva);
    if (!tls->AddressOfCallBacks) return;
    auto** cb = (PIMAGE_TLS_CALLBACK*)(uintptr_t)tls->AddressOfCallBacks;
    for (size_t i = 0; i < 64 && cb[i]; ++i)
        cb[i]((PVOID)img.base, attach ? DLL_PROCESS_ATTACH : DLL_PROCESS_DETACH, nullptr);
}

namespace {
typedef int (*PFN_ENTRY)(void*, unsigned);

} // namespace

void PatchExitImports(MappedImage& img, const PeInfo& info) {
    HMODULE k32 = ::GetModuleHandleW(L"kernel32.dll");
    HMODULE nt  = ::GetModuleHandleW(L"ntdll.dll");
    if (k32) g_ExitProcess_addr = (uintptr_t)::GetProcAddress(k32, "ExitProcess");
    if (nt)  g_RtlExitUserProcess_addr = (uintptr_t)::GetProcAddress(nt, "RtlExitUserProcess");
    if (!g_ExitProcess_addr && !g_RtlExitUserProcess_addr) return;

    if (!info.dir_import_rva || !info.rva_in_image(info.dir_import_rva, 20)) return;
    auto* d = (IMAGE_IMPORT_DESCRIPTOR*)At(img.base, info.dir_import_rva);
    for (; d->Name; ++d) {
        uint64_t* iat = (uint64_t*)At(img.base, d->FirstThunk);
        for (size_t i = 0; i < 65536 && (d->OriginalFirstThunk
                 ? ((uint64_t*)At(img.base, d->OriginalFirstThunk))[i] : iat[i]); ++i) {
            if (iat[i] && (iat[i] == g_ExitProcess_addr || iat[i] == g_RtlExitUserProcess_addr))
                iat[i] = (uint64_t)(void*)&ExitProcessThunk;
        }
    }
}

// Each thread that runs mapped code needs its own copy of the TLS template,
// because static TlsSlots[] entries are not populated by TlsAlloc.
void PrepThreadTls(const MappedImage& img) {
    if (!img.tls_active || !img.tls_template || !img.tls_total) return;
    void* copy = ::HeapAlloc(::GetProcessHeap(), HEAP_ZERO_MEMORY, img.tls_total);
    if (!copy) return;
    if (!::getenv("PELOAD_NOCPY")) ::memcpy(copy, img.tls_template, img.tls_total);
    if (!::getenv("PELOAD_NOTLSV")) ::TlsSetValue(img.tls_index, copy);

    // Compiled __declspec(thread) code indexes TEB->ThreadLocalStoragePointer
    // (gs:[58h]) directly, and that array is only as long as the process's
    // implicit-TLS slot count -- writing past it corrupts the heap. So publish
    // a longer copy of the array for this thread and point the TEB at it.
    // The loader frees whatever pointer is there at thread exit, and the
    // replacement comes from the same process heap, so that stays valid.
    void** old = (void**)__readgsqword(0x58);
    size_t need = 64;   // TEB TLS arrays are TlsSlots-sized; keep the shape
    void** arr = (void**)::HeapAlloc(::GetProcessHeap(), HEAP_ZERO_MEMORY, need * sizeof(void*));
    if (!arr) return;
    if (old) for (size_t i = 0; i < img.tls_index; ++i) arr[i] = old[i];
    arr[img.tls_index] = copy;
    if (g_verbose) fprintf(stderr, "[tlsp] old=%p need=%zu arr=%p\n", (void*)old, need, (void*)arr);
    if (!::getenv("PELOAD_NOGS")) __writegsqword(0x58, (unsigned long long)arr);
    if (g_verbose) {
        fprintf(stderr, "[tlsp] old[0]=%p old[1]=%p arr[0]=%p arr[1]=%p arr[2]=%p\n",
                (void*)(old?old[0]:0), (void*)(old?old[1]:0), (void*)arr[0], (void*)arr[1], (void*)arr[2]);
        fprintf(stderr, "[tlsp] validate=%d\n", ::HeapValidate(::GetProcessHeap(), 0, nullptr));
    }
    if (g_verbose) fprintf(stderr, "[tlsp] wrote gs:58 -> %p\n", (void*)__readgsqword(0x58));
    if (g_verbose) fprintf(stderr, "[tlsp] validate_after=%d need=%zu\n", ::HeapValidate(::GetProcessHeap(), 0, nullptr), need);
}

namespace {
struct EntryCtx {
    PFN_ENTRY fn;
    void*     base;
    const MappedImage* img;
    int       rc;
    HANDLE    done;
    HANDLE    park;
    void*     orig_array;
};

LONG CALLBACK VectoredLog(PEXCEPTION_POINTERS ep) {
    wchar_t mn[MAX_PATH] = L"?"; HMODULE mh = nullptr;
    ::GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, (LPCWSTR)ep->ExceptionRecord->ExceptionAddress, &mh);
    if (mh) ::GetModuleFileNameW(mh, mn, MAX_PATH);
    fprintf(stderr, "[veh] module=%ls rva=0x%llX\n", mn, mh ? (unsigned long long)((uintptr_t)ep->ExceptionRecord->ExceptionAddress - (uintptr_t)mh) : 0ull);
    fprintf(stderr, "[veh] code=0x%08X addr=%p rip=%p rsp=%p rax=%p rcx=%p rdi=%p\n",
            ep->ExceptionRecord->ExceptionCode, ep->ExceptionRecord->ExceptionAddress,
            (void*)ep->ContextRecord->Rip, (void*)ep->ContextRecord->Rsp,
            (void*)ep->ContextRecord->Rax, (void*)ep->ContextRecord->Rcx,
            (void*)ep->ContextRecord->Rdi);
    // Walk the faulting thread's stack so the HeapFree/av site is attributable.
    if (ep->ExceptionRecord->ExceptionCode == 0xC0000374 ||
        ep->ExceptionRecord->ExceptionCode == 0xC0000005) {
        void* fr[56] = {};
        USHORT n = RtlCaptureStackBackTrace(0, 56, fr, nullptr);
        for (USHORT i = 0; i < n; ++i) {
            HMODULE fh = nullptr; wchar_t fn[MAX_PATH] = L"?";
            ::GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS, (LPCWSTR)fr[i], &fh);
            if (fh) ::GetModuleFileNameW(fh, fn, MAX_PATH);
            fprintf(stderr, "[veh] frame[%u] %p %ls+0x%llX\n", i, fr[i], fn,
                    fh ? (unsigned long long)((uintptr_t)fr[i] - (uintptr_t)fh) : 0ull);
        }
    }
    return EXCEPTION_CONTINUE_SEARCH;
}

DWORD WINAPI EntryThread(LPVOID p) {
    auto* c = (EntryCtx*)p;
    if (g_verbose) ::AddVectoredExceptionHandler(1, VectoredLog);
    c->orig_array = (void*)__readgsqword(0x58);
    g_orig_tls_array = c->orig_array;
    PrepThreadTls(*c->img);
    if (g_verbose) {
        void* tp = (void*)__readgsqword(0x58);
        void* slot = nullptr;
        if (c->img->tls_active) slot = ::TlsGetValue(c->img->tls_index);
        fprintf(stderr, "[tlsdbg] idx=%lu teb_tlsp=%p slot=%p get=%p\n",
                (unsigned long)c->img->tls_index, tp,
                tp && c->img->tls_active ? ((void**)tp)[c->img->tls_index] : nullptr, slot);
    }
    __try {
        c->rc = c->fn(c->base, DLL_PROCESS_ATTACH);
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        c->rc = -(int)::GetExceptionCode();
    }
    // Hand the TEB's original TLS array back before the thread parks, so the
    // loader's own teardown sees the shape it created.
    if (c->orig_array) { __writegsqword(0x58, (unsigned long long)c->orig_array); g_orig_tls_array = nullptr; }
    // Do not return: keeping the thread alive defers its TLS teardown, which
    // is where the loader's implicit-TLS bookkeeping would need our grown
    // array to be a real loader allocation.
    ::SetEvent(c->done);
    ::WaitForSingleObject(c->park, INFINITE);
    return (DWORD)c->rc;
}
} // namespace

int CallEntryPoint(const MappedImage& img, const PeInfo& info) {
    if (!info.entry_rva) return -999;
    if (info.entry_rva >= img.size) return -998;

    EntryCtx ctx{ (PFN_ENTRY)(img.base + info.entry_rva), (void*)img.base, &img, 0,
                  ::CreateEventW(nullptr, TRUE, FALSE, nullptr),
                  ::CreateEventW(nullptr, TRUE, FALSE, nullptr), nullptr };
    g_exit_taken = false;
    HANDLE th = ::CreateThread(nullptr, 2u << 20, EntryThread, &ctx, 0, nullptr);
    if (!th) return -997;
    // The image may either return, raise, or call ExitProcess (which we turn
    // into ExitThread); watch the parking event and the thread itself.
    HANDLE waits[2] = { ctx.done, th };
    DWORD which = ::WaitForMultipleObjects(2, waits, FALSE, INFINITE);
    if (which == WAIT_OBJECT_0) return ctx.rc;
    DWORD code = 0;
    ::GetExitCodeThread(th, &code);
    return (int)code;
}

bool ExitWasTaken() { return g_exit_taken; }

void UnmapImage(MappedImage& img) {
    if (!img.mapped) return;
    ClearTlsIndex(img);
    ::VirtualFree((void*)img.base, 0, MEM_RELEASE);
    img.mapped = false;
    img.base = 0;
}

} // namespace peload
