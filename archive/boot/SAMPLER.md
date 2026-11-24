# Slots 86 / 108 and the post-sampler diagnostic failure

Checkout: `work/astra/sampler-86108` (copy of `work/astra/sampler-validation`, base **a989b11**, branch
`retail-sampler-validation`). Build `work/astra/sampler-86108-build` (`build-86108.cmd`); runs from
`work/astra` with `LEONIDA_D3D12=vulkan`, `LEONIDA_SHADERS=work/astra/shaders-probe`, and `LEONIDA_SKIP_INT3=1`
for the diagnostic leg. GPU: NVIDIA GeForce GTX 1060 6GB, Vulkan backend.

Deliverable commit: **4e7c8a8a5fd6f7e11f495874eaa710484c75ad82**, the five commits of PR #8517 on a989b11
(`8f8f7d1` route 86/101/108 · `9554992` 56-byte desc stride · `bd20968` 1025-descriptor batch · `ec77f46`
test fixed array · `4e7c8a8` call through queried interfaces). 5 files, +484/−19. Applies by itself: it needs
nothing outside `runtime/shims/d3d12_xs_device.{h,cpp}` and `runtime/test/*` (the two docs lines are optional).

---

## 1. The two pull requests

Both open on `ItsNotRexed/Leonida`, both mergeable, both five commits, both touching
`docs/d3d12_vulkan.md`, `runtime/shims/d3d12_xs_device.{h,cpp}`, `runtime/test/device_proxy_test.cpp`,
`runtime/test/xs_proxy_mock_test.cpp`.

| | #7201 `justr4mzi` | #8517 `Hiiva` |
|---|---|---|
| title | "route device slots 86, 101, and 108 to PC Device2/Device5/Device8" | "use queried interfaces for slots 86, 101 and 108" |
| head / base | `1d080f4a` / `8575d36ed` | `07b32da9` / `867d922f0` |
| size | 5 commits, +360/−6 | 5 commits (the four of #7201 through `8e765684`, then `07b32da9`), +467/−7 |
| ancestry | base `8575d36ed` is an ancestor of a989b11 | base `867d922f0` **is** an ancestor of a989b11, and #8517 contains all four #7201 commits |

**Interface each method needs.** Slot 86 `CreatePipelineStateX(desc, riid, out)` needs PC
`ID3D12Device2::CreatePipelineState` (PC slot 47); slot 101 `CreateStateObjectX` needs
`ID3D12Device5::CreateStateObject` (PC slot 62, displaced on Xbox by compute-PSO slot 62); slot 108
`GetResourceAllocationInfo2X` needs `ID3D12Device8::GetResourceAllocationInfo2` (PC slot 68).

**How it is acquired.**

- #7201 never queries. It indexes the *base* device vtable — `self->real_vtable[47]`, `[62]`, `[68]` — and treats
  `slot_count > PC-slot` as proof that the interface exists. This assumes the extended interface has the same
  pointer and vtable as `ID3D12Device`.
- #8517 queries per call: `real->QueryInterface(__uuidof(ID3D12Device2|5|8), &p)`, calls `p->Method(...)`,
  then `p->Release()`.

**Interface lifetime.** #7201 borrows the base device: no reference is added, nothing is held, nothing is
released. #8517 holds the interface for exactly one call, and releases it on every path (success, backend
failure, after the QI check).

**What the caller gets when the interface is unavailable.**

- #7201: `slot_count <= 47/62/68` -> `refuse_beyond_device` -> `E_NOINTERFACE`, `*out` pre-nulled (86/101); for
  108 `{UINT64_MAX, 0}` in the return buffer, that buffer's address in RAX. The gap: when a distinct interface
  pointer exists but `slot_count` is high, nothing is detected and the call goes through the base vtable entry,
  which may be an unrelated method of different arity.
- #8517: QI failure -> the QI HRESULT (or `E_NOINTERFACE` if QI succeeds with a null pointer), `*out` nulled;
  108 -> `{UINT64_MAX, 0}`; measured on the retail title, that path is only reached for a runtime that answers
  `slot_count > 68` but then fails QI(Device8), i.e. it is defensive.

**Tests.** #7201: refusals by interface level, forwarding, both slot-108 caller ABIs, Xbox layout/flag
normalisation, a 1025-descriptor batch; 12/12 ctests on an RX 6700 XT. #8517 adds
`check_distinct_device_interfaces`, a fixture with **one COM identity and two pointers** (base and extension
tables): it asserts the extension receiver is used and the base one untouched, that a failing backend HRESULT
propagates, and that `refs` returns to 0 after each call — with a negative control that exits 1 against #7201's
production code.

**Choice: #8517.** It is a superset (contains #7201 exactly) plus the pointer/vtable correction, and its base is
an ancestor of our checkout, so it applies without dropping anything. Worth recording: on this machine
`QueryInterface(__uuidof(ID3D12Device8))` returns the *same* pointer as the base device (measured:
`[dbg] slot86 device2=0x…0F70 real=0x…0F70`), so the retail run cannot tell the two PRs apart. Only the mock
fixture with distinct pointers separates them. The choice is therefore correctness-under-the-spec, not a
measured retail difference.

---

## 2. Synthetic controls (no game data)

`sampler-86108-build/xs_proxy_mock_test.exe` — PASS, 10 allocations refused on purpose, including
`slots 86/101/108 use distinct QI pointers, preserve results and balance references`. That fixture supplies one
IUnknown identity at two pointers: the base table has no 47/62/68 receiver, the extension table has them, and
`QueryInterface(Device8)` deliberately does not return the base pointer. It checks the receiver that was called
(`extension->calls[47]`, `base->calls[47] == 0`), the arguments that arrived, that `*out` starts non-null and
comes back null, that a failing backend returns `E_ABORT` to the caller, and that `extension->refs` is 0 after
every path (the QI reference is balanced).

**Interface levels, PC-vtable sizes.** `check_levels` walks devices with 44 (Device), 47 (Device1), 51
(Device3) and 76 (Device9) PC slots and asserts, for each: slots 86/101 forward when the PC slot they need is
inside the table and refuse `E_NOTIMPL` with a nulled output when it is not; slot 108 returns the real
allocation info when `slot_count > 68` and `{UINT64_MAX, 0}` otherwise. `check_xbox_slots` runs on a
**Device11 device with 80 PC vtable slots** — the PC table size that 86 and 108 sit beyond — and there all three
slots still work, because the handlers index PC slots 47/62/68 and never the console slot number. That is the
assumption that breaks if a handler indexes by number, and the tests cover it explicitly.
`device_proxy_test.exe` (WARP, real `ID3D12Device8`): `PASS slot 86 creates a PSO via PC
ID3D12Device2::CreatePipelineState (slot 47)` and `PASS slot 108 C-ABI GetResourceAllocationInfo2 with 56-byte
Xbox descs matches PC Device8`. Its 4 failures are pre-existing at a989b11 ("slot 48's queue is a compute queue
with the console flags dropped", recorded in `work/astra/PROGRESS.md`) and touch neither slot.

---

## 3. Before / after on the retail diagnostic

Same harness, same package, one run each side; `LEONIDA_SKIP_INT3=1` masks the title's own `int3` asserts in
both legs, so the skipped set is stated per run. The slot 86/108 return values and the two counts come from an
instrumented build of the same commit (extra `[dbg]` prints only, no behaviour change); the failure positions are
from the clean builds.

| | before (a989b11, 368 log lines) | after (4e7c8a8, 368 log lines) |
|---|---|---|
| int3 skipped | `+0x247af2d`, `+0x19f4f58`, `+0x1e6c2c5` (3) | the same three **plus `+0xcc2936`** (4) |
| slot 86 | forwarded, `E_NOTIMPL` ("beyond the PC device vtable (80 slots)"), 6 calls, tolerated | handler, 6 calls, `E_INVALIDARG` (`0x80070057`), `*out` null, stream length `0x2b0` |
| slot 108 | forwarded with the return buffer as `this` | handler, returns the struct |
| first failure | AV **at `0x44`**, `[rsp] = game+0xabfe0d` | AV at `game+0xcc2861`, read at `0x10`, `[rsp] = game+0x5bfec15` |

**The 0x44 fault disappears; it does not move to a neighbouring address.** What it is replaced by is a different,
later failure of a different origin (§4).

**Slot 108's return, measured** (`[dbg] slot108`, one call of two, from an instrumented build of the same commit):
`visible_mask=1 count=1 descs=… info1=…` -> `SizeInBytes=0x400000 Alignment=0x400000`,
`info1[0]={SizeInBytes=0x400000 Alignment=0x400000 Offset=0x0}`, for
`desc0={dim=3 (TEXTURE2D) 1x1 layout=0x0 flags=0x1 format=28}`; the second call is
`flags=0x2 format=19` with the same size. Not a zeroed answer, and not `UINT64_MAX`. **First subsequent use:**
the same frame, `game+0xabfe0d` `vmovups xmm0,[rdi]` -> `game+0xabfe11`
stores the 16 bytes into the caller's struct at `[rsi]`, then `game+0xabfe15` `cmp dword ptr [rsi+4],0` (an
assert that the size fits in 32 bits) is **not** taken — the high dword of `0x400000` is 0. The alternate path
(`game+0xabfdaf`, `cmp qword ptr [rsi+8],0x1000`) compares the alignment with 4 KiB and retries with another
device global when it differs; with alignment `0x400000` that retry path is the one taken.

**Slot 86's return.** All six calls are `E_INVALIDARG` with a null output for a 688-byte (`0x2b0`) stream: the
console `CreatePipelineStateX` stream is not accepted by PC `ID3D12Device2::CreatePipelineState`. Nothing later
in the run dereferences that null PSO, so it is a pending gap rather than a fault source (see §5).

**Queue submission / completion / Present.** None in either leg: no `ExecuteCommandLists`, no backend
completion and no `Present` line appears (the only "submit" text is the unimplemented audio import
`XDspSubmitCommand`), so neither run establishes more than pipeline/resource creation.

---

## 4. Why 0x44, and what the next failure is

**Proven.** At a989b11 the generic thunk took RCX as the `DeviceProxy`. Instrumented on the real call:

```
[rt] d3d12_xs: device slot 108 (forwarded) first call
[dbg] thunk 108: self=0x499D7FEBF0 is_proxy(self)=0 a1=0x1864E9C73D0 is_proxy(a1)=1
                 slot_count(self)=4194304 real_vtable(self)=0x19389400500 ret=0x140ABFE0D
[dbg] thunk 108: forwarding to fn=0x0000000000000044 real=0x14006A0A6
```

`0x499D7FEBF0` is the title's 16-byte return buffer on the stack, so `slot_count` and `real_vtable` were read out
of the caller's stack, `real_vtable[108]` happened to hold `0x44`, and the forwarded call (compiled as a tail
jump — note that `[rsp]` is still `game+0xabfe0d`) executed address `0x44`. So the AV *is* the slot-108 call, not
a later consumer of its output. Slot 86 was never causal: it arrives in the PC form, is refused cleanly, and the
title calls it six times without consequence; "86 was logged first" is timing, not causation.

**Proven.** After the fix the same frame completes: the struct is written, the caller's size assertion passes.

**Proven (by control).** The first failure after the fix is the title's own assert `game+0xcc2936` in the helper
`game+0xcc2840` (`test rcx,rcx; je int3`), called from `game+0x5bfec10` with `RCX = [0x147fe9c68]`, which was
written at `game+0x5bfeba6` from the return of the retail call at `game+0x5204e60`. The layer logs
`ID3D12Device::CreateCommittedResource refused (initial state of a texture (buffer-only or undefined bits)),
dimension 3` immediately before, for `state=0x6` with `flags=0x1` and then `flags=0x2`, twice, from an internal
caller. Making the layer accept those three creations (control only: the state is mapped to
RENDER_TARGET/DEPTH_WRITE per the resource flags) removes the `+0xcc2936` assert entirely and moves the first
failure to a completely different chain, `game+0x24844a9` (write at `0x20`, 385 log lines). So that null object
is the refused creation's result, not a slot-86/108 output.

**Inferred.** That `game+0x5204e60` returns exactly the refused resource (observed order plus the control, not a
register trace of the call). That the assert would also fire without `LEONIDA_SKIP_INT3` in a run that got there
— the diagnostic leg is the only leg that reaches this point.

**Hand-back.** If the next person wants the shortest bad value: it is **null**, produced by
`create_committed_validated`'s `initial_state_refusal` refusing a TEXTURE2D whose Xbox initial state mixes
buffer-only bits (`state=0x6`) with a `flags=0x1`/`0x2` resource, consumed by the title's helper `game+0xcc2840`
through the global `0x147fe9c68`.

---

## 5. Open points (not proven, worth a claim)

- Slot 86 returns `E_INVALIDARG` for a 688-byte stream, six times. Either the console stream carries an
  Xbox-only subobject the PC runtime rejects, or `CreatePipelineStateX`'s argument shape is not
  `(stream desc, riid, out)`. Nothing uses the null PSO yet, so this is invisible today.
- The three `CreateCommittedResource` refusals above are the next visible wall; they are in
  `initial_state_refusal` (`runtime/shims/d3d12_vulkan_device.cpp`), unrelated to slots 86/101/108.
- `device_proxy_test`'s 4 slot-48 queue-flag failures are pre-existing at a989b11, not introduced here.
