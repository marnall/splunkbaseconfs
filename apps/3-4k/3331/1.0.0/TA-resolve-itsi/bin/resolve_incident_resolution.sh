read sessionKey
echo -e "$SPLUNK_ARG_0\n$0\n$1\n$2\n$3\n$4\n$5\n$6\n$7\n$8\n$sessionKey" >> \
"$SPLUNK_HOME/etc/apps/TA-resolve-itsi/bin/resolve_incident_resolution.output"
