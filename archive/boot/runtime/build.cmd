@echo off
rem build.cmd -- build the PE loader harness (x64, MSVC).
rem Usage: build.cmd
setlocal enabledelayedexpansion
set "VSDIR=C:\Program Files\Microsoft Visual Studio\18\Community"
set "VCVARS=%VSDIR%\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%VCVARS%" (
  echo [build] vcvars64.bat not found at "%VCVARS%"
  exit /b 1
)
call "%VCVARS%" >nul 2>&1
if errorlevel 1 (
  echo [build] vcvars64 initialization failed
  exit /b 1
)
pushd "%~dp0"
if not exist out mkdir out
echo [build] compiling...
cl /nologo /std:c++20 /EHsc /O2 /W4 /permissive- /wd4611 /D_CRT_SECURE_NO_WARNINGS ^
   /Fo:out\ /Fe:out\peload.exe src\*.cpp ^
   /link /SUBSYSTEM:CONSOLE
set "RC=!errorlevel!"
popd
if not "!RC!"=="0" (
  echo [build] FAILED with !RC!
  exit /b !RC!
)
echo [build] ok -^> out\peload.exe
exit /b 0
