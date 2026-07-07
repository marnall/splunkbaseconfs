echo off
echo "running the for loop"
FOR /F "delims=" %%i IN ('wmic service SplunkForwarder get Pathname ^| findstr /m service') DO set SPLUNKDPATH=%%i
echo "setting splunk path"
set SPLUNKPATH=%SPLUNKDPATH:~1,-28%
echo %DATE%-%TIME% The SplunkUniversalForwarder is installed at %SPLUNKPATH%

::set path of logging directory
set LokiLogPath=%SPLUNKPATH%\var\log\TA_Loki


:: create new directory
echo creating new directory at %LokiLogPath%
mkdir "%LokiLogPath%"
echo path %LokiLogPath%

:: set scan path, you can use --allhds if you want to scan all hard drives
set ScanPath=C:\

echo %DATE%-%TIME% starting loki && "%SPLUNKPATH%"\etc\apps\TA_Loki\bin\loki.exe  --csv --intense -p %ScanPath% --logfolder "%LokiLogPath%"    && echo %DATE%-%TIME% scan complete! && exit

echo %DATE%-%TIME% scan failed
