#!/bin/bash

#---------------------------------------------------------------------------#

PS_GREP_PATTERN='-Dhadoop'
SED_STRIP_PREFIX='s/-D//'
SED_STRIP_RELDIRS='s/\/[a-zA-Z0-9_-]*\/\.\.//g'
AWK_MAKE_VAR_EVAL='{upper=toupper($1); gsub("[.]","_",upper) ;print upper"=\""$2"\""}'

REQUIRED_CONFIG_ELEMENTS="HADOOP_LOG_DIR HADOOP_HOME_DIR HADOOP_CONF_DIR"
REQUIRED_METRICS_ELEMENTS="NAMENODE JOBTRACKER TASKTRACKER DATANODE"

#---------------------------------------------------------------------------#
for token in $(cat sveserv52-vm1.ps )
do
  # filter for -Dhadoop.*.* entries from the command line
  # then strip out the -D prefix and replace the relative directories
  # with absolute paths. Finally generate variable creation statements
  # that we can pass to eval. The result is that we should have
  # local variables for HADOOP_LOG_DIR, HADOOP_CONF_DIR
  HADOOP_VARS=$( \
    echo $token |  grep -- $PS_GREP_PATTERN | \
    sed -e $SED_STRIP_PREFIX -e $SED_STRIP_RELDIRS | \
    awk -F= "$AWK_MAKE_VAR_EVAL")

  if [[ -n $HADOOP_VARS ]]
  then
    eval export $HADOOP_VARS
  fi
done

export HADOOP_CONF_DIR=$HADOOP_HOME_DIR/conf

for file in $(grep -h metrics   $(find $HADOOP_CONF_DIR -type f -print )  | grep sink  | grep filename | grep -v "^#" ) 
do
  SED_DOT_DIR='.\/'
  SED_LOG_DIR=$(echo $HADOOP_LOG_DIR | sed 's/\//\\\//g')
  HADOOP_VARS=$(echo $file |  awk -F= '{ split($1,a,"[.]") ; print toupper(a[1])"="$2}' | eval sed 's/=${SED_DOT_DIR}/=${SED_LOG_DIR}/' ) 
 
  if [[ -n $HADOOP_VARS ]]
  then
    eval export $HADOOP_VARS 
  fi
done

#---------------------------------------------------------------------------#
for el in $REQUIRED_CONFIG_ELEMENTS
do
  item=$(eval echo \$${el})

  if [[ ! -d $item ]]
  then
     echo "Unable to find $el: $item"
     exit 1
  else
     echo "found config $el: $item"
  fi
done
#---------------------------------------------------------------------------#


#---------------------------------------------------------------------------#
for el in $REQUIRED_METRICS_ELEMENTS
do
  item=$(eval echo \$${el})

  if [[ -z $item ]]
  then
     echo "Unable to find required metric sink: : $el"
     exit 1
  else
     echo "found metric sink: $el : $item"
  fi
done
#---------------------------------------------------------------------------#