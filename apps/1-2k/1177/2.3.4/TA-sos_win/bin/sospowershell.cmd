@ECHO OFF

:: ######################################################
:: #
:: # Splunk on Splunk add-on for Windows
:: # Powershell scripted input launcher
:: # 
:: # Copyright (C) 2012 Splunk, Inc.
:: # All Rights Reserved
:: #
:: ######################################################

Powershell -command ". '%~dp0\powershell\%1'"
