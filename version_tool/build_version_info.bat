@echo off
set MAJOR=0
set MINOR=6
set PATCH=0
echo ------------------------------------
echo.
echo.

IF EXIST "..\file_version_info.txt" ECHO Deleting original file...
IF EXIST "..\file_version_info.txt" DEL "..\file_version_info.txt"

echo Adding text header...
echo # File created with Aerox Software Versioning Tool > file_version_info.txt
echo # UTF-8 >> file_version_info.txt
echo. >> file_version_info.txt
echo. >> file_version_info.txt

echo VSVersionInfo( >> file_version_info.txt
echo   ffi=FixedFileInfo( >> file_version_info.txt
echo     filevers=(%MAJOR%, %MINOR%, %PATCH%), >> file_version_info.txt
echo     prodvers=(%MAJOR%, %MINOR%, %PATCH%), >> file_version_info.txt
echo. >> file_version_info.txt
echo     mask=0x3f, >> file_version_info.txt
echo. >> file_version_info.txt
echo     flags=0x0, >> file_version_info.txt
echo. >> file_version_info.txt
echo     # 0x4 - WinNT >> file_version_info.txt
echo     OS=0x40004, >> file_version_info.txt
echo     # 0x1 - Application. >> file_version_info.txt
echo     fileType=0x1, >> file_version_info.txt
echo     # subtype = AppFunction >> file_version_info.txt
echo     # 0x0 - undefined >> file_version_info.txt
echo     subtype=0x0, >> file_version_info.txt
echo     # Creation date-time stamp. >> file_version_info.txt
echo     date=(0, 0) >> file_version_info.txt
echo     ), >> file_version_info.txt
echo   kids=[ >> file_version_info.txt
echo     StringFileInfo( >> file_version_info.txt
echo       [ >> file_version_info.txt
echo       StringTable( >> file_version_info.txt
echo         '040904B0', >> file_version_info.txt
echo         [StringStruct('CompanyName', 'Aerox Software'), >> file_version_info.txt
echo         StringStruct('FileDescription', 'Forge Game Data (FGD) Editing Utility'), >> file_version_info.txt
echo         StringStruct('FileVersion', '%MAJOR%.%MINOR%.%PATCH%'), >> file_version_info.txt
echo         StringStruct('InternalName', 'Entity-Forge'), >> file_version_info.txt
echo         StringStruct('LegalCopyright', '© Copyright 2025 Aerox Software'), >> file_version_info.txt
echo         StringStruct('OriginalFilename', 'EntityForge.exe'), >> file_version_info.txt
echo         StringStruct('ProductName', 'Entity Forge'), >> file_version_info.txt
echo         StringStruct('ProductVersion', '%MAJOR%.%MINOR%.%PATCH%')]) >> file_version_info.txt
echo       ]), >> file_version_info.txt
echo     VarFileInfo([VarStruct('Translation', [1033, 1200])]) >> file_version_info.txt
echo   ] >> file_version_info.txt
echo ) >> file_version_info.txt

echo.
echo ------------------------------------
echo.
echo Moving new file to parent directory...
move "file_version_info.txt" ..\
echo File created and placed successfully.

exit /b 0