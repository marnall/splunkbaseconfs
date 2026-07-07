@echo OFF

reg Query "HKLM\Hardware\Description\System\CentralProcessor\0" | find /i "x86" > NUL && set cpu_arch=32 || set cpu_arch=64

cd /D %~dp0
cd %cpu_arch%

BrowsingHistoryView.exe /HistorySource 1 /VisitTimeFilterType 2 /VisitTimeFilterValue 01 /sxml BrowsingHistoryView.temp

powershell -c "Get-Content BrowsingHistoryView.temp | Set-Content -Encoding utf8 ..\BrowsingHistoryViewLog.xml"

del /F BrowsingHistoryView.temp
