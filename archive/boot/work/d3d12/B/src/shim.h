// shim.h -- per-DLL shim tables + generated logging miss-thunks.
#pragma once
#include <windows.h>

#include <cstdio>
#include <string>
#include <vector>

namespace peload {

// True if `dll` has a hand-written shim table at all.
bool ShimHasTable(const char* dll);

// Resolve one shimmed import to a callable address.
// Returns nullptr if the shim table has no entry for it.
// `is_real` (optional) reports whether the returned pointer is a real
// implementation rather than nothing.
void* ShimLookup(const char* dll, const char* fn);

// Build a logging stub for an unimplemented import. The thunk logs
// "SHIM-MISS dll!fn" once per call to `log_stream`, returns `retval` in RAX
// (and zero in XMM0 for float returns), then returns to the caller.
// Returns nullptr on allocation failure.
void* ShimMakeMissThunk(const char* dll, const char* fn, uintptr_t retval);

struct ShimMiss {
    std::string dll, fn;
};
const std::vector<ShimMiss>& ShimMisses();
size_t ShimMissCallCount();

// Redirect thunk logging (default stderr).
void ShimSetLogFile(FILE* f);

} // namespace peload
