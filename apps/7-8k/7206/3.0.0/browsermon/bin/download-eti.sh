#!/usr/bin/env bash
#
# Author: EUNOMATIX, Browsermon Team
#
# Description: Downloads EUNOMATIX Threat Intelligence (ETI) feeds from EUNOMATIX website.
#
# Release Data 31 May 2026
#

URL=https://eunomatix.com/threats

SAVEPATH=../lookups

FILE_ATI_DOMAINS=eti-ti-domains.csv
FILE_ATI_HASHES=eti-ti-hashes.csv
FILE_ATI_IPS=eti-ti-ips.csv

URL_CHECK_REGEX='(https?|ftp|file)://[-[:alnum:]\+&@#/%?=~_|!:,.;]*[-[:alnum:]\+&@#/%=~_|]'
if [[ "${URL}" =~ ${URL_CHECK_REGEX} ]]; then
    echo "${URL} is a valid URL."
else
    echo "${URL} is an invalid URL."
    exit 1
fi

echo ... Downloading Files

download_ati()
{
  wget $URL/$1 -O $2/$1.download

  if [ $(head -n 1 $2/$1.download | wc -l) -eq 1 ];  
  then
     echo renaming $1.download
     mv $2/$1.download $2/$1
  fi
}

download_ati $FILE_ATI_DOMAINS $SAVEPATH
download_ati $FILE_ATI_HASHES $SAVEPATH
download_ati $FILE_ATI_IPS $SAVEPATH


