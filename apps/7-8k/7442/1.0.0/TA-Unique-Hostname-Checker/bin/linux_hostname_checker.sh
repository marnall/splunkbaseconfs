#!/bin/bash

# Define file paths
server_conf="/opt/splunkforwarder/etc/system/local/server.conf"
instance_cfg="/opt/splunkforwarder/etc/instance.cfg"

# Hostname expected in the files
expected_server_hostname=$(hostname)

# Toggle for enabling or disabling updates
update_enabled=false

# Function to update file content if updating is enabled
function update_file_content() {
    local path="$1"
    local pattern="$2"
    local expected_hostname="$3"
    local line=$(grep -E "^$pattern\s*=" $path)

    if [ -z "$line" ]; then
        echo "false Hostname not found"  # Match status and error message
        return
    fi

    local current_hostname=$(echo "$line" | sed -r "s/^\s*$pattern\s*=\s*(.*)\s*/\1/")
    if [[ "$current_hostname" == "$expected_hostname" ]]; then
        echo "true $current_hostname"
    else
        if $update_enabled; then
            sed -i "s|^\s*$pattern\s*=.*|$pattern = $expected_hostname|" $path
        fi
        echo "false $current_hostname"
    fi
}

# Function to read the Splunk Agent GUID
function get_splunk_agent_guid() {
    local guid_line=$(grep -P 'guid\s*=' $1)
    if [ -n "$guid_line" ]; then
        echo "$guid_line" | sed -r 's/.*guid\s*=\s*(.*)/\1/'
    else
        echo "Read Error"
    fi
}

# Check which user the Splunk service is running as
function get_splunk_service_account() {
    local user_info=$(ps aux | grep "[s]plunk" | grep -v grep | awk '{print $1}' | sort | uniq)
    echo $user_info | tr '\n' ' '  # Transform newline to space for better readability
}

# Read and optionally update server.conf
IFS=' ' read match_result server_host < <(update_file_content "$server_conf" "serverName" "$expected_server_hostname")
server_conf_verification="@{ServerConfMatch=$match_result}"
current_server_host_output="@{CurrentServerHost=$server_host}"

# Get the Splunk service account
splunk_service_account=$(get_splunk_service_account)
splunk_service_account_output="@{SplunkServiceAccount=$splunk_service_account}"

# Get the Splunk Agent GUID
splunk_agent_guid=$(get_splunk_agent_guid "$instance_cfg")
splunk_cfg_instance_guid="@{SplunkCfgInstanceGuid=$splunk_agent_guid}"

# Output the results
echo $server_conf_verification
echo $current_server_host_output
echo $splunk_service_account_output
echo $splunk_cfg_instance_guid
