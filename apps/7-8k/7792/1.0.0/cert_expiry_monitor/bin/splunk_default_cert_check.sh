#!/bin/bash

# Detect Splunk home directory dynamically
if [ -z "$SPLUNK_HOME" ]; then
    SPLUNK_HOME="/opt/splunkforwarder"
fi

# Define paths for configuration files
APP_NAME="cert_expiry_monitor"
APP_PATH="$SPLUNK_HOME/etc/apps/$APP_NAME"
DEFAULT_CONFIG="$APP_PATH/default/splunkforwarderpath.conf"
LOCAL_CONFIG="$APP_PATH/local/splunkforwarderpath.conf"

# Load the appropriate config file (local takes precedence)
CONFIG_FILE=""
if [ -f "$LOCAL_CONFIG" ]; then
    CONFIG_FILE="$LOCAL_CONFIG"
elif [ -f "$DEFAULT_CONFIG" ]; then
    CONFIG_FILE="$DEFAULT_CONFIG"
else
    echo "ERROR: Configuration file not found!"
    exit 1
fi

# Read configurations dynamically from splunkforwarderpath.conf
CERT_PATHS=$(awk -F' = ' '/^cert_paths/ {print $2}' "$CONFIG_FILE")

# Ensure CERT_PATHS is set, otherwise use default values (without cacert.pem.default)
if [ -z "$CERT_PATHS" ]; then
    CERT_PATHS="/opt/splunkforwarder/etc/auth/server.pem,/opt/splunkforwarder/etc/auth/cacert.pem"
fi

# Convert the comma-separated string into an array
IFS=',' read -r -a CERT_ARRAY <<< "$CERT_PATHS"

# Remove /opt/splunkforwarder/etc/auth/cacert.pem.default dynamically if present
FILTERED_CERT_ARRAY=()
for cert in "${CERT_ARRAY[@]}"; do
    if [[ "$cert" != "/opt/splunkforwarder/etc/auth/cacert.pem.default" ]]; then
        FILTERED_CERT_ARRAY+=("$cert")
    fi
done

HOSTNAME=$(hostname)

# Function to check certificate expiry
check_certificate() {
    local cert_file="$1"

    if [ -f "$cert_file" ]; then
        EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d= -f2)
        TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

        LOG_OUTPUT="[$TIMESTAMP] cert_expiry_check, hostname=\"$HOSTNAME\", cert_path=\"$cert_file\", expiry_date=\"$EXPIRY_DATE\""
        echo "$LOG_OUTPUT"
    else
        echo "ERROR: Certificate file not found at $cert_file"
    fi
}

# Loop through the filtered certificate paths and check each one
for cert in "${FILTERED_CERT_ARRAY[@]}"; do
    check_certificate "$cert"
done

