@echo off
cd "%SPLUNK_HOME%"\etc\apps\TrendMicroDeepDiscovery\default.old.*
@copy ADS-base.conf "%SPLUNK_HOME%"\etc\apps\TrendMicroDeepDiscovery\default\ADS-base.conf
cd "%SPLUNK_HOME%"\etc\apps\TrendMicroDeepDiscovery
FOR /d %%X IN (default.old.*) DO RD /S /Q "%%X"
