#!/bin/bash
# USAGE
# capturepstack <PID> (-f <OUTPUT-FILENAME>)?  (-s <#SAMPLES>)? (-t <TIMEOUT-SECONDS>)? (-c <COMPRESS 0|1>)?

# defaults 
filename="file"
samples=100
timeoutsec=1
pid=$1
compress=0
dt="ts %s"
cfile="$filename-$pid-$dt-pstack.tgz"

# displays the usage
function usage(){
echo "USAGE:
capturepstack <PID> (-f <OUTPUT-FILENAME>)?  (-s <#SAMPLES>)? (-t <TIMEOUT-SECONDS>)? (-c <COMPRESS-0|1>)?

defaults:
OUTPUT-FILENAME: [String] Name of the pstack file. For. e.g. filename=nike will generate nike.$i.$pid.$ts.pstack. This can be a path as well. For e.g. /tmp/nike and all of these files will be stored as /tmp/nike.$i.$pid.$ts.pstack. Default is $filename
SAMPLES: [Int] Count of samples needed to be captured. Default is $samples
TIMEOUT-SECONDS: [Int] Time in seconds the script will sleep between collecting pstack samples. 0 means continuous samples. Default is $timeoutsec
COMPRESS: [0|1] When set to 1 (True), the pstack samples will be compressed into a single pstack tar.gz file and samples will be deleted. Default is $compress
"
}

function capturepstack(){
i=0
while [ $i -lt $3 ]; do
  let i=$i+1
  dh=$(date "+%c")
  de=$(date "+%s")
  #cmd="pstack $1 > $2.$i.$1.$de.pstack"
  cmd="pstack $1"
  ofile="$2.$i.$1.$de.pstack"
  echo "$dh sample $i: $cmd > $ofile"
  { $cmd > $ofile; } || break 
  sleep $4
done
}


if [ $# -lt 1 ]; then
  echo "Missing PID"
  usage
elif [ $# -eq 1 ]; then
  capturepstack $pid $filename $samples $timeoutsec
elif [ $# -gt 1 ]; then
  pid=$1
  shift
  while [ $# -gt 0 ]; do
    case "$1" in
       -f) filename="$2"; shift;;
       -s) samples="$2"; shift;;
       -t) timeoutsec="$2"; shift;;
       -c) compress=$2; shift;;
       -*) echo "Invalid option $1"; usage; exit 1;;
       *) echo "Invalid argument $1"; usage; exit 1;;
    esac
    shift
  done
  capturepstack $pid $filename $samples $timeoutsec

  if [ $compress -eq 1 ]; then
      cfile="$filename-$pid-pstack.tgz"
      cmd="tar -cvzf $cfile $filename.* --remove-files"
      echo "compressing ..."
      echo "$cmd"
      { $cmd; } || echo "Failed"

  fi

fi
