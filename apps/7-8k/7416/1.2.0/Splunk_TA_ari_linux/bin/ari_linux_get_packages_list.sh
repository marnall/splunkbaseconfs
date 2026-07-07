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
nt_host=$(hostname -s | sed 's/^/"/' | sed 's/$/"/')

ROWS=""
if [ "`uname -s`" = "Linux" ] ; then

    if [ -e /etc/debian_version ]; then DEBIAN=true; else DEBIAN=false; fi

    if $DEBIAN; then
        FORMAT='{name=$1;version=$2;sub("\\.?[^0-9\\.:\\-].*$", "", version); release=$2; sub("^[0-9\\.:\\-]*","",release); if(release=="") {release="unknown"}; arch=$3; if (NF>3) {sub("^.*:\\/\\/", "", $4); sub("^www\\.", "", $4); sub("\\/.*$", "", $4); vendor=$4} else {vendor="unknown"}}'
        PRINTF='{printf "ari_software_product=\"%s\" ari_software_version=\"%s\" release=\"%s\" arch=\"%s\" ari_software_vendor=\"%s\"\n", name, version, release, arch, vendor}'
        ROWS=$(dpkg-query -W -f='${Package} ${Version} ${Architecture} ${Homepage}\n' | awk "$FORMAT $PRINTF")
    else
        ROWS=$(rpm --query --all --queryformat "ari_software_product=\"%{name}\" ari_software_version=\"%{version}\" release=\"%{release}\" arch=\"%{arch}\" ari_software_vendor=\"%{vendor}\"\n")
    fi

    O=$IFS
    IFS=$(echo -en "\n\b")

    for ROW in ${ROWS[@]}
    do
        echo "$date_time ari_nt_host=$nt_host $ROW"
    done

    IFS=$O
fi