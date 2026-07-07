#!/bin/bash
# This does not keep historical records it will overwrite on every execution
# Can change to Exit nodes only if wanted -  IP List: https://iplists.firehol.org/?ipset=tor_exits_30d
# Full Tor node list - https://www.dan.me.uk/torlist/
URL='https://www.dan.me.uk/torlist/'
OUTPUT='/opt/splunk/etc/apps/cyber_recon/lookups/tor_node_full.csv'

DATE=$(date +"%Y-%m-%dT%H:%M:%SZ" -u)

echo "tor_ip,tor_type,tor_last_update" >$OUTPUT
wget -O - "$URL" 2>/dev/null | while read L
do
   [[ $L =~ ^#.*$ ]] && continue
   echo $L,"tor_node",$DATE >>$OUTPUT
done
