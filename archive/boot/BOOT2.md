# BOOT2.md — retail GTA VI boot, from compute pipeline state toward a first Present

_Written 2026-11-24 on `retail-boot-validation`: HEAD `8c57e8fba`, on top of the merge of `origin/main`
`867d922f0` (7 new commits, including #6522's public presentation slots) into `a26520ee0`. Everything below is
from runs against the read-only package `GTA6.Xbox.v1.0.2.1` with `LEONIDA_D3D12=vulkan` on the GTX 1060, a
342-module translated-shader folder, and `LEONIDA_SKIP_INT3=1` (the title's own `int3` at `retail+0x247af2d` is
stepped over, as in `BOOT.md`)._

**Verdict: still no Present, no window, no frame — so no frame time and no backbuffer to dump. Three of the four
assigned items moved: the boot path's real shader need is now measured (52 modules, not 400), the compute
root-signature spill array is modelled and the refusal message is gone, and slot 70 now writes a real raw buffer
view from the title's own pages instead of the null view. The first failure is unchanged and is the one `BOOT.md`
called "the null callback": it is not null any more — it is a call through device slot 61 whose arity the layer
gets wrong.**

## 1. Wall clock, per iteration

A run costs **2–3 s of process time**; a `dry-run` + `run` pair through `boot_local.py` is **6 s total** (measured
5.6–6.5 s). The 20–35 s runs in `BOOT.md` were CPU starvation from the stopped corpus sweeps, not the boot. Teardown
after a fault is now ~3 s, not 40 s.

## 2. Iterations — the first failure of each run

| Run | Change this round | First failure |
|---|---|---|
| boot-011014 | baseline on the merged tree | **Different from `BOOT.md`.** `0xC0000005` at 14.1 s: **read at `0xffffffffffffffff`, host `gta6rt+0x3ecd2a`**, caller `game+0x12b981e`, loop `game+0x2215eca`. Symbols → `ID3D12Device::CreateMetaCommand`, source line 5433 (`if (out) *out = nullptr`). Before that: slots 39, 27, 41, 61 are reached, 342 shaders load, `int3` at `+0x19f4f58` is skipped. |
| boot-012111 | `LEONIDA_SHADER_LOG=1` + root-signature shape dump | Same fault, same place, 2.65 s. New measurements: **53 shader resolutions, 52 distinct, 0 misses, all `cs bvh/*`**; the failing signature is **9 parameters = 8 root descriptors (2 dwords each) + 14 constants = 30 dwords from s4**. |
| boot-013334 | spill array implemented | Same fault, 2.30 s. `root signature usable for graphics only` **gone**; no other change to the sequence. |
| boot-013844 | slot 70 copy fallback (64 MiB cap too low) | Same fault. New log: the raw view's width is **182,452,224 bytes (174 MiB)**, over the cap. |
| boot-013950 | cap raised, still one `VirtualQuery` | Same fault. The title's VA is **many** `VirtualAlloc` regions, so a single query refused the range. |
| boot-014106 | per-region copy | Same fault. **Slot 70 wrote a real raw buffer view**: 182,452,224 bytes copied from console VA `0x17bfb8f0000`, first element 0, **45,613,056 elements**. A second slot-70 call has a different shape (`arg2 is not a raw R32_TYPELESS view`) and still writes the null view. First failure unchanged: slot 61 at 3.05 s. |

The fault moves around between runs (`boot.md`'s null **write** at `retail+0x2215c35` did not recur; the call at
`+0x2215eca` above it is in the same 1-second polling loop). The title's startup is threaded, so which D3D12 call
the loop reaches first depends on timing. What is stable across all six runs is the **sequence of device slots**:
device → queues → fences → allocators → lists → descriptor heaps → slot 133 → slot 14 heaps → 18/19/17/70 →
25 → 127 → 20 → 16 → 62 (compute PSOs) → 39/27/41 → 61.

## 3. Item 1 — how many shaders the boot path actually needs

**Measured: 52 distinct modules, all compute, all `cs bvh/*` from `XboxBvhBuilder.dll`. Zero modules from
`shaders.rpf`'s 26,503.** No run in this session reported a missing shader. `work\astra\corpus_loop.py` automates the
loop that starts with the boot and folds each missing FSSM into `shaders-probe` (it reads the layer's own log lines,
so it stays valid as the boot goes further):

```powershell
cd C:\Users\suki dai yoh!\Documents\gta6\work\astra
python corpus_loop.py 6        # writes corpus_loop.json: rounds, distinct, by_stage, modules
```

Its output for the current tree:

```
round 0: 53 resolutions, 52 distinct, 0 missing
distinct modules the boot path resolved: 52 {'cs': 52}
```

So the corpus is **not** a blocker at this point in the boot, and the earlier worry that boot would need hundreds of
`shaders.rpf` programs is not confirmed: it needs the BVH builder's 52 compute programs and nothing else **so far**.
The game's own shaders are reached by the *render* path (graphics PSOs, draws), which the boot has not entered yet —
that is where `make_game.py --stages shaders` (6–7 h for all 26,503) becomes necessary, and the on-demand path buys
nothing there unless the misses are few. The honest statement for the docs: *boot needs 52; the first frame's
graphics corpus need is still unmeasured.*

The number is a hard measurement for the boot and would be wrong to present as the frame's requirement.

## 4. Item 2 — the root-signature spill array

### The rule, measured on the title's own console-compiled programs

The failing signature is the BVH builder's: 8 root CBVs (2 dwords each) + one 14-dword constants parameter = 30
dwords, i.e. 2 more than the 28 user SGPRs above compute's s4 base. `BOOT.md`/`d3d12_vulkan.md` said only that the
overflow goes "to the spill array behind s[0:1], not modelled".

`shaders-bvh\fssm\LoadTriangles.fssm` (one of the 52 the boot resolves) settles it:

* `COMPUTE_PGM_RSRC2` at `+0x138` = `0x00000088`: **USER_SGPR = 4**, TGID_X. So s0..s3 are user data and **s4 is the
  workgroup id** — no root parameter is inline.
* The first instructions are
  `s_and_b32 s3, s1, 0xff`, `s_mov_b32 s2, s0`, then `s_load_dwordx16 s[8:23], s[2:3], 0x40`,
  `s_load_dwordx8 s[24:31], s[2:3], 0x20`, `s_load_dwordx2 s[22:23], s[2:3], null`.

So **s[0:1] is a 40-bit pointer to a block** (s2 = s0 zero-extended, s3 = s1 & 0xff) and the block holds **the whole
root argument list**, laid out dword for dword like the inline layout: the 8 root-descriptor VAs at `+0x00..+0x3F`,
the 14 constants at `+0x40..+0x77` (the offset-0x40 read is 64 bytes and covers them). The reads at 0x00, 0x20 and
0x40 are exactly parameters 0, 4–7 and the constants. Nothing is passed inline.

That is a stronger statement than "the parameters from the first that does not fit go to the array": here **no**
parameter is inline. It is implemented that way.

### What was implemented

* `runtime/src/root_signature.{h,cpp}`: `pack_stage` no longer refuses. When the parameter span would pass the 28
  dwords above the stage base it re-lays **every** parameter from dword 0 of the block, sets
  `StagePackResult::spilled`, and reports `end_sgpr` = the block's dword count (30 here). `pack()` (graphics) is
  untouched.
* `root_signature_test.cpp`: the four spill cases updated; **the whole test PASSes** (`root_signature_test.exe`,
  exit 0), including `28 constants fill compute exactly`, `an overflowing signature spills whole, laid out from
  dword 0` (`first_sgpr == {0, 27}`, `end_sgpr == 29`), `20 one-dword tables fit compute`, `a 17th table spills on
  mesh`.
* `RootArgumentLayout` gained `compute_spilled` / `compute_dwords`; the command list's root state is now **64**
  dwords (D3D12's cost limit) and writes past dword 32 are no longer stubbed.
* At `Dispatch` / `ExecuteIndirect(dispatch)` the command list copies the block into the device's GPU address arena
  (256-byte aligned, 256 bytes per dispatch, never freed) and puts its address in push-constant dwords 0 and 1 —
  the translated shader's s0/s1. Addresses above 2^40 are logged once, because the console shader masks s1 to 8
  bits.
* Result: `[rt] d3d12: root signature usable for graphics only: … (spill array not modelled)` **no longer appears**
  (boot-013334 onward), and the signature is accepted at both bind points.

**Proven:** the message is gone, the signature parses and binds at the compute point, the layout rule above, and the
tests. **Inferred / not yet exercised:** no dispatch has happened yet, so the runtime half (arena copy + s[0:1]) has
never run in the retail title — it is unit-tested logic but not measured on the GPU. The arena's device address on
this Pascal box may also exceed 40 bits; the layer logs it once if it does, and that would be the next thing to fix
(the block could live in the first 1 TiB of the arena if the driver allows it, or the shader's masking would have to
be mirrored in the translator).

## 5. Item 3 — slot 133 / slot 70 VA backing

### What was measured

* Slot 133 places a **174 MiB** buffer (desc `Width = 0xAE00000`) at a console VA the title already committed
  (`XMemVirtualAlloc` + `XMemMapPhysicalPages`), e.g. `0x1d1be500000..0x1d1c9300000`. The layer creates a committed
  resource for it but does not back it with those pages.
* Slot 70's call names a **different** console VA — e.g. `0x1d1bda00220`, ~11 MiB *below* the slot-133 range — with
  the **same 174 MiB width**. No buffer of the layer holds it: the registered buffer VAs are offsets in the GPU
  address arena (below 4 GiB), while this VA is ~2 TB. So the "null view" was never an aliasing bug — the VA is one
  of the title's own `XMem` ranges, and there is no Vulkan buffer behind it at all.
* The title's memory is **many small `VirtualAlloc` regions**, not one: a single `VirtualQuery` covering the whole
  174 MiB fails, which is why the first copy attempt still reported the range as unreadable.

### What was chosen, and why

**Alias-and-copy on first use**, not `VK_KHR_external_memory_win32`. Reason: the pages come from the `xmem` shim's
`XMemVirtualAlloc`/`XMemMapPhysicalPages`, which is plain `VirtualAlloc` memory — exporting it needs a **section
handle**, i.e. changing `xmem.cpp` to allocate through `CreateFileMapping` and to hand the handle to the layer. That
is the right long-term fix (it removes the copy and keeps the title's writes visible), but it is a change to the
allocation shim used by everything else, and it cannot be shown to help before a dispatch/present exists. The copy
shows the bytes reaching the GPU **now**, in one iteration.

Implementation (`runtime/shims/d3d12_xs_device.cpp`): when `resource_provider` cannot name the VA, the layer copies
`Width` bytes region by region (`copy_console_va`, zeroing nothing it cannot read) into an UPLOAD-heap buffer and
writes the raw `R32_TYPELESS`/`RAW` view over it (`FirstElement = 0`, `NumElements = Width / 4`).

**Measured effect (boot-014249):**

```
[rt] d3d12_xs: slot 70 copied 182452224 of 182452224 bytes from the console VA 0x17bfb8f0000 into an upload buffer
[rt] d3d12_xs: slot 70 wrote a raw buffer view (va 0x17bfb8f0000, first element 0, 45613056 elements)
```

That is the first **non-null** slot 70 view in any run. Limits, stated plainly: the copy is a snapshot at view
creation (a later write by the title is not seen), the buffer is never released (174 MiB per call, one call so far),
and a **second** slot-70 call has a different, non-`R32_TYPELESS` shape — unmeasured texture shapes — which still
writes the PC null view with `arg2 is not a raw R32_TYPELESS view`.

Slot 133's own resource is still not backed by the title's pages; with the copy path above, that no longer blocks
slot 70, but anything that *writes through the resource* still writes the layer's own memory.

## 6. Item 4 — the "null callback", characterised

It is a real call, and the crash is an **arity mismatch**, proven from the executable:

`game+0x12b981e` disassembles to `push %rsi; sub $0x20,%rsp; mov %rdx,%rsi; mov %rcx,%rdx; mov <global>,%rcx;
mov %rsi,%r8; mov (%rcx),%rax; call *0x1e8(%rax)` — that is **slot 61** (`0x1e8 / 8`) with
`rcx = device, rdx = a1, r8 = a2`: the console method takes **two** arguments (a1 is a pointer to a 144-byte
structure the caller fills in just before). The layer forwards slot 61 by number to `ID3D12Device::CreateMetaCommand`
(`REFGUID, UINT, const void*, SIZE_T, REFIID, void**`), whose sixth argument it reads from stale stack — `-1` — and
faults writing `*out`. The global is **not** null; the fault is a **read of `0xffffffffffffffff`** inside
`CreateMetaCommand`'s `if (out) *out = nullptr`.

**Proven:** the call site, the slot, the two-argument console shape, the failing PC function, the stale `out`.
**Inferred:** console slot 61 is *not* `CreateMetaCommand` — the layer's "Xbox slot = PC slot + 1" mapping, which
holds for these bytes' neighbours (16 root signature, 18/20 views, 25 allocation info, 27 committed resource), must
break at the console-only methods. The 144-byte structure is filled from a shader-container-like description
(words at +4, +8, +12, +20, +24, +32, +36, +48, +52, +64, +68…) but is not identified.
**Does it disappear once (2) and (3) are done?** No — it is reached with both implemented. So it is **not** a symptom
of the spill or of the VA, at least not at this arity: the layer must model/create the console method.

Device slots **78** (`SetFrameIntervalX`) and **79** (`ScheduleFrameEventX`) are called by the retail title, in
`boot.md`'s and this session's logs — that **upgrades #6522's public "corroborated" mapping to "observed in a retail
title"** for 78/79. Slot 80 (`WaitFrameEventX`) has not been called yet, and no queue slot 30/32 `PresentX` call has
appeared: the swapchain/present path has not been entered.

## 7. Present, frame time, backbuffer

**Present was never called in any run of this session.** No swapchain is created, no window appears, so there is no
frame time and no PNG to dump — "a white clear" and "a rendered frame" remain indistinguishable because neither has
happened. The first failure is still before any queue submission: no `ExecuteCommandLists` has been seen.

## 8. Proven vs inferred

**Proven (measured in a run, or read off the binary):**

* Run cost 2–3 s; the boot path resolves **52 distinct compute modules**, all `bvh/*`, no misses.
* The on-screen sequence of device slots up to slot 61, including 78/79.
* The failing root signature's shape (9 parameters, 30 dwords) and the message disappearing once the spill model is in.
* The spill rule: USER_SGPR = 4, s[0:1] a 40-bit pointer, block holds all 9 parameters (LoadTriangles.fssm).
* `root_signature_test` PASSes with the spill cases.
* Slot 70's VA is not held by any layer buffer, its width is 174 MiB, and the copy path writes a real raw view
  (45,613,056 elements).
* The slot-61 call site's two-argument console shape and that the fault is `CreateMetaCommand`'s stale `out`.
* No Present, no swapchain, no submit.

**Inferred (reasoned, not yet measured):**

* Console slot 61 is not `CreateMetaCommand`; the layer's +1 slot mapping breaks at the console-only methods.
* The 144-byte structure's meaning.
* That the spill runtime path (arena copy, s[0:1]) works on this GPU — it is untested until a dispatch happens, and
  the arena's address may exceed the console's 40 bits.
* That the render path will need `shaders.rpf` modules (no measurement of how many).

## 9. Commands

```powershell
cd C:\Users\suki dai yoh!\Documents\gta6\work\astra\upstream
.\..\boot-dev-build.cmd
$env:LEONIDA_D3D12 = 'vulkan'
$env:LEONIDA_SHADERS = 'C:\Users\suki dai yoh!\Documents\gta6\work\astra\shaders-probe'
$env:LEONIDA_SKIP_INT3 = '1'
$env:LEONIDA_SHADER_LOG = '1'      # names every module a pipeline resolves
cd ..
python boot_local.py               # 6 s for dry-run + run; writes work\astra\boot-<hhmmss>\
python corpus_loop.py 6            # translate whatever the boot says it is missing, then re-run
```

`root_signature_test` is not part of `boot-dev-build.cmd`'s target list; build and run it in a vcvars64 shell:

```powershell
cmd /c '"C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul && set "PATH=<CMake>\bin;<Ninja>;%PATH%" && cmake --build ..\boot-build --target root_signature_test && ..\boot-build\root_signature_test.exe'
```

## 10. Next blocker, in order

1. **Device slot 61's real method.** It is the first failure and both (2) and (3) are in. The layer needs the
   console method's identity (or at least its arity: `(device, a1, a2)`), which the 144-byte structure and the
   slot-78/79 frame calls should pin down.
2. **A dispatch.** Nothing has been submitted. The spill path, the slot-70 copy and any draw are all unexercised on
   the GPU until a command list is executed.
3. **The render path's shader corpus**, which is the first place `shaders.rpf`'s 26,503 modules matter.
4. **The swapchain and `PresentX`** (queue slot 30/32, device 78–81) — #6522 documents the ABI but upstream has not
   wired it; the layer will need it the moment the title asks for a frame.
