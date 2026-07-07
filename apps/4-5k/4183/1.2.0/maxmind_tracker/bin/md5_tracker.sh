#!/bin/bash

#############################
### MaxMind MD5 Tracker   ###
### Author:  Mark Hill    ###
### Date:    03-09-2018   ###
### Version: 1.0          ###
#############################

## 20-01-2020 - MH - updated to reflect the new API key download method. You need to replace XXXXXXXXXXX in the wget command with your own API key gained from signing up on the website.

echo -n >> $SPLUNK_HOME/etc/apps/maxmind_tracker/bin/md5_tracker.log
wget -O $SPLUNK_HOME/etc/apps/maxmind_tracker/bin/GeoLite2-City.tar.gz.md5 "https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=XXXXXXXXXXXXXXX&suffix=tar.gz.md5" --append-output=$SPLUNK_HOME/etc/apps/maxmind_tracker/bin/md5_tracker.log || { echo 'Could not download MaxMind GeoIP MD5, exiting.' ; exit 1; }

exit







