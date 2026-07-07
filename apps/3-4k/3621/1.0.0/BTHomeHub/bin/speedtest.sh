#!/bin/bash

echo $(date) > /tmp/st.res |python $SPLUNK_HOME/etc/apps/BTHomeHub/bin/speedtest.py |grep load: >> /tmp/st.res
cat /tmp/st.res |xargs -n3 -d'\n'

