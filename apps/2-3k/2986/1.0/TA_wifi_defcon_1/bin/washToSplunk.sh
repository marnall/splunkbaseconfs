#!/bin/bash

#Author: Alessandro Dantas <alessandro.dantas@katana1.com>
#Description: Script to check if your wifi is vulnerable to WPS attack
#Release 1.0
#date 08/10/2015 GMT +10 Sydney/NSW

if [ $# != 2 ];
 then
  echo "$0 only accepts 2 arguments."
  echo "Usage: $0 <Interface> <Syslog Server>"
  exit 2
fi


#Please set your variables
monitor_interface=$1
splunk_server=$2
splunk_install_path="/home/splunk"
local_logpath="${splunk_install_path}""/etc/apps/TA_wifi_defcon_1/bin/logs"

# Verify we are root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 1>&2
   exit 1
fi

killall wash 2&>1 >/dev/null

#Launch wash 

timeout 120s wash -i "${monitor_interface}" -C  -s -o "${local_logpath}"/WPS-devices.txt 2&>1 >/dev/null

#Wait at least 20 seconds to write the initial file

#Convert to csv and syslog to Splunk

cat "${local_logpath}"/WPS-devices.txt |sed '1d' |sed '1d' > "$local_logpath"/WPS-indexed-devices.csv ;logger -u /tmp/ignored -d -P 514 -f "$local_logpath"/WPS-indexed-devices.csv -t wifiwps -n "${splunk_server}"

