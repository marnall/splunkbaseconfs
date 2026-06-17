#!/bin/bash
#
# Wrapper for Sample Twitter streaming API client
# 
# USAGE
#     capture_twitter.sh [<FILTER_KEYWORD>]
# 
#     FILTER_KEYWORD
#         string on which to search Twitter; leave blank to get the standard 1% firehose

BIN_PATH=`dirname $0`

$SPLUNK_HOME/bin/splunk cmd python $BIN_PATH/twitter_stream.py $1

