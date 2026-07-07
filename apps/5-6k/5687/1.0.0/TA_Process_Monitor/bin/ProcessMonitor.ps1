#check for running process

$process=$args[0]
$time=GET-Date -UFormat "%Y/%m/%d %R"


if((get-process $process -ErrorAction SilentlyContinue) -eq $Null)
{ echo "$time process=$process status=stopped host=$env:COMPUTERNAME" }else{ echo "$time process=$process status=running host=$env:COMPUTERNAME" }