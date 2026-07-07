#!/bin/bash
if [ -z "$1" ]; then
  echo 'Usage: start_threatupload.sh <threatdir>'
  exit
fi

threats_dir=$1
base_dir=/opt/splunk/bin/scripts/threatDB
python_bindir=/usr/bin

feeds_list=(
'emergingthreats=http://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt'
'binarydefense=http://www.binarydefense.com/banlist.txt' 
'alienvaultreputation=https://reputation.alienvault.com/reputation.snort.gz' 
'sslipblacklist=https://sslbl.abuse.ch/blacklist/sslipblacklist.csv' 
'ransomwaretracker=https://ransomwaretracker.abuse.ch/downloads/RW_IPBL.txt' 
'blocklistdessh=https://lists.blocklist.de/lists/ssh.txt' 
'blocklistdeapache=https://lists.blocklist.de/lists/apache.txt' 
'blocklistdebots=https://lists.blocklist.de/lists/bots.txt' 
'cinsscore=http://cinsscore.com/list/ci-badguys.txt' 
'stopforumspam=http://www.stopforumspam.com/downloads/bannedips.zip' 
'sblam=http://sblam.com/blacklist.txt' 
'atlasattacks=https://atlas.arbor.net/summary/attacks.csv' 
'atlasfastflux=https://atlas.arbor.net/summary/fastflux.csv' 
'atlasphishing=https://atlas.arbor.net/summary/phishing.csv' 
'atlasscans=https://atlas.arbor.net/summary/scans.csv' 
'myip=https://myip.ms/files/blacklist/general/latest_blacklist.txt' 
'botvrij=http://www.botvrij.eu/data/ioclist.ip-dst.raw' 
'darklist=http://www.darklist.de/raw.php' 
'labssnort=http://labs.snort.org/feeds/ip-filter.blf' 
'openbl=http://www.openbl.org/lists/base_1days.txt'
'dangerrulez=http://danger.rulez.sk/projects/bruteforceblocker/blist.php'
'bambenekconsulting=http://osint.bambenekconsulting.com/feeds/c2-ipmasterlist.txt'
'torproject=https://check.torproject.org/exit-addresses'
)

echo
echo 'Make temp feeds dir and clean if exist'

mkdir -p $threats_dir
rm -rf $threats_dir/*.feed

echo 'Flush NETs DB'
$python_bindir/python $base_dir/threat_flushdb.py netsdb flush

echo
echo 'Start download feeds'

set -o braceexpand
for i in ${feeds_list[@]} 
do
  feed_code=''
  feed_url=''
  unset tmpfeed

  # Parse feeds array
  tmpfeed=(${i//=/ })
  feed_code=${tmpfeed[0]}
  feed_url=${tmpfeed[1]}

  if [[ $feed_code == "alienvaultreputation" ]]
    then
      wget "$feed_url" -P $threats_dir --no-check-certificate -N
      gzip -d $threats_dir/reputation.snort.gz
      mv $threats_dir/reputation.snort $threats_dir/$feed_code.feed

  elif [[ $feed_code == "stopforumspam" ]]
    then
      wget "$feed_url" -P $threats_dir --no-check-certificate -N
      unzip -d $threats_dir $threats_dir/bannedips.zip 
      tr ',' '\n' < $threats_dir/bannedips.csv > $threats_dir/$feed_code.feed
      rm -rf $threats_dir/bannedips.zip
      rm -rf $threats_dir/bannedips.csv
  
  else	        
    wget "$feed_url" -O $threats_dir/$feed_code.feed --no-check-certificate -N
  fi

  # Countinue if not downloaded
  if [ -s $threats_dir/$feed_code.feed ]
    then
      echo "status=done, threatsource=$feed_code, message=Downloaded" 
  else 
    echo "status=error, threatsource=$feed_code, message=Notfound"
    continue
  fi
  
  # Upload to DB
  $python_bindir/python $base_dir/threatuploader.py ipdb $feed_code $threats_dir/$feed_code.feed

done

exit

