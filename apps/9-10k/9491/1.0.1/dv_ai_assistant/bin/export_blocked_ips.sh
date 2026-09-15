#!/bin/bash




sleep 2

SPLUNK_HOME=${SPLUNK_HOME:-/opt/splunk}
LOOKUP_FILE="$SPLUNK_HOME/etc/apps/dv_ai_assistant/lookups/ai_ip_block.csv"
OUTPUT_FILE="$SPLUNK_HOME/etc/apps/dv_ai_assistant/appserver/static/ai_ip_block.txt"


if [ -f "$LOOKUP_FILE" ]; then




    
    sed '1d' "$LOOKUP_FILE" | tr -d '"' | grep -oE "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b" | sort -u > "$OUTPUT_FILE"
    

    chmod 644 "$OUTPUT_FILE"
else
    echo "[ERROR] Lookup file not found: $LOOKUP_FILE"
fi
