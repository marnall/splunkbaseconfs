#!/bin/bash  
current_dir=$(dirname "$0")
"$SPLUNK_HOME/bin/splunk" cmd python "$current_dir/app/cmx_monit.py" $@