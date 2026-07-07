#!/bin/bash
APP_NAME=TA-geolocate
TARGETFILEURL=http://download.geonames.org/export/dump/cities1000.zip
OUTPUTDIR=$SPLUNK_HOME/etc/apps/$APP_NAME/static
OUTPUTFILE=$OUTPUTDIR/cities1000.zip

echo "[`date`] SCRIPT=citiesupdate.sh SPLUNK_HOME=${SPLUNK_HOME}, APP_NAME=${APP_NAME}, OUTPUTDIR=${OUTPUTDIR} Starting execution."

# Do some cleanup of old files, just in case
rm -f $OUTPUTFILE
rm -f $OUTPUTDIR/cities1000.txt

# Get the latest file
wget -O $OUTPUTFILE $TARGETFILEURL

# If the file exists, extract it and parse
if [ -f $OUTPUTFILE ]; then
	echo "[`date`] Zip file exists."
	unzip $OUTPUTFILE -d $OUTPUTDIR/

	if [ -f $OUTPUTDIR/cities1000.txt ]; then
		echo "[`date`] Cities1000.txt appears to exist. Creating modified version."
		cat $OUTPUTDIR/cities1000.txt | cut -f3,5,6,9,11,18 > $OUTPUTDIR/cities1000_mod.txt

		if [ -f $OUTPUTDIR/cities1000_mod.txt ]; then
			echo "[`date`] cities1000_mod.txt exists; assuming successful execution."
		else
			echo "[`date`] cities1000_mod.txt does not exist. Assuming error."
		fi
		# Let's not keep the zip file around or the original cities file
		rm -f $OUTPUTFILE
		rm -f $OUTPUTDIR/cities1000.txt
	else
		echo "[`date`] Cities1000.txt does not exist. Stop processing."
	fi
else
	echo "[`date`] Zip file not downloaded. Stop processing."
fi

echo "[`date`] Ending execution."
