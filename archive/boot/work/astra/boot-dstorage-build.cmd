@echo off
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
set "CMAKEROOT=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\CMake"
set "PATH=%CMAKEROOT%\CMake\bin;%CMAKEROOT%\Ninja;%PATH%"
cmake -S runtime -B ../boot-build -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo "-DVulkan_INCLUDE_DIR=%CD%\..\..\..\engine\include" "-DVulkan_LIBRARY=%CD%\..\..\..\engine\vulkan-1.lib" -DLEONIDA_SDL3_FETCH=ON "-DFETCHCONTENT_SOURCE_DIR_SDL3=%CD%\..\..\..\scratch\review-5076\out\_deps\sdl3-src" > ../boot-config.log 2>&1 || exit /b 1
cmake --build ../boot-build --target gta6rt dstorage_test xgameruntime_test -j 8 > ../boot-build.log 2>&1

