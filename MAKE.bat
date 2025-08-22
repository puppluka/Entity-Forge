@echo off

cd version_tool
echo Building EXE Version Info File...
py version_update.py build
timeout /t 1 > nul
cd ..
py -m PyInstaller release.spec
timeout /t 1 > nul
cls
echo Build completed! Check dist/ folder.
timeout /t 3 > nul
exit /b 0