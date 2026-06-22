@echo off

setlocal enabledelayedexpansion

SET Filename=ea_get_user_details.ps1

SET ThisScriptsDirectory=%~dp0
SET PowerShellScriptPath=%ThisScriptsDirectory%..\lib\%Filename%
PowerShell -NoProfile -ExecutionPolicy Bypass -Command "& '%PowerShellScriptPath%'";