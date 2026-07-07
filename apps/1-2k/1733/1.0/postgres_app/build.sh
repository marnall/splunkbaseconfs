#!/bin/bash
# This should be run from the $SPLUNK_HOME/etc/apps/oidemo directory.

# set destination dir
APP_DIRNAME="postgres_app"

usage() {

cat << EOF
Usage: $0 [ -e ] [ -h ] [ -d DIR ]"

-h - print this help message
-e - embed eventgen 
-d DIR - destination directory for package (defeault = .)
	
EOF
}

while getopts "hed:" opt;do
	case $opt in
		h) usage; exit;;
		e) EMBED_EVENTGEN=1;;
		d) DEST_DIR=$OPTARG;;
	esac
done
EMBED_EVENTGEN=${EMBED_EVENTGEN:-0}
[ -n "$DEST_DIR" ] || DEST_DIR=.

# Save for later
CURRENT_PWD=`pwd`


# Cleanup
rm -f $DEST_DIR/$APP_DIRNAME.spl

# Create a build directory that we can use
BUILD_DIR=.build/$APP_DIRNAME
BUILD_DIR_PARENT=.build
mkdir -p $BUILD_DIR

cp -R * $BUILD_DIR
[ -d $BUILD_DIR/local ] && rm $BUILD_DIR/local/*

if [ $EMBED_EVENTGEN -eq 1 ];then
	[ -d ../eventgen/ ] || { echo "Error - eventgen directory not found. Please make sure it's available in ../eventgen/" >&2; rm -fr $BUILD_DIR;exit 1; }
	echo '!!! Embedding eventgen - FOR INTERNAL Linux Polska USE ONLY !!!'
	# Copy all of the eventgen into the Build directory first.  This makes sure oidemo will overwrite any duplicates from eventgen
	mkdir -p $BUILD_DIR/bin/
	cp ../eventgen/bin/eventgen.py $BUILD_DIR/bin/
	mkdir -p $BUILD_DIR/lib/
	cp -R ../eventgen/lib/* $BUILD_DIR/lib/
	cat $BUILD_DIR/default/embed_eventgen.conf >> $BUILD_DIR/default/inputs.conf
	rm $BUILD_DIR/default/embed_eventgen.conf
	# embed eventgen config
	cat ../eventgen/default/eventgen.conf >> $BUILD_DIR/default/eventgen.conf
	[ -d $BUILD_DIR/local ] || mkdir $BUILD_DIR/local
	cat $BUILD_DIR/default/eventgen.conf.example >> $BUILD_DIR/local/eventgen.conf
fi
cd $BUILD_DIR_PARENT

tar cfz $DEST_DIR/$APP_DIRNAME.spl $APP_DIRNAME --exclude "$APP_DIRNAME/$APP_DIRNAME.spl" --exclude "$APP_DIRNAME/bin/output/*" --exclude "$APP_DIRNAME/.*" 
cd $CURRENT_PWD
rm -rf $BUILD_DIR

echo "Build Complete"
