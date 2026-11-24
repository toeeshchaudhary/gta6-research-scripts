# Leonida contribution and retail integration closeout

24 November 2026 · Local retail validation on Windows with the Vulkan backend and GTX 1060 6 GB

The integration work established where retail startup stopped and which earlier failures could be moved with controlled changes. Local tests reached queue, fence, descriptor, compute-pipeline and indirect-command-signature setup. No retail command-list submission, backend completion, presentation or menu was observed.

## Upstream work recorded locally

| Submission | Evidence and limits |
| --- | --- |
| #7170, function and RTTI inventory | Synthetic controls exercised the scanner. The retail export contained 299,257 address-ordered runtime-function ranges. Ranges can represent fragments and do not establish a unique source-function count. |
| #7177, compiler length-vector search | All 12 synthetic control families were tested. No contiguous 129–140-byte candidate passed in the scanned image. A later check identified the proposed 0x28-stride descriptor as MSVC exception metadata. The candidate decoder was never tied to the story payload. |
| #7178, virtual-memory call shape | Recovered caller-side counts of three and four and exercised both forms with a synthetic host. The test shim returned E_NOTIMPL. Page reservation and mapping semantics remain open. |
| #7220, PSIN root registration | Located registrations for both root IDs and measured 39 member offsets across the layouts. Cross-checked 1,009 script and 2,270 story headers. Field naming and serialized instance layout remain incomplete. |

These identifiers and submissions come from local session records. Upstream search was unavailable at closeout, so merge status is unverified. Integration of another contributor’s patch below means adoption in a local test branch.

## What changed in the boot path

1. **Loader and device bring-up.** Integrating TLS, GDK and storage work moved execution into device creation. The session recorded five targeted TLS tests, 144 GDK checks and 272 storage checks passing. Queue and command-list interface fixes then exposed resource and descriptor calls.
2. **Compute shader demand.** One trace recorded 53 shader resolutions covering 52 distinct BVH compute programs. All 52 translated modules passed SPIR-V validation. An index containing a shader hash and stage, with the corresponding module alongside it, sufficed for this experiment.
3. **Argument spill.** The measured BVH signature had eight two-word descriptors and fourteen constants. Its compiled program loaded the complete argument block through a 40-bit pointer in the first register pair. Packing the whole block removed the graphics-only diagnostic for this signature. A corpus-wide shader-to-root-signature contract was never established.
4. **Resource and sampler fixes.** Copying 182,452,224 bytes into a backing buffer produced the first real raw view for one slot-70 call shape. Slot 61 passed two arguments into a host method expecting six. Cross-project comparison suggested a sampler method, followed by local sampler tests. Four pre-existing queue-related mock assertions remained on the recorded integration branch.
5. **Allocation accounting.** Adapting upstream #7235 to the local resource path reduced the measured residual at the title’s budget check from 64 MiB to 256 KiB. Two fresh, assertions-enabled runs passed the old check and stopped at a later breakpoint at retail RVA 0x19f4f58. These are the normal-run controls.

## Last diagnostic and remaining uncertainty

BOOT6 recorded local revision ad6b1182f on retail-boot-validation with guest breakpoint skipping enabled. The failing record was the first surface in the presenter’s back-buffer array. The layer answered the 3840 × 2160 allocation query with size 0x1FE0000 and 64 KiB alignment. Before the fault, the only subsequent layer entry in the traced interval was a host-side reference increment. The title’s surface allocation left the entry null.

Small surfaces succeeded. A separate probe saw a non-null heap selection for a 4 MiB surface but lost the failing larger call under the debugger. The evidence leaves two explanations open: selection of a different heap, or insufficient capacity in the selected heap. A discriminating measurement would record the size, selection flags and heap for both a successful surface and the failing surface in the same run.

## Preservation boundary

This report consolidates the local Astra progress journal, SAMPLER, XCL, BOOT2, BOOT5 and BOOT6. The filtered research repository does not preserve the complete validation worktrees, unmerged commits, local patch stacks, debugger captures, retail inventories or shader cache. The revision and PR numbers provide provenance, not a guarantee that those objects remain retrievable.
