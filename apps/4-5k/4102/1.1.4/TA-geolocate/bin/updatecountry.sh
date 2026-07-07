#!/bin/bash
APP_NAME=TA-geolocate
TARGETFILEURL=http://download.geonames.org/export/dump/countryInfo.txt
OUTPUTDIR=$SPLUNK_HOME/etc/apps/$APP_NAME/static
OUTPUTFILE=$OUTPUTDIR/countryinfo_mod.txt

echo "[`date`] SCRIPT=updatecountry.sh SPLUNK_HOME=${SPLUNK_HOME}, APP_NAME=${APP_NAME}, OUTPUTDIR=${OUTPUTDIR} Starting execution."

# Do some cleanup of old files, just in case
rm -f $OUTPUTDIR/countryInfo.txt

# Get the latest file
wget -O $OUTPUTDIR/countryInfo.txt $TARGETFILEURL

# If the file exists, parse
if [ -f $OUTPUTDIR/countryInfo.txt ]; then
	echo "[`date`] countryInfo.txt exists. Parsing."

	cat $OUTPUTDIR/countryInfo.txt | grep -v '^#' | cut -f1,5 > $OUTPUTFILE
	if [ -f $OUTPUTFILE ]; then
		echo "[`date`] countryinfo_mod.txt exists; assuming successful execution."
	else
		echo "[`date`] countryinfo_mod.txt does not exist. Assuming error."
	fi

	# cleanup
	rm -f $OUTPUTDIR/countryInfo.txt

else
	echo "[`date`] countryInfo.txt not downloaded. Parsing skipped."
fi

echo "[`date`] Ending execution."
