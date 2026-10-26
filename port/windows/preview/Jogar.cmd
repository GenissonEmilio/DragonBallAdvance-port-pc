@echo off
setlocal
if "%~1"=="" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Iniciar.ps1"
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Iniciar.ps1" -Rom "%~f1"
)
set "game_exit=%errorlevel%"
if not "%game_exit%"=="0" pause
exit /b %game_exit%
