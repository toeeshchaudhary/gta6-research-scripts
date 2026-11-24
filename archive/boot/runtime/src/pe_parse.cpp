// pe_parse.cpp -- PE32+ header/section/directory parsing + human report.
#include "pe_image.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <unordered_set>

namespace peload {

const char* DllClass_Name(DllClass c) {
    switch (c) {
    case DllClass::System:  return "system";
    case DllClass::Bundled: return "bundled";
    default:                return "shim";
    }
}

std::string Narrow(const std::wstring& w) {
    if (w.empty()) return {};
    int n = ::WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), nullptr, 0, nullptr, nullptr);
    std::string s((size_t)n, '\0');
    ::WideCharToMultiByte(CP_UTF8, 0, w.c_str(), (int)w.size(), s.data(), n, nullptr, nullptr);
    return s;
}

std::wstring Widen(const std::string& s) {
    if (s.empty()) return {};
    int n = ::MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), nullptr, 0);
    std::wstring w((size_t)n, L'\0');
    ::MultiByteToWideChar(CP_UTF8, 0, s.c_str(), (int)s.size(), w.data(), n);
    return w;
}

double ShannonEntropy(const uint8_t* data, size_t len) {
    if (!data || !len) return 0.0;
    uint64_t freq[256] = {};
    for (size_t i = 0; i < len; ++i) freq[data[i]]++;
    double e = 0.0;
    for (uint64_t f : freq) {
        if (!f) continue;
        double p = (double)f / (double)len;
        e -= p * std::log2(p);
    }
    return e;
}

const SectionInfo* PeInfo::find_section(uint32_t rva) const {
    for (const auto& s : sections) {
        uint32_t span = std::max(s.vsize, s.rawsize);
        if (rva >= s.va && rva < s.va + span) return &s;
    }
    return nullptr;
}

bool PeInfo::rva_in_image(uint32_t rva, uint32_t len) const {
    if (!rva || rva >= size_of_image) return false;
    if (len > size_of_image - rva) return false;
    return find_section(rva) != nullptr;
}

// Standard PE checksum (same algorithm as CheckSumMappedFile).
static uint32_t ComputeChecksum(const std::vector<uint8_t>& f, uint32_t checksum_off) {
    uint64_t sum = 0;
    size_t n = f.size();
    for (size_t i = 0; i + 1 < n; i += 2) {
        if (i == checksum_off || i == checksum_off + 2) continue;
        sum += (uint64_t)(f[i] | (f[i + 1] << 8));
        sum = (sum & 0xFFFF) + (sum >> 16);
    }
    if (n & 1) {
        sum += f[n - 1];
        sum = (sum & 0xFFFF) + (sum >> 16);
    }
    sum = (sum & 0xFFFF) + (sum >> 16);
    return (uint32_t)(sum + n);
}

static bool ReadFileBytes(const std::wstring& path, std::vector<uint8_t>& out, std::string& err) {
    HANDLE h = ::CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr,
                             OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (h == INVALID_HANDLE_VALUE) {
        err = "CreateFileW failed, GetLastError=" + std::to_string(::GetLastError());
        return false;
    }
    LARGE_INTEGER li{};
    if (!::GetFileSizeEx(h, &li)) {
        err = "GetFileSizeEx failed";
        ::CloseHandle(h);
        return false;
    }
    if (li.QuadPart <= 0 || li.QuadPart > (int64_t)1 << 31) {
        err = "file size out of range";
        ::CloseHandle(h);
        return false;
    }
    out.resize((size_t)li.QuadPart);
    size_t done = 0;
    while (done < out.size()) {
        DWORD got = 0;
        if (!::ReadFile(h, out.data() + done, (DWORD)(out.size() - done), &got, nullptr)) {
            err = "ReadFile failed, GetLastError=" + std::to_string(::GetLastError());
            ::CloseHandle(h);
            return false;
        }
        if (!got) break;
        done += got;
    }
    ::CloseHandle(h);
    if (done != out.size()) { err = "short read"; return false; }
    return true;
}

bool ParsePeFile(const std::wstring& path, PeInfo& info, std::string& err) {
    std::vector<uint8_t> f;
    if (!ReadFileBytes(path, f, err)) return false;
    if (f.size() < sizeof(IMAGE_DOS_HEADER)) { err = "file smaller than DOS header"; return false; }

    auto* dos = (const IMAGE_DOS_HEADER*)f.data();
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) {
        err = "bad MZ signature (0x" + [&] { char b[8]; sprintf_s(b, "%04X", dos->e_magic); return std::string(b); }() + ")";
        return false;
    }
    if (dos->e_lfanew <= 0 || (size_t)dos->e_lfanew + sizeof(IMAGE_NT_HEADERS64) > f.size()) {
        err = "e_lfanew out of range";
        return false;
    }
    auto* nt = (const IMAGE_NT_HEADERS64*)(f.data() + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) { err = "bad PE signature"; return false; }

    info.machine        = nt->FileHeader.Machine;
    info.characteristics= nt->FileHeader.Characteristics;
    info.timestamp      = nt->FileHeader.TimeDateStamp;
    info.num_dirs       = nt->FileHeader.SizeOfOptionalHeader >= 0x70 ? nt->OptionalHeader.NumberOfRvaAndSizes : 0;
    info.magic          = nt->OptionalHeader.Magic;
    info.subsystem      = nt->OptionalHeader.Subsystem;
    info.dll_chars      = nt->OptionalHeader.DllCharacteristics;
    info.image_base     = nt->OptionalHeader.ImageBase;
    info.section_align  = nt->OptionalHeader.SectionAlignment;
    info.file_align     = nt->OptionalHeader.FileAlignment;
    info.size_of_image  = nt->OptionalHeader.SizeOfImage;
    info.size_of_headers= nt->OptionalHeader.SizeOfHeaders;
    info.entry_rva      = nt->OptionalHeader.AddressOfEntryPoint;
    info.checksum       = nt->OptionalHeader.CheckSum;
    info.os_version_major = nt->OptionalHeader.MajorOperatingSystemVersion;
    info.os_version_minor = nt->OptionalHeader.MinorOperatingSystemVersion;
    info.subsystem_version_major = nt->OptionalHeader.MajorSubsystemVersion;
    info.subsystem_version_minor = nt->OptionalHeader.MinorSubsystemVersion;

    if (!info.is_x64()) { err = "not x86-64 (machine 0x" + std::to_string(info.machine) + ")"; return false; }
    if (!info.is_pe32plus()) { err = "not PE32+"; return false; }

    uint64_t hdr_end = (uint64_t)dos->e_lfanew + sizeof(IMAGE_NT_HEADERS64);
    if (hdr_end > f.size()) { err = "truncated optional header"; return false; }

    auto dir = [&](int i) -> const IMAGE_DATA_DIRECTORY& {
        static const IMAGE_DATA_DIRECTORY zero{};
        return (i < (int)info.num_dirs) ? nt->OptionalHeader.DataDirectory[i] : zero;
    };
    info.dir_export_rva = dir(IMAGE_DIRECTORY_ENTRY_EXPORT).VirtualAddress;
    info.dir_export_size= dir(IMAGE_DIRECTORY_ENTRY_EXPORT).Size;
    info.dir_import_rva = dir(IMAGE_DIRECTORY_ENTRY_IMPORT).VirtualAddress;
    info.dir_import_size= dir(IMAGE_DIRECTORY_ENTRY_IMPORT).Size;
    info.dir_reloc_rva  = dir(IMAGE_DIRECTORY_ENTRY_BASERELOC).VirtualAddress;
    info.dir_reloc_size = dir(IMAGE_DIRECTORY_ENTRY_BASERELOC).Size;
    info.dir_tls_rva    = dir(IMAGE_DIRECTORY_ENTRY_TLS).VirtualAddress;
    info.dir_tls_size   = dir(IMAGE_DIRECTORY_ENTRY_TLS).Size;
    info.dir_pdata_rva  = dir(IMAGE_DIRECTORY_ENTRY_EXCEPTION).VirtualAddress;
    info.dir_pdata_size = dir(IMAGE_DIRECTORY_ENTRY_EXCEPTION).Size;
    info.dir_delay_rva  = dir(IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT).VirtualAddress;
    info.dir_delay_size = dir(IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT).Size;

    // checksum
    uint32_t cks_off = (uint32_t)((const uint8_t*)&nt->OptionalHeader.CheckSum - f.data());
    info.checksum_calc = ComputeChecksum(f, cks_off);

    // sections
    auto* sec = IMAGE_FIRST_SECTION(nt);
    for (WORD i = 0; i < nt->FileHeader.NumberOfSections; ++i, ++sec) {
        if ((const uint8_t*)(sec + 1) > f.data() + f.size()) { err = "section table past EOF"; return false; }
        SectionInfo si;
        char nm[9] = {};
        memcpy(nm, sec->Name, 8);
        si.name    = nm;
        si.va      = sec->VirtualAddress;
        si.vsize   = sec->Misc.VirtualSize;
        si.rawsize = sec->SizeOfRawData;
        si.rawptr  = sec->PointerToRawData;
        si.chars   = sec->Characteristics;
        if (si.rawptr && si.rawptr < f.size())
            si.entropy = ShannonEntropy(f.data() + si.rawptr,
                                        std::min<size_t>(si.rawsize, f.size() - si.rawptr));
        info.sections.push_back(std::move(si));
    }
    if (info.sections.empty()) { err = "no sections"; return false; }

    // imports
    // --- RVA -> file-offset view ------------------------------------------
    // RVA and file offset differ whenever VirtualAddress != PointerToRawData,
    // so every directory read goes through this translation.
    auto At = [&](uint32_t rva, size_t len) -> const uint8_t* {
        if (!rva || rva >= info.size_of_image) return nullptr;
        const SectionInfo* s = info.find_section(rva);
        if (!s || !s->rawptr) return nullptr;
        uint64_t delta = (uint64_t)rva - s->va;
        if (delta + len > s->rawsize) return nullptr;
        uint64_t off = (uint64_t)s->rawptr + delta;
        if (off + len > f.size()) return nullptr;
        return f.data() + off;
    };
    auto Remaining = [&](uint32_t rva) -> size_t {
        const SectionInfo* s = info.find_section(rva);
        if (!s || !s->rawptr || rva < s->va) return 0;
        uint64_t delta = (uint64_t)rva - s->va;
        return delta >= s->rawsize ? 0 : (size_t)(s->rawsize - delta);
    };
    auto NameAt = [&](uint32_t rva) -> std::string {
        const uint8_t* p = At(rva, 1);
        if (!p) return "<bad-rva>";
        size_t max = Remaining(rva);
        const char* c = (const char*)p;
        size_t n = 0;
        while (n < max && c[n]) n++;
        return std::string(c, n);
    };

    // imports
    if (const uint8_t* dp = At(info.dir_import_rva, sizeof(IMAGE_IMPORT_DESCRIPTOR))) {
        auto at = [&](size_t i) { return (const IMAGE_IMPORT_DESCRIPTOR*)dp + i; };
        for (size_t di = 0; at(di)->Name && Remaining(info.dir_import_rva) >= (di + 1) * sizeof(IMAGE_IMPORT_DESCRIPTOR); ++di) {
            const IMAGE_IMPORT_DESCRIPTOR* d = at(di);
            ImportDll id;
            id.name = NameAt(d->Name);
            uint32_t hint = d->OriginalFirstThunk ? d->OriginalFirstThunk : d->FirstThunk;
            if (const uint8_t* tp = At(hint, 8)) {
                size_t n = Remaining(hint) / 8;
                for (size_t k = 0; k < n && ((const uint64_t*)tp)[k]; ++k) {
                    uint64_t v = ((const uint64_t*)tp)[k];
                    ImportFn fn;
                    if (v & IMAGE_ORDINAL_FLAG64) { fn.by_ordinal = true; fn.ordinal = (uint16_t)(v & 0xFFFF); }
                    else fn.name = NameAt((uint32_t)(v & 0x7FFFFFFF) + 2);
                    id.fns.push_back(std::move(fn));
                }
            }
            info.imports.push_back(std::move(id));
        }
    }

    // delay imports
    if (const uint8_t* dp = At(info.dir_delay_rva, sizeof(IMAGE_DELAYLOAD_DESCRIPTOR))) {
        auto at = [&](size_t i) { return (const IMAGE_DELAYLOAD_DESCRIPTOR*)dp + i; };
        for (size_t di = 0; at(di)->DllNameRVA &&
             Remaining(info.dir_delay_rva) >= (di + 1) * sizeof(IMAGE_DELAYLOAD_DESCRIPTOR); ++di) {
            const IMAGE_DELAYLOAD_DESCRIPTOR* d = at(di);
            bool rva_based = (d->Attributes.AllAttributes & 1) != 0;
            auto fix = [&](uint32_t v) -> uint32_t {
                return rva_based ? v : (uint32_t)((uint64_t)v - info.image_base);
            };
            ImportDll id;
            id.name = NameAt(fix(d->DllNameRVA));
            uint32_t int_rva = fix(d->ImportNameTableRVA);
            if (const uint8_t* tp = At(int_rva, 8)) {
                size_t n = Remaining(int_rva) / 8;
                for (size_t k = 0; k < n && ((const uint64_t*)tp)[k]; ++k) {
                    uint64_t v = ((const uint64_t*)tp)[k];
                    ImportFn fn;
                    if (v & IMAGE_ORDINAL_FLAG64) { fn.by_ordinal = true; fn.ordinal = (uint16_t)(v & 0xFFFF); }
                    else fn.name = NameAt((uint32_t)(v & 0x7FFFFFFF) + 2);
                    id.fns.push_back(std::move(fn));
                }
            }
            info.delay_imports.push_back(std::move(id));
        }
    }

    // exports
    if (const uint8_t* ep = At(info.dir_export_rva, sizeof(IMAGE_EXPORT_DIRECTORY))) {
        auto* ed = (const IMAGE_EXPORT_DIRECTORY*)ep;
        uint32_t nf = std::min<uint32_t>(ed->NumberOfFunctions, 8192);
        uint32_t nn = std::min<uint32_t>(ed->NumberOfNames, 8192);
        auto* funcs = (const uint32_t*)At(ed->AddressOfFunctions, (size_t)nf * 4);
        auto* names = (const uint32_t*)At(ed->AddressOfNames, (size_t)nn * 4);
        auto* ords  = (const uint16_t*)At(ed->AddressOfNameOrdinals, (size_t)nn * 2);
        if (funcs) for (uint32_t i = 0; i < nf; ++i) {
            if (!funcs[i]) continue;
            ExportFn e;
            e.rva = funcs[i];
            e.ordinal = ed->Base + i;
            e.forwarded = funcs[i] >= info.dir_export_rva &&
                          funcs[i] < info.dir_export_rva + info.dir_export_size;
            info.exports.push_back(e);
        }
        if (names && ords) for (uint32_t i = 0; i < nn; ++i) {
            uint32_t oi = ords[i];
            if (oi >= nf) continue;
            for (auto& e : info.exports) {
                if (e.ordinal == ed->Base + oi && e.name.empty()) { e.name = NameAt(names[i]); break; }
            }
        }
    }

    // .pdata (RUNTIME_FUNCTION count comes from the directory size)
    if (info.dir_pdata_rva && info.dir_pdata_size &&
        info.rva_in_image(info.dir_pdata_rva, info.dir_pdata_size))
        info.runtime_functions = info.dir_pdata_size / sizeof(RUNTIME_FUNCTION);
    else
        info.runtime_functions = 0;

    info.checksum_ok = (info.checksum == 0) || (info.checksum == info.checksum_calc);
    return true;
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------

static const char* SubsystemName(uint16_t s) {
    switch (s) {
    case 1:  return "NATIVE";
    case 2:  return "WINDOWS_GUI";
    case 3:  return "WINDOWS_CUI (console)";
    case 5:  return "OS2_CUI";
    case 7:  return "POSIX_CUI";
    case 9:  return "WINDOWS_CE_GUI";
    case 10: return "EFI_APPLICATION";
    case 16: return "WINDOWS_BOOT_APPLICATION";
    case 17: return "XBOX (IMAGE_SUBSYSTEM_XBOX) -- stock loader rejects";
    default: return "UNKNOWN";
    }
}

static void DllCharFlags(uint16_t v, std::string& out) {
    struct { uint16_t bit; const char* n; } m[] = {
        {0x0020,"HIGH_ENTROPY_VA"},{0x0040,"DYNAMIC_BASE"},{0x0080,"FORCE_INTEGRITY"},
        {0x0100,"NX_COMPAT"},{0x0200,"NO_ISOLATION"},{0x0400,"NO_SEH"},
        {0x0800,"NO_BIND"},{0x1000,"APPCONTAINER"},{0x2000,"WDM_DRIVER"},
        {0x4000,"GUARD_CF"},{0x8000,"TERMINAL_SERVER_AWARE"} };
    for (auto& e : m) if (v & e.bit) { out += e.n; out += ' '; }
    if (out.empty()) out = "<none>";
}

static void SectionFlags(uint32_t c, std::string& out) {
    if (c & IMAGE_SCN_MEM_EXECUTE) out += "X";
    if (c & IMAGE_SCN_MEM_READ)    out += "R";
    if (c & IMAGE_SCN_MEM_WRITE)   out += "W";
    if (c & IMAGE_SCN_CNT_CODE)    out += " code";
    if (c & IMAGE_SCN_CNT_INITIALIZED_DATA) out += " idata";
    if (c & IMAGE_SCN_CNT_UNINITIALIZED_DATA) out += " bss";
    if (c & IMAGE_SCN_MEM_DISCARDABLE) out += " discard";
    if (out.empty()) out = "-";
}

void PrintReport(const PeInfo& info, const std::wstring& gameDir,
                 const std::wstring& path, bool entries) {
    printf("==== IMAGE REPORT ====\n");
    printf("path              : %s\n", Narrow(path).c_str());
    printf("machine           : 0x%04X %s\n", info.machine, info.is_x64() ? "(AMD64)" : "(NOT x64!)");
    printf("magic             : 0x%04X %s\n", info.magic, info.is_pe32plus() ? "(PE32+)" : "(NOT PE32+!)");
    printf("subsystem         : %u  %s\n", info.subsystem, SubsystemName(info.subsystem));
    printf("  -> accepted by stock Win loader: %s\n",
           (info.subsystem == 1 || info.subsystem == 2 || info.subsystem == 3) ? "yes" : "NO (needs custom loader)");
    std::string fc; DllCharFlags(info.dll_chars, fc);
    printf("DllCharacteristics: 0x%04X %s\n", info.dll_chars, fc.c_str());
    printf("characteristics   : 0x%04X %s\n", info.characteristics, info.is_dll() ? "(DLL)" : "(EXE)");
    printf("image base        : 0x%llX\n", (unsigned long long)info.image_base);
    printf("entry RVA         : 0x%X\n", info.entry_rva);
    printf("section alignment : 0x%X\n", info.section_align);
    printf("file alignment    : 0x%X\n", info.file_align);
    printf("  align match: %s (mapped images require SectionAlign >= 0x1000)\n",
           info.section_align == info.file_align ? "EQUAL (unusual)" : "differ (normal)");
    printf("size of image     : 0x%X (%.1f KiB)\n", info.size_of_image, info.size_of_image / 1024.0);
    printf("size of headers   : 0x%X\n", info.size_of_headers);
    printf("size of stack rsv : 0x%llX\n", (unsigned long long)0);
    printf("subsystem version : %u.%u\n", info.subsystem_version_major, info.subsystem_version_minor);
    printf("OS version        : %u.%u\n", info.os_version_major, info.os_version_minor);
    printf("checksum          : 0x%08X stored / 0x%08X computed -> %s\n",
           info.checksum, info.checksum_calc, info.checksum_ok ? "ok" : "MISMATCH");
    printf("num rva and sizes : %u\n", info.num_dirs);
    printf("has .reloc        : %s (size 0x%X)\n", info.has_reloc() ? "yes" : "no", info.dir_reloc_size);
    printf("has .pdata        : %s  RUNTIME_FUNCTION entries: %u\n", info.has_pdata() ? "yes" : "no",
           info.runtime_functions);
    printf("TLS directory     : %s\n", info.has_tls() ? "PRESENT" : "absent");
    printf("delay-load imports: %s (%zu dll, %zu fn)\n", info.has_delay() ? "PRESENT" : "absent",
           info.delay_imports.size(),
           [&] { size_t n = 0; for (auto& d : info.delay_imports) n += d.fns.size(); return n; }());

    printf("\n-- sections (%zu) --\n", info.sections.size());
    printf("%-10s %-10s %-10s %-10s %-7s %-6s %s\n", "name", "VA", "VSize", "RawSize", "Entropy", "Flags", "note");
    for (const auto& s : info.sections) {
        std::string fl; SectionFlags(s.chars, fl);
        const char* note = "";
        if (s.entropy > 7.2) note = "very high entropy (compressed/packed/encrypted)";
        else if (s.entropy > 6.5) note = "high entropy";
        else if (s.vsize > s.rawsize && s.rawsize) note = "BSS tail";
        else if (!s.rawsize) note = "uninitialized (BSS)";
        printf("%-10s 0x%-8X 0x%-8X 0x%-8X %-7.3f %-6s %s\n",
               s.name.c_str(), s.va, s.vsize, s.rawsize, s.entropy, fl.c_str(), note);
    }

    // ---- imports classification ----
    size_t n_sys = 0, n_bun = 0, n_shim = 0, fn_total = 0;
    for (const auto& d : info.imports) {
        fn_total += d.fns.size();
        switch (ClassifyDll(d.name, gameDir)) {
        case DllClass::System:  n_sys++;  break;
        case DllClass::Bundled: n_bun++;  break;
        default:                n_shim++; break;
        }
    }
    printf("\n-- imports: %zu DLLs, %zu functions --\n", info.imports.size(), fn_total);
    printf("   system=%zu  bundled=%zu  shim=%zu\n", n_sys, n_bun, n_shim);

    auto dump = [&](const char* title, const std::vector<ImportDll>& v, bool cls) {
        printf("\n%s\n", title);
        if (v.empty()) { printf("  <none>\n"); return; }
        for (const auto& d : v) {
            if (cls) printf("  [%-7s] %s\n", DllClass_Name(ClassifyDll(d.name, gameDir)), d.name.c_str());
            else     printf("  %s\n", d.name.c_str());
            if (entries) for (const auto& f : d.fns) {
                if (f.by_ordinal) printf("      #%u\n", f.ordinal);
                else              printf("      %s\n", f.name.c_str());
            }
        }
    };
    dump("-- system imports --", [&] {
        std::vector<ImportDll> r;
        for (auto& d : info.imports) if (ClassifyDll(d.name, gameDir) == DllClass::System) r.push_back(d);
        return r; }(), true);
    dump("-- bundled imports --", [&] {
        std::vector<ImportDll> r;
        for (auto& d : info.imports) if (ClassifyDll(d.name, gameDir) == DllClass::Bundled) r.push_back(d);
        return r; }(), true);
    dump("-- shim imports (need reimplementation) --", [&] {
        std::vector<ImportDll> r;
        for (auto& d : info.imports) if (ClassifyDll(d.name, gameDir) == DllClass::Shim) r.push_back(d);
        return r; }(), true);
    if (!info.delay_imports.empty()) dump("-- DELAY-LOAD imports --", info.delay_imports, false);

    printf("\n-- exports: %zu --\n", info.exports.size());
    if (!info.exports.empty()) {
        size_t shown = 0;
        for (const auto& e : info.exports) {
            if (shown++ >= 40) { printf("  ... (%zu more)\n", info.exports.size() - 40); break; }
            printf("  #%u %s%s%s\n", e.ordinal, e.name.empty() ? "<ordinal-only>" : e.name.c_str(),
                   e.forwarded ? " -> forwarded: " : "", e.forwarded ? "" : "");
        }
    }
    printf("==== END REPORT ====\n");
}

} // namespace peload
