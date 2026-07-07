#!/usr/bin/python
'''
This script to check status of specified service
Arguments: service_name
Author: Basant Kumar, GSLab
'''

#Import from standard libraries
import commands
import time
import datetime
import os
import sys

#Variable declaration
status = 'unrecognized service'
ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

#Select tool to get service status details
command_check_code, command_check_output = commands.getstatusoutput("command -v systemctl")
if command_check_code == 0:
	service_status_command_code, service_status_command_output = commands.getstatusoutput(command_check_output+" is-active "+str(sys.argv[1]))
	if service_status_command_code == 0 and 'active' in service_status_command_output:
		status = 'running'
		code = 0
	else:
		status = 'stopped'
		code = 1
else:
	service_status_command_code, service_status_command_output = commands.getstatusoutput("/usr/sbin/service "+str(sys.argv[1])+" status")
	ps_command_code, ps_command_output = commands.getstatusoutput("ps -A")
	if sys.argv[1] in ps_command_output or 'running' in service_status_command_output:
	        status = 'running'
	        code = 0   
	else:
	        status = 'stopped'
	        code = 1
print "timestamp="+st+",service_name=\""+str(sys.argv[1])+"\",error_code=\""+str(code)+"\",service_status=\""+status+"\""
