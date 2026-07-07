:: mbbr_scan_batch.bat
:: Version: 1.0.0
:: Purpose: Wrapper script for MBBR.EXE
::          Intended to be run in batch remotely and capture all relevant information from a run is 'piped' into logfiles

@ECHO OFF
::------------------------------------------------------------------------------------------------------------
SET licensekey=
SET  logserver=
SET syslog=true
SET logport=515
REM Hide the Scan Progress screen when running from script.  Unhide if debugging
SET hidescreen=true
SET mbbrversion=3
SET exclusions=true
SET proxyenabled=false
REM This is for customer IOC rules
SET iocs=true
:: Allow these values to be input by commandline, to overwrite above, for easier test/save cycle
IF [%1] NEQ [] SET licensekey=%1
IF [%2] NEQ [] SET logserver=%2
IF [%3] NEQ [] SET hidescreen=%3
::------------------------------------------------------------------------------------------------------------
:: SET SCAN PARAMETERS - Note, only difference from SCAN is -remove
::------------------------------------------------------------------------------------------------------------
SET scanparms=-threat        -stdout:summary -pfi:10
REM SET scanparms=-threat -stdout:summary -pfi:30
REM SET scanparms=-threat -stdout:summary -pfi:10
:: NOTE: -threat             scan will do all local drives and take longer
::       -threat                scan is fastest to do an immediate triage of infection.
::       -threat                 scan is for in-memory threats. Don't use -ark with this
::       -pfi:nnnnn             outputs ScanProgress.xml, at nnnnn second intervals useful for testing/monitoring on endpoint

::---------------------------------------------------------------------------------------------
:: Setup paths and ensure current directory is script's local directory
::------------------------------------------------------------------------------------------------------------
MKDIR %SystemDrive%\mbbr_remediation
MKDIR %SystemDrive%\mbbr_remediation\logs
PUSHD %SystemDrive%\mbbr_remediation
REM SET logfiledest="%CD%\logs\mbbr_bat_log.txt"
SET  logfiledest="%CD%\logs\MBBR-STDOUT.txt"
SET  mbbrstdout="%CD%\logs\MBBR-STDOUT.txt"

SETLOCAL EnableDelayedExpansion

CALL :ISTASKRUNNING mbbr.exe
IF [!RETURN!] EQU [C001130C] (
   CALL :LOG ........ %COMPUTERNAME% MBBR script execution started, but MBBR.EXE already running - TERMINATING *****
   PAUSE
   GOTO :EOF
)

REM Changed to not erasing, in case of repeat runs
REM ECHO. > %logfiledest%
REM ECHO. > %mbbrstdout%
::------------------------------------------------------------------------------------------------------------
:: Start Script's Logging.  Output to file, but also foreground if running manually
::------------------------------------------------------------------------------------------------------------
CALL :LOG ........ %COMPUTERNAME% MBBR script execution started *****
CALL :LOG ........ %COMPUTERNAME% logging to %logfiledest%
CALL :LOG ........ %COMPUTERNAME% outputting to %mbbrstdout%
CALL :LOG ........ %COMPUTERNAME% current directory %CD%
::------------------------------------------------------------------------------------------------------------
:: CHECK IF RUNNING AS ADMINISTRATOR
::------------------------------------------------------------------------------------------------------------
>nul 2>&1 NET SESSION
IF %ERRORLEVEL% NEQ 0 (
   CALL :LOG C0063009 %COMPUTERNAME% Must run as administrator
   GOTO :ERROR
)
::------------------------------------------------------------------------------------------------------------
:: CHOOSE VERSION OF MBBR
::------------------------------------------------------------------------------------------------------------
IF [%mbbrversion%] EQU [3] (
  SET mbbrin=%CD%\MBBR-3.exe
  CALL :LOG ........ %COMPUTERNAME% Running version 3 !mbbrin!
  ) ELSE (
  SET mbbrin=%CD%\MBBR.exe
  CALL :LOG ........ %COMPUTERNAME% Running version 2 !mbbrin!
  )
SET    mbbrpath="%CD%\mbbr.exe"
::--------------------------------
:: Initial run to self-extract - note this deletes original and creates MBBR.exe.  Version 3 cannot overwrite self.
::--------------------------------
%mbbrin% >> %mbbrstdout%

::------------------------------------------------------------------------------------------------------------
:: CONFIGURE SETTINGS
:: Note: -color:off is required for PSEXEC/PAEXE and terminals if logging to screen, to suppress special chars
::------------------------------------------------------------------------------------------------------------
%mbbrpath% settings -color:off > nul 2>&1

::------------------------------------------------------------------------------------------------------------
:: CONFIGURE SYSLOG AND TEST
::------------------------------------------------------------------------------------------------------------
IF [%syslog%] EQU [true] GOTO :SYSLOGTRUE
  REM ELSE
  %mbbrpath% settings -log.enabled:false
  CALL :LOG 00000000 Syslog disabled
  GOTO :NEXT1

:SYSLOGTRUE
  %mbbrpath% settings -log.enabled:true -log.server:%logserver% -log.port:%logport%>>%mbbrstdout%
  SET return=%=ExitCode%
  CALL :LOG !return! returned by settings log
  IF [!return!] NEQ [00000000] GOTO :ERROR
  CALL :LOGTEST
  CALL :LOG !return! returned by log test
  IF [!return!] NEQ [00000000] GOTO :ERROR
)
:NEXT1
::------------------------------------------------------------------------------------------------------------
:: CONFIGURE SETTINGS - REBOOT
::------------------------------------------------------------------------------------------------------------
SET reboot=-scan.rebootwait:300 -scan.rebootmsg:"Please save and reboot as soon as possible to clean malware"
%mbbrpath% settings %reboot% >>%mbbrstdout%
SET return=%=ExitCode%
CALL :LOG !return! returned by settings %reboot%
:: Check return code because above can have rejected settings
IF [!return!] NEQ [00000000] GOTO :ERROR

::------------------------------------------------------------------------------------------------------------
:: CONFIGURE SETTINGS - PROXY
::------------------------------------------------------------------------------------------------------------
:: NOTE1:  It is far better to configure proxy-passthrough, as Malwarebytes' communication is SSL and very
:: specific point-to-point
CALL :PROXYSETUP
IF [!return!] NEQ [00000000] GOTO :ERROR

::------------------------------------------------------------------------------------------------------------
:: REGISTER LICENSE KEY
::------------------------------------------------------------------------------------------------------------
%mbbrpath% register -key:%licensekey%>>%mbbrstdout%
SET return=%=ExitCode%
CALL :LOG !return! returned by register
IF [!return!] NEQ [00000000] GOTO :ERROR

::------------------------------------------------------------------------------------------------------------
:: UPDATE DATABASE
::------------------------------------------------------------------------------------------------------------
%mbbrpath% update>>%mbbrstdout%
SET return=%=ExitCode%
CALL :LOG !return! returned by update
IF [!return!] NEQ [00000000] GOTO :ERROR


::------------------------------------------------------------------------------------------------------------
:: CONFIGURE SETTINGS - EXCLUSIONS
::------------------------------------------------------------------------------------------------------------
IF [%exclusions%] EQU [true] (
   IF  %mbbrversion% LSS 3 (
      SET xlist="%CD%\xlist1.xml;"
   ) ELSE (
     SET xlist="%CD%\xlist1.json;"
   )
   SET SCANPARMS=%SCANPARMS% -excludelist:!xlist!
   CALL :LOG 00000000 Configured exclusions !SCANPARMS!
)
::------------------------------------------------------------------------------------------------------------
:: CONFIGURE SETTINGS - Indicators Of Compromise
::------------------------------------------------------------------------------------------------------------
IF [%iocs%] EQU [true] (
   IF  %mbbrversion% LSS 3 (
     SET ioclist="%CD%\ioclist1.xml;"
   ) ELSE (
     SET ioclist="%CD%\ioclist1.json;"
  )
  %mbbrpath% settings -customdb.clear>>%mbbrstdout%
  %mbbrpath% settings -customdb.load:!ioclist!>>%mbbrstdout%
  SET return=%=ExitCode%
  CALL :LOG !returni! returned by settings -customdb.load:!ioclist!
  IF [!return!] NEQ [00000000] GOTO :ERROR
  %mbbrpath% settings -customdb.list>>%mbbrstdout%
  %mbbrpath% settings -customdb.enabled:true>>%mbbrstdout%
) ELSE (
  %mbbrpath% settings -customdb.enabled:false>>%mbbrstdout%
)
::------------------------------------------------------------------------------------------------------------
:: RUN SCAN using scanparms
::------------------------------------------------------------------------------------------------------------
ECHO Scan Parameters are: !scanparms! >> %mbbrstdout%
CALL :LOG ........ Starting MBBR.EXE scan
if [%hidescreen%] EQU [true] (
   REM Suppress output, as it sends too much screen refresh back if remote
   %mbbrpath% scan !scanparms! >nul
) ELSE (
   REM Display Text GUI when scanning
   REM NOTE: Version 3.6.1 does not return error for syntax problems with exclusions. Run in foreground to see this.
   %mbbrpath% scan !scanparms!
)
SET return=%=ExitCode%
CALL :LOG !return! returned by scan
IF [!return!] NEQ [00000000] GOTO :ERROR
GOTO :END


::------------------------------------------------------------------------------------------------------------
:ERROR
::------------------------------------------------------------------------------------------------------------
:: Output some meaningful errors important codes, for interactive testing
:: Pseudo-switch statements


IF [!return!] EQU [80070057] (
   CALL :LOG 80070057 Excludelist missing
   GOTO :ERRORBREAK
)

IF [!return!] EQU [C0051208] (
   CALL :LOG 80070057 Could not open the given custom rules file.
   GOTO :ERRORBREAK
)

IF [!return!] EQU [C001130C] (
   CALL :LOG C001130C Another instance is already running
   GOTO :ERRORBREAK
)
IF [!return!] EQU [C002140A] (
   CALL :LOG C002140A Failed to remove malware
   GOTO :ERRORBREAK
)
IF [!return!] EQU [C0063017] (
   CALL :LOG C0063017 ERROR_MBBR_CERT_INVALID - Check CA Certs
   GOTO :ERRORBREAK
)
IF [!return!] EQU [C001130F] (
   CALL :LOG C001130F General Error - Failed to connect to Syslog server [%logserver%]
   GOTO :ERRORBREAK
)
::OTHERWISE - If above conditions not met
  CALL :LOG 00000001 Exiting due to error, check logs,  MBBR-STDERR.TXT and prior errors against documentation '.\doc\mbbrerr.h'

:ERRORBREAK
:: Continue from switch statements

::------------------------------------------------------------------------------------------------------------
:END
::------------------------------------------------------------------------------------------------------------
IF [%return%] NEQ [00000000] EXIT /B 1
EXIT /B 0  &REM ELSE is OK

::----------  SUBROUTINES -----------------------------
::-----------------------------------------------------------------------------------------
:LOGTEST
::-----------------------------------------------------------------------------------------
:: settings -log.test shows FAILED, but does not set error code. This snippet does the test
SETLOCAL EnableDelayedExpansion
SET ret=00000000
FOR /F "usebackq tokens=1,2* skip=4 delims= " %%a IN (`mbbr.exe settings -log.test`) DO (
    REM ECHO a:%%a :%%b
    IF [%%a] EQU [Failed] (
	SET ret=C001130F
    )
    IF [%%a] EQU [Unspecified] (
	SET ret=C001130F
    )
)
ENDLOCAL & SET return=%ret%
GOTO :EOF

::-----------------------------------------------------------------------------------------
:LOG
::-----------------------------------------------------------------------------------------
:: Show in screen for interactive user
@echo %date% %time% : %*
:: Write to logfile, with some blank lines
@echo. >>%logfiledest%
@echo.** %date% %time% : %* >>%logfiledest%
@echo. >>%logfiledest%
GOTO :EOF

::-----------------------------------------------------------------------------------------
:PROXYSETUP
::-----------------------------------------------------------------------------------------
IF [%proxyenabled%] EQU [true] (
   %mbbrpath% settings -proxy.enabled:true -proxy.server:my.proxy.server -proxy.port:nnnn -proxy.user:userid -proxy.password:ppppp>>%mbbrstdout%
   SET return=%=ExitCode%
   CALL :LOG %return% returned by settings -proxy.
) ELSE (
   %mbbrpath% settings -proxy.enabled:false>>%mbbrstdout%
    SET return=%=ExitCode%
    CALL :LOG %return% returned by settings -proxy.enabled:false
)
GOTO :EOF

::-----------------------------------------------------------------------------------------
:ISTASKRUNNING
::-----------------------------------------------------------------------------------------
FOR /F "usebackq tokens=1-6*" %%a IN (`TASKLIST /NH /FI "IMAGENAME eq %1"`) DO (
  IF %%a EQU %1 (
     SET return=C001130C
     ECHO %return%
  ) ELSE (
    SET return=00000000
  )
)
GOTO :EOF

:: CHANGES
:: 2019-03-05 V0.9.37
::   Added indicators of compromise reference and settings. Tidied exclusions settings.
::
:: 2019-02-07 V0.9.36
::   Handle exclusions from an externally referenced file.  Must use matching PowerShell to deploy exclusion 0.9.361+
::   Moved setting of exclusions ust before scan block.  Used SETLOCAL DelayedExpansion to ensure SCANPARMS update
::   Replaced handling of RETURN with delayed expansion variables !return!.  Fixed check for mbbr.exe already running.
::   Change output logfile to MBBR-STDOUT, to interleave with results, and reduce number of logs for review
::   Logs append to prior run
::
:: 2018-10-15
::   Handle mbbr-v3 differences.  Change check for -logtest result to look for Failed instead of Success
::   Create directory for logging before MBBR Starts. Check if MBBR is already running
::   Create JSON exclusions example
:: POTENTIAL ENHANCEMENTS
::
