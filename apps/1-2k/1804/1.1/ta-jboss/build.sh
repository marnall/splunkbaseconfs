#!/bin/bash

# set destination dir
APP_DIRNAME="ta-jboss"

usage() {

cat << EOF
Usage: $0 [ -h ] [ -d DIR ]"

-h - print this help message
-d DIR - destination directory for package (defeault = .)
	
EOF
}

while getopts "hed:" opt;do
	case $opt in
		h) usage; exit;;
		d) DEST_DIR=$OPTARG;;
	esac
done
[ -n "$DEST_DIR" ] || DEST_DIR=.

# Save for later
CURRENT_PWD=`pwd`


# Cleanup
rm -f $DEST_DIR/$APP_DIRNAME.tgz

# Create a build directory that we can use
BUILD_DIR=.build/$APP_DIRNAME
BUILD_DIR_PARENT=.build
mkdir -p $BUILD_DIR

cp -R * $BUILD_DIR
[ -d $BUILD_DIR/local ] && rm $BUILD_DIR/local/*

cd $BUILD_DIR_PARENT

tar cfz $DEST_DIR/$APP_DIRNAME.tgz $APP_DIRNAME --exclude "$APP_DIRNAME/$APP_DIRNAME.tgz" --exclude "$APP_DIRNAME/bin/output/*" --exclude "$APP_DIRNAME/.*" 
cd $CURRENT_PWD
rm -rf $BUILD_DIR

echo "Build Complete"
