#!/bin/bash

# Detect Splunk home dynamically if not set
if [ -z "$SPLUNK_HOME" ]; then
    SPLUNK_HOME="/opt/splunkforwarder"
fi

HOSTNAME=$(hostname)
CERT_PATHS=()

# Function to extract certificate paths and expand $SPLUNK_HOME
extract_cert_paths() {
    local conf_file="$1"

    if [ -f "$conf_file" ]; then
        CLIENT_CERT=$(awk -F' = ' '/^\s*clientCert/ {print $2}' "$conf_file" | tr -d '\r' | tr -d ' ')
        SSL_CA_PATH=$(awk -F' = ' '/^\s*sslRootCAPath/ {print $2}' "$conf_file" | tr -d '\r' | tr -d ' ')

        # Expand $SPLUNK_HOME if it appears in the path
        CLIENT_CERT=${CLIENT_CERT/\$SPLUNK_HOME/$SPLUNK_HOME}
        SSL_CA_PATH=${SSL_CA_PATH/\$SPLUNK_HOME/$SPLUNK_HOME}

        if [ -n "$CLIENT_CERT" ]; then
            CERT_PATHS+=("$CLIENT_CERT")
        fi
        if [ -n "$SSL_CA_PATH" ]; then
            CERT_PATHS+=("$SSL_CA_PATH")
        fi
    fi
}

# Extract cert paths from system configs
extract_cert_paths "$SPLUNK_HOME/etc/system/local/outputs.conf"
extract_cert_paths "$SPLUNK_HOME/etc/system/local/server.conf"

# Scan all apps for outputs.conf and server.conf
for app in "$SPLUNK_HOME/etc/apps/"*; do
    if [ -d "$app" ]; then
        extract_cert_paths "$app/local/outputs.conf"
        extract_cert_paths "$app/local/server.conf"
        extract_cert_paths "$app/default/outputs.conf"
        extract_cert_paths "$app/default/server.conf"
    fi
done

# Function to check certificate expiry and format output
check_certificate() {
    local cert_file="$1"

    if [ -f "$cert_file" ]; then
        EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)

        if [ -n "$EXPIRY_DATE" ]; then
            TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
            echo "[$TIMESTAMP] cert_expiry_check, hostname=\"$HOSTNAME\", cert_path=\"$cert_file\", expiry_date=\"$EXPIRY_DATE\""
        fi
    fi
}

# Check each certificate path
for cert in "${CERT_PATHS[@]}"; do
    check_certificate "$cert"
done

