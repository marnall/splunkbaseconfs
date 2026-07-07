@rem
@rem Copyright 2015 the original author or authors.
@rem
@rem Licensed under the Apache License, Version 2.0 (the "License");
@rem you may not use this file except in compliance with the License.
@rem You may obtain a copy of the License at
@rem
@rem      https://www.apache.org/licenses/LICENSE-2.0
@rem
@rem Unless required by applicable law or agreed to in writing, software
@rem distributed under the License is distributed on an "AS IS" BASIS,
@rem WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
@rem See the License for the specific language governing permissions and
@rem limitations under the License.
@rem

@if "%DEBUG%" == "" @echo off
@rem ##########################################################################
@rem
@rem  corvil startup script for Windows
@rem
@rem ##########################################################################

@rem Set local scope for the variables with windows NT shell
if "%OS%"=="Windows_NT" setlocal

set DIRNAME=%~dp0
if "%DIRNAME%" == "" set DIRNAME=.
set APP_BASE_NAME=%~n0
set APP_HOME=%DIRNAME%..

@rem Resolve any "." and ".." in APP_HOME to make it shorter.
for %%i in ("%APP_HOME%") do set APP_HOME=%%~fi

@rem Add default JVM options here. You can also use JAVA_OPTS and CORVIL_OPTS to pass JVM options to this script.
set DEFAULT_JVM_OPTS="-Dhttps.protocols=TLSv1.1,TLSv1.2" "-DSPLUNK_HOME=%SPLUNK_HOME%"

@rem Find java.exe
if defined JAVA_HOME goto findJavaFromJavaHome

set JAVA_EXE=java.exe
%JAVA_EXE% -version >NUL 2>&1
if "%ERRORLEVEL%" == "0" goto execute

echo.
echo ERROR: JAVA_HOME is not set and no 'java' command could be found in your PATH.
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:findJavaFromJavaHome
set JAVA_HOME=%JAVA_HOME:"=%
set JAVA_EXE=%JAVA_HOME%/bin/java.exe

if exist "%JAVA_EXE%" goto execute

echo.
echo ERROR: JAVA_HOME is set to an invalid directory: %JAVA_HOME%
echo.
echo Please set the JAVA_HOME variable in your environment to match the
echo location of your Java installation.

goto fail

:execute
@rem Setup the command line

set CLASSPATH=%APP_HOME%\lib\splunk-1.2.3.jar;%APP_HOME%\lib\splunk-1.6.2.jar;%APP_HOME%\lib\org.apache.sling.commons.json-2.0.10.jar;%APP_HOME%\lib\connector-1.2.3.jar;%APP_HOME%\lib\httpclient-4.5.2.jar;%APP_HOME%\lib\commons-codec-1.10.jar;%APP_HOME%\lib\jaxws-api-2.3.0.jar;%APP_HOME%\lib\jsr181-api-1.0-MR1.jar;%APP_HOME%\lib\jaxb-runtime-2.3.0.1.jar;%APP_HOME%\lib\jaxb-core-2.3.0.1.jar;%APP_HOME%\lib\jaxb-api-2.3.0.jar;%APP_HOME%\lib\saaj-impl-1.5.1.jar;%APP_HOME%\lib\javax.xml.soap-api-1.4.0.jar;%APP_HOME%\lib\stax-ex-1.8.1.jar;%APP_HOME%\lib\FastInfoset-1.2.13.jar;%APP_HOME%\lib\jakarta.xml.bind-api-2.3.2.jar;%APP_HOME%\lib\jakarta.activation-api-1.2.1.jar;%APP_HOME%\lib\jakarta.xml.soap-api-1.4.1.jar;%APP_HOME%\lib\mimepull-1.9.11.jar;%APP_HOME%\lib\protobuf-java-2.6.1.jar;%APP_HOME%\lib\dom4j-1.6.1.jar;%APP_HOME%\lib\jaxen-1.1.6.jar;%APP_HOME%\lib\syslog4j-0.9.30.jar;%APP_HOME%\lib\log4j-core-2.17.1.jar;%APP_HOME%\lib\log4j-api-2.17.1.jar;%APP_HOME%\lib\slf4j-simple-1.7.21.jar;%APP_HOME%\lib\zookeeper-3.4.5.jar;%APP_HOME%\lib\slf4j-log4j12-1.6.1.jar;%APP_HOME%\lib\slf4j-api-1.7.21.jar;%APP_HOME%\lib\univocity-parsers-2.3.1.jar;%APP_HOME%\lib\txw2-2.3.0.1.jar;%APP_HOME%\lib\istack-commons-runtime-3.0.5.jar;%APP_HOME%\lib\xml-apis-1.0.b2.jar;%APP_HOME%\lib\httpcore-4.4.4.jar;%APP_HOME%\lib\commons-logging-1.2.jar;%APP_HOME%\lib\log4j-1.2.16.jar;%APP_HOME%\lib\jline-0.9.94.jar;%APP_HOME%\lib\netty-3.2.2.Final.jar;%APP_HOME%\lib\junit-3.8.1.jar


@rem Execute corvil
"%JAVA_EXE%" %DEFAULT_JVM_OPTS% %JAVA_OPTS% %CORVIL_OPTS%  -classpath "%CLASSPATH%" com.corvil.connectors.splunk %*

:end
@rem End local scope for the variables with windows NT shell
if "%ERRORLEVEL%"=="0" goto mainEnd

:fail
rem Set variable CORVIL_EXIT_CONSOLE if you need the _script_ return code instead of
rem the _cmd.exe /c_ return code!
if  not "" == "%CORVIL_EXIT_CONSOLE%" exit 1
exit /b 1

:mainEnd
if "%OS%"=="Windows_NT" endlocal

:omega
