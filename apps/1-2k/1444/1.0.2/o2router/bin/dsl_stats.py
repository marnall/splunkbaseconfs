# Splunk for O2 Wireless box
# Version : 1.0.2
# Date: 02 Apr 2013
#
# written by Rui Ataide
# This software is provided "as is" without express or implied warranty or support
#
import sys
import telnetlib
import re
import time

def str_convert(s):
    if re.search('[\s+=]',s):
       return('"'+s+'"')
    return(s)

try:
    # read configuration from o2router.conf in the app/default or app/local directory
    from splunk.clilib.cli_common import getMergedConf
    HOST = getMergedConf('o2router')['o2router']['host']
    USER = getMergedConf('o2router')['o2router']['username'] + '\r'
    PASSWORD = getMergedConf('o2router')['o2router']['password'] + '\r'
except:
    # If any of the above fails all settings will be taken from here, might convert to one by one check
    # Change the settings below to your environment
    # -- Configuration Settings start --
    HOST = "192.168.1.254"
    USER = "SuperUser\r"
    PASSWORD = "O2Br0ad64nd\r"

COMMAND = ":xdsl info expand=enabled\r"

tn = telnetlib.Telnet(HOST)

s = tn.read_until("Username : ")
tn.write(USER)
s = tn.read_until("Password : ")
tn.write(PASSWORD)
s = tn.read_until("{SuperUser}=>")
tn.write(COMMAND)
tn.write("exit\r")

out = tn.read_all()
lines = [x for x in re.split(r"\n+", out)]
list = []
for line in lines:
    fields=re.match('\s*Modem state:\s+(.*).',line)
    if fields :
       list.append('modem_state='+str_convert(fields.group(1)))
    fields=re.match('\s+Up time \(Days hh:mm:ss\):\s+(.*).',line)
    if fields :
       list.append('up_time='+str_convert(fields.group(1)))
    fields=re.match('\s+xDSL Standard:\s+(.*).',line)
    if fields :
       list.append('xdsl_standard='+str_convert(fields.group(1)))
    fields=re.match('\s+xDSL Annex:\s+(.*).',line)
    if fields :
       list.append('xdsl_annex='+str_convert(fields.group(1)))
    fields=re.match('\s+Channel Mode:\s+(.*).',line)
    if fields :
       list.append('channel_mode='+str_convert(fields.group(1)))
    fields=re.match('\s+Number of reset:\s+(.*).',line)
    if fields :
       list.append('number_reset='+str_convert(fields.group(1)))
    fields=re.match('\s+Payload rate \[Kbps\]:\s+(\S+)\s+(\S+)\s+',line)
    if fields :
       list.append('downstream_speed='+str_convert(fields.group(1)+' Kbps'))
       list.append('upstream_speed='+str_convert(fields.group(2)+' Kbps'))
    fields=re.match('\s+Attenuation \[dB\]:\s+(\S+)\s+(\S+)\s+',line)
    if fields :
       list.append('downstream_attenuation='+str_convert(fields.group(1)+' dB'))
       list.append('upstream_attenuation='+str_convert(fields.group(2)+' dB'))
    fields=re.match('\s+Margins \[dB\]:\s+(\S+)\s+(\S+)\s+',line)
    if fields :
       list.append('downstream_SNR='+str_convert(fields.group(1)+' dB'))
       list.append('upstream_SNR='+str_convert(fields.group(2)+' dB'))
    fields=re.match('\s+Output power \[dBm\]:\s+(\S+)\s+(\S+)\s+',line)
    if fields :
       list.append('downstream_output_power='+str_convert(fields.group(1)+' dBm'))
       list.append('upstream_output_power='+str_convert(fields.group(2)+' dBm'))

event = time.strftime("%Y-%b-%d %H:%M:%S %z") + ' ' + HOST + ' DSL Status:'
for item in list:
    event += ' ' + item
print event

