#!/bin/sh

#
# getphishlist by Josh Diakun (joshd AT joshd DOT ca)
# version 1.1
# date: Sep 28, 2013
#
# gets the free data feed from phishtank.com that has current confirmed phishing URLs
# credit for original creation of the script goes to Nimish Doshi.
# 

if [ "$(uname)" == "Darwin" ]; then
  # Do something under Mac OS X platform        
  SPLUNK_HOME=/Applications/splunk 
# elif [ "$(expr substr $(uname -s) 1 5)" == "Linux" ]; then
else
  # Default to /opt/splunk
  SPLUNK_HOME=/opt/splunk
fi

curl -s http://data.phishtank.com/data/online-valid.csv > $SPLUNK_HOME/etc/apps/BarracudaWebFilter/lookups/online-valid.csv

