#!/bin/bash
########################
# NAME    - UPSC Monitor Script
# VERSION - v0.1
# DATE    - 10/11/2022
# AUTHOR  - SIMON RICHARDSON 
# INFORMATION -
#   Confirmes upsc command is available and then
#   runs upsc binary file along with user specified 
#   name for the UPS we're querying.
#   Data is then exported to Splunk.
########################

# EDITABLE SCRIPT VARIABLES
########################

# UPS NAME (specified in /etc/ups/upsd.conf on RHEL based systems)
UPSNAME="powerwalker"

# MAIN SCRIPT 
########################

if ! [[ $(upsc -l &> /dev/null) ]]; then
	echo "The upsc command failed.  Check upsc command is available!"
	exit
else
	upsc $UPSNAME	
fi
