# GTA VI research closeout

24 November 2026 · Xbox Series build 1.0.2.1 · Windows 11, Ryzen 3 3300X, GTX 1060 6 GB

The project produced a standalone Win32 Vulkan renderer, a structural mission-table executor and a local test setup for bringing up the retail executable. The renderer drew reconstructed scenes. The retail executable reached graphics initialization and back-buffer setup on a diagnostic path. No run recorded a game menu or a presented frame.

## From archive to scene

The original package inventory recorded 108 matching SHA-256 checks across 208.51 GiB. The initial investigation proceeded without the executable. A separately obtained executable became available later, so the early report and the later boot runs describe different experimental conditions.

| Measurement | Result | Interpretation |
| --- | --- | --- |
| Geometry | 185,352 hash-to-OBJ bindings | Provides candidate meshes to a viewer. A binding alone does not verify materials or placement. |
| World placement | 1,670,435 entities across 23,532 maps | 99.85% of names resolved and 84.161% bound to a model in the reported pass. |
| Shader discovery | 26,503 containers | Inventory of containers in the scanned corpus. |
| Shader translation | 18,464 of 19,007 tested passed SPIR-V validation | Structural validation. Visual equivalence requires a separate rendering test. |
| Story structure | 145 mission IDs, 40,804 state records and 135 job flows | Structural relationships recovered from data. Branch conditions and opcodes remain unresolved. |

The [renderer source](../engine/src) contains the OBJ and DDS loaders, scene placement and screenshot writer. A hand-assembled street demonstrated meshes at consistent scale. A 17,168-triangle handguard exercised translated vertex and pixel stages. A full-screen shader test compared sampled pixels against known input and recorded luminance correlation of 0.9982. These are separate tests with different inputs and success criteria.

The mission executor consumed 2,314 decoded group files and walked mission, state, band, record and entity relationships. Five runs produced traces, plans and scene descriptions. One scene rendered at the recorded entity positions. This demonstrates traversal and placement. Playing a mission would also require control flow and gameplay systems.

## Retail execution

The local PE loader passed 23 of 23 fixture images in the recorded mapping, relocation and import tests. Later runs exercised the original executable through a console graphics compatibility layer. Startup demanded a small, identifiable compute-shader subset. Following the call stream let the project test changes in seconds rather than waiting hours for a complete corpus rebuild.

The furthest documented run stopped while preparing the first 3840 × 2160 back buffer. The standalone renderer and the retail executable have independent rendering paths. See the [Leonida integration report](leonida-final.md) for the controls, diagnostic settings and fault boundary.

## Archive coverage

The repository preserves selected Python research scripts and renderer source. The source snapshots were filtered before publication. This report summarizes the local REPORT, ENGINE_M2, ENGINE_M4, MISSIONRT, SPIRV_RUN, CITY and BOOT6 records. Raw inputs, screenshots, per-run traces, intermediate data, binaries and the complete original Git histories are outside this archive. A fresh checkout alone cannot recreate the historical measurements.
