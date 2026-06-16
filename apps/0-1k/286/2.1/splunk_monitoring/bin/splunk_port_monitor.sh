# Splunk Port Monitor
# splunk_port_monitor.sh
#
# Due to the use of the $SPLUNK_HOME variable, you
# must either run this script using Splunk or set your
# Splunk environment in advance using the setSplunkEnv
# script.
#
# If you have set Splunk to run on a port other than
# the default port 8089, then you will need to set the
# port variable below to the alternate port.
#
# You will need to have nmap installed for this script
# to work properly.  Please change the nmap variable
# below to the correct path of your nmap executable.
#
# You will need to add your own host information to
# the tags.conf file with each host having a single
# entry.  It does not matter what the alias is, but
# note that multiple entries means multiple monitors.
# 
#/bin/bash

# VARIABLES
port="8089";
nmap="/usr/bin/nmap";
tag_file="$SPLUNK_HOME/etc/system/local/tags.conf";
#tag_file="$SPLUNK_HOME/etc/apps/splunk_monitoring/local/tags.conf";

# If the tags.conf file exists and is readable
if [ -r $tag_file ]; then
	# Get all host names in the file
	hosts=`grep "host=" $tag_file | cut -d= -f 2 | cut -d] -f 1`;
else
	# Return an empty list of hosts
	hosts="";
fi

# If the nmap command exists
if [ -x $nmap ]; then

	# For each hostname found in the tags.conf file
	for host in $hosts
	do

        	# Run Port Test
        	test=`$nmap -p $port $host | grep -c open`;

        	# If the port is open
        	if [ $test == 1 ]; then
                	status="$host:UP";
        	fi

        	# If the port is closed
        	if [ $test == 0 ]; then
                	status="$host:DOWN";
        	fi

        	# If other
        	if [ $test != 0 ] && [ $test != 1 ]; then
                	status="$host:UNKNOWN";
        	fi

        	echo $status; 
	done
fi
