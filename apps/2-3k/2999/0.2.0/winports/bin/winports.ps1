. ".\Get-NetworkStatistics.ps1"

$ProgressPreference = "SilentlyContinue";
$stats=Get-NetworkStatistics

$date = get-date
$timestamp = $date.ToString("yyyy-MM-dd HH:mm:ss")

foreach($stat in $stats) {
    $output = "$timestamp "
    $stat.PSObject.Properties |
        where { $_.Name -ne 'ComputerName' } |
        where { ! [string]::IsNullOrEmpty($_.Value) } |
        foreach {
        $name = $_.Name
        $value = $_.Value

        $output = "$output $name=`"$value`""
    }
    echo $output
}
