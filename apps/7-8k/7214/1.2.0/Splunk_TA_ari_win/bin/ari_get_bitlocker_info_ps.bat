@echo off

setlocal enabledelayedexpansion

SET Filename=ari_get_bitlocker_info.ps1

SET ThisScriptsDirectory=%~dp0
SET PowerShellScriptPath=%ThisScriptsDirectory%..\lib\%Filename%
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%PowerShellScriptPath%'";