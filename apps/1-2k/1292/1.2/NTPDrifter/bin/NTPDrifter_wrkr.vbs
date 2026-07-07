' NTPDrifter
'
' Used to report the difference between local server time and a known NTP source.
' Windows only.
'
' Requirements
' Host must be configured for NTP correctly. (I use Window Time Agent from www.greyware.com, check it out)
'
' copyright 2012
' Conradejohnston@gmail.com
'
' CAUTION
' This script has no brain, you must use your own before executing it. I accept no liablilty please
' use this script at your own risk.
'
' version control
' v1.0 24th Nov 2012 - Initial release
' v1.1 27th Nov 2012 - Streamed data out for splunk, removed script generated timestamp
' v1.2 29th Nov 2012 - Removed location specifc dependancies
'
' Tested ok on:
' Windows XP
' Windows 7
' Windows 2003 R2
' Windows 2008 R2

Option Explicit

'global variables
Dim StrNTPTarget, StrDataOut, StrSplunkOut
Dim  StrVariance, StrExecute

'# Script config ########################################################################

	' Put your NTP source hostname here
	StrNTPTarget = "<NTPSERVERNAME>"
	
	' only enable this if you want verbose messages to try and trouble shoot something
	Const verbose = false

' # work ################################################################################

	If verbose Then
		WScript.Echo "+Script - NTPDrift" 
	End If
	
	CheckNTPDrift
	
	WScript.Echo strSplunkout
	
	If verbose Then
		WScript.Echo "-Script - NTPDrift" 
	End If
	
'# Functions ############################################################################

Function CheckNTPDrift

	If verbose Then
		WScript.Echo "+Function - CheckNTPDrift" 
	End If
	
	Dim objExecObject, objShell
	Dim i, y, StdOutput, ArrOutput(), ArrData, StrData
	Dim StrLine, StrError, IntError
	
	Set objShell = WScript.CreateObject("Wscript.Shell")

	i=0
	y=0
	
	'NTP String
	'w32tm /stripchart /computer:<NTPTarget> /samples:1 /dataonly
	
	
	'build the execution string
	StrExecute = "w32tm /stripchart /computer:" & StrNTPTarget & " /samples:1 /dataonly"
		
	Set objExecObject = objShell.Exec(StrExecute)
		
	Do While Not objExecObject.StdOut.AtEndOfStream
			
		ReDim Preserve ArrOutput(i)
			
		ArrOutput(i) = objExecObject.StdOut.ReadLine()
			
		If verbose Then
				WScript.Echo " [w32tm stdout] " & ArrOutput(i)
		End if
			
		i = i + 1
			
	Loop
		
	'Replay the stdoutput captured in ArrOutput() and check for errors
	For y=LBound(ArrOutput) To  UBound(ArrOutput) Step 1
		
		' inject the output into an array, one entry per line
		StrLine = Trim(ArrOutput(y))
			
		StrError = "error"
			
		'check For known error codes
		IntError = InStr(ArrOutput(y),"error")
		
		If IntError <> 0 Then
			WScript.Echo "Error detected when running NTPDrifter" & vbCrLf &_
			"Please run the command manually on the target server to test." & vbCrLf & vbCrLf &_
			"Command = " & StrExecute			
			Exit function 
		End if			
	
	If y=3 Then
			
			' grab our data line
			StrData = ArrOutput(y)	
			
			' split the data line
			ArrData = Split(StrData,",")
		
			' grab the variance, trim it and knock the s off the end
			StrVariance = Trim(ArrData(1))
			
			' trim off the trailing s
			StrVariance = Left(StrVariance,(Len(StrVariance)-1))
			
			' generate our output ready for splunk
			StrSplunkOut = "[ntpHost=" & StrNTPTarget & ":ntpDrift=" & StrVariance & "]"
							
		End If
		
	Next
	
	'write out our data line
	If verbose Then
		WScript.Echo StrSplunkOut
	End If
			
	If verbose Then
		WScript.Echo "-Function - CheckNTPDrift" 
	End If
	
End Function

' ############