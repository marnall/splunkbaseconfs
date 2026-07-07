# 01-03-2017 - MrGibbon
#!/bin/bash

cat $SPLUNK_HOME/etc/apps/fping/local/fping.conf | grep server | cut -d" " -f3  | xargs -n1 fping -D -C 1 -A -n
