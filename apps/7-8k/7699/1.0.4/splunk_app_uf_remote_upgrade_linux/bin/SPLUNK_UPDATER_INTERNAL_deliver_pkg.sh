#!/bin/bash

set -eu

SCRIPT_DIR="$(realpath "$(dirname "${BASH_SOURCE[0]}")")"
# Index the package delivery logs by default
LOG_FILE="$SPLUNK_HOME/var/log/splunk/upgrader_package_delivery.log"

# redirect stdout & stderr to a file globally, since this is a data input
# and should not output anything or else it'd be ingested by Splunk
exec >>"$LOG_FILE" 2>&1

# indicate if the package has been delivered or not
PKG_DELIVERED_FILE="$SCRIPT_DIR/pkg_delivered"

# the UF packages should be placed in this dir
SRC_PKG_DIR="$SCRIPT_DIR/../local/packages"

# print_log: print logs with timestamp
# parameters: 
#    msg: the log message to be printed
# return: 
#    None
print_log() {
    local msg="$1"
    echo "$(date +"%Y-%m-%d-%T") $msg" >>"$LOG_FILE" 2>&1
}

# run_cmd: print the command and execute it, output the stdout/stderr to the log file
# parameters: 
#    cmd: the command
# return: 
#    None
run_cmd() {
    local cmd="$1"
    print_log "Running cmd: $cmd"
    bash -c "$cmd" >>$LOG_FILE 2>&1
}

# found_files_in_dir: check if there are any files under a given directory
# parameters: 
#    dir: the directory
# return: 
#    0: files found
#    1: no files found
found_files_in_dir() {
    local dir="$1"
    if [ -d "$dir" ]; then
        if [ -n "$(ls -A "$dir")" ]; then
            return 0
        fi
    fi
    return 1
}

# cancel_delivery_and_wait_for_next_interval: skip package delivery and wait for next data input internal to try to deliver the package again.
# parameters: 
#    msg: the log message about why the delivery is cancelled
# return: 
#    None
cancel_delivery_and_wait_for_next_interval() {
    local msg="$1"
    print_log "$msg"
    print_log "Cancelling package delivery and waiting for next interval."
    exit 1
}

if [ -f "$PKG_DELIVERED_FILE" ]; then
    # don't log when this happens, to avoid flooding /var/log/upgrader_package_delivery.log
    exit 1
fi

print_log "Checking if any forwarder packages are available"
if found_files_in_dir "$SRC_PKG_DIR" ; then
    # dir not empty
    print_log "Found files in $SRC_PKG_DIR. Will deliver them."
else
    print_log "No packages available in $SRC_PKG_DIR. Canceling package delivery"
    exit 1
fi

# read dest dir from $SPLUNK_HOME/var/run/splunk/splunkupdater/info
info_path="$SPLUNK_HOME/var/run/splunk/splunkupdater/info"
if [ ! -f "$info_path" ]; then
    cancel_delivery_and_wait_for_next_interval "Conf file from UF updater does not exist at \"$info_path\". The UF updater is likely not installed or running."
fi

# should get 2 vars: 
# FWD_PKG_DIR: the directory Updater is monitoring
# FWD_UPGRADE_TRIGGER_FILENAME: the trigger file to start the upgrade
source "$info_path"

# validate FWD_UPGRADE_TRIGGER_FILENAME
if [ -z "$FWD_UPGRADE_TRIGGER_FILENAME" ]; then
    cancel_delivery_and_wait_for_next_interval "FWD_UPGRADE_TRIGGER_FILENAME is not defined in $info_path"
fi

# validate FWD_PKG_DIR
if [ -z "$FWD_PKG_DIR" ]; then
    cancel_delivery_and_wait_for_next_interval "FWD_PKG_DIR is not defined in $info_path"
elif [ ! -d "$FWD_PKG_DIR" ]; then
    cancel_delivery_and_wait_for_next_interval "FWD_PKG_DIR=$FWD_PKG_DIR does not exist"
fi

# FWD_PKG_DIR is not empty, which means the UF upgrade is still ongoing
if found_files_in_dir "$FWD_PKG_DIR" ; then
    cancel_delivery_and_wait_for_next_interval "Target dir \"$FWD_PKG_DIR\" is not empty"
fi

# copy UF packages from ./local/packages to the dest dir
print_log "Copying files from $SCRIPT_DIR/../local/packages to $FWD_PKG_DIR"
run_cmd "cp -r \"$SCRIPT_DIR/../local/packages/.\" \"$FWD_PKG_DIR\""

# create a file in UF updater to trigger the upgrade
print_log "Creating a trigger file to start upgrade: $FWD_PKG_DIR/$FWD_UPGRADE_TRIGGER_FILENAME" 
run_cmd "touch \"$FWD_PKG_DIR/$FWD_UPGRADE_TRIGGER_FILENAME\""

# create pkg_delivered file to stop this script
print_log "Completed the package delivery. Creating a file to make sure it only happens once."
run_cmd "touch \"$PKG_DELIVERED_FILE\""
print_log "Completed!"
