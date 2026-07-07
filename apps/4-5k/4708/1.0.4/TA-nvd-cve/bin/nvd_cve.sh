#!/bin/sh

##Add the Proxy detail if required else hash the next line 
#export https_proxy=http://<http_proxy>:<Port>

##Setting variables to be used for fetching cve data
d=$(date +'%Y-%m-%d')
END_YEAR=$(date +'%Y')
START_YEAR=$((END_YEAR-4)) 
echo $END_YEAR
echo $START_YEAR

##Set below variable to assign the download directory for logs
DOWNLOAD_DIR="/opt/data/cve_data/$d/%y"

##URL for Feed download with year as variable
CVE_20_BASE_URL='https://nvd.nist.gov/feeds/json/cve/1.0/nvdcve-1.0-%d.json.gz'

##Execution start to count total duration 
START_TIME=$(date +%s)

download () {
echo
    echo "Starting download of $1"
     wget --no-check-certificate $1 -P $2

    if [ "$?" != 0 ]; then
        echo "ERROR: Downloading of $1 failed."
        exit 1
   fi 
    echo "Download of $1 sucessfully completed."
echo
}
 
echo "Starting download of NVD files ..."
 
for ((i=$START_YEAR;i<=$END_YEAR;i++));
do

    download "${CVE_20_BASE_URL//%d/$i}" "${DOWNLOAD_DIR//%y/$i}"

##allowed 5 min of sleep between consecutve downloads to allow splunk to finish reading one file at a time

    sleep 5m
done
 
END_TIME=$(date +%s)
DURATION=$((END_TIME-START_TIME))
echo "Download of NVD files successfully completed in $DURATION seconds."
