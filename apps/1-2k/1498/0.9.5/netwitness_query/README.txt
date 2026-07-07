# Splunk/RSA Security Analytics REST API Query scripted input
# Version : 0.9.5
# Date: 05 Jul 2022
#
# written by Rui Ataide <rataide+splunkapps@gmail.com>
# This software is provided "as is" without express or implied warranty or support

 === Splunk for RSA Security Analytics ===

 This Splunk app will connect to a RSA Security Analytics Concentrator/Broker via REST API.
 It will poll the RSA Security Analytics device regularly to collect new session meta data based on the provided query.
 
 To install:
   - Extract to $SPLUNK_HOME/etc/apps/
   - Reconfigure as per below
     -> If deploying on a Splunk Windows a good LAST_MID_FILE value for Windows is LAST_MID_FILE = 'c:\\.last_mid.query'
   - Restart Splunk

 The following Splunk search will provide any relevant error logs for this app:

   index=_* nwsdk_query.py sourcetype="splunkd"

 Make sure the REST interface is enabled on your RSA Security Analytics device.

 To troubleshoot connections to your RSA Security Analytics device use:
   curl -u <user>:<password> "http://<serverip>:50103/sdk?msg=summary&id1=0&id2=0&size=2000&force-content-type=text/plain"

 Configure the following variables in nwsdk_query.conf.
 Make sure you place it in <app>/local/nwsdk_query.conf to avoid overwrite during app upgrades:

   # top_level_url = http://192.168.160.33:50105/

 Authentication is now using Splunk PassAuth capability, in order to configure credentials go to "Manage Apps" > "netwitness_query" > Setup
 Enter your RSA Security Analytics credentials and click "Save".

 Alternatively the following can still be used in the configuration file as a back if credentials aren't passed through from Splunk. This
 is to maintain backwards compatibility.

   # username = admin
   # password = netwitness

 The TOP_LEVEL_URL is the URL to access your RSA Security Analytics device REST interface,
 the other two variables are self-explanatory.

   # query = select * where service=0
 
 The NW_QUERY parameter selects what data should be imported from the NextGen deployment.
 You can specify only one query per configuration file but you can use different files and configure mutliple inputs.
 If you need to configure multiple inputs used different configuration files and pass them as an argument.

 The following options can be left as they are on most *nix & Mac OS X systems,
 but you can also reconfigure them for your environment:
   # last_mid_file = /tmp/.last_id.OTHER

 If you use multiple configurations each will require a different LAST_MID_FILE for each.
 
 == HASHING ==
 
 For privacy and compliance reasons any key can now be replaced by its MD5 cryptographic hash value (e.g. cc.number).
 A new section [hashing] was created for this. In it add your hash mappings in the format: <nw meta name>=<prefix splunk field name>,<prefix length>
 if no prefix necessary use length 0 and any random prefix name both values are required. See example below:

   [hashing]
   cc.number=cc_bin,6

 The above example will replace credit card numbers with their corresponding MD5 hash and will extract the credit card first 6 digits (BIN) to a new field
 named cc_bin. 

 == ADDITIONAL MAPPINGS ==

 If you would like to add your own mappings for RSA Security Analytics meta data to Splunk fields or change the default map for your environment. 
 Create a new section [mappings] on your copy of nwsdk.conf and add as many mappings as required, one per line in the form of
 <nw meta name>=<splunk field name> as per example below.

   # Additional mappings should be added below in the form of <nw meta name>=<splunk field name>
   [mappings]
   crypto=cipher
   ma.flag=malware_flag
   tld=top_level_domain

 == OTHER CONFIG OPTIONS ==

   # If app falls too far behind skip to the end of the NWDB immediately (time in seconds behind, -1 disables)
   skip_older_than = -1
   # Logging Destination (use "stderr" or logfile full path) e.g. /opt/splunk/var/log/splunk/nwsdk_query.log
   logging=stderr 
