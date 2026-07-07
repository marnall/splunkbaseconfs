#!/bin/sh

# Get into Splunk
BIN="$SPLUNK_HOME/bin/splunk"
$BIN login -auth admin:changeme 

# Run the lookup generations with 1 month of timeframe
$BIN search 'earliest=-1month `credant_shield2host`'
$BIN search 'earliest=-1month `credant_shield2uid`'
$BIN search 'earliest=-1month `credant_uid2user`'

