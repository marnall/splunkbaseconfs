REM
REM getphishlist by Josh Diakun (joshd AT joshd DOT ca)
REM version 1.1
REM date: Sep 28, 2013
REM
REM gets the free data feed from phishtank.com that has current confirmed phishing URLs
REM credit for original creation of the script goes to Nimish Doshi.
REM

@echo off
REM set SPLUNK_HOME
REM set SPLUNK_HOME=c:\Program Files\Splunk

curl -s http://data.phishtank.com/data/online-valid.csv > $SPLUNK_HOME\BarracudaWebFilter\lookups\online-valid.csv
