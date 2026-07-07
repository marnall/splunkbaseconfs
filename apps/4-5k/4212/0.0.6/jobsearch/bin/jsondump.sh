#!/bin/bash

#found the fix here: https://answers.splunk.com/answers/418398/how-to-get-splunk-to-run-my-python-shell-script.html
unset PYTHONPATH

CLASSPATH=/usr/lib/python3/dist-packages/
export CLASSPATH

#PYTHONVEROSE=1
#export PYTHONVERBOSE
/usr/bin/python3 "$SPLUNK_HOME/etc/apps/jobsearch/bin/jsondump.py
"