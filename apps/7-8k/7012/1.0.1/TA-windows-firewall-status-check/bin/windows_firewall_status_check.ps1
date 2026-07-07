## This script generates the result of Windows Firewall status (ON/OFF)

$result = NetSh Advfirewall show allprofiles state 
$result = $result -replace '([-]+)', ''

$final=""

foreach ($line in $result)
{
    $line = $line -replace '([\s]{2,})', ' = '
    $final = $final + $line + " "
}

$final = $final -replace '(ON)', 'ON  ||'
$final = $final -replace '(OFF)', 'OFF  ||'
$final = $final -replace '(\|\|\sOk\.)', ''

Write-Output $final

exit
