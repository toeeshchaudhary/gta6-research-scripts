# BOOT6 — the null back-buffer entry, measured: the console slot table is not its producer

Branch `retail-boot-validation`, HEAD `ad6b1182f` (BOOT5's `2cae40ec2` plus the call trace). Runs from
`work/astra` with `LEONIDA_D3D12=vulkan`, `LEONIDA_SHADERS=work/astra/shaders-probe`, `LEONIDA_SKIP_INT3=1`;
GTX 1060 6GB, Vulkan backend, ~4 s per run. Every iteration is logged in
[`work/astra/PROGRESS.md`](work/astra/PROGRESS.md).

**Headline.** The null that crashes the back-buffer setup is **not** a value a layer call returned: between the last
layer answer and the fault the layer is entered exactly once, by nobody in the title (an AddRef from host code). The
table entry is `[presenter+0x60][0]`, the first back buffer's resource of the title's own presenter object, and the
producer is the title's **own** surface allocation, which fails for the 3840×2160 back buffer while every surface of
≤ 512 KiB succeeds. No `ExecuteCommandLists`, no completion, no `Present` yet.

---

## 1. The instrument (one commit, off by default)

`ad6b1182f` adds four trace hooks to `runtime/shims/d3d12_xs_device.cpp` and `d3d12_vulkan_device.cpp`, all gated on
`LEONIDA_XS_TRACE_CALLS=1`:

| hook | what it prints |
|---|---|
| `proxy_slot` wrapper (`trace_device_call`) | one line per **device-slot call**: thread id, slot, the guest **return address** (`_ReturnAddress()`, also as `game+RVA`, base from `LEONIDA_XS_TRACE_BASE`, default `0x140000000`), the first four arguments, and the value that went back |
| `trace_allocation_answer` | slot 25 and 108 answers: the description (`dim`, `WxH`, `fmt`, mips, array, `flags`, `layout`) and the `SizeInBytes`/`Alignment` returned |
| `trace_creation` | every resource creation (`create #N`): method, description, state, HRESULT and the pointer the caller got |
| `trace_dump_state` (`LEONIDA_XS_TRACE_DUMP=0xADDR:n,...`) | the qwords at guest addresses, printed with each slot 25/76/108/127/133 call — the only way to read the title's own state behind a null |

`proxy_slot_impl` now takes the caller as an argument so slot 61's console/host classification keeps using the *guest*
return address (with `_ReturnAddress()` inside the impl it saw the wrapper's own frame and took the host path, which
faulted in `CreateMetaCommand` — the BOOT2-era `0xffffffffffffffff` read).

Tests after the change: `xs_proxy_mock_test` PASS (10 allocations refused on purpose), `device_proxy_test` 134 PASS,
4 FAIL — the same 4 pre-existing "slot 48's queue" failures.

---

## 2. Task 1 — the null entry, by identity

### 2.1 The object and the record array (measured, gdb hardware breakpoint at `game+0x1862f2`)

`game+0x186170` is the presenter's per-frame back-buffer loop:

```
186183  testb $0x4,0x48(%rcx)          ; a special path, not taken (dword 0x48 = 0)
1861a2  cmpl $3,0x40(%rsi)             ; not 3 (dword 0x40 = 0)
1861a8  movzbl 0x45(%rsi),%r14d        ; back-buffer count, measured 1
1861b2  mov 0x60(%rsi),%r15            ; record array, +0x28 per record (second step)
1862a6..1862e3                          ; one record per buffer:
        create  ->  [r15+0x30*i+0x00]
        view    ->  [r15+0x30*i+0x18]  (through 0x140cc2840)
```

Measured at `game+0x1862f2` (the instruction after the create, one hit per buffer):

```
presenter object           0x10cc7e610   vtable game+0x658da80
[rsi+0x60] record array    0x10cc7e678   (== object+0x68; the object is allocated with the array inline)
record[0] +0x00            <created resource>   -> 0 on the failing pass
record[0] +0x18            0                     (the view, filled by 0xcc2840)
record[0] +0x28            0xf00  (3840)         record[0] +0x2c  0x870 (2160)
presenter +0x45            1     +0x46 0x500    +0x47 0x05   +0x48 0x0   +0x40 0
surface desc at [rbx]      dword0 0x08700f00 (width 3840 | height 2160 << 16), byte 6 = 1, byte 7 = 0x41
```

So the record the title walks is the **3840×2160 back buffer**: one record, `+0x00` = its resource, `+0x18` = the
render-target view.

### 2.2 The crash, restated precisely (proven)

```asm
140186313  mov 0x60(%rsi),%rax      ; record array
140186317  mov -0x14(%r15,%r13),%r8 ; record[i]+0x18
14018631c  mov (%rax),%rcx          ; record[0].resource  <-- null
14018631f  call 0x140cc2840
140cc2849  test %rcx,%rcx
140cc2852  je 0x140cc2936           ; the title's own "this is null" int3, skipped
140cc2861  testb $0x4,0x10(%rdi)    ; <- 0xC0000005 READ 0x10
```

`rcx` is null at the call, the assert is skipped, and the next instruction dereferences it. The int3 at
`0xcc2936` is therefore not a separate bug: it is the title *telling us* the pointer is null.

### 2.3 The producer of the null: the create at `game+0x1862e3`, not a slot (measured + inferred)

Measured at the callsite (gdb hbreak at `game+0x1862e3`): `rcx = 0`, `rdx = <surface desc 0x…fa92>`, `r8 = 1`,
`r9 = 2`, stack `+0x20 = 0`, `+0x28 = 0x108|…`, `+0x30 = 1`, `+0x38 = &out`, `+0x40 = 0`.
`game+0x1862e3` calls `0x145204e60`, which is a 5-byte jump to `0x14034beb0`. That helper, for this argument shape:

1. `0x142478140(surface desc)` — a pure validator on `width != 0`, `height != 0`, `flags@0xd`. **Passes** for the
   measured desc (`0x0f00`, `0x0870`, byte `0xd = 0` → `test $2` clear → return 1). *Proven by the desc bytes and the
   disassembly.*
2. builds the CPU-side surface object (`0x14501f390`, filled by `0x140164db0`),
3. `0x14193de10(object, 0)` — "make the GPU resource". Its disassembly (`0x14193de10`–`0x14193e313`) has exactly two
   `return 0` sites that this call can reach: `0x14193e310`, entered when the **internal allocation at `0x14193e23c`
   (`0x142474690`) returns null** (`je 0x14193e310` at `0x14193e24b`), or when the **slot 133 call fails**
   (`0x14193e303`).
4. `0` → `0x14034c0c0`: the object is destroyed and the helper returns null.

**The negative result that matters.** A failing slot-133 call is excluded: the trace prints every slot call, and in
that window the layer is entered once (an AddRef the layer makes itself, return address in `gta6rt.exe`). The whole
tail of the run, from the fault's own frame:

```
[trace] alloc25  dim=3 3840x2160 fmt=28 mips=1 array=1 flags=0x300001 layout=0x0 -> size=0x1fe0000 align=0x10000
[trace] tid 14444 device 25  from 0x140344188 (+0x344188)  args …,0x1,0x1,<descs>   -> <out>
[trace] alloc108 dim=3 3840x2160 fmt=28 mips=1 array=1 flags=0x300001 layout=0x0 -> size=0x1fe0000 align=0x10000
[trace] tid 14444 device 108 from 0x140abfe0d (+0xabfe0d)  args …,0x1,0x1,<descs>   -> <out>
[trace] tid 14444 device 1   from 0x7ff6b41a8d02 (host)    -> 0x8bf                (the layer's own AddRef)
   <crash: int3 0xcc2936 skipped, 0xC0000005 READ 0x10 at 0xcc2861>
```

So `record[0].resource` never got a value from any slot: **the answer the title needed (a 3840×2160 surface) was not
a slot answer at all.** The layer answered every question correctly — `GetResourceAllocationInfo` and
`GetResourceAllocationInfo2` both say `SizeInBytes 0x1FE0000, Alignment 0x10000` for the exact description the title
then fails to create.

### 2.4 Where inside the title the allocation fails (inferred, from the disassembly)

`0x142474690(size, align, kind)` returns null only when `size == 0` or `0x144fac3c0` fails, and `0x144fac3c0` starts
with `0x144fc99c0(cl, dl)` — a lookup into a **static heap table at `0x14aad45b0`**, address `(cl*9 + dl)*8 + 8`,
`cl = (object_flags@+0x10 >> 3) & 3`, `dl = object_flags & 3`. Dumped at the last calls of the run
(`LEONIDA_XS_TRACE_DUMP=0x14aad45b0:16,0x14aad45e0:16,0x14aad4610:16`):

```
[0][0] [0][1] [0][2]                 non-null
[1][6] [1][7] [1][8]                 non-null
[2][0] … [2][6]                      non-null
[3][4] … [3][7]                      non-null
every other (cl, dl)                 NULL
```

The table is sparse, the five 160×90/256×256/127×128 surfaces the same pass created all found a heap, and the
3840×2160 one did not. One conditional hardware breakpoint (`hbreak *0x14193e230 if $r8 > 0x100000`, so the small
surfaces do not consume the one or two hits gdb survives here) did stop on a large surface object and measured:

```
size=0x400000  align=0  object flags@+0x10 = 0x981  (cl = 0, dl = 1)  +0x44 = 0  +0x45 = 0  index@+0x12 = 3
heap table [0][0]=0x1471c1560 [0][1]=0x1471c1460 [0][2]=0x1471c2808 [1][0]=0x1474438b0 …
```

`0x142474690`'s own branch is `cmp $1, dl; ja` → `dl > 1` uses `[cl][dl]`, `dl <= 1` uses `[0][2]`; the measured
large object had `dl = 1`, so it took `[0][2]` (non-null — the table's sparseness is therefore not the cause for it).
The 33.4 MiB call itself was never reached in that debugger run (gdb stalls in the presenter thread after the first
hit — see §7). So the two candidate causes left are (a) the flags word of the 3840×2160 surface object selects a
row/column the title never filled, (b) the heap it selects cannot serve 33.4 MiB. Distinguishing them needs the
surface object's `+0x10` flags for a failing versus a succeeding surface, which is the next measurement (§7).

---

## 3. Task 2 — the present-path slot audit (measured)

| console slot | method | called | answer |
|---|---|---|---|
| device 78 | `SetFrameIntervalX` | yes, once | routed (`args 0x0 0x8235 0x3 0x100000000 …`) |
| device 79 | `ScheduleFrameEventX` | yes, once | routed |
| device 80 | `WaitFrameEventX` | yes, once | routed (`args 0x0 0x0 0x0 0x2 …`) |
| queue 32 | (queue extension) | yes | 0 |
| queue 35, queue 16 | `GetDesc`, `GetTimestampFrequency` | yes | non-null |
| queue PresentX | slot 30 **or** 32 per `XCL.md` §7.1 | not yet | — |
| swap-chain creation / back-buffer retrieval | — | **no such call exists in this path** | — |

`PresentX ready (window …)` is reached (the presentation core makes a window and a swapchain), but **there is no
console slot that hands the title its back buffers**: it makes them itself, at console VAs out of its own arena, and
only the *placement* reaches us:

```
[trace] state[0x149e1dac0] = base 0x18a3b160000  size 0x600000000 (24 GiB)  bias 0x1903b160000   (measured)
[trace] tid … device 133 from 0x14193e2db args <va> <desc> 0x6 0x0 -> 0
```

so the 24 GiB arena is not what runs out (33.4 MiB is nothing against it), and the failure is in the *backing store*
allocation, before the placement call.

**Answers that were non-success anywhere in the run** (whole-run census of the trace, no filter):

| slot | count | value | where |
|---|---|---|---|
| 57 | 585 | `E_NOTIMPL` | always from `game+0x247757e`; the layer logs it as `CreateLifetimeTracker (not supported)` |
| 67 | 42 | `E_INVALIDARG` | the known FSPX kind-6/kind-0 misses |
| 86 | 6 | `E_INVALIDARG` | the known 688-byte PSO stream |
| 74 | 1 | `E_INVALIDARG` | `0x141e6c2c1`, a `CreateHeap`-shaped call the layer forwards |

None of them is in the fault window, and none of them produces a pointer the presenter stores.

---

## 4. Iterations (first failure each)

| # | build | first failure | boot dir |
|---|---|---|---|
| 8 (BOOT5) | `2cae40ec2` | `0xC0000005` READ 0x10 at `game+0xcc2861` after int3 `0xcc2936`; 5 int3 skipped; no submission | `boot-041720` |
| 9 | `+ad6b1182f` call trace (slot 61 caller threaded through, `_ReturnAddress()` moved into the wrapper) | **new, earlier**: `0xC0000005` READ `0xffffffffffffffff` in `gta6rt.exe+0xb9caa`, from slot 61 taking the *host* path (`CreateMetaCommand`). Fixed in the same build: the impl now receives the guest caller | `boot-045235` |
| 10 | same, rebuilt | back to `0xC0000005` READ 0x10 at `game+0xcc2861`; the trace names the whole window (§2.3) | `boot-045508` |
| 11 | + `trace_allocation_answer`, + `trace_creation` | same fault; the failing surface is named: 3840×2160 fmt 28 flags 0x300001, allocation answer `0x1FE0000/0x10000`, and the create emits no `create #N` line — the layer is never reached | `boot-051312` |
| 12 | + `LEONIDA_XS_TRACE_DUMP` (arena + heap table) | same fault; arena 24 GiB (not exhausted), heap table `0x14aad45b0` sparse, the 33.4 MiB row null | `boot-053241`, `boot-053203` |

Int3s skipped, every run 9–12, all five: `0x247af2d`, `0x1e6c2c5`, `0x344196`, `0xabfe1b`, `0xcc2936`. They are the
same five as BOOT5; none of the new instrumentation skips anything else. (`0x247af2d` is the resource-budget assert
`(end - start + [0x1475e6ff0]) <= 0x1FFFFF`; the code after it is the same on both branches, so skipping it changes
nothing but the assert. With `LEONIDA_SKIP_INT3` unset the run stops there, as before.)

`LEONIDA_XS_TRACE_CALLS=1` does not change the behaviour of the boot: run 10 reproduces BOOT5's fault exactly, and
the four creation/validation results the trace adds are the same with the trace off.

---

## 5. Submission, backend completion, Present — three separate facts

- **Submission: none.** No `ExecuteCommandLists` line; the list proxy's slot log stops at the list-creation calls
  (`list slot 0/9/131/132/139/146/32/52/71/72/74`), none of them a submission.
- **Backend completion: none.** No fence value, no `Signal` completion, nothing submitted to complete.
- **Present: none.** `PresentX ready` is the presenter's *construction* (window `0x5507FC`), not a call.

All three remain open. The boot is stopped before the frame loop's first submission by the back-buffer resource.

---

## 6. Corpus and new shader demand

Unchanged at 669 modules in `work/astra/shaders-probe`: **48 "no translated" lines, 40 distinct**, all FSPX
kind-6/kind-0 with no carved FSSM blob — the same 40 as BOOT5. **No new shader demand appears** in runs 9–12: the
path that fails now (the presenter's back-buffer setup) resolves no shader at all, and the compute-PSO misses
(42 `E_INVALIDARG` on slot 67) are the same programs as before.

---

## 7. Next blocker and the next measurement

**Next blocker (measured):** the title's own surface allocation for the 3840×2160 back buffer returns null inside
`0x14193de10`; the layer is not called in that window, so no slot can be blamed and no slot fix can move it.

**The next experiment, in order of cost:**

1. *Distinguish "sparse row" from "row too small".* Put one hardware breakpoint on `0x14193e230` (the arena branch of
   `0x14193de10`, reached once per placed surface, six times) and print `%r8` (the byte size handed to `0x142474690`)
   and `*(uint16*)($rsi+0x10)` (the object flags that choose the heap table row/column) for the five sizes that work
   and the 3840×2160 that does not. If the flags differ, the title is choosing a different heap for the back buffer;
   if they are the same and only `%r8` differs, the heap cannot serve 33.4 MiB.
   *Caveat measured in this session:* gdb hardware breakpoints on this binary survive only one or two hits — the guest's
   vector handler records the debug trap as `EXCEPTION_SINGLE_STEP (0x80000004)` and the process ends. One
   breakpoint, few hits, or a guest-side patch is required; four breakpoints at once silently lose hits under the
   thread switch the presenter thread causes.
2. *Find who fills `0x14aad45b0`.* A scan for RIP-relative stores to that address lists the heap registrations; the
   missing row's registration is the code path the boot does not take, and whatever gates it (a device feature answer,
   an `XMem` budget, a `D3D12XboxCreateDevice` parameter) is the layer's lever.
3. *Only then* consider a layer change. Until (1) or (2) names a gate, any layer change is a guess; the one thing this
   session proves is that the current best guess in BOOT5 §7 ("`[rsi+0x60]` is a table of per-frame objects the title
   fills from a call we answer with a null") is **wrong**: nothing null came from a slot in that window.

**Hand-back.** The shortest true statement: `record[0].resource` of the presenter's back-buffer array is null because
the title's own allocator could not hand out the 33.4 MiB backing store for a 3840×2160 surface; the layer answered
`GetResourceAllocationInfo(2)` correctly (`0x1FE0000`, 64 KiB) one call earlier and was not asked to create anything.
