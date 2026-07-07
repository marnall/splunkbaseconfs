# 
# THOR - Splunk App
#
# Florian Roth, May 2016
# This App provides advanced analysis of THOR APT Scanner Events

The THOR App is the visual counterpart to the THOR Add-on. It provides general dashboards, special filtered views and a lot of reports to analyze and visualize the THOR log data. 
In order to use the indexed data, you have to install the THOR Add-on.

=== Dependencies

It requires the Add-on and the Decrypt app that are also available in Splunkbase. 

THOR Add-on
https://splunkbase.splunk.com/app/2711/

DECRYPT
https://splunkbase.splunk.com/app/2655/

=== Log Input

You could use the input provided by the Add-on, which is on port 514/udp by default. Syslog input on any port is supported. You can also index the THOR text log files written by THOR during the scan. 

Always choose "thor" as index and "thor" as sourcetype to make the results visible in the App.

=== Event Type

All searches and dashboards work with the "thor_events" event type. Adjust the event type to select a different data set for the App. 

For example: 
If you have collected THOR reports from a certain unit and want to inlcude only these reports in the App, you could edit the event type via "Settings > Event Types" and change the event type to somthing like

```source=/var/log/thor_logs_from_unit_x/*```

=== False Positives

Define false positives via "Settings > Tags" and edit the "false_positives" tag to add more false positive expressions. 

=== Encryption

Adjust the password to decrypt XOR encrypted messages via "Settings > Advanced Search > Search Macros" and edit the "decrypt_thor_events" search macro. 

Use the "--xor" parameter and optionally the "-k" parameter in THOR scans to enable encrypted SYSLOG message and set a custom key.

=== Contact

Main developer
Florian Roth
BSK Consulting GmbH / HvS Consulting AG

Email:
florian.roth@bsk-consulting.de
