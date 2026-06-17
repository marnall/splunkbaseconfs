#!/bin/sh

curl http://adblockplus.mozdev.org/easylist/easylist.txt > $SPLUNK_HOME/etc/apps/EasyList/local/easylist.txt

