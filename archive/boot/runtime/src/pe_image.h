// pe_image.h -- x64 PE32+ image parser / mapper / import binder.
// Part of the GTA VI (Xbox Series) host runtime. See PE_LOADER.md.
#pragma once

#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>

#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

namespace peload {

enum class DllClass { System, Bundled, Shim };

const char* DllClass_Name(DllClass c);

struct SectionInfo {
    std::string name;
    uint32_t    va       = 0;
    uint32_t    vsize    = 0;
    uint32_t    rawsize  = 0;
    uint32_t    rawptr   = 0;
    uint32_t    chars    = 0;
    double      entropy  = 0.0;
};

struct ImportFn {
    std::string name;
    uint16_t    ordinal    = 0;
    bool        by_ordinal = false;
};

struct ImportDll {
    std::string           name;
    std::vector<ImportFn> fns;
};

struct ExportFn {
    std::string name;      // empty for ordinal-only (non-forwarded) exports
    uint32_t    ordinal = 0;
    uint32_t    rva     = 0;
    bool        forwarded = false;
};

class PeInfo {
public:
    // --- identity / headers -------------------------------------------------
    uint16_t machine        = 0;
    uint16_t magic          = 0;
    uint16_t subsystem      = 0;
    uint16_t dll_chars      = 0;
    uint16_t characteristics= 0;
    uint32_t timestamp      = 0;
    uint64_t image_base     = 0;
    uint32_t section_align  = 0;
    uint32_t file_align     = 0;
    uint32_t size_of_image  = 0;
    uint32_t size_of_headers= 0;
    uint32_t entry_rva      = 0;
    uint32_t checksum       = 0;
    uint32_t checksum_calc  = 0;
    bool     checksum_ok    = false;
    uint32_t num_dirs       = 0;

    // --- data directories of interest --------------------------------------
    uint32_t dir_import_rva   = 0, dir_import_size   = 0;
    uint32_t dir_export_rva   = 0, dir_export_size   = 0;
    uint32_t dir_reloc_rva    = 0, dir_reloc_size    = 0;
    uint32_t dir_tls_rva      = 0, dir_tls_size      = 0;
    uint32_t dir_pdata_rva    = 0, dir_pdata_size    = 0;
    uint32_t dir_delay_rva    = 0, dir_delay_size    = 0;

    std::vector<SectionInfo> sections;
    std::vector<ImportDll>   imports;
    std::vector<ImportDll>   delay_imports;
    std::vector<ExportFn>    exports;

    bool is_dll() const  { return (characteristics & IMAGE_FILE_DLL) != 0; }
    bool is_x64() const  { return machine == IMAGE_FILE_MACHINE_AMD64; }
    bool is_pe32plus() const { return magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC; }

    bool has_reloc()  const { return dir_reloc_size  != 0; }
    bool has_tls()    const { return dir_tls_size    != 0; }
    bool has_pdata()  const { return dir_pdata_size  != 0; }
    bool has_delay()  const { return dir_delay_size  != 0; }
    bool has_exports()const { return dir_export_size != 0; }

    uint32_t runtime_functions = 0;   // .pdata entries (size / 12)
    uint16_t subsystem_version_major = 0, subsystem_version_minor = 0;
    uint16_t os_version_major = 0, os_version_minor = 0;

    // Number of imports that cannot possibly be satisfied by the OS loader
    // because the image is not a stock Windows image (subsystem 17 etc.).
    const SectionInfo* find_section(uint32_t rva) const;
    bool rva_in_image(uint32_t rva, uint32_t len) const;
};

// Parse a PE32+ file from disk into `info`. Returns false and fills `err`.
bool ParsePeFile(const std::wstring& path, PeInfo& info, std::string& err);

// Classify one imported DLL name. `gameDir` may be empty (then nothing is
// classified as bundled).
DllClass ClassifyDll(const std::string& dll, const std::wstring& gameDir);

// Full report of everything required by the task spec.
void PrintReport(const PeInfo& info, const std::wstring& gameDir,
                 const std::wstring& path, bool entries);

struct RelocStats {
    uint32_t blocks = 0, entries = 0, applied = 0, skipped_abs = 0, unknown = 0;
    bool     ok = false;
    std::string err;
};

struct BindStats {
    uint32_t descriptors = 0, bound = 0, shim_real = 0, shim_stub = 0;
    uint32_t missing = 0, thrown = 0;
    uint32_t delay_descriptors = 0, delay_bound = 0, delay_missing = 0;
    std::vector<std::string> unbound;   // "dll!func  (reason)"
    bool ok = false;
    std::string err;
};

class MappedImage {
public:
    uintptr_t base      = 0;
    size_t    size      = 0;
    uintptr_t preferred = 0;
    bool      mapped    = false;
    bool      relocated = false;
    RelocStats reloc;
    BindStats  bind;

    void* tls_template = nullptr;   // owned allocation for the TLS template
    DWORD tls_index    = 0;
    bool  tls_active   = false;
    size_t tls_total   = 0;
};

// Reserve + commit at `prefer_base` (0 => use the image's ImageBase), copy
// sections, apply relocations, zero BSS tails, set up TLS. Does not bind
// imports. Returns false on fatal error.
bool MapImage(const PeInfo& info, const std::vector<uint8_t>& file,
              uintptr_t prefer_base, MappedImage& out);

// Resolve every thunk: system/bundled via LoadLibrary+GetProcAddress, shim via
// the shim table (real handler or a logging miss thunk).
bool BindImports(MappedImage& img, const PeInfo& info,
                 const std::wstring& gameDir, DllClass (*classifier)(const std::string&, const std::wstring&));

// Install the image's own .pdata via RtlAddFunctionTable.
bool InstallUnwindInfo(const MappedImage& img, const PeInfo& info, std::string& err);
void RemoveUnwindInfo(const MappedImage& img, const PeInfo& info);

// Tuning knobs.
void MapSetStubRetval(uintptr_t v);   // value returned by miss/stub thunks
void MapSetVerbose(bool v);

// Apply final section protections (image is RW in RAM until this point).
bool SealProtections(const MappedImage& img, const PeInfo& info, std::string& err);

// Call TLS callbacks / DllMain-style notify for an image being loaded.
void NotifyTlsCallbacks(const MappedImage& img, const PeInfo& info, bool attach);

// Run the entry point as an EXE entry (rcx=ImageBase, rdx=0). Returns exit
// code; negative values encode a structured exception.
int CallEntryPoint(const MappedImage& img, const PeInfo& info);

// Replace ExitProcess/RtlExitUserProcess IAT slots with a guard so a mapped
// CRT's terminating exit() returns to the harness instead of killing it.
void PatchExitImports(MappedImage& img, const PeInfo& info);
bool ExitWasTaken();
void PrepThreadTls(const MappedImage& img);

void UnmapImage(MappedImage& img);

// Utility
double ShannonEntropy(const uint8_t* data, size_t len);
std::string Narrow(const std::wstring& w);
std::wstring Widen(const std::string& s);

} // namespace peload
