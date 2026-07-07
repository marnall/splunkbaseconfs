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
interfaces=($(ip -4 -o addr show scope global | awk '/^[0-9]+: / {print $2}'))

for i in "${interfaces[@]}"
do
    aura_ip=$(ip -f inet addr show $i | sed -En -e 's/.*inet ([0-9.]+).*/\1/p')
    aura_mac=$(cat /sys/class/net/$i/address 2>/dev/null)

    if [[ -n "$aura_ip" && -n "$aura_mac" ]]; then
        echo $date_time ari_nt_host=$(hostname -s) interface=$i ari_ip=$aura_ip ari_mac=$aura_mac
    fi
done
: