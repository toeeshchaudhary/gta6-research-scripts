// peload.cpp -- CLI driver for the x64 PE image loader harness.
//
//   peload <image> --game-dir <dir> [--check-only] [--dry-run] [--exec]
//          [--prefer-base 0x...] [--entries] [--stub-returns-fail] [--strict]
//          [--call-tls] [--keep] [--verbose]
//
// Exit codes:
//   0 ok        1 usage       2 parse error      3 map/bind error
//   4 entry point raised / exec guard fired      5 unbound imports with --strict
#include "pe_image.h"
#include "shim.h"

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

using namespace peload;

namespace {

void Usage() {
    printf(
        "usage: peload <image.exe|image.dll> --game-dir <folder> [options]\n"
        "\n"
        "  --game-dir <dir>     folder holding the bundled game DLLs (required)\n"
        "  --check-only         parse and report only; never map\n"
        "  --dry-run            map + bind + install unwind, do not run entry (default)\n"
        "  --exec               also call the entry point (test executables only)\n"
        "  --prefer-base 0x...  force this base instead of ImageBase (relocation test)\n"
        "  --entries            list every imported function\n"
        "  --stub-returns-fail  stub/miss thunks return E_NOTIMPL instead of 0\n"
        "  --strict             exit 5 if any import could not be bound\n"
        "  --call-tls           invoke TLS callbacks on load\n"
        "  --keep               leave the image mapped until process exit\n"
        "  --verbose            extra mapping detail\n");
}

bool StartsWith(const char* s, const char* p) { return ::strncmp(s, p, ::strlen(p)) == 0; }

} // namespace

int main(int argc, char** argv) {
    std::wstring image;
    std::wstring gameDir;
    uintptr_t preferBase = 0;
    bool checkOnly = false, exec = false, entries = false, strict = false,
         callTls = false, keep = false, verbose = false;

    for (int i = 1; i < argc; ++i) {
        const char* a = argv[i];
        if (StartsWith(a, "--game-dir")) {
            if (i + 1 >= argc) { Usage(); return 1; }
            gameDir = Widen(argv[++i]);
        } else if (StartsWith(a, "--prefer-base")) {
            if (i + 1 >= argc) { Usage(); return 1; }
            preferBase = (uintptr_t)::_strtoui64(argv[++i], nullptr, 0);
        } else if (!::strcmp(a, "--check-only")) checkOnly = true;
        else if (!::strcmp(a, "--dry-run"))  exec = false;
        else if (!::strcmp(a, "--exec"))     exec = true;
        else if (!::strcmp(a, "--entries"))  entries = true;
        else if (!::strcmp(a, "--strict"))   strict = true;
        else if (!::strcmp(a, "--call-tls")) callTls = true;
        else if (!::strcmp(a, "--keep"))     keep = true;
        else if (!::strcmp(a, "--trace-d3d12")) { verbose = true; _putenv_s("PELOAD_TRACE", "1"); }
        else if (!::strcmp(a, "--verbose"))  verbose = true;
        else if (!::strcmp(a, "--stub-returns-fail")) MapSetStubRetval(0x80004001u);
        else if (StartsWith(a, "--")) { printf("unknown option: %s\n", a); Usage(); return 1; }
        else if (image.empty()) image = Widen(a);
        else { printf("extra positional argument: %s\n", a); return 1; }
    }
    if (image.empty() || gameDir.empty()) { Usage(); return 1; }
    MapSetVerbose(verbose);

    // ---- parse ------------------------------------------------------------
    PeInfo info;
    std::string err;
    if (!ParsePeFile(image, info, err)) {
        printf("PARSE FAILED for %s: %s\n", Narrow(image).c_str(), err.c_str());
        return 2;
    }

    PrintReport(info, gameDir, image, entries);

    if (info.subsystem != 1 && info.subsystem != 2 && info.subsystem != 3)
        printf("\nNOTE: subsystem %u (%s) is rejected by the stock Windows loader; "
               "this harness maps it anyway.\n", info.subsystem,
               info.subsystem == 17 ? "XBOX" : "non-Windows");

    if (checkOnly) { printf("\n(check-only: image not mapped)\n"); return 0; }

    // ---- map --------------------------------------------------------------
    std::vector<uint8_t> bytes;
    {
        // ParsePeFile already read the file; read it again for the mapper.
        HANDLE h = ::CreateFileW(image.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
                                 OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        if (h == INVALID_HANDLE_VALUE) { printf("open failed\n"); return 3; }
        LARGE_INTEGER li{};
        ::GetFileSizeEx(h, &li);
        if (li.QuadPart > 0) {
            bytes.resize((size_t)li.QuadPart);
            DWORD got = 0;
            ::ReadFile(h, bytes.data(), (DWORD)bytes.size(), &got, nullptr);
        }
        ::CloseHandle(h);
    }

    MappedImage img;
    if (!MapImage(info, bytes, preferBase, img)) {
        printf("\nMAP FAILED: %s\n", img.reloc.err.c_str());
        return 3;
    }
    printf("\nMAPPED at 0x%llX (preferred 0x%llX), size 0x%zX\n",
           (unsigned long long)img.base, (unsigned long long)img.preferred, img.size);
    if (img.relocated) {
        printf("RELOCATED: delta applied for %u/%u entries in %u blocks (%u ABSOLUTE skipped, %u unknown)\n",
               img.reloc.applied, img.reloc.entries, img.reloc.blocks, img.reloc.skipped_abs,
               img.reloc.unknown);
    }

    // ---- bind -------------------------------------------------------------
    BindImports(img, info, gameDir, nullptr);
    // Rewrap the free-form signature into the plain function pointer type.
    printf("IMPORTS: %u descriptors; bound=%u shim-real=%u shim-stub=%u MISSING=%u\n",
           img.bind.descriptors, img.bind.bound, img.bind.shim_real, img.bind.shim_stub,
           img.bind.missing);
    if (img.bind.delay_descriptors)
        printf("DELAY IMPORTS: %u descriptors; bound=%u missing=%u\n",
               img.bind.delay_descriptors, img.bind.delay_bound, img.bind.delay_missing);
    if (!img.bind.unbound.empty()) {
        printf("UNBOUND (%zu):\n", img.bind.unbound.size());
        for (const auto& u : img.bind.unbound) printf("  ! %s\n", u.c_str());
    }

    // The exec guard rewrites IAT slots, which must happen before sealing.
    if (exec) PatchExitImports(img, info);

    // ---- unwind -----------------------------------------------------------
    std::string uerr;
    if (InstallUnwindInfo(img, info, uerr))
        printf(".pdata: %u RUNTIME_FUNCTION entries registered via RtlAddFunctionTable\n",
               info.runtime_functions);
    else
        printf(".pdata: registration FAILED: %s\n", uerr.c_str());

    std::string perr;
    if (!SealProtections(img, info, perr)) {
        printf("protection sealing FAILED: %s\n", perr.c_str());
        return 3;
    }

    int rc = 0;
    // ---- execute ----------------------------------------------------------
    if (exec) {
        if (info.is_dll()) {
            printf("entry: image is a DLL; binding only (exports are not invoked)\n");
        } else {
            printf("EXEC: calling entry point RVA 0x%X\n", info.entry_rva);
            ::fflush(stdout);
            if (callTls) NotifyTlsCallbacks(img, info, true);
            int code = CallEntryPoint(img, info);
            ::fflush(stdout);
            if (ExitWasTaken())
                printf("EXEC: image called ExitProcess(%d) -- exit code 0x%08X "
                       "(guard returned to harness)\n", code, (unsigned)code);
            else
                printf("EXEC: entry returned %d (0x%08X)\n", code, (unsigned)code);
            rc = code;
            if (code < 0 && code > -1000) { rc = 4; printf("EXEC: structured exception 0x%08X\n", (unsigned)-code); }
        }
    } else {
        printf("(dry-run: entry point not executed)\n");
    }

    if (strict && img.bind.missing) { printf("STRICT: %u unbound imports\n", img.bind.missing); rc = 5; }

    printf("shim miss thunks live: %zu\n", ShimMisses().size());

    if (keep) {
        printf("image left mapped at 0x%llX\n", (unsigned long long)img.base);
        return rc;
    }
    RemoveUnwindInfo(img, info);
    UnmapImage(img);
    printf("image unmapped\n");
    return rc;
}
