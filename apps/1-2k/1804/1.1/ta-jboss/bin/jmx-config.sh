#!/bin/bash

##############################################
#
#  Created by Tomasz Cholewa <tch@linupolska.com>
#  The JMX configurator
#
##############################################

base=$(cd $(dirname $0);pwd)
base="$base/.."

usage() {
cat <<EOF
This script will try to automatically detect your JBoss version and based on that will 
generate inputs.conf configuration for JBoss Add-on.

Usage: $0 [ -u user ] [ -p password ] [ -i host ] [ -w ] [ -h ]

-u user     - user to authenticate as
-p password - password for authentication
-i host     - ip address (or host name) to use for autodetection (localhost by default)
-w          - write configuration directly to local/inputs.conf instead of stdout

EOF

}

args="$*"

while getopts 'u:p:i:hw' opt;do
	case $opt in
		u) userarg="-u $OPTARG" ;;
		p) passarg="-p $OPTARG" ;;
		i) host="$OPTARG" ;;
		w) out="$base/local/inputs.conf" ;;
		h) usage; exit 2 ;;
		*) echo "ERROR: Unknown option $opt" 1>&2; exit 2 ;;
	esac
done

host=${host:-localhost}


shift $((OPTIND-1))
jmxuri="$1"

apphome=$(cd $(dirname $0);pwd)

uris="service:jmx:rmi://$host/jndi/rmi://localhost:9999/jmxrmi service:jmx:remoting-jmx://$host:9999"
# prefer local over default directory when searching for config file
for jmxuri in $uris;do
	echo "INFO: Trying JMX URI - $jmxuri" 1>&2
	if $apphome/jmxstats $userarg $passarg detect "$jmxuri" 1>&2;then
		jmxok="$jmxuri"		
		break
	fi
done
if [ -n "$jmxok" ];then
	echo "INFO: Found JMX interface" 1>&2
	if [ -n "$out" ];then
		echo "INFO: Writing to $out" 1>&2
cat << EOF > $out

[script://./bin/jmxstats $userarg $passarg statistics $jmxuri]
disabled = false
index = jboss
interval = 30
source = jmxstats_${HOSTNAME}
sourcetype = jmxstats

EOF

	else
        echo "INFO: Autodected JMX URI:"
		echo "$jmxok"
        echo
        echo "INFO: Now you can write changes to the config file (inputs.conf)"
        echo "INFO: Please rerun this script with '-w' option to write changes:"
        echo
        echo "$0 $args -w"
        echo
	fi
	exit 0
else
	echo "ERROR: Failed to find jmx uri..." 1>&2
	exit 1
fi

