# BOOT.md — retail GTA VI boot attempt, continued from boot-221336

_Started 2026-11-23 22:50 UTC+5:30 on `retail-boot-validation` (HEAD f6d6e9698), continuing the handover at the
descriptor-write fault. This file is written as the run progresses; the final state is at the bottom._

**Verdict: no intro video, no menu, no present. The descriptor-write fault is gone; #7066's slot 70 and, found here,
slot 25 (struct return) and slot 127 (committed resource) are handled, the slot-133 VA question is measured, and
compute-pipeline creation now succeeds with translated shaders. The run survives ~35 s instead of 2.5 s before dying on
a null global callback in the title's own startup loop. No pixel has been presented, so nothing has been rendered and
nothing can be called a frame.**

## 1. What was merged

* `origin/main` merged into `retail-boot-validation` (merge commit 664e4cfd8, 113 commits, 296 files, no conflicts).
  The 9 local integration commits are kept on top of tested upstream 8575d36ed.
* PR **#7066** (Xbox device slot 70: a shader-resource view from raw words) integrated by a 3-way apply of its whole
  four-commit diff, not by cherry-pick: the branch shares no merge base with the shallow clone, and a single apply
  gives one conflict set instead of four. Conflicts resolved as unions, keeping the local `133`/`26`/`25`/`17-24`
  routes and making the refactored `route_xbox_device_slot` call `proxy_create_command_queue_x` so the console queue
  flags stay translated. Test sections renumbered 11/12/13.

## 2. What was changed and why

Each item is one experiment; the first failure after it is in §3.

| Change | Why |
|---|---|
| PR #7066 as-is (slot 70 → null view, then a raw view when the VA is a known buffer) | The handover's `0xC0000005 **write**` to `0x144dac5fa` was the title's SRV writer writing through a destination the proxy had let the PC `CreatePlacedResource1` (slot 70) misinterpret. |
| Slot 25 (`GetResourceAllocationInfo`) takes the console's struct-return form | After #7066 the next stop was `host+0xeee45`, `jmp [r10+0xC8]` with `r10 = [rbx+0x10]`, where `rbx` was the title's return buffer, not the device: the console passes the 16-byte return buffer in RCX and the device in RDX, as already measured for slot 26. Handled with the same `is_device_proxy(a1)` sniffer so PC callers still forward. |
| Slot 127 (`CreateCommittedResourceX`) implemented | Slot 127 is past an 80-slot PC vtable, so the title got `E_NOTIMPL` and asserted (`retail+0xcc2834`). Its call site (`retail+0x193e1b4`, `call [rax+0x3f8]`) passes (heap properties, heap flags 8, resource desc, state, clear value, 0, 0, 0, `IID_ID3D12Resource`, out) — the PC `CreateCommittedResource` with three extra zero words. Xbox flag bits are masked; the resource is built for real. |
| A texture initial state with no texture bits becomes `RENDER_TARGET` | The title passed state `3` (the two buffer-only bits) for a 3D render-target texture and the layer refused it. |
| `xs_proxy_mock_test`'s slot-18 call now passes a real SRV description | #7066's mock copies the description while the call is live; the local heap-hook test passed the integer `0x33` as a pointer and faulted. |

Not changed: slot 133 still creates a committed resource that is **not** backed by the VA (open, §5).

## 3. Iterations — the first failure of each run

| Run | First failure |
|---|---|
| boot-225514 | Reproduction after the merge: `0xC0000005` **write** at `0x144dac5fa`, `host+0x4042f5`, called from `game+0x4ecc821` — the same fault as boot-221336 (host RVA moved with the rebuild). |
| boot-231434 | After #7066: slot 70 handled; `0xC0000005` **read** at `0xffffffffffffffff`, `host+0xeee45`, caller `game+0x344188` — slot 25 forwarded with the console's argument order. |
| boot-232146 | After the slot-25 handler: slot 25 passes (buffer/device/mask 1/count 1 logged), then slot 127 is beyond the PC vtable → `E_NOTIMPL` → the title's `int3` assert at `game+0xcc2834`. |
| boot-233610 | Slot 127 handled but the layer refused the description: `CreateCommittedResource refused (initial state of a texture (buffer-only or undefined bits)), dimension 3`. |
| boot-233711 | Slot 127 creates a 3840x2160 R8G8B8A8 3D texture, slot 20 (`CreateRenderTargetView`) is called, then the title's own sanity check `int3`s at `game+0x247af2d` (a `begin/end` difference compared against 2 MiB; inputs `0x4000000`, i.e. 64 MiB, so it looks like a block-size sanity check that the console's placement satisfies and the PC side does not). |
| boot-234003 | With `LEONIDA_SKIP_INT3=1` (diagnostic): the assert is stepped over, slots 16 (`CreateRootSignature`) and 62 (`Xbox CreateComputePipelineState`) are reached, then `[rt] d3d12: no translated shaders: set LEONIDA_SHADERS to <work>/shaders/spirv` and a C++ exception from `XboxBvhBuilder.dll`. |
| boot-002058 | With a 290-entry hand-built shader index (`work\astra\shaders-probe`): `290 translated shaders`, then `no translated compute shader for FSSM sha256 b5316b2e…` — that program is XboxBvhBuilder.dll's, not one of the 26,503 in `shaders.rpf`. |
| boot-003753 / 004305 | With the DLL's 52 compute programs translated too (`shaders-probe\bvh`): 342 shaders load, **slot 62 (CreateComputePipelineState) no longer fails**, the title's `int3` at `game+0x247af2d` is skipped, then 16 s with no D3D12 call at all and a `0xC0000005` **write at 0**, `game+0x2215c35`, from a null global callback inside the 1-second polling loop at `game+0x2215af6`. The run now lives 22-38 s instead of 2.5 s. Still no present. |
| boot-005251 | With the CPU free (the corpus shards stopped): the title's `int3` at 10.4 s, then the root signature and the compute pipeline, then the layer reports `root signature usable for graphics only: root parameter 8 does not fit in the user SGPRs from s4 (spill array not modelled)`, and at 33.7 s the same null-callback `0xC0000005` write at 0. The 75 s harness timeout fired on this run only because the process takes over 40 s to tear down after the fault. |
| boot-005738 | Repeat with a 180 s harness timeout (the 75 s one can fire during teardown): the same sequence, the null write at 34.9 s, and the process exits `0xC0000005` — so the fault, not a hang, is the first failure. |

### The assert at `game+0x247af2d`

`rax = [rsp+0x78] - [rsp+0x70]; add rax, [rip+…]; cmp rax, 0x1FFFFF; jbe ok; int3`. Both words are set just before the
resource-creation loop: `[rsp+0x70] = 0` and `[rsp+0x78] = 0x4000000` (64 MiB, or `0x5200000` when a query returns
true), so the comparison is 64 MiB against a 2 MiB limit. Read as a block-size sanity check around the placed-resource
path, the console's placement satisfies it and this one does not; whether it is the caller's bug or a consequence of the
committed-instead-of-placed resource is not established. With the check stepped over the title runs 16 s more and then
dies on the null callback, so it is not noise.

## 4. Exact commands

```powershell
cd "C:\Users\suki dai yoh!\Documents\gta6\work\astra\upstream"
.\..\boot-dev-build.cmd                       # cmake RelWithDebInfo build of gta6rt + the two proxy tests
$env:LEONIDA_D3D12 = 'vulkan'
$env:LEONIDA_SHADERS = 'C:\Users\suki dai yoh!\Documents\gta6\work\astra\shaders-probe'
$env:LEONIDA_SKIP_INT3 = '1'                  # diagnostic: step over the title's own int3 asserts
python ..\boot_local.py
```

The last run: `work\astra\boot-005738\run.jsonl` (structured) and `run.log`; `boot-005251` is the same
sequence under the old 75 s harness timeout. Raw runs stay local. `work\astra\boot_local.py` now uses a
180 s timeout per mode: the process takes over 40 s to tear down after the fault, so 75 s sometimes reported a
timeout instead of the exit code.

### Building the shader folder that got past slot 62

```powershell
# XboxBvhBuilder.dll's 52 compute programs (about 4 minutes)
$d = 'C:\Users\suki dai yoh!\Documents\gta6\work\astra\shaders-bvh'
python -I tools\pe_shader_containers.py "<package>\XboxBvhBuilder.dll" --extract $d
python -I tools\fssm_unpack.py $d --carve-index "$d\index.json"
python -I tools\shader_disasm.py "$d\fssm" --unpack-index "$d\fssm_index.json" --out "$d\disasm" --mcpu gfx1013 --jobs 8
python -I tools\rdna2spirv.py "$d\disasm" --out "$d\spirv" --no-asm --max-shared-memory 32768 --wave64-emulate
# then copy "$d\spirv\*.spv" and index.json into shaders-probe\bvh\
# one shaders.rpf program on demand, by the FSSM hash the runtime names: python ..\add_shader.py <sha256>
```

`index.json` needs only `fssm_sha256` (SHA-256 of the FSSM blob, which is the lookup key) and `stage` per entry, plus
`<name>.spv` beside it; every other field is optional and the layer accepts the defaults.

## 5. Next blocker and open items

* **The null-callback trap after 16 silent seconds** (`game+0x2215c35`) is the current first failure. It sits in a
  1-second polling loop near the top of the title's startup and the global it loads is zero. Not yet identified.
* **Slot 133's VA is still not backed.** Measured on the first call: the placed resource's VA is `0x25343630000`
  with a 185 MiB width — the address range `XMemVirtualAlloc` had already reserved as a placeholder and that
  `XMemMapPhysicalPages` fills page by page. So the title's own writes there *are* backed by its physical pages; what
  is missing is the other direction: the Vulkan buffer behind the placed resource is the layer's own allocation, so
  the bytes at the console VA never reach the GPU, and `slot 70`'s raw view resolves to the null view ("no buffer
  holds the address"). The fix is to make the resource's Vulkan memory the same pages — import the section into
  Vulkan (`VK_KHR_external_memory_win32`) or register the console VA as an alias of the resource and copy on submit.
  `map_placed_va` (new) maps only ranges the title has *not* already reserved, and logs that it leaves the measured
  one alone; it is a diagnostic step, not the fix.
* **The full shader corpus is not built.** `make_game.py --stages shaders` disassembly of the 26,503 FSSM blobs runs
  ~6-7 h on this 8-core machine (it was stopped so it would not starve the runs). The on-demand path covers what the
  boot actually reaches; a real frame will need the rest.
* **Pixels.** No Present has been called in any run, so there is still no window to capture: the "blank white
  Americas screen" has been neither reproduced nor refuted here.
