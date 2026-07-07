#!/bin/bash

# Define file paths
server_conf="/opt/splunkforwarder/etc/system/local/server.conf"
instance_cfg="/opt/splunkforwarder/etc/instance.cfg"
marker_file="/opt/splunkforwarder/instance_cfg_deleted.marker"

# Hostname expected in the files
expected_server_hostname=$(hostname)

# Remediation flags
remediation_hostname=false
remediation_guid=false

# Initialize remediation status
remediation_status="noaction"

# Function to update file content if updating is enabled
function update_file_content() {
    local path="$1"
    local pattern="$2"
    local expected_hostname="$3"
    local line=$(grep -E "^$pattern\s*=" "$path")

    if [ -z "$line" ]; then
        if $remediation_hostname; then
            echo "$pattern = $expected_hostname" >> "$path"
            remediation_status="remediation_hostname"
            echo "true $expected_hostname"
        else
            echo "false hostname not found"
        fi
        return
    fi

    local current_hostname=$(echo "$line" | sed -r "s/^\s*$pattern\s*=\s*(.*)\s*/\1/")
    if [[ "$current_hostname" == "$expected_hostname" ]]; then
        echo "true $current_hostname"
    else
        if $remediation_hostname; then
            sed -i "s|^\s*$pattern\s*=.*|$pattern = $expected_hostname|" "$path"
            remediation_status="remediation_hostname"
            echo "true $expected_hostname"
        else
            echo "false $current_hostname"
        fi
    fi
}

# Function to read the Splunk Agent GUID
function get_splunk_agent_guid() {
    local guid_line=$(grep -P 'guid\s*=' "$1")
    if [ -n "$guid_line" ]; then
        echo "$guid_line" | sed -r 's/.*guid\s*=\s*(.*)/\1/'
    else
        echo "read error"
    fi
}

# Check which user the Splunk service is running as
function get_splunk_service_account() {
    local user_info=$(ps aux | grep "[s]plunk" | grep -v grep | awk '{print $1}' | sort | uniq)
    echo "$user_info" | tr '\n' ' '  # Transform newline to space for better readability
}

# Function to determine Linux OS type
function get_linux_os_type() {
    osType="unknown"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "$ID" in
            ubuntu|debian|centos|rhel|fedora|suse)
                osType="linux_server"
                ;;
            *)
                osType="unknown_linux_distribution"
                ;;
        esac
    else
        osType="not_a_linux_system"
    fi
    echo "$osType"
}

# Function to delete instance.cfg file
function delete_instance_cfg() {
    if [ -f "$1" ]; then
        rm -f "$1"
        touch "$2"  # Create marker file
        remediation_status="remediation_guid"
    fi
}

# Read and optionally update server.conf
IFS=' ' read -r match_result server_host < <(update_file_content "$server_conf" "serverName" "$expected_server_hostname")
server_conf_verification="@{ServerConfMatch=$(echo "$match_result" | tr '[:upper:]' '[:lower:]')}"
current_server_host_output="@{CurrentServerHost=$server_host}"

# Execute remediations based on flags
if $remediation_guid && [ ! -f "$marker_file" ]; then
    delete_instance_cfg "$instance_cfg" "$marker_file"
fi

# Get the Splunk service account
splunk_service_account=$(get_splunk_service_account)
splunk_service_account_output="@{SplunkServiceAccount=$splunk_service_account}"

# Get the Splunk Agent GUID
splunk_agent_guid=$(get_splunk_agent_guid "$instance_cfg")
splunk_cfg_instance_guid="@{SplunkCfgInstanceGuid=$splunk_agent_guid}"

# Determine the OS type
OsType=$(get_linux_os_type)
os_type_output="@{OSType=$OsType}"

# Create remediation status output
remediation_status_output="@{RemediationStatus=$remediation_status}"

# Output the results
echo "$server_conf_verification"
echo "$current_server_host_output"
echo "$splunk_service_account_output"
echo "$splunk_cfg_instance_guid"
echo "$os_type_output"
echo "$remediation_status_output"
