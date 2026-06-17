$DebugLogging = 0

$Header = "{0,-10} {1,-10} {2,-10} {3,-10} {4,-18} {5,-10} {6}" -f 'PID','pctCPU','RSZ_KB','VSZ_KB','ELAPSED','COMMAND','ARGS'
Write-Host $Header

$processes = @(Get-Process -Name "splunkd*", "splunkweb*" | Select-Object Id,WorkingSet64,VirtualMemorySize64,ProcessName,StartTime)

foreach ($process in $processes) {

    $ValidResult = 1

    try {
        $myPID = $process.Id
        $pctCPU = get-wmiobject Win32_PerfFormattedData_PerfProc_Process -Filter "IDProcess = $myPID" | select -expand PercentProcessorTime
        $CMDLINE = get-wmiobject Win32_Process -Filter "ProcessId = $myPID" | select -expand CommandLine

        $RSZ_KB = $process.WorkingSet64 / 1024
        $VSZ_KB = $process.VirtualMemorySize64 / 1024
        $COMMAND = $process.ProcessName
        $CMDLINE = $CMDLINE.replace('"','')
        $ARGS = $CMDLINE -replace ".*?splunk(d|web)(\.exe)?\s?",""
        $ARGS = $ARGS.replace(' ','_')

        if ( $process.StartTime ) {
            $ELAPSED_UNFORMATTED = ((Get-Date)-$process.StartTime)
            $ELAPSED = [string]::format("{0}-{1}:{2}:{3}", `
            $ELAPSED_UNFORMATTED.Days, `
            $ELAPSED_UNFORMATTED.Hours, `
            $ELAPSED_UNFORMATTED.Minutes, `
            $ELAPSED_UNFORMATTED.Seconds)
            }
        else {
            $ELAPSED = "n/a"
            }
        }

    catch [Exception] {
        $ValidResult = 0
        if ($DebugLogging -eq 1) {
            Write-Error "Throwing away incomplete record for process: $process"
            }

        }


    if ($ValidResult -eq 1) {

        $ResultRow = "{0,-10} {1,-10} {2,-10} {3,-10} {4,-18} {5,-10} {6}" -f $myPID,$pctCPU,$RSZ_KB,$VSZ_KB,$ELAPSED,$COMMAND,$ARGS
        Write-Host $ResultRow
        }
    }
