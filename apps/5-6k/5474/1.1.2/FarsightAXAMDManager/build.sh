#!/usr/bin/env sh
# Copyright (c) 2017 by Farsight Security, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Configuration Items
PACKAGE_NAME="SA-FarsightSentryManager"
BUILD_DIR=/tmp
CURRENT_PWD=`pwd`

# Get my current git tag
GIT_TAG=`git describe --tags`

# Name the package
SPL_OUTPUT=$CURRENT_PWD/$PACKAGE_NAME-$GIT_TAG.spl

# Setup the build location.
BUILD_DIR_SRC=$BUILD_DIR/$PACKAGE_NAME
rm -rf $BUILD_DIR_SRC
mkdir -p $BUILD_DIR_SRC

# Copy the files we want in the package.

rsync -av --progress --exclude=.git --exclude=build.sh --exclude=gitignore --exclude=*.spl $CURRENT_PWD/* $BUILD_DIR_SRC


cd $BUILD_DIR
tar cvfz $SPL_OUTPUT $PACKAGE_NAME
cd $CURRENT_PWD
rm -rf $BUILD_SRC

echo "Build Complete"
echo "SPL file location: $SPL_OUTPUT"
