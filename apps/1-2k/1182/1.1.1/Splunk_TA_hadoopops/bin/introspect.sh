#!/bin/bash

# 
# this script is run once by the Splunk_TA_hadoopops app
# it looks at the ps output on the running host
# and finds the log file to be monitored based on java command line properties
# mainly hadoop.log,dir and hadoop.log.file
#

REQUIRED_CONFIG_ELEMENTS="HADOOP_LOG_DIR HADOOP_HOME_DIR HADOOP_CONF_DIR"
REQUIRED_METRICS_ELEMENTS="NAMENODE JOBTRACKER TASKTRACKER DATANODE"

read AUTH_TOKEN
SPLUNK_TOK=$AUTH_TOKEN  # magic env variable - thanks Amrit
export SPLUNK_TOK

PS_GREP_PATTERN='-Dhadoop'
PS_LOGDIR_PROP='-Dhadoop.log.dir'
PS_LOGFILE_PROP='-Dhadoop.log.file'

PS_DMN_PATTERN='-Dproc_'

PS_NN_PATTERN='-Dproc_namenode'
PS_SNN_PATTERN='-Dproc_secondarynamenode'
PS_JT_PATTERN='-Dproc_jobtracker'
PS_DN_PATTERN='-Dproc_datanode'
PS_TT_PATTERN='-Dproc_tasktracker'
PS_BLNCR_PATTERN='-Dproc_balancer'

PS_JT_GREP_PATTERN='-Dproc_jobtracker'
SED_STRIP_PREFIX='s/-D//'
SED_STRIP_RELDIRS='s/\/[a-zA-Z0-9_-]*\/\.\.//g'
AWK_MAKE_VAR_EVAL='{upper=toupper($1); gsub("[.]","_",upper) ;print upper"=\""$2"\""}'
AWK_JAVA_PROP_VALUE='{print $2}'
REQUIRED_CONFIG_MATCH=$( echo $REQUIRED_CONFIG_ELEMENTS | awk '{gsub("  *" , "|"); print "("$0")"}')

declare -a hadoop_vars=()
declare -a hadoop_metrics=()
declare -a monitor_files=()

_SUCCESS=1
_SCRIPT_DIR=$(dirname $0)
_SCRIPT_NAME=$(basename $0)
_INTROSPECT_FILE=${_SCRIPT_DIR}/.${_SCRIPT_NAME%.sh}
_MONITOR_JT_FILE=${0%.sh}.jt.inputs
_MONITOR_TT_FILE=${0%.sh}.tt.inputs

function append_hadoop_vars() {
  if [[ -n $1 ]]
  then
    eval export $1
    if [[ ${#hadoop_vars[@]} == "0" ]]
    then 
      hadoop_vars=("$1")
    else
      hadoop_vars=("${hadoop_vars[@]}" "$1")
    fi
  fi
}

function append_hadoop_metrics() {
  if [[ -n $1 ]]
  then
    eval export $1
    if [[ ${#hadoop_metrics[@]} == "0" ]]
    then 
      hadoop_metrics=("$1")
    else
      hadoop_metrics=("${hadoop_metrics[@]}" "$1")
    fi
  fi
}

function get_daemon_log_filepath() {
  local FILEPATH=
  for token in $(ps -ef | grep -- "-Dproc_$1" )
  do
    logdir=$( \
      echo $token |  grep -- $PS_LOGDIR_PROP | \
      sed -e $SED_STRIP_PREFIX -e $SED_STRIP_RELDIRS | \
      awk -F= "$AWK_JAVA_PROP_VALUE"  )
    logfile=$( \
      echo $token |  grep -- $PS_LOGFILE_PROP | \
      sed -e $SED_STRIP_PREFIX -e $SED_STRIP_RELDIRS | \
      awk -F= "$AWK_JAVA_PROP_VALUE" | sed  's/.log/*/g' )
    if [[ -n $logdir ]]
    then
      FILEPATH=$logdir
    fi
    if [[ -n $logfile ]]
    then 
     FILEPATH="$FILEPATH/$logfile"
    fi
  done
  echo $FILEPATH # return full filepath
}

function create_monitor_endpoint_disabled() {
  app_name=Splunk_TA_hadoopops
  rest_monitor=/servicesNS/nobody/$app_name/data/inputs/monitor
  rest_config=/servicesNS/nobody/$app_name/admin/conf-inputs/monitor%3A%252F%252F
  rest_config2=/servicesNS/nobody/$app_name/admin/conf-inputs
  res=$(echo $AUTH_TOKEN | $SPLUNK_HOME/bin/splunk _internal call $rest_monitor $1 -post:disabled) # create the monitor endpoint
  res=$(echo $AUTH_TOKEN | $SPLUNK_HOME/bin/splunk _internal call $rest_monitor/$2/disable -method POST) # disable it
  res=$(echo $AUTH_TOKEN | $SPLUNK_HOME/bin/splunk _internal call $rest_config2/_reload -method POST) # disable it
  res=$(echo $AUTH_TOKEN | $SPLUNK_HOME/bin/splunk _internal call $rest_config$2 -post:index $3) # configure the index
  res=$(echo $AUTH_TOKEN | $SPLUNK_HOME/bin/splunk _internal call $rest_config2/_reload -method POST) # disable it
  # not checking REST output values now
}

function parse_create_monitor_endpoint_disabled() {
  post=$( eval echo "$1"  | awk -F, '{for(i=1; i<=NF; i++ ) if(match($i,"name=|sourcetype=|blacklist=")) { sub("^","-post:",$i);  sub("="," ",$i);printf("%s ", $i) } ; printf "\n"}')
  index=$( eval  echo "$1" | awk -F, '{for(i=1; i<=NF; i++ ) if(match($i,"index=")) { sub("index=","",$i);printf("%s ", $i) } ; printf "\n"}')
  name=$( eval echo "$1" | awk -F, '{for(i=1; i<=NF; i++ ) if(match($i,"name=")) { sub("name=","",$i);printf("%s ", $i) } ; printf "\n"}')
  url_name=$( echo $name | sed -e 's/\//%252F/g' -e 's/\*/%2A/g' -e 's/  *$//')
  create_monitor_endpoint_disabled "$post" $url_name $index
  echo $name
}

# given a monitor input, enable it
function enable_monitor_input()
{
    app_name=Splunk_TA_hadoopops
    enable_response=`echo $AUTH_TOKEN | $SPLUNK_HOME/bin/splunk _internal call /servicesNS/nobody/$app_name/data/inputs/monitor/$1/enable -method POST`
} 

# sets the scripted input list in $output
function get_script_list
{
    echo `$SPLUNK_HOME/bin/splunk list exec`
}

# build a command name suitable for use in a REST target
function build_scripted_input_endpoint()
{
    temp=`echo $1 | awk -F"/" '{print $NF}'`
    echo ".%252Fbin%252F"$temp
}

# given a script name, enable it
function enable_scripted_input()
{
    app_name=Splunk_TA_hadoopops
    enable_response=`echo $AUTH_TOKEN | $SPLUNK_HOME/bin/splunk _internal call /servicesNS/nobody/$app_name/data/inputs/script/$1/enable -method POST`
}

# build a path name suitable for use in a REST target
function build_monitor_input_endpoint()
{
    echo `echo $1 |  sed -e 's/\//%252F/g'`
}

# enables all endpoints
function enable_all_inputs
{
    oldIFS=$IFS
    IFS='
    '
    script_list=$(get_script_list)
    for line in $script_list; do
        case "$line" in 
           *hadoopmonitorfwd* | *Splunk_TA_hadoopops* )  input_endpoint=$(build_scripted_input_endpoint "$line"); enable_scripted_input $input_endpoint;;
        esac
    done
    set -f
    for line in $MONITOR_INPUTS; do
	input_endpoint=$(build_monitor_input_endpoint $line)
        enable_monitor_input $input_endpoint
    done
    set +f
    IFS=$oldIFS
}

#---------------------------------------------------------------------------#
for token in $(ps -ef | grep -- $PS_GREP_PATTERN )
do
  #
  # filter for -Dhadoop.*.* entries from the command line
  # then strip out the -D prefix and replace the relative directories
  # with absolute paths. Finally generate variable creation statements
  # that we can pass to eval. The result is that we should have
  # local variables for HADOOP_LOG_DIR, HADOOP_CONF_DIR
  #
  item=$( \
    echo $token |  grep -- $PS_GREP_PATTERN | \
    sed -e $SED_STRIP_PREFIX -e $SED_STRIP_RELDIRS | \
    awk -F= "$AWK_MAKE_VAR_EVAL" | egrep "$REQUIRED_CONFIG_MATCH" )
  append_hadoop_vars $item
done

export HADOOP_CONF_DIR=$HADOOP_HOME_DIR/conf
append_hadoop_vars "HADOOP_CONF_DIR=$HADOOP_CONF_DIR"

if [[ ! -d $HADOOP_CONF_DIR ]]
then
  _SUCCESS=0
fi

# find the metric file locations from the properties file
for file in $(grep -h metrics   $HADOOP_CONF_DIR/*.properties   | grep -i filename | grep -v "^#" ) 
do
  SED_DOT_DIR='.\/'
  SED_LOG_DIR=$(echo $HADOOP_LOG_DIR | sed 's/\//\\\//g')
  item=$(echo $file |  awk -F= '{ split($1,a,"[.]") ; print "HADOOP_METRICS_"toupper(a[1])"="$2}' | eval sed 's/=${SED_DOT_DIR}/=${SED_LOG_DIR}/' ) 
  append_hadoop_metrics $item
done

#---------------------------------------------------------------------------#
for el in $REQUIRED_CONFIG_ELEMENTS
do
  item=$(eval echo \$${el})

  if [[ ! -d $item ]]
  then
    _SUCCESS=0
  fi
done
#---------------------------------------------------------------------------#

#---------------------------------------------------------------------------#
for el in $REQUIRED_METRICS_ELEMENTS
do
  item=$(eval echo \$HADOOP_METRICS_${el})

  if [[ -z $item ]]
  then
    _SUCCESS=0
  fi
done
#---------------------------------------------------------------------------#

#
# REST endpoints are created only once 
# but the .introspect file can be removed (and local/inputs.conf) and
# introspect run again
#
if [[ ! -f $_INTROSPECT_FILE ]]
then
  set -f
  #
  # create conf file endpoint
  #
  name="$HADOOP_CONF_DIR/*.xml"
  post="-post:name $name  -post:sourcetype hadoop_global_conf -post:crc-salt <SOURCE>"
  index=hadoopmon_configs
  url_name=$( echo $name | sed -e 's/\//%252F/g' -e 's/\*/%2A/g' -e 's/  *$//')
  MONITOR_INPUTS="$MONITOR_INPUTS $name" 
  create_monitor_endpoint_disabled "$post" $url_name $index
  #
  # create metric file endpionts
  #
  for item in ${hadoop_metrics[@]}
  do
    echo  $item >> $_INTROSPECT_FILE
    name=$(echo $item | awk -F= '{print $2}')
    # all metrics files will not be on all nodes
    if [[ -f $name ]]
    then
      post="-post:name $name  -post:sourcetype hadoop_metrics"
      index=hadoopmon_metrics
      url_name=$( echo $name | sed -e 's/\//%252F/g' -e 's/\*/%2A/g' -e 's/  *$//')
      MONITOR_INPUTS="$MONITOR_INPUTS $name" 
      create_monitor_endpoint_disabled "$post" $url_name $index
    fi
  done
  #
  # create daemon log endpoints conditionally 
  # some hardcoding (index and sourcetype) compared to previous version
  # but the fileame and dir are exact now and can vary by each daemon
  #
  for daemon in namenode jobtracker datanode secondarynamenode balancer tasktracker
  do
    filepath=$(get_daemon_log_filepath $daemon)
    if [[ -n $filepath ]]
    then
      post="-post:name $filepath  -post:sourcetype hadoop_$daemon"
      index=hadoopmon_logs
      url_name=$( echo $filepath | sed -e 's/\//%252F/g' -e 's/\*/%2A/g' -e 's/  *$//')
      MONITOR_INPUTS="$MONITOR_INPUTS $filepath" 
      create_monitor_endpoint_disabled "$post" $url_name $index
      if [[ $daemon == "jobtracker" ]] 
      then
        #
        # create all jobtracker related endpoints because this node is running jobtracker
        # these endpoints are relative to the jobtracker log dir and so can templated in introspect,inputs
        #
        dir=$(echo $filepath | sed 's#\(.*\)/.*#\1#')
        HADOOP_JTLOG_DIR=$dir
        values=$( cat $_MONITOR_JT_FILE )
        for input in $values
        do
          name=$(parse_create_monitor_endpoint_disabled $input)
          MONITOR_INPUTS="$MONITOR_INPUTS $name" 
        done
      fi
      if [[ $daemon == "tasktracker" ]]
      then
        dir=$(echo $filepath | sed 's#\(.*\)/.*#\1#')
        HADOOP_TTLOG_DIR=$dir
        values=$( cat $_MONITOR_TT_FILE )
        for input in $values
        do
          name=$(parse_create_monitor_endpoint_disabled $input)
          MONITOR_INPUTS="$MONITOR_INPUTS $name" 
        done
      fi
    fi
  done
  #
  # update MONITOR_INPUTS variable with all the endpoints so setup script can find and manage them 
  #
  MONITOR_INPUTS=$(echo $MONITOR_INPUTS | sed 's/^  *//') 
  echo "MONITOR_INPUTS=\"$MONITOR_INPUTS\"" >> $_INTROSPECT_FILE
  # HADOOP-743
  # enable_all_inputs

  set +f
fi
#  ---- EOF ---- #
