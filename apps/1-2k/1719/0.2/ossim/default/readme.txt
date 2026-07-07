# Splunk App for OSSIM Instances and with Logger support
# More information in www.a3sec.com
# Author: Angel Israel Gutierrez Barreto @a3sec
# version 0.2 2014
# Copyright Creative Commons Commons Reconocimiento-NoComercial-CompartirIgual 3.0 Unported.
#
#
Description:
This APP is for analysis the OSSIM information such as OSSIM System Events and Alarms, providing a new way to explore your data, which are already capturing by your OSSIM Box, this app is intented to install in OSSIM Boxes using JailBreak function, OSSIM is an OpenSource SIEM, this app allow to explore and expand the intelligence of the collection of data through OSSIM, and provides a comprehensive set of dashboards, data models and searches to help the managment of your OSSIM Box. offer the posibility to increase your security intelligence process and helps the fine tunning of your OSSIM box.

Required Apps:
Sideview Utils: http://apps.splunk.com/app/466/
Splunk WebFramework Toolkit: http://apps.splunk.com/app/1613/
timewrap:  http://apps.splunk.com/app/1645/


Prerequisites:
OSSIM Ver 4.x Installation, this app mus be on your OSSIM instalation

Configuration: 

There is two methods for obtain Information as Events or Alarms from OSSIM (Syslog - Action )
-----------------
First Syslog
Configuration - Deployment - Components - Server (Selec yoyur server)
Alarms to Syslog *   -- Select Yes
Now all the alarms will be forwarded to the local syslog
We  can create a Filter in Syslog to Moving the Log to another prefered location
The Alarm syslog messages contain the word "Alienvault:" so we can create a filter in /etc/rsyslog.conf with the next statement:
	if $rawmsg contains 'Alienvault:' then -/var/log/ossim_alarms.log
	#Stop processing the message after it was written to the log
	& ~
Restart the rsyslog service "/etc/init.d/rsyslog restart"
And now we are moving all the logs from the Alarms to "/var/log/ossim_alarms.log" which will be the location for the datainput in the Splunk APP
* Note if you change the destination file you need to change the value in Ossim APP on the  Splunk page
-----------------------
Second Action
Other way to export data to a file with OSSIM are the actions, actions allow to do some stuff when an event do match with the conditions described in policies
a Simple script was provided with the app in "/opt/splunk/etc/apps/ossim/bin/actionlog.sh" you could used in your actions when create an action, select in type: "Excute an external program"
On the command Option you could write something like this:

/opt/splunk/etc/apps/ossim/bin/./actionlog.sh ""'"FECHA=DATE ALARMA=SID_NAME RIESGO=RISK SRCIP=SRC_IP:SRC_PORT DSTIP=DST_IP:DST_PORT NOMBRESRC=SRC_IP_HOSTNAME NOMBREDST=DST_IP_HOSTNAME SEN=SENSOR ID=PLUGIN_ID SID=PLUGIN_SID EVID=EVENT_ID USER=USERNAME PASS=PASSWORD DATA1=USERDATA1 DATA2=USERDATA2 DATA3=USERDATA3 DATA4=USERDATA4 DATA5=USERDATA5 DATA6=USERDATA6 DATA7=USERDATA7 DATA8=USERDATA8 DATA9=USERDATA9 BACKLOG=BACKLOG_ID"'""

The statment above ejecute the script in the OSSIM APP and passes all the data from the event as a variable to create a log in "/var/log/ossim_action.log"
If you want to change the location of the log, you need to think in the script file and the Data Input on Splunk
-----------------------


Consider LogRotation for your new logs sometimes things can be bigger, in a OSSIM Box you can add Logrotation statements in /etc/logrotate.d/ as file like ossimapp  a sample of the file was provided in "/opt/splunk/etc/apps/ossim/bin/"

Once we have the correct log fie created and configured, The Ossim APP for Splunk will index all the data and the searches, extractions and reports will work

*Note:
Some Extractions are expecting the format descrive above in the actionlog.sh script, also for the Syslog option we are using Ossim ver4.4


#
#Any Extra Information you can contact ossimappforsplunk@a3sec.mx
#
#
Folowing Releases (To Do)

** More Dashboards for the Alarms
** Translations
** More Intelligence in the Logger
** Combo selectors for time
