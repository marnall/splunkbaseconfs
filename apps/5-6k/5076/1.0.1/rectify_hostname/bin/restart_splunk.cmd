@echo off
timeout /t 5
rem "C:\Program Files\SplunkUniversalForwarder\bin\splunk.exe" restart
%WINDIR%\system32\net.exe stop SplunkForwarder
%WINDIR%\system32\net.exe start SplunkForwarder
exit
