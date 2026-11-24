# XCL — can it shorten Leonida's path to a real first frame?

**Candidate:** `ivall/xcl`, clone at `work/xcl-eval`, pinned at
**`38b05b7b6954cfa5bd21cec72f68823603ca2227`** (2026-11-23T21:47:00+01:00, *"Retail game shows its
first menu: target pages instead of arenas, lazy physical pages, PC view formats"*).
Verified with `git rev-parse HEAD`; tree clean; 115 `.rs` files; one crate (`crates/xcl`) plus a
synthetic test title (`tests/testtitle`) and a test DLL. Steps: `work/xcl-eval/PROGRESS.md`.

**Answer in one line.** Yes, but not by reuse: XCL targets *exactly* Leonida's generation and its
source contains the identity of Leonida's own blocking slot (**console device slot #61 is
`CreateSamplerX(desc, destination)` — two arguments**), so it shortens the path by giving us a
testable hypothesis and a measured ABI, while GPL-2.0-**only** against GPLv3 means we may re-derive
but not copy.

Marking: **[V]** = verified by reading the pinned source (path given). **[I]** = inferred by me.
**[D]** = a claim the project makes about itself (README / HANDOFF), quoted but not independently
reproducible here (no game data in the clone).

---

## 1. Ground truth of "playable": Minecraft Preview

### 1.1 What the code says the target is

| Question | Answer | Evidence |
|---|---|---|
| Guest hardware generation | Xbox **Series X\|S** (Scarlett), GPU = **RDNA2 gfx10.3 + console-only ISA extensions kept from gfx10.1** | `crates/xcl/src/gpu/rdna2_xbox.rs:1` *"Instructions the Xbox Series GPU executes that the retail RDNA2 (gfx10.3) spec does not"*; `hle/kernelx.rs:1228` console type `0x64` Series X / `0x60` Series S; `hle/xgameruntime/mod.rs:231-238` `XSystemGetDeviceType() → DEVICE_XBOX_SCARLETT_ANACONDA`; `config.rs:11` `device_type: "anaconda"\|"lockhart"` **[V]** |
| CPU model | **none** — guest x64 runs natively; only console libraries are replaced (Wine model) | `README.md` lead paragraph; `loader.rs` / `pe.rs` map the game's own PEs **[V]** |
| Executable / package format | **unpacked game folder**: x64 PE `.exe` chosen from `<ExecutableList>` of **`MicrosoftGame.config`** (GDK manifest) | `launcher.rs:89` *"MicrosoftGame.config as text, without its comments"*, `launcher.rs:127`; `manifest.rs:40 parse`, `manifest.rs:60 load`; GPL note "no code for decrypting DRM — unpacked files you own" **[V]** |
| Guest graphics API | **D3D12.X** (`d3d12_xs.dll`): a *console vtable layout* of D3D12 with extra methods (`CreateGraphicsPipelineStateX`, `CreateSamplerX`, frame pacing, `PresentX`…), console descriptor heaps of 32-byte T#/V# and 16-byte S# slots, console command lists whose SDK inline writers pack records into the object | `real.rs:743-816` `console_slots()`; `console_heap.rs:32-34` `SLOT`/`SAMPLER_SLOT`; `title_list.rs` module doc **[V]** |
| Guest shader format | console container **XDAT → XBCH v3 → FSSM**, containing RDNA2 machine code (not DXBC) | `gpu/xbox.rs` (format), `HANDOFF.md:1522` *"FSSM sub-version (+0x10) 5 = Fortnite's GDK, 6 = XDefiant's / Minecraft's"* **[V]** |
| Host backend | **D3D12 on Windows** (`hle/d3d12x/real.rs`, 240 KB) + **DXIL** produced at runtime by in-process **DXC** (`hle/dxcompiler.rs`, `gpu/recomp/dxc.rs`), with a `null.rs` (33 KB) fallback for "no GPU / `graphics="null"`" | `real.rs` device adoption + extended vtables; README build section (DXC from the Windows SDK) **[V]** |

So the split with Leonida is **not** the guest: both map the retail Series-X executable, shim the
same console libraries and recompile the same RDNA2 programs. The split is **DXIL/D3D12 vs
SPIR-V/Vulkan**.

### 1.2 The evidence that Minecraft is "playable"

The project's *only* evidence for a real game is a human-supervised run plus counters, not a test:

* `HANDOFF.md:1389` — *"**Minecraft is playable (2026-11-22)**: a world is created, loads and runs;
  the Ore UI screens take the gamepad."* **[D]**
* The concrete measurement behind it, in the same entry (`HANDOFF.md:1395-1398`): per-draw data had
  been allocated in 64 KiB grains, the 2 GB unified-memory window filled in seconds and draws were
  skipped; after moving to a 256 KiB/256-byte arena — *"16.7 M draws, 0 skipped"*. The same fact is
  restated independently in a code comment, `gpu/uma.rs:625` *"2 GB within seconds in a scene of
  thousands of draws (Minecraft's world), and the draws…"* **[V]** (comment), **[D]** (the number).
* Two real bugs were found *only* by that run and are described as fixed in general terms, not
  per-title: the Ore UI gamepad path (`XUserRegisterForDeviceAssociationChanged` was never called,
  so `GameControllerInputHandler` dropped a controller it never saw arrive —
  `HANDOFF.md:1390-1394`) and helper-lane reads in the UI pixel shader (`rla` via quad reads,
  `recomp/emit.rs` prelude, `HANDOFF.md:1378-1388`). **[D]**
* Input for "playable" in the README's own table: *"Minecraft Preview \| Microsoft.MinecraftBeta
  1.18.3064.0 \| ✅ \| fully playable \| –"* (`README.md`, Games table). **[D]**

**Where the README overstates.** The README's Limits column is "–". The repo's *later* note on the
same title (`HANDOFF.md:1489`, marked "latest") says it reaches its **main menu** — panorama, logo,
buttons, character, music, Enter — offers the **trial** because `XStore` is refused, and *"stops at
the Microsoft-account sign-in (Xbox Live)"*; also `HANDOFF.md:1488` *"Minecraft stays a trial (XStore
refused)"*, and the version there is **1.18.30.64**, not the README's **1.18.3064.0**. **[V]** (both
texts read) — the two entries are different runs of possibly different builds, and the README picks
the stronger one. Also note the run uses `Minecraft.Windows.exe.original`; a 29-byte `Minecraft.Windows.exe`
patch that forces licence checks true exists next to it but *"not run by XCL work"* (`HANDOFF.md:1491-1492`). **[V]**

**What is *not* evidence, stated plainly.** There is no CI in the clone (`.github/` holds only
`ISSUE_TEMPLATE/`), no golden-image test, and no test that runs a retail title: every real-data test
is environment-gated and silently passes when the variable is unset —
`tests/console_dlls_e2e.rs:14` `std::env::var_os("XCL_SAMPLE_DLLS")?`, `tests/console_shaders.rs:20`
`XCL_SAMPLE_DXC`, README *"without them those tests pass without running anything"*. So "370+ tests"
certifies the *generic* machinery (unit tests + a synthetic console title that renders a triangle
through the shim, `tests/testtitle`), and the word "playable" rests on the manual runs in
`HANDOFF.md`. **[V]**

**Shim completeness at the point of "playable"** (this is the honest metric, and it is high):
`HANDOFF.md` records for the same period — 26 698 / 26 698 RDNA2 programs translate (0 missing
instructions), 23 869→26 503 shaders of a retail pack parsed, 0 DXC errors on samples, 909/912
textures byte-exact, 1 449 frames in 60 s, 3 443 pipelines with none failed, `report.json`
`called_stubs` used as the to-do list. **[D]**

---

## 2. One concrete comparison: guest **sampler creation**, XCL vs Leonida's slot 61

### 2.1 The XCL chain, hop by hop (each hop read in source)

Console code never receives a PC object. `real.rs` gives console code its own vtable whose entries
are **guards**: `guard::make_guard` (`guard.rs:31`) inspects the *return address* — a call from the
game's image is a console method, anything else is XCL or the runtime — and forwards accordingly;
`guard::make_split` (`guard.rs:45`) / `guard::make_layout_split` (`guard.rs:74`) pick between a
console and a PC target, keeping all argument registers (xmm too) untouched. **[V]**

| # | Hop | Path : symbol |
|---|---|---|
| 1 | **Guest entry point** — console device method **#61**, `CreateSamplerX(desc*, destination)`; `destination` is a **console CPU descriptor handle**, i.e. an *address in unified memory* | `hle/d3d12x/real.rs:796` `(61, x::create_sampler_x)` inside `console_slots(Kind::Device)` |
| 2 | **Argument decode** — console sampler desc is **0x6C bytes** with PC fields at different offsets: `+0x18/+0x1C/+0x20` address U/V/W, `+0x24/+0x28` min/max LOD, `+0x2C` bias, `+0x34` max anisotropy, `+0x40` comparison; further console anisotropy fields *"not modelled"* | `hle/d3d12x/device_x.rs:624-646` `create_sampler_x`; guard `crate::gpu::shader::readable(x, 0x6C)` first |
| 3 | **Convergence** — the same function also serves the PC-numbered slot **#22** `CreateSampler(desc, cpu_handle)` | `real.rs:784` `(22, dev_create_sampler_x)`; body at `real.rs:1607-1614` |
| 4 | **Descriptor-heap translation** — console handle → `Slot`: which console heap, which slot index `k`, the shadow address `at = shadow + k*16`, and the *PC* handle `pc_srv`. Console handles are not D3D12 handles at all; they are UMA addresses in a shadow array | `hle/d3d12x/console_heap.rs:324-340` `slot(cpu)`; `SAMPLER_SLOT = 16` at `:34`, `SLOT = 32` at `:33` |
| 5 | **Heap creation / registration** — heap desc `[type, n, flags, node]` from console code: samplers get `n` PC slots (**views get `2n`**, an SRV/UAV pair per console slot), all sampler slots are pre-filled with a deterministic point/wrap sampler so an *unwritten* console slot still samples as the console does, then `register(obj, n, cpu, gpu, inc, sampler, shared, visible)` records shadow+handles | `real.rs:923-974` `dev_create_descriptor_heap_x` (pre-fill loop `:965-967`); `console_heap.rs:236` `register` |
| 6 | **Backing write** — the real PC sampler is created at the slot's PC handle; then **4 dwords are written into the UMA shadow**: `[0, 0, 0, index & 0xFFF]`. Word 3 `[11:0]` = *PC sampler-heap index*; the sampler's *state* lives only in the PC sampler object | `real.rs:1609-1614` `dev_create_sampler_x`: `f(this, desc, slot.pc_srv)` then `console_heap::write(&slot, &[0,0,0, slot.index & 0xFFF])`; `console_heap.rs:392 write` |
| 7 | **ABI contract for the recompiled shader** | `gpu/desc.rs:336-342` `xcl_sampler_words` (*"sampler heap index in word 3 [11:0] (BORDER_COLOR_PTR…)"*); `gpu/recomp/emit.rs:1530-1543` `sampler_ref` → `SamplerDescriptorHeap[NonUniformResourceIndex(s3 & 0xFFFu)]` |
| 8 | **Copy path (the thing that made every frame black once)** — descriptors are *values*: the title copies descriptors as memory into a shader-visible heap, so each console view heap gets a *range in one shared PC heap* and the copied T#/S# keeps naming the right PC descriptor | `console_heap.rs:355-368` `publish_range`, `:400-413` `copy_words` (renumbers word 3 for samplers, word 0 for views); `real.rs:1618-1637` `copy_console_slots`; `HANDOFF.md` §*"Why every frame was black: descriptors are values"* |
| 9 | **Separate static path** — when the S# is built from constants in the program (the console's static samplers), XCL does not touch a heap at all: it finds the constants, puts them in the pipeline's root signature as **static samplers**, and indexes them as `xcl_ssN` | `recomp/mod.rs:1249-1251` `constant_samplers`; `recomp/pso.rs:82` `pub type StaticSampler = ([u32;4], bool)`, `:595 abi_root_signature_with`; `emit.rs:1535-1542` |

The pure S#→`D3D12_SAMPLER_DESC` decoder (`gpu/desc.rs:280 sampler_d3d12`, border-colour table,
`SQ_TEX_DEPTH_COMPARE`→`D3D12_COMPARISON_FUNC`, aniso `1<<((w[0]>>9)&7)`, D3D12 filter packing) is
**not** on the runtime console-API path: its only callers are its own tests and
`tests/gpu_pso_e2e.rs:386`. It serves the *shader-side* S# (constants / static samplers). **[V]**

### 2.2 Leonida's measured slot-61 path

From `BOOT2.md:164-172` and `work/astra/PROGRESS.md:38` (quoted, not re-derived): the call site
`game+0x12b981e` loads `rcx=[global device]`, sets `rsi=a2, rdx=a1, r8=a2` and does
`call [rax+0x1e8]` = **slot 61** with **two** arguments; the layer forwards by number under an
"Xbox slot = PC slot + 1" rule to a **6-argument** `ID3D12Device::CreateMetaCommand`, whose
`if (out) *out = nullptr` reads a stale stack out-pointer (`0xffffffffffffffff`) at 3.05 s. Everything
before it succeeds: device, queues, fences, allocators, lists, descriptor heaps, 133, 14, 18/19/17/70,
25, 127, 20, 16, 62. No `ExecuteCommandLists`, no `PresentX`.

### 2.3 What XCL does that we do not, and what it does differently *by construction*

**(i) It knows what console slot 61 is — and the two-argument shape agrees with our disassembly.**
`real.rs:796` `(61, x::create_sampler_x)` with `create_sampler_x(this, desc*, dest)` —
`this + 2` arguments, decoded as a pointer to a **0x6C-byte** console sampler desc plus a console
descriptor handle. **[V]** Our `rsi=a2, rdx=a1` two-register call is the same shape. Leonida's
"+1 slot mapping" (`BOOT2.md:172`) is an assumption XCL's table disproves: the console device vtable
has extra methods inserted, so console and PC indices diverge from at least #60 (XCL's own comment
at `real.rs:743-745`: console #62 = `CreateComputePipelineState` with two extra args, *"PC #62 =
CreateStateObject"*, and #76 = `CreateCommittedResource` with *"PC #76 = CreateCommittedResource3"*).
**[V]** for XCL's table; **[I]** that this is the same divergence Leonida hit.

**(ii) Console code never holds a PC handle.** Leonida passes the console's handle onward to the PC
API (the shape of the fault: a *stale stack out-pointer* read by the PC method). XCL's console heap
is a **shadow array in unified memory**: a console `CPU_DESCRIPTOR_HANDLE` is an address inside it
(`console_heap.rs:324-340`), PC descriptors live elsewhere and only a 12-bit index ever crosses into
the shader. The write that "backs" the descriptor is a 4-dword store into that shadow
(`real.rs:1613`), not an API call. That is why a sampler can be *copied as bytes* and still work
(`copy_words`), and it is exactly the mechanism absent from a slab that maps console handles onto PC
heaps 1:1. **[V]**

**(iii) It translates the descriptor from the *console API struct*, not only from the S#.**
`device_x.rs:632-644` reads the console's own sampler desc at console offsets. Leonida has no such
decoder because it never gets that far. **[V]**

**(iv) It makes an unwritten console slot deterministic** (`real.rs:949-968`: every sampler slot is
pre-filled point/wrap, because *"an unwritten PC descriptor is undefined"*). A one-line behaviour we
can copy as an idea at zero cost. **[V]**

**(v) By construction: the shader side is *ours*, so the ABI is free.** Because XCL recompiles RDNA2
itself, it can dictate that an S# carries a heap index in word 3 (bits nobody else reads) and that
static samplers become root-signature static samplers. Leonida's SPIR-V route must arrive at an
equivalent contract by a different route (separate/combined samplers + descriptor indexing), so
XCL's *encoding* does not transfer even though its *idea* does. **[V] for XCL, [I] for the Vulkan
side.**

---

## 3. Command-queue submission + presentation, traced to an observable

Better documented of the two candidates (allocation-size queries get `get_resource_allocation_info_x`
`real.rs:769` / `:813` and `tests/heap_probe.rs`, plus the console-C-calling-convention story at
`HANDOFF.md` #25; presentation has a whole 37 KB module, a 26 KB frame-pacing module, two layout
generations and fps counters — so presentation it is).

| Hop | Path : symbol | What it does |
|---|---|---|
| 1 | `real.rs:4315` `QUEUE_FIRST = 14`; `real.rs:4406-4417` `queue_slots!` macro | every queue slot from #14 up gets an entry (a 4-integer trampoline), so console-only queue methods land in XCL, not in the driver |
| 2 | `real.rs:4319-4333` `queue_dispatch` | converts the call to the **older** layout's numbering: `if shifted && slot >= 16 { slot - 2 }`; the two console layouts are *detected at run time* |
| 3 | `real.rs:4325-4331` `is_fence` probe | a fence passed to queue #16/#17 ⇒ the newer layout (`Signal #16, PresentX #32, CopyTextureRegionX #85`); a fence at #14/#15 ⇒ the older one. This is the whole detection mechanism — argument shape again, not a title table |
| 4 | `real.rs:4377-4381` `#35 ExecuteCommandListsX(count, lists, value, flags) → q_execute_command_lists` | *"a retail game submits all its command lists this way (flags 3…); as a stub nothing the title recorded ran on the GPU but its first two frames"* |
| 5 | `real.rs:4373` `#30 → present::present_x` | `PresentX(planeCount, planes, params)` |
| 6 | `present.rs:47-60` `present_x` | plane 0's first resource is the frame; **always returns S_OK** (*"a console present does not fail for the title"*); then `frame::mark_flipped(token)` |
| 7 | `present.rs:62-71` `present_x_frame` | counts `BOUNDARIES`, logs **`"D3D12.X: {frames} frames presented, {:.1} fps over the last 300"`**, first call logs *"PresentX – the title presents its own frames"*; `real::stop_if_device_removed()` |
| 8 | `present.rs:509-544`, `:669` | a real `DXGI_SWAP_CHAIN_DESC1` + `CreateSwapChainForHwnd(queue, hwnd, …)` on XCL's own window, `sc.Present(0, 0)` |
| 9 | `frame.rs:172-…` `set_frame_interval_x` / `schedule_frame_event_x` / `wait_frame_event_x`, `TYPES = 3`, `ORIGIN_SEMAPHORE_MAX = 4` | the console's frame pacing (a clock thread, deadlines `base+offset+k·interval`) — the console way a title *knows* a frame happened |
| 10 | `present.rs:138 counters()`, `:251 activity()` | `(presents, executes)` — the observable pair |

**Observable result (verified as text, the runs themselves are [D]):** retail titles show a picture
and a frame rate — *"632 frames in 30 s"*, *"1 449 frames in 60 s"*, *"~53 fps"* (XDefiant),
*"16.7 M draws, 0 skipped"* (Minecraft) — and, for the title Leonida resembles, *"its first menu is
visible (2026-11-23) — the account prompt … at 30 fps (632 frames in 30 s, 720 draws per 2 s), no
crash"*, after the queue-shift fix at #35 and the list-shift fix at #61 were found **by the
argument-shape probe in hop 3**. **[V]** for the mechanism and log strings, **[D]** for the numbers.

The point for Leonida: XCL's own recorded failure before hop 4 was *"as a stub nothing the title
recorded ran on the GPU but its first two frames"* — i.e. submission is the true first-frame gate,
and XCL found it because the *queue* slot #35, not the list, was where the retail title submitted.

---

## 4. Returned items

### (a) Source paths and symbols

| Item | Path : symbol |
|---|---|
| Console device slot table (console↔PC divergence, with reasons) | `crates/xcl/src/hle/d3d12x/real.rs:743-816` `console_slots(Kind)` |
| **Console device #61 = CreateSamplerX** | `hle/d3d12x/device_x.rs:624-646` `create_sampler_x`; `real.rs:796` |
| Console sampler desc layout (0x6C B) | `device_x.rs:625-644` |
| Descriptor heap create / pre-fill / register | `real.rs:923-974` `dev_create_descriptor_heap_x`; `console_heap.rs:236 register` |
| Console handle → slot translation | `console_heap.rs:324-340 slot`; `SAMPLER_SLOT=16`, `SLOT=32` (`:33-34`) |
| Backing write (S# in UMA shadow) | `real.rs:1609-1614 dev_create_sampler_x`; `console_heap.rs:392 write` |
| Descriptor copy = memory copy, index renumbering | `console_heap.rs:400-413 copy_words`, `:355-368 publish_range` |
| S# → D3D12 sampler (shader side) | `gpu/desc.rs:280 sampler_d3d12`, `:338 xcl_sampler_words` |
| Recompiled-shader sampler reference | `gpu/recomp/emit.rs:1530-1543 sampler_ref`; static path `recomp/mod.rs:1251 constant_samplers`, `recomp/pso.rs:595 abi_root_signature_with` |
| Console-code detection (guard by return address) | `hle/d3d12x/guard.rs:31 make_guard`, `:45 make_split`, `:74 make_layout_split` |
| Pointer-validity guard on every console pointer | `gpu/shader.rs readable` (`VirtualQuery`-based) |
| Queue slot dispatch + layout detection | `real.rs:4315-4404 queue_dispatch`; `NEWER_LIST_SLOTS` `:4299`; `QUEUE_SHIFTED` `:4292` |
| Submission | `real.rs:4377` → `q_execute_command_lists` |
| Presentation | `present.rs:49 present_x`, `:62 present_x_frame`, `:138 counters`, `:533 CreateSwapChainForHwnd`, `:669 Present` |
| Frame pacing | `frame.rs:172 set_frame_interval_x`, `schedule_frame_event_x`, `wait_frame_event_x`, `mark_flipped` |
| Memory: title heaps in sparse windows, page table plan | `hle/d3d12x/sparse.rs`, `gpu/uma.rs`, `hle/kernelx/lazy.rs`, `hle/kernelx/placeholders.rs` |
| Licence | `Cargo.toml` (`license = "GPL-2.0-only"`), `LICENSE`, `README.md` §Licenses, `THIRD_PARTY.md:3` |

### (b) One behaviour Leonida can test **without adopting XCL**

**Test the console↔PC slot identity by argument shape, not by number.** Concretely, for the slot-61
call site: treat `arg1` as *a pointer to a 0x6C-byte console sampler description* and `arg2` as *a
handle inside a console descriptor heap we created at slot 14*, then check the decoded fields before
calling anything:

* `arg1 ≠ 0` and `VirtualQuery(arg1, 0x6C)` fully committed and readable (**this alone kills the
  current fault**: a pointer that is readable as 0x6C bytes is a desc, a stale stack word usually is
  not);
* `*(u32*)(arg1+0x18)`, `+0x1C`, `+0x20` (address U/V/W) each ≤ 6 (`WRAP..BORDER`-ish);
* `*(u32*)(arg1+0x34)` (max anisotropy) in `1..=16`;
* `*(u32*)(arg1+0x24)`, `+0x28` (min/max LOD) as floats in `0..16`;
* `arg2` lies inside `[heap_start, heap_start + n*16)` for some sampler heap the title created.

Evidence that these are the right offsets: `device_x.rs:632-644`. We do not need XCL's code, only
these six numbers, which are *facts about the console ABI* (uncopyrightable) and which our own
disassembly can confirm within one run. No adoption of XCL's architecture, no Vulkan work.

### (c) One incompatibility that limits reuse

**The DXIL/Vulkan split invalidates the ABI layer, not the measurements.** Concretely, what cannot
transfer:

* **The shader ABI encoding.** `SamplerDescriptorHeap[NonUniformResourceIndex(s3 & 0xFFFu)]` and the
  `xcl_image_words`/`xcl_sampler_words` rewriting (`desc.rs:326-342`) only work because XCL owns the
  DXIL. In SPIR-V/GLSL the same idea becomes descriptor-indexing with **separate** sampler/image
  arrays and an index baked into the interface; the specific "heap index in word 3 [11:0]" convention
  is reusable as a *convention*, not as code.
* **Root-signature machinery**: `abi_root_signature(_with)` (`recomp/pso.rs:564/595`), 24 user SGPRs
  `s8..s31` + a table at `s[0:1]`, directly-indexed heaps, `[WaveSize(64)]`/`[WaveOpsIncludeHelperLanes]`
  behaviour — all D3D12/DXIL-specific. The *numbers* (s8..s31 for a VS/PS, s0..s7 driver-reserved,
  `s[4:5]` = VS fetch shader) are ABI facts and **do** transfer.
* **Mesh-shader workaround**: NGG/GS/ES run as `[WaveSize(64)]` compute + `mesh_passthrough`, because
  *"DXC does not allow WaveSize in an MS"*; Vulkan has no mesh requirement at all, so this whole
  design is dead weight on Leonida's side.
* **`D3D12_SAMPLER_DESC`-shaped results** (`sampler_d3d12`, `device_x::create_sampler_x` building a
  D3D12 struct) must be re-expressed as `VkSamplerCreateInfo` — trivial, but the border-colour table
  (console type 3 → transparent black), `SQ_TEX_DEPTH_COMPARE → ComparisonFunc` (`+1`), and
  `aniso = 1<<((w[0]>>9)&7)` mappings are *semantics* worth re-deriving.

**What still transfers for another Xbox generation:** XCL's target *is* Leonida's generation
(Series X|S, gfx10.3, GDK, D3D12.X), so there is no generation gap to bridge. If Leonida later
targeted **Xbox One** (gfx6/gfx7, D3D11.X), then: the ISA tables (`rdna2_spec.rs`, 752 KB generated
from AMD's ISA XML), `rdna2_xbox.rs` extensions, the FSSM container parser and all GFX10 tiling
tables **cease to apply**, while these keep applying: the *architecture* (native x64 + HLE console
libraries + GPU-ISA recompilation to a host API), the **guard-by-return-address** split, the
**argument-shape** slot detection, **descriptor-shadow-in-UMA** as the translation model, and the
**census-driven methodology** (`report.json` → `called_stubs` / `unknown_iids` → next shim; `readable()`
on every console pointer; `XCL_PROBE=rva,…` hardware breakpoints to find a code path without patching
the game). **[V]**

### (d) Licensing constraint on copying

**XCL is GPL-2.0-*only*; Leonida is GPLv3; therefore Leonida may not copy XCL source — it may only
re-derive.**

* File that states it: **`Cargo.toml`**, `[workspace.package] license = "GPL-2.0-only"`; corroborated
  by `LICENSE` (GNU GPL **Version 2, June 1991**) and by `README.md` §Licenses —
  *"**GPL-2.0-only** (`LICENSE`)"*. **[V]**
* `THIRD_PARTY.md:3` repeats it and, in its dependency policy, lists the compatible set and then
  *"Incompatible: Apache-2.0 without an alternative, **GPL-3.0**, LGPL-3.0, AGPL"* — XCL's own norm
  treats GPLv3 as incompatible, and `HANDOFF.md` shows the licence was *chosen*: *"The user agreed to
  relicense XCL to GPL-2.0-only (2026-11-20)"* (to absorb AnyPS5, also GPL-2.0-only). **[V]**
* Consequence **[I], but a settled FSF position**: GPLv2-**or-later** code can move *into* a GPLv3
  work (via §9 "any later version"); GPLv2-**only** cannot. Because XCL removed the "or later" option,
  it is **mutually incompatible** with GPLv3 in both directions. Copying XCL `.rs` files (or verbatim
  HLSL emission strings) into `leonida/` would make the combined work unlicensable as GPLv3.
* What is *not* restricted: **facts and ideas** — slot numbers (#61 = CreateSamplerX, #35 =
  ExecuteCommandListsX, #32 = PresentX), struct offsets (0x18/0x1C/0x20/0x34), the 0x6C desc size, the
  16/32-byte descriptor slot sizes, the FSSM container layout, the GFX10 swizzle tables (themselves
  MIT from Mesa), the ISA tables (MIT from AMD). These are re-derivable and freely usable; write them
  in our own words/code and cite "measured against XCL 38b05b7" as provenance.
* If bulk reuse ever looks worthwhile (e.g. the 752 KB `rdna2_spec.rs` or the recompiler's emitter),
  the cheap fix is a **written dual-licence grant from XCL's author** ("GPL-2.0-only OR GPL-3.0"), or
  relicensing Leonida's port template to GPL-2.0-or-later — a project-level decision, not a code one.

---

## 5. Recommended bounded experiment (pass/fail)

**Hypothesis (from §2):** Leonida's slot 61 is the console's `CreateSamplerX(desc, destination)`; the
current fault is our "+1 slot" forwarding, not the title's data.

**Bounded experiment** — one logging run plus one minimal implementation run, ≤ 1 h total, no
architecture change, no XCL code:

1. **Run A (log only, ~20 min).** At device slot 61, before forwarding anywhere: dump
   `arg1`, `arg2`, and — if `VirtualQuery` says `arg1` is readable for `0x6C` bytes — the 0x6C bytes
   with the six fields of §4(b) decoded; log whether `arg2` falls in any range created at slot 14
   (sampler heaps, slot size 16). Keep the existing behaviour otherwise. Cap the run at 60 s or 64
   slot-61 calls.
2. **Run B (minimal implementation).** Stop forwarding slot 61 by number at all. Decode it as
   `CreateSamplerX`: create one PC sampler from the console desc, and write the console ABI word
   `[0,0,0,index&0xFFF]` into the slot-61 destination **if** that destination is inside one of our
   console shadow heaps; return `void` (XCL's `create_sampler_x` returns `()` — a 2-argument console
   method has no HRESULT to consume). **[V]** `device_x.rs:628`.

**Pass criteria (both, in this order):**

* **Gate 1 (identity).** Over the ≥ 8 slot-61 calls of one run: `arg1` readable for 0x6C bytes in
  ≥ 90 % of calls; address modes at `+0x18/+0x1C/+0x20` all ≤ 6; anisotropy at `+0x34` in `1..=16`;
  and `arg2` inside a known console sampler heap range in ≥ 90 % of calls.
  → *Pass*: slot 61 is `CreateSamplerX` and we now know the console ABI. *Fail*: our disassembly's
  argument reuse is being misread, or this title's device layout is shifted — then re-run Gate 1 with
  the *other* anchors from XCL's table (console #60 `CreateGraphicsPipelineStateX`, #62
  `CreateComputePipelineState(desc,NULL,NULL,riid,ppv)`, #76 `CreateCommittedResource`) to find where
  the shift begins.
* **Gate 2 (path).** With Gate 1 passed and slot 61 decoded, the run must reach
  **`ExecuteCommandLists` count > 0** (`activity().1`) within 60 s — our current runs reach 0.
  → *Pass*: the first real submission. *Fail*: the boot still stalls before the queue; the next
  suspects are then queue slots #35 (`ExecuteCommandListsX`) and list #61 (which XCL maps to the
  older #59 = `ExecuteIndirect`), i.e. the same shift, one level up.

**Why this is worth the hour:** if Gate 2 passes, Leonida jumps from "compute PSOs created" to
"command lists submitted" — the same jump XCL needed for its first frame; and if Gate 1 fails, we have
disproved a hypothesis from an independent implementation at the cost of one run instead of one
invention.

---

## 6. The two conditional questions, answered plainly

* **Does XCL target this generation?** Yes — Series X|S (Scarlett), gfx10.3 RDNA2 + gfx10.1 legacy
  ops, GDK `MicrosoftGame.config` packages, D3D12.X guest API, FSSM RDNA2 shader containers. Same
  generation as Leonida, same shader pack, same console libraries. **[V]**
* **Does it require per-title recompilation?** **No per-title shader recompilation**: translation is
  per *program* (cached by HLSL, and by console-bytes+XCL-binary-hash on disk), and one retail pack
  went 26 698/26 698 with no title-specific handling **[V]** (`HANDOFF.md`, `gpu/recomp`). It **does**
  require per-title *runtime* adaptation, and it is honest about it: `xcl.toml` per title
  (`config.rs`: `device_type`, `title_memory`, `uma_mb`, `aliases`, `stub_returns`, `graphics`,
  `window_width/height`, `keyboard_mouse`), plus **auto-detected** D3D12.X layout generations
  (`QUEUE_SHIFTED` / `QUEUE_OLDER`, `NEWER_LIST_SLOTS`, `guard::make_layout_split`) and per-title
  memory policy (`uma.rs`, `sparse.rs`, `Uma::reserve_pool`). The `HANDOFF` is a sequence of
  title-by-title blockers. So: port the *runtime*, not the title — but expect a title-shaped week.

**Component that transfers regardless of backend, licence or generation:** the **diagnostic
methodology**, in three reusable pieces — (1) `guard` by *return address* (who called: game image vs
runtime) so one vtable can serve both; (2) **`readable(ptr, len)` on every console pointer** before
use, which converts "stale stack out-pointer" faults into logged skips; (3) the `report.json` **call
census** as the work queue (`called_stubs`, `unknown_iids`, `xgameruntime.unimplemented`, shader
mnemonics, audio formats) — all of which XCL learned while booting retail titles and none of which
depends on DXIL, GPL version, or GPU generation.
