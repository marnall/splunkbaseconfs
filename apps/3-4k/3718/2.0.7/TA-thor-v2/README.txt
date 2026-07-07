# 
# THOR - Splunk Add-on
#
# Florian Roth, November 2017
# This App provides advanced analysis of THOR APT Scanner Events

The THOR App is the visual counterpart to the THOR Add-on. It provides general dashboards, special filtered views and a lot of reports to analyze and visualize THOR and SPARK log data. 
In order to use the indexed data, you have to install the THOR Add-on.

=== Log Input

You could use the input provided by the Add-on, which is on port 514/udp by default. Syslog input on any port is supported. You can also index the THOR text log files written by THOR during the scan. 

Always choose "thor" as sourcetype and make sure that the index that holds the THOR data is searched by default (Settings > Access Control > Roles > 'user' > Indexes search by default) to make the results show up in the App.

=== Index

The newest versions of this Add-on will not create an index but allows you to define your own index for the log data. The THOR events will now be selectable via their sourcetype "thor" and can be stored in any index. 

Recommendation:
Create an index named "thor" and add this index to the base event type definition (Settings > Event Types > "thor_events")
sourcetype=thor AND index=thor

=== Event Type

All searches and dashboards work with the "thor_events" event type. Adjust the event type to select a different data set for the App. 

For example: 
If you have collected THOR reports from a certain unit and want to inlcude only these reports in the App, you could edit the event type via "Settings > Event Types" and change the event type to somthing like

```source=/var/log/thor_logs_from_unit_x/*```

=== False Positives

Define false positives via "Settings > Tags" and edit the "false_positives" tag to add more false positive expressions.

=== Executing THOR via Forwarder

You can use the Add-on to schedule and run THOR on the end systems that run a splunk universal forwarder or heavy forwarder. See the binaries, config files and scripts in the ./bin folder.

Steps to make the remote execution work:
1. Copy the Add-on into the $SPLUNK_HOME/etc/deployment-apps folder
2. Rename the template files in ./bin by removing the ".sample" suffix
3. Copy the inputs.conf into a new ./local folder and set the scripted input "disabled = False"
4. Copy the program directory of THOR into the ./bin/thor sub folder (see the README.txt in that folder for details)
5. Adjust 'sourcetype' and 'index' in ./local/inputs.conf
6. Adjust the schedule in ./bin/scheduler.csv
7. Deploy the Add-on

=== Contact

Main developer
Florian Roth
Nextron Systems GmbH

Email:
support@nextron-systems.com
