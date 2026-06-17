# Splunk/NetWitness REST API Session Meta scripted input
# Version : 0.9.8
# Date: 05 Jul 2022
#
# written by Rui Ataide <rataide+splunkapps@gmail.com>
# This software is provided "as is" without express or implied warranty or support

 === Splunk for NetWitness ===

 This Splunk app will connect to a NetWitness Concentrator/Broker via REST API.
 It will poll the NetWitness device regularly to collect new session meta data.
 
 To install:
   - Extract to $SPLUNK_HOME/etc/apps/
   - Reconfigure as per below
     -> If deploying on a Splunk Windows a good LAST_SID_FILE value for Windows is LAST_SID_FILE = 'c:\\.last_sessionid'
   - Restart Splunk

 The following Splunk search will provide any relevant error logs for this app:

   index=_* nwsdk.py sourcetype="splunkd"

 Make sure the REST interface is enabled on your NetWitness device.
 **NOTE: SSL access to the REST interface currently requires the use of a hack**
 Please see http://splunk-base.splunk.com/answers/40255/does-splunk-for-netwitness-support-ssl-access-to-the-rest-api for more details

 To troubleshoot connections to your NetWitness device use:
   curl -u <user>:<password> "http://<serverip>:50103/sdk?msg=summary&id1=0&id2=0&size=2000&force-content-type=text/plain"

 Configure the following variables in nwsdk.conf.
 Make sure you place it in <app>/local/nwsdk.conf to avoid overwrite during app upgrades:

   # TOP_LEVEL_URL = http://192.168.160.33:50105/
   # NW_USERNAME = admin
   # NW_PASSWORD = netwitness

 The TOP_LEVEL_URL is the URL to access your NetWitness device REST interface,
 the other two variables are self-explanatory.

 The following options can be left as they are on most *nix & Mac OS X systems,
 but you can also reconfigure them for your environment:
   # LAST_SID_FILE = /tmp/.last_sessionid
   # NO_SID_FILE_OPTION = -1
   # NO_SID_SECONDS_BACK = 300
 
 Details on these three options are:
   # LAST_SID_FILE is the file containing the last sessionid processed

   # If LAST_SID_FILE file doesn't exist then use NO_SID_FILE_OPTION
   # -2 to start <no_sid_seconds_back> ago
   # -1 to start from highest sessionid in NW DB
   #  0 to start read all available data
   # <any positive integer> to start from that value sessionid

   # NO_SID_SECONDS_BACK is th number of seconds to go back from current time to import new data on first run (default: 5 minutes)

 A fallback configuration still exists on the nwsdk.py script but its use is not recommended, it allows to run stand-alone if needed.

 == ADDITIONAL MAPPINGS ==

 If you would like to add your own mappings for NetWitness meta data to Splunk fields or change the default map for your environment. 
 Create a new section [mappings] on your copy of nwsdk.conf and add as many mappings as required, one per line in the form of
 <nw meta name>=<splunk field name> as per example below.

   # Additional mappings should be added below in the form of <nw meta name>=<splunk field name>
   [mappings]
   crypto=cipher
   ma.flag=malware_flag
   tld=top_level_domain

