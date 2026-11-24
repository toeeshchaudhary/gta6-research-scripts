# GTA VI research scripts

Selected Python scripts from local graphics and file-format research, preserving the original folder layout. These are working research scripts. Many expect intermediate files from earlier experiments and use paths relative to the repository root. Inputs, generated outputs and the separate Leonida checkout are excluded.


## Vulkan renderer

The engine folder contains the Win32 Vulkan renderer, OBJ and DDS loaders, scene placement, screenshot writer and hand-written SPIR-V assembly. On Windows, put spirv-as and spirv-val on PATH and run engine\build.cmd (or engine\build.cmd explore for BlockExplorer). The script uses the Visual Studio x64 toolset at the path configured in build.cmd. Supply your own input assets for runtime experiments.

## Final reports

- [GTA VI research and renderer](reports/gta6-final.md)
- [Leonida contributions and retail boot investigation](reports/leonida-final.md)
