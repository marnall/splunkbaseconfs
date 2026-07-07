#!/bin/bash

## ########################################################################################
## ##
## ## SPLUNK_TA_ARI_MAC Edge Discovery
## ##
## ## Copyright (C) 2025 - Splunk Inc. - All Rights Reserved
## ## Splunk Software Licence and Support Agreement
## ##
## ########################################################################################

## Setting file path variables
system_software_info_raw_output_file_path="$SPLUNK_HOME/etc/apps/Splunk_TA_ari_mac/tmp/Software.log"
system_Hardware_info_raw_output_file_path="$SPLUNK_HOME/etc/apps/Splunk_TA_ari_mac/tmp/Hardware.log"

## Set current date and time
date_time=$(date +"%FT%T%z")

## Get filevault
fde_status=$(fdesetup status)

## Get Hostname
aura_nt_host=$(hostname -s | sed 's/^/"/' | sed 's/$/"/')

## Fetching All System Info
system_profiler SPSoftwareDataType | sed 's/^[[:space:]]*//g' | awk 'NF' > $system_software_info_raw_output_file_path
system_profiler SPHardwareDataType | sed 's/^[[:space:]]*//g' | awk 'NF' > $system_Hardware_info_raw_output_file_path

## Getting all required details from Software info log and save it in variable
System_Version=$(grep "System Version: " $system_software_info_raw_output_file_path | sed 's/System Version: //' | sed 's/^/"/' | sed 's/$/"/')
Kernel_Version=$(grep "Kernel Version: " $system_software_info_raw_output_file_path | sed 's/Kernel Version: //' | sed 's/^/"/' | sed 's/$/"/')
Boot_Volume=$(grep "Boot Volume: " $system_software_info_raw_output_file_path | sed 's/Boot Volume: //' | sed 's/^/"/' | sed 's/$/"/')
Boot_Mode=$(grep "Boot Mode: " $system_software_info_raw_output_file_path | sed 's/Boot Mode: //' | sed 's/^/"/' | sed 's/$/"/')
Secure_Virtual_Memory=$(grep "Secure Virtual Memory: " $system_software_info_raw_output_file_path | sed 's/Secure Virtual Memory: //' | sed 's/^/"/' | sed 's/$/"/')
System_Integrity_Protection=$(grep "System Integrity Protection: " $system_software_info_raw_output_file_path | sed 's/System Integrity Protection: //' | sed 's/^/"/' | sed 's/$/"/')
Time_since_boot=$(grep "Time since boot: " $system_software_info_raw_output_file_path | sed 's/Time since boot: //' | sed 's/^/"/' | sed 's/$/"/')

## Getting all required details from Hardware info log and save it in variable
Model_Name=$(grep "Model Name: " $system_Hardware_info_raw_output_file_path | sed 's/Model Name: //' | sed 's/^/"/' | sed 's/$/"/')
Model_Identifier=$(grep "Model Identifier: " $system_Hardware_info_raw_output_file_path | sed 's/Model Identifier: //' | sed 's/^/"/' | sed 's/$/"/')
Apple_Chip=$(grep "Chip: " $system_Hardware_info_raw_output_file_path | sed 's/Chip: //' | sed 's/^/"/' | sed 's/$/"/')
Intel_Chip="$(grep "Processor Name: " $system_Hardware_info_raw_output_file_path | sed 's/^Processor Name: /"/') $(grep "Processor Speed: " $system_Hardware_info_raw_output_file_path | sed -E 's/Processor Speed: (.*)/\1"/')"
Total_Number_of_Cores=$(grep "Total Number of Cores: " $system_Hardware_info_raw_output_file_path | sed 's/Total Number of Cores: //' | sed 's/^/"/' | sed 's/$/"/')
Memory=$(grep "Memory: " $system_Hardware_info_raw_output_file_path | sed 's/Memory: //' | sed 's/^/"/' | sed 's/$/"/')
System_Firmware_Version=$(grep "System Firmware Version: " $system_Hardware_info_raw_output_file_path | sed 's/System Firmware Version: //' | sed 's/^/"/' | sed 's/$/"/')
OS_Loader_Version=$(grep "OS Loader Version: " $system_Hardware_info_raw_output_file_path | sed 's/OS Loader Version: //' | sed 's/^/"/' | sed 's/$/"/')
Serial=$(grep "Serial Number (system): " $system_Hardware_info_raw_output_file_path | sed 's/Serial Number (system): //' | sed 's/^/"/' | sed 's/$/"/')
Hardware_UUID=$(grep "Hardware UUID: " $system_Hardware_info_raw_output_file_path | sed 's/Hardware UUID: //' | sed 's/^/"/' | sed 's/$/"/')
Provisioning_UDID=$(grep "Provisioning UDID: " $system_Hardware_info_raw_output_file_path | sed 's/Provisioning UDID: //' | sed 's/^/"/' | sed 's/$/"/')
Activation_Lock_Status=$(grep "Activation Lock Status: " $system_Hardware_info_raw_output_file_path | sed 's/Activation Lock Status: //' | sed 's/^/"/' | sed 's/$/"/')

fde=""
if [ "$fde_status" == "FileVault is On." ]; then
    fde=" fde_encrypted=1 fde_version=FileVault"
fi

## Process some of the values
Total_Number_of_Cores2=$(echo $Total_Number_of_Cores | sed -E 's/"([0-9]*) .*/\1/')
Memory2=$(echo $Memory | sed -E 's/"([0-9]*) .*/\1/' | awk '{print $0*1024}')
os=$(echo $System_Version | sed -E 's/"(macOS [0-9]*)\..*/\1/')
os_version=$(echo $System_Version | sed -E 's/"macOS (.*) \(.*/\1/')
if [ -n "$Apple_Chip" ]; then Chip=$Apple_Chip; else Chip=$Intel_Chip; fi

output="$date_time ari_vendor=\"Apple\" asset_type=\"Workstation\""
[ -n $"$Model_Name" ] && output+=" ari_product=$Model_Name"
[ -n $"$Model_Identifier" ] && output+=" model_identifier=$Model_Identifier"
[ -n $"$Chip" ] && output+=" chip=$Chip"
[ -n $"$Total_Number_of_Cores2" ] && output+=" cpu_cores=$Total_Number_of_Cores2"
[ -n $"$Memory2" ] && output+=" mem=$Memory2"
[ -n $"$System_Firmware_Version" ] && output+=" system_firmware_version=$System_Firmware_Version"
[ -n $"$OS_Loader_Version" ] && output+=" os_loader_version=$OS_Loader_Version"
[ -n $"$Serial" ] && output+=" serial=$Serial"
[ -n $"$Hardware_UUID" ] && output+=" hardware_uuid=$Hardware_UUID"
[ -n $"$Provisioning_UDID" ] && output+=" provisioning_udid=$Provisioning_UDID"
[ -n $"$Activation_Lock_Status" ] && output+=" activation_lock_status=$Activation_Lock_Status"
[ -n $"$os\"" ] && output+=" os=\"$os\""
[ -n $"$os_version\"" ] && output+=" os_version=\"$os_version\""
[ -n $"$Kernel_Version" ] && output+=" kernel_version=$Kernel_Version"
[ -n $"$Boot_Volume" ] && output+=" boot_volume=$Boot_Volume"
[ -n $"$Boot_Mode" ] && output+=" boot_mode=$Boot_Mode"
[ -n $"$aura_nt_host" ] && output+=" ari_nt_host=$aura_nt_host"
[ -n $"$Secure_Virtual_Memory" ] && output+=" secure_virtual_memory=$Secure_Virtual_Memory"
[ -n $"$System_Integrity_Protection" ] && output+=" system_integrity_protection=$System_Integrity_Protection"
[ -n $"$Time_since_boot$fde" ] && output+=" time_since_boot=$Time_since_boot$fde"

echo $output

## Cleaning log files used in script
rm $system_software_info_raw_output_file_path $system_Hardware_info_raw_output_file_path