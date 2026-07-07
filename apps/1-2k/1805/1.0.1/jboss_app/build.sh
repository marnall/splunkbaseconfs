#!/bin/bash

# set destination dir
APP_DIRNAME="jboss_app"

usage() {

cat << EOF
Usage: $0 [ -h ] [ -e ] [ -d DIR ]"

-h - print this help message
-d DIR - destination directory for package (defeault = .)
-e - enable eventgen 
	
EOF
}

while getopts "hed:" opt;do
	case $opt in
		h) usage; exit;;
		e) EMBED_EVENTGEN=1;;
		d) DEST_DIR=$OPTARG;;
	esac
done
[ -n "$DEST_DIR" ] || DEST_DIR=.

# Save for later
CURRENT_PWD=`pwd`


# Create a build directory that we can use
BUILD_DIR=.build/$APP_DIRNAME
BUILD_DIR_PARENT=.build
mkdir -p $BUILD_DIR

cp -R * $BUILD_DIR
[ -d $BUILD_DIR/local ] && rm $BUILD_DIR/local/*

if [ ${EMBED_EVENTGEN:-0} -eq 1 ];then
	echo '!!! Embedding eventgen - FOR INTERNAL Linux Polska USE ONLY !!!' 1>&2
	cat $BUILD_DIR/default/embed_eventgen.conf >> $BUILD_DIR/default/inputs.conf
	rm $BUILD_DIR/default/embed_eventgen.conf
	# embed eventgen config
	cat $BUILD_DIR/default/eventgen.conf.base >> $BUILD_DIR/default/eventgen.conf
	[ -d $BUILD_DIR/local ] || mkdir $BUILD_DIR/local
	cat $BUILD_DIR/default/eventgen.conf.example >> $BUILD_DIR/local/eventgen.conf
fi

cd $BUILD_DIR_PARENT

# Cleanup
rm -f $DEST_DIR/$APP_DIRNAME.tgz

tar cfz $DEST_DIR/$APP_DIRNAME.tgz $APP_DIRNAME --exclude "$APP_DIRNAME/$APP_DIRNAME.tgz" --exclude "$APP_DIRNAME/bin/output/*" --exclude "$APP_DIRNAME/.*" 
cd $CURRENT_PWD
rm -rf $BUILD_DIR

echo "Build Complete"
