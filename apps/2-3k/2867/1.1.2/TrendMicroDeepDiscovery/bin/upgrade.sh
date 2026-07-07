#! /bin/bash

cp $SPLUNK_HOME/etc/apps/TrendMicroDeepDiscovery/default.old.*/ADS-base.conf $SPLUNK_HOME/etc/apps/TrendMicroDeepDiscovery/default/ADS-base.conf
rm -rf $SPLUNK_HOME/etc/apps/TrendMicroDeepDiscovery/default.old.*
