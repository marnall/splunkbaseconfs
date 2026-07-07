#!/bin/sh
/opt/splunk/bin/splunk cmd python2.7 /opt/splunk/etc/apps/cbfeed/bin/xml2csv.py url www.clickbank.com/feeds/marketplace_feed_v2.xml.zip 
