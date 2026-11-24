# BOOT5 — slot 61 + slots 86/108 merged, the state refusal fixed, the next wall

Branch `retail-boot-validation` in `work/astra/upstream`. Runs from `work/astra` with
`LEONIDA_D3D12=vulkan`, `LEONIDA_SHADERS=work/astra/shaders-probe`, `LEONIDA_SKIP_INT3=1`; GPU NVIDIA GTX 1060 6GB,
Vulkan backend. Every iteration is logged in [`work/astra/PROGRESS.md`](work/astra/PROGRESS.md).

## 1. The merge

`4e7c8a8a5` (slots 86/101/108, PR #8517 deliverable) is an ancestor-line descendant of `8c57e8fba`, so the two pieces
share a base and the merge is content-only: **`20b1281f8`**, five files, one conflicted file.

| item | what was done |
|---|---|
| conflict `runtime/shims/d3d12_xs_device.cpp` | slot 61 keeps **one** handler (the console-description decode) inside **one** caller-gated dispatch branch instead of two competing `Slot == 61` branches; the overridden-slot predicate is the union of both sets; the slot-name entry names both behaviours |
| `runtime/shims/d3d12_xs_device.h` | slot 61 comment updated to the decoded form; the `ConsoleCaller` hook from #8517 kept |
| `runtime/test/xs_proxy_mock_test.cpp` | the two slot-61 sites pass a console 0x6C-byte description (`ConsoleSamplerDesc`) and assert every decoded field, the anisotropy clamp, the null-description skip and the handle translation |
| `docs/d3d12_vulkan.md` | slot 61 sentence added beside the 86/101/108 paragraph |

**Regression the merge itself caused, and its fix.** Resolving the dispatch by hand dropped the `Slot == 62` branch
(the two slot-61 branches had bracketed it). `device_proxy_test` then died with `0xC0000409` (stack-cookie overrun) on
the first slot-62 call, because slot 62 fell through to the by-number forward onto `CreateStateObject`. Restoring the
branch fixed it; a set comparison of `Slot == N` branches and of `slot_name` cases against both parents now reports no
missing slot.

### Test status (merge parent control included)

| test | merge `20b1281f8` | parent A `962a1d70d` | parent B `4e7c8a8a5` |
|---|---|---|---|
| `device_proxy_test` | FAILED, 4 failures: "slot 48's queue is a compute queue with the console flags dropped" | identical 4 failures | identical 4 failures |
| `xs_proxy_mock_test` (contains `check_levels`) | PASS (10 allocations refused on purpose) | PASS | PASS |
| `d3d12_vulkan_device_test` | exit 1 (same as parent), 0 mismatches in every compared section | exit 1, 0 mismatches | not built |

The 4 `device_proxy_test` failures are **pre-existing** (the same text, 4×, on both parents: the queue proxy answers an
unproven slot 18 as the frequency getter, so `GetDesc` returns garbage). `xs_proxy_mock_test` covers `check_levels`
(section 1, "devices up to ID3D12Device, Device1, Device3, Device9: 44/47/51/76 slots, 45/46/50/75 refused without
E_NOINTERFACE" — passed). `d3d12_vulkan_device_test`'s exit 1 is also pre-existing on this driver (it prints
"invalid arguments format 40 RT: the host accepts it, this Vulkan driver can't" and ends at "upload buffer memory:
system memory" on the untouched parent too); the merge adds no mismatch. Final HEAD `2cae40ec2` re-runs the same way:
`device_proxy_test` 4 pre-existing failures, `xs_proxy_mock_test` PASS.

Commits: `962a1d70d` (slot 61 decode, committed first as asked), `20b1281f8` (merge).

## 2. Runs, first failure each

| # | build | first failure | boot dir |
|---|---|---|---|
| 1 | merge `20b1281f8` | int3 at `game+0xcc2936` skipped, then `0xC0000005` READ 0x10 at `game+0xcc2861`; last layer line is the initial-state refusal, dimension 3 | `work/astra/boot-032839` |
| 2 | `cd57450eb` (state map, first version) | same AV — the map returned the *original* state, so the render-target texture was still refused (the depth one mapped to 16) | `work/astra/boot-033834` |
| 3 | `cd57450eb` + `return kept` fix | **the assert is gone**; first failure is the 108-agent's measured stop: `0xC0000005` WRITE 0x20 at `game+0x24844a9` | `work/astra/boot-034040` |
| 4 | + slot-41 probe | same; probe shows signature 3 refused `0x80070057` (argument type 105) | `work/astra/boot-035713` |
| 5 | + console type 105 mapped by size | same; signature 5 (mesh dispatch) `0x80004001` E_NOTIMPL | `work/astra/boot-040900` |
| 6 | + DISPATCH_MESH → dispatch kind | **the `0x24844a9` null is gone**; new first failure: int3 `0xcc2936` skipped, then `0xC0000005` READ 0x10 at `game+0xcc2861` (frames `0x186324`, `0x18573b`, `0x184f42`, `0x5b132d3`); "PresentX ready" reached | `work/astra/boot-041011` |
| 7 | + creation-failure probe | same; no `CreateCommittedResource` failure logged | `work/astra/boot-041225` |
| 8 | + 42 translated shaders | same; "no translated" 84 → 48 lines, 40 distinct, all FSPX | `work/astra/boot-041720` |

Int3s skipped, run 8, all five: `0x247af2d`, `0x1e6c2c5`, `0x344196`, `0xabfe1b`, `0xcc2936`. The `0xcc2936` site is
the same assert as in iteration 1 but a different caller (see §6): it is the title's "this pointer is null" breakpoint,
hit from several places.

## 3. The initial-state mapping

`runtime/shims/d3d12_vulkan_device.cpp`, commit `cd57450eb`.

`console_initial_state(desc, state)` replaces the state for a **texture** before validation, from the resource's own
flags: `RENDER_TARGET` with `ALLOW_RENDER_TARGET`, `DEPTH_WRITE` with `ALLOW_DEPTH_STENCIL`, `UNORDERED_ACCESS` with
`ALLOW_UNORDERED_ACCESS`, `GENERIC_READ` with `ALLOW_SIMULTANEOUS_ACCESS`. A state whose single write bit the flags
already back is kept (its buffer-only bits are dropped, which is the fix iteration 2 missed); a state no flag accounts
for is returned unchanged and `initial_state_refusal` still refuses it. Buffers take any bits and are untouched. The
mapping runs in `create_committed_validated`, `create_placed` and the reserved path, and the **mapped** state is what
`create_committed` creates the image in, not only what the check sees.

Test: `d3d12_vulkan_device_test` gained a `console_state` case flag checked on the layer alone (a mapped console state
must be `S_OK`; the PC runtime is only reported), with four cases — render target and depth texture in
`INDEX_BUFFER | RENDER_TARGET` 0x6, a UAV texture in `VERTEX_AND_CONSTANT_BUFFER | UNORDERED_ACCESS`, and the
read-only `INDEX_BUFFER | RENDER_TARGET` on a plain texture that must stay refused. **Measured surprise**: the host
runtime *accepts* 0x6 when the flag is `ALLOW_RENDER_TARGET` or `ALLOW_UNORDERED_ACCESS` (it only looks at the flag, not
the extra bit), so the layer's original refusal was wrong there too; only the depth case actually diverges from the host.

## 4. Console command signatures (the `0x24844a9` wall)

Proven by the slot-41 probe: the boot creates five signatures — `(0, 16 B)`, `(1, 20 B)`, `(105, 12 B)`, `(2, 12 B)`,
`(10, 12 B)` — and the init that owns them returns false when any fails, so the 0xD8-byte frame-ring array it allocates
right after them (`0x145cabb50`, called from `0x142479662`) is never created, and the first frame writes into the null.

`CreateCommandSignature` now translates a **console** argument type on a copy of the description by the argument size
the signature's own `ByteStride` carries: 12 → `DISPATCH`, 16 → `DRAW`, 20 → `DRAW_INDEXED`, 24 → `DISPATCH_RAYS`.
`DISPATCH_MESH` (a public type the kind switch answered `E_NOTIMPL`) maps to the `dispatch` kind — `IndirectKind` has no
mesh entry and the argument is the same three counts. **Inferred, not proven**: that 105 is a dispatch at all. Nothing
names it (the public enum stops at 11; the XS reference page was not reachable); the 12-byte stride is the whole
argument. The first `ExecuteIndirect` with that signature will show which pipeline the title binds.

## 5. Shader corpus

`add_shader.py` had rotted against tool drift and translated nothing: `rdna2spirv.py` no longer takes `--jobs`, and both
tools want the carve's layout (`<stage>/fssm/<name>.fssm` with `<stage>/index.json` naming each file's stage) — the
script copied flat files and no index, so every shader came back "stage ?" and then "missing translation input".
`corpus_loop.py` also had to delete an existing `run.jsonl` (`gta6rt` refuses an existing trace).

After the fix: **42 FSSM modules translated** (corpus 627 → 669, index 290 → 332 entries). The boot's "no translated"
lines fall 84 → 48, and the 40 distinct hashes that remain are **all FSPX kind-6/kind-0**, for which no carved FSSM
blob exists (`add_shader.py` reports "not carved" for every one). So the on-demand FSSM corpus is complete for this
path: the boot needs no further FSSM module, and 40 FSPX payloads are the open shader work.

## 6. Submission

**No `ExecuteCommandLists` has ever been called. Nothing has been submitted. No `Present`.** What has been established:

- pipeline creation — five command signatures created (S_OK), compute PSOs still failing (`slot 67 ... 0x80070057`,
  one per missing FSPX blob), graphics PSO through slot 86 accepted;
- presenter object — `PresentX ready (window 0x850870)`, i.e. the presentation core made a window and a swapchain;
- backend completion / Present — none.

## 7. Next blocker

`0xC0000005` READ 0x10 at **`game+0xcc2861`** (boot-041720), reached with a null pointer: the caller does
`mov 0x60(%rsi),%rax; mov (%rax),%rcx` and passes that as the context of the helper at `0x140cc2840`, which asserts on a
null context (`je 0xcc2936`) and then reads `0x10(%rcx)`. The table at `[rsi+0x60]` has a null first entry; the loop
over its 0x30-byte records runs right after `PresentX ready`, i.e. during the title's back-buffer/frame setup.

Proven: the pointer is null at source, no `CreateCommittedResource` in that window fails (creation-failure probe), the
corpus is not involved (the failure is identical with 42 more shaders), and the same crash site appears both with and
without the signature work — what changed is only how far the run gets before it.

Inferred: `[rsi+0x60]` is a table of per-frame/back-buffer objects the title fills from a call we answer with a null,
most likely one whose IID or description this layer does not map. Not yet proven which call fills entry 0; gdb can stop
at the AV but needs the guest's relocation base (the image is ASLR-mapped, `break *0x140cc2861` is not hit), and the
int3 asserts need pass-through under the debugger first.
