#!/bin/bash

## ########################################################################################
## ##
## ## SPLUNK_TA_ARI_MAC Edge Discovery
## ##
## ## Copyright (C) 2025 - Splunk Inc. - All Rights Reserved
## ## Splunk Software Licence and Support Agreement
## ##
## ########################################################################################

#Set current date and time
date_time=$(date +"%FT%T%z")

#Getting machine's local mac and internal ip
for interface in $(ipconfig getiflist); do
    machine_internal_ip=$(ipconfig getifaddr $interface)
    machine_mac=$(ifconfig $interface | awk '/ether/{print $2}')

    #Output the discovered details
    if [[ -n $machine_internal_ip && -n $machine_mac ]]; then
        echo $date_time ari_nt_host=$(hostname -s) ari_ip=$machine_internal_ip ari_mac=$machine_mac
    fi
done