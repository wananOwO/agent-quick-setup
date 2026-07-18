@echo off
setlocal
set "AGENT_SETUP_SCRIPT=%~dp0install.ps1"
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "try { & $env:AGENT_SETUP_SCRIPT %* } catch { [Console]::Error.WriteLine(('Agent Quick Setup: ' + $_.Exception.Message)); exit 1 }"
exit /b %ERRORLEVEL%
