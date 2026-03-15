@echo off
set "d=%USERPROFILE%\Documents\maya\modules"
mkdir "%d%" 2>nul
copy /Y "%~dp0nntools_maya.mod" "%d%\" >nul
"%windir%\system32\robocopy.exe" "%~dp0nntools_maya" "%d%\nntools_maya" /E /NFL /NDL /NJH /NJS /NP >nul
echo Installation finished.
exit /b 0
