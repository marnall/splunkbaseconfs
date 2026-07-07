#!/bin/bash
#Script to execute python script
#Arguments: $1 = python script file name, $2 = argument to script
#Author: Basant Kumar, GSLab
unset PYTHONPATH
unset LD_LIBRARY_PATH
BASEDIR=$(dirname $0)
./$BASEDIR/$1 $2
