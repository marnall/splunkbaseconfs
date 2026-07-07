#!/usr/bin/python
'''
This script to check status of specified service
Arguments: None
Author: Basant Kumar, GSLab
'''

#Import from standard libraries
import commands
import time
import datetime
import re
import os

#Variable declaration
ts = time.time()
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

#Execute command to get Disk Usage details
code, output = commands.getstatusoutput("df -hT /")
output_list = filter(None, output.replace('/','').split('\n')[1].split(' '))
total_disk = output_list[2].replace('G','')
used_disk = output_list[3].replace('G','')
free_disk = output_list[4].replace('G','')
used_disk_perc = (float(used_disk)/float(total_disk))*100
free_disk_perc = 100 - used_disk_perc
log_string =  "timestamp="+st+",total_disk=\""+total_disk+"\",used_disk=\""+used_disk+"\",free_disk=\""+str(free_disk)+"\",free_disk_perc=\""+str(round(free_disk_perc,2))+"\",used_disk_perc=\""+str(round(used_disk_perc,2))+"\""

#Execute command to get RAM Usage details
code, output = commands.getstatusoutput("cat /proc/meminfo")
output_list = output.split('\n')
total_ram = output_list[0].replace('MemTotal:','').replace('kB','').replace(' ','')
free_ram = output_list[1].replace('MemFree:','').replace('kB','').replace(' ','')
used_ram = int(total_ram) - int(free_ram)
used_ram_perc = (float(used_ram)/float(total_ram))*100
free_ram_perc = 100 - used_ram_perc
log_string = log_string + "total_ram=\""+str(total_ram)+"\",used_ram=\""+str(used_ram)+"\",free_ram=\""+str(free_ram)+"\",free_ram_perc=\""+str(round(free_ram_perc,2))+"\",used_ram_perc=\""+str(round(used_ram_perc,2))+"\""

#Execute command to get user, load, etc details
load_string = ''
code, output = commands.getstatusoutput("w")
output = output.split('\n')
matchObj = re.match( r'(.*)up', output[0].replace(' ','').split(',')[0], re.M|re.I)
uptime = output[0].replace(' ','').split(',')[0].replace(matchObj.group(0),'')


users = output[0].replace(' ','').split(',')[1].replace('user','').replace('s','')
load_list = output[0].replace(' ','').split(',')[2:]
index = 0
for load_value in load_list:
	load_string=load_string + "load"+str(index)+"=\""+load_value+"\","
	index = index + 1
load_string = load_string.replace('loadaverage:',"")
log_string = log_string + "uptime=\""+str(uptime)+"\",users=\""+users+"\","+load_string

#Execute command to get CPU Usage details
code, output = commands.getstatusoutput("top -b -n1 | grep Cpu")
output_list = output.split(',')
free_cpu = output_list[3].replace(' ','').replace('%id','').replace('id','')
used_cpu = 100-float(free_cpu)
log_string = log_string + "used_cpu=\""+str(used_cpu)+"\",free_cpu=\""+str(free_cpu)+"\""

#Print console line with system status information
print log_string
