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
app_details_raw_output_file_path="$SPLUNK_HOME/etc/apps/Splunk_TA_ari_mac/tmp/output.log"
app_details_raw_file_path="$SPLUNK_HOME/etc/apps/Splunk_TA_ari_mac/tmp/applist.log"

#Set current date and time
date_time=$(date +"%FT%T%z")

#Fetching All Application Info
system_profiler SPApplicationsDataType | sed '1d' > $app_details_raw_output_file_path

#Adding App_Name: before each app, so it can be divided into chunks based on that
cat $app_details_raw_output_file_path | sed -e 's/^[[:space:]]\{4\}\([[:alnum:]]\)/App_Name: \1/g' | sed 's/^[[:space:]]*//g' | awk 'NF' > $app_details_raw_file_path

#Getting total number of apps
App_count=$(grep "App_Name: " $app_details_raw_file_path | wc -l)

#Spliting each app details into separate files
csplit -s -n3 -f $SPLUNK_HOME/etc/apps/Splunk_TA_ari_mac/tmp/OSx_App_Details_ $app_details_raw_file_path '/^App_Name/' {$(expr $App_count - 2 )}

#Iterating through each app details file, get required details and save it csv file
for i in $SPLUNK_HOME/etc/apps/Splunk_TA_ari_mac/tmp/OSx_App_Details_*
do

    App_Name=$(grep "App_Name: " ${i} | sed 's/App_Name: //' | sed 's/.$//' | sed 's/^/"/' | sed 's/$/"/')
    Version=$(grep "Version: " ${i} | sed 's/Version: //g' | sed 's/^/"/' | sed 's/$/"/')
    Obtained_from=$(grep "Obtained from: " ${i} | sed 's/Obtained from: //g' | sed 's/^/"/' | sed 's/$/"/')
    Last_Modified=$(grep "Last Modified: " ${i} | sed 's/Last Modified: //g' | sed 's/^/"/' | sed 's/$/"/')
    Kind=$(grep "Kind: " ${i}| sed 's/Kind: //g' | sed 's/^/"/' | sed 's/$/"/')
    Signed_by=$(grep "Signed by: " ${i} | sed 's/Signed by: //g' | sed 's/^/"/' | sed 's/$/"/')
    Location=$(grep "Location: " ${i} | sed 's/Location: //g' | sed 's/^/"/' | sed 's/$/"/')
    Get_Info_String=$(grep -A 20 "Get Info String:" ${i} | sed 's/Get Info String: //g' | tr -d '\n' | sed 's/^/"/' | sed 's/$/"/')

    aura_vendor="\"Unknown\""
    if  [[ $Signed_by == \"Developer* ]] ;
    then
        tmp_vendor=$(echo $Signed_by | sed -E 's/"Developer ID Application: (.*) \(.*/\1/')
        aura_vendor="\"$tmp_vendor\""
    elif  [[ $Signed_by == \"Apple* ]] || [[ $Signed_by == "\"Software Signing, Apple Code Signing Certification Authority, Apple Root CA\"" ]];
    then
        aura_vendor="\"Apple\""
    fi


    output="$date_time ari_nt_host=$(hostname -s)"
    [ -n "$aura_vendor" ] && output+=" ari_software_vendor=$aura_vendor"
    [ -n "$App_Name" ] && output+=" ari_software_product=$App_Name"
    [ -n "$Version" ] && output+=" ari_software_version=$Version"
    [ -n "$Obtained_from" ] && output+=" obtained_from=$Obtained_from"
    [ -n "$Last_Modified" ] && output+=" install_date=$Last_Modified"
    [ -n "$Kind" ] && output+=" kind=$Kind"
    [ -n "$Signed_by" ] && output+=" signed_by=$Signed_by"
    [ -n "$Location" ] && output+=" install_location=$Location"
    [ -n "$Get_Info_String" ] && output+=" get_info_string=$Get_Info_String"

    echo $output
done

# Cleaning App Details files
rm $SPLUNK_HOME/etc/apps/Splunk_TA_ari_mac/tmp/OSx_App_Details_*  $app_details_raw_output_file_path $app_details_raw_file_path