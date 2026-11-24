@echo off
rem ---------------------------------------------------------------------------
rem GTA6 engine v0 build. Requires the VS x64 toolset (vcvars64.bat).
rem Produces GTA6.exe, assembles/validates the SPIR-V shaders, and makes a
rem vulkan-1 import library from the system loader if one is not present.
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

set "VCVARS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" (
  echo [build] vcvars64.bat not found: %VCVARS%
  exit /b 1
)
call "%VCVARS%" >nul
if errorlevel 1 (
  echo [build] vcvars64 failed
  exit /b 1
)

echo [build] assembling shaders
spirv-as.exe --target-env vulkan1.1 -o shaders\mesh.vert.spv shaders\mesh.vert.spvasm || exit /b 1
spirv-as.exe --target-env vulkan1.1 -o shaders\mesh.frag.spv shaders\mesh.frag.spvasm || exit /b 1
spirv-val.exe --target-env vulkan1.1 shaders\mesh.vert.spv || exit /b 1
spirv-val.exe --target-env vulkan1.1 shaders\mesh.frag.spv || exit /b 1
spirv-as.exe --target-env vulkan1.1 -o shaders\gs\dbg_const.frag.spv shaders\gs\dbg_const.frag.spvasm || exit /b 1
spirv-val.exe --target-env vulkan1.1 shaders\gs\dbg_const.frag.spv || exit /b 1

if not exist vulkan-1.lib (
  echo [build] generating vulkan-1 import library from the system loader
  if not exist vulkan-1.def (
    echo [build] vulkan-1.def missing
    exit /b 1
  )
  lib /nologo /def:vulkan-1.def /machine:x64 /out:vulkan-1.lib || exit /b 1
)

set "TARGET=GTA6.exe"
set "MODE="
if /i "%~1"=="explore" (
  set "TARGET=BlockExplorer.exe"
  set "MODE=/DBLOCK_EXPLORER"
)
echo [build] compiling
cl %MODE% /nologo /O2 /MD /EHsc /std:c++17 /W3 /D_CRT_SECURE_NO_WARNINGS /I include ^
   src\main.cpp src\obj_loader.cpp src\dds_loader.cpp src\png_writer.cpp ^
   /Fe:%TARGET% /link vulkan-1.lib user32.lib gdi32.lib shell32.lib ole32.lib psapi.lib
if errorlevel 1 (
  echo [build] compile/link failed
  exit /b 1
)

echo [build] ok: %CD%\%TARGET%
exit /b 0

