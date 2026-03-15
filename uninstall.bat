@echo off
set "d=%USERPROFILE%\Documents\maya\modules"
del /Q "%d%\nntools_maya.mod" >nul 2>&1
rmdir /S /Q "%d%\nntools_maya" >nul 2>&1
echo Uninstallation finished.
exit /b 0

