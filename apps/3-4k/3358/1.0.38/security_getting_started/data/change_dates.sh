#!/bin/sh
##################
# To update move the dir to /tmp/data
# Run the script by changing $DATE_OLD to $DATA_NEW 
##################

WORKING_DIR="/tmp/data"
DATE_OLD=2016
DATE_NEW=2020
##################

for FILE_NAME in `cd $WORKING_DIR ; ls $WORKING_DIR/SPL*gz ; ls $WORKING_DIR/INPUT*gz`
do
	echo "Processing file : $FILE_NAME"
	zcat $FILE_NAME | sed -e "s/$DATE_OLD/$DATE_NEW/g" > ${FILE_NAME}_NEW
	#rm $WORKING_DIR/$FILE_NAME
	gzip ${FILE_NAME}_NEW 
	mv ${FILE_NAME}_NEW.gz $FILE_NAME
done
