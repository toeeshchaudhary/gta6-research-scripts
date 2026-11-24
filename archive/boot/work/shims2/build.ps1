# Build the seven substitute GDK DLLs (x64, MSVC) into .\bin.
# Writes only under .\work\shims2; the game package is untouched.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$vcvars = 'C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path -LiteralPath $vcvars)) { throw "vcvars64.bat missing: $vcvars" }

New-Item -ItemType Directory -Force -Path "$root\bin", "$root\build" | Out-Null

$names = 'xmem','d3d12_xs','acphal','xapu','chad','xg_xs','xcrdapi'
$lines = @('@echo off', "call `"$vcvars`" >nul 2>&1", 'if errorlevel 1 ( echo VCVARS_FAILED & exit /b 1 )', "cd /d `"$root\build`"")
foreach ($n in $names) {
    $lines += "cl /nologo /LD /O2 /W3 /MT /D_CRT_SECURE_NO_WARNINGS /Fe:$n.dll `"$root\src\$n.c`" /link /DEF:`"$root\src\$n.def`" /MACHINE:X64 kernel32.lib psapi.lib advapi32.lib /OUT:$n.dll"
    $lines += "if errorlevel 1 ( echo $n`_BUILD_FAILED & exit /b 1 )"
}
$lines += 'exit /b 0'
$bat = $lines -join "`r`n"
$tmp = Join-Path $env:TEMP 'shims2_build.bat'
Set-Content -LiteralPath $tmp -Value $bat -Encoding ascii
& cmd /c $tmp
if ($LASTEXITCODE -ne 0) { throw "build failed ($LASTEXITCODE)" }

foreach ($n in $names) { Copy-Item "$root\build\$n.dll" -Destination "$root\bin\$n.dll" -Force }
Write-Host "Built 7 DLLs into $root\bin"
Get-ChildItem "$root\bin\*.dll" | Select-Object Name, Length
