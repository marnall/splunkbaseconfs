#!/bin/bash

## ########################################################################################
## ##
## ## SPLUNK_TA_ARI_LINUX Edge Discovery
## ##
## ## Copyright (C) 2025 - Splunk Inc. - All Rights Reserved
## ## Splunk Software Licence and Support Agreement
## ##
## ########################################################################################

#Set current date and time
date_time=$(date +"%FT%T%z")

#Getting all system info  (Ex. hostname, cpu, memory, serial number, internal ip, external ip, MAC etc)
aura_nt_host=$(hostname -s | sed 's/^/"/' | sed 's/$/"/')
os=$(cat /etc/os-release | grep "^PRETTY_NAME=" | sed 's/^[^\=]*\=//')
os_version=$(cat /etc/os-release | grep "^VERSION=" | sed 's/^[^\=]*\=//')
aura_vendor=$(cat /sys/devices/virtual/dmi/id/chassis_vendor | sed 's/^/"/' | sed 's/$/"/')
aura_product=$(cat /sys/devices/virtual/dmi/id/product_name | sed 's/^/"/' | sed 's/$/"/')
chip=$(lscpu | grep "^Model name:" | awk '{$1=$2=""; print $0}' | sed 's/^[[:space:]]*//' | sed 's/^/"/' | sed 's/$/"/')
cpu_count=$(lscpu | grep "^CPU(s):" | awk '{print $2}')
cpu_mhz=$(lscpu | grep "^CPU MHz:" | awk '{print $3}')
mem=$((`grep "MemTotal" /proc/meminfo | awk '{print $2}'`/1024))
kernel_name=$(uname -s | sed 's/^/"/' | sed 's/$/"/')
kernel_release=$(uname -r | sed 's/^/"/' | sed 's/$/"/')
kernel_version=$(uname -v | sed 's/^/"/' | sed 's/$/"/')
machine_hardware_name=$(uname -m | sed 's/^/"/' | sed 's/$/"/')
processor_type=$(uname -p | sed 's/^/"/' | sed 's/$/"/')
hardware_platform=$(uname -i | sed 's/^/"/' | sed 's/$/"/')
hypervisor_vendor=$(lscpu | grep "^Hypervisor vendor:" | awk '{print $3}' | sed 's/^/"/' | sed 's/$/"/')
time_since_boot=$(uptime | sed 's/^.*up/"up/; s/, *[0-9]* *user.*$/"/')

cpu_cores_per_unit=$(lscpu | grep "^Core(s) per socket:"| awk '{print $4}')
if [ -n "$cpu_cores_per_unit" ]; then
    unit_count=$(lscpu | grep "^Socket(s):" | awk '{print $2}')
else
    cpu_cores_per_unit=$(lscpu | grep "^Core(s) per cluster:"| awk '{print $4}')
    unit_count=$(lscpu | grep "^Cluster(s):" | awk '{print $2}')
fi
if [ -z "$unit_count" ] || [ "$unit_count" = "-" ]; then unit_count=1; fi
cpu_cores=$(($cpu_cores_per_unit * $unit_count))

output="$date_time \
asset_type=\"Server\""
[ -n "$aura_nt_host" ] && output+=" ari_nt_host=$aura_nt_host"
[ -n "$aura_vendor" ] && output+=" ari_vendor=$aura_vendor"
[ -n "$aura_product" ] && output+=" ari_product=$aura_product"
output="${output} os_platform=\"Linux\""
[ -n "$os" ] && output+=" os=$os"
[ -n "$os_version" ] && output+=" os_version=$os_version"
[ -n "$cpu_count" ] && output+=" cpu_count=$cpu_count"
[ -n "$cpu_cores" ] && output+=" cpu_cores=$cpu_cores"
[ -n "$cpu_mhz" ] && output+=" cpu_mhz=$cpu_mhz"
[ -n "$mem" ] && output+=" mem=$mem"
[ -n "$kernel_name" ] && output+=" kernel_name=$kernel_name"
[ -n "$kernel_release" ] && output+=" kernel_release=$kernel_release"
[ -n "$kernel_version" ] && output+=" kernel_version=$kernel_version"
[ -n "$machine_hardware_name" ] && output+=" machine_hardware_name=$machine_hardware_name"
[ -n "$processor_type" ] && output+=" processor_type=$processor_type"
[ -n "$hardware_platform" ] && output+=" hardware_platform=$hardware_platform"
[ -n "$chip" ] && output+=" chip=$chip"
[ -n "$hypervisor_vendor" ] && output+=" hypervisor_vendor=$hypervisor_vendor"
[ -n "$time_since_boot" ] && output+=" time_since_boot=$time_since_boot"

echo $output