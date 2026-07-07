################################################
###             NECROMANCER V2               ###
################################################
###         Created by Blake Putnam          ###
################################################
###    Email: SplunkSecDevOps@Gmail.com      ###
################################################
###       Please email for any concern!      ###
################################################
https://www.linkedin.com/in/blake-putnam-319451103/


################################################
Overview:


Necromancer has two scripts available one for systemd
And one for init.d based hosts. Systemd version assumes
Splunk user is has access to run systemctl commands.
Init.d version assumes Splunk user has access to start
splunkd without the need for sudo. Both scripts can be
edited to include sudo where needed. In "misc" folder 
you will find both versions- select the one you need 
and copy/ vi into necromancer.sh . Cron schedules are
defined in hexxed.sh located in bin folder. Default 
for necromancer.sh health check is every 15m. The 
default for cryptkeeper.sh is every day at 0300. This
is to avoid any health check output being written to 
necromancer.log  


################################################
Scripts:

1) The below scripts should have ownership of common
Splunk user "IE: chown splunk:splunk hexxed.sh" 

2) Scripts should be executable before EVER being deployed
IE: chmod a+x hexxed.sh

3) All scripts and location

necromancer/bin/hexxed.sh
necromancer/necromancer.sh
necromancer/cryptkeeper.sh 

################################################
Deployment: 

Rename "DEPLOYMENT - necromancer" to only "necromancer" and move to 
$SPLUNK_HOME/etc/deployment-apps . Recommended to create
"necromancer" serverclass for systemd and init where needed. Necromancer
is written for index cluster and searched cluster also.  


###############################################
Dependancies:

Necromancer script assumes $SPLUNK_HOME = /opt/splunk*

Index must be created and named "necro"

Splunk user has access to /etc/cron.allow to write cron schedules



################################################
Macros:

There are several Macro's that support the dash-
board. The list of Macros is as follows.

ritual_count
ritual_events
ritual_events_info
ritual_performed
ritual_performed_info
top10_ritual_performed
top10_ritual_performed_info

################################################
Dashboards:

There is one Dashboard for Necromancer App. 
Necromancer Overview.


################################################
Alerts:

Necromancer comes prepackaged with an Alert, however you need 
to edit the email to be notified. 


###############################################
Fields, Source, SourceType:

1) Fields
- status
- result
- action
- script
- summon

2) Source
- necro:*

3) Sourcetype
- necro:*

