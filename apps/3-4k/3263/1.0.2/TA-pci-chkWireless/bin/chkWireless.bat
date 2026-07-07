@echo off
REM Daniel Wilson
REM Checks if Wireless is enabled
REM Echos the results in Splunk friendly format

sc query "Wlansvc" | findstr "RUNNING" > deleteme.txt


IF ERRORLEVEL 1  (
  echo action=blocked os=Windows command=sc
) ELSE (
  echo action=allowed os=Windows command=sc
)
