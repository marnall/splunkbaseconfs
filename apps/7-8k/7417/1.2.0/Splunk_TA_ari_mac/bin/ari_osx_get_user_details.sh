#!/bin/bash

## ########################################################################################
## ##
## ## SPLUNK_TA_ARI_MAC Edge Discovery
## ##
## ## Copyright (C) 2025 - Splunk Inc. - All Rights Reserved
## ## Splunk Software Licence and Support Agreement
## ##
## ########################################################################################

#Setting file path variables
active_user_raw_output_file="$SPLUNK_HOME/etc/apps/Splunk_TA_ari_mac/tmp/user_mac_osx_output.log"

#Set hostname and current date & time
date_time=$(date +"%FT%T%z")
aura_nt_host=$(hostname -s | sed 's/^/"/' | sed 's/$/"/')

#Getting list of all active user names
user_names=( $(users | sed 's/[[:space:]]/\n/g' | uniq) )

#counter to be used for array
counter=0

#Getting required user details
for i in "${user_names[@]}"
do
    #Getting last logged in details and save raw file
    last $i | grep "logged in" | head -1 > $active_user_raw_output_file

    #Iterate through raw file to get all required details and save it in array
    while IFS= read -r last
    do
        aura_user_id[$counter]=$(echo $i | sed 's/^/"/' | sed 's/$/"/')
        user_info[$counter]=$(dscl . -read /Users/$i RealName | tail -n 1 | sed 's/^ */"/; s/ *$/"/')
        session[$counter]=$(echo $last | awk '{print $2}' | sed 's/^/"/' | sed 's/$/"/')
        aura_lastdetect[$counter]=$(date "+%s")
        let counter++
    done < $active_user_raw_output_file
done

#Saving all the user details into csv file
for ((i=0; i<$counter; i++))
do
    if [ -n $aura_user_id[$i] ]; then
        output="$date_time ari_nt_host=$aura_nt_host ari_user_id=${aura_user_id[$i]}"
        [ -n "$user_info[$i]" ] && output+=" user_info=${user_info[$i]}"
        [ -n "$session[$i]" ] && output+=" session=${session[$i]}"
        [ -n "$aura_lastdetect[$i]" ] && output+=" ari_lastdetect=${aura_lastdetect[$i]}"

        echo $output
    fi
done

# Cleaning temp log files used in script
rm $active_user_raw_output_file