This is an add-on powered by the Splunk Add-on Builder.
The Forinet Active Response add-on defined an alert action, which will enable
users to block traffic from/to a particular source IP, destination IP or a
network user through FortiGate's ReSTful API.
Installation:
1. Can be installed from Manage Apps->Search for FortinetAR.
2. Can also be installed from file, which can be downloaded from splunkbase.

Configuration:
1. Click "Set up" after the add-on is installed.
2. Add Devices and Admin passwords for FortiGates reporting logs to Splunk.
The information will be used to send ReSTful API commands to the corresponding
FortiGate. Device ID and its admin user password will be needed here.
3. Add mapping between Device ID and its IP address for RestFul API or the IP
address of FortiGate which have https access enabled.

Usage:
1. Create a correlation search under Enterprise Security->Configure->Content
Management.
2. In the correlation search: fill out Search field based on the CIM datamodel
generated from FortiGate logs, such as:
   | datamodel "Malware" "Malware_Attacks" search
and time range for the search.
3. Add active response actions for the matching event, for example, report a
Notable Event, which will create an event notification in Incident Review.
Or you can directly add the FortiGateActions here if you are sure which field
you want to block when the search returns a result.
4. If notable event is reported, you can go to Incident Review tab to look for
the event and run active response actions from there.
5. After the active response action is taken, there will be a firewall policy
added in the FortiGate which trigged the event. The policy will include a
comment "fgt_ar" for users to easily identify.

Troubleshooting:
If the policy is not created on FortiGate after running active response
action:
1. Make sure the add-on has been set up with FortiGate's information including
correct device id, admin password, IP address and the IP address enables https
access.
2. If set up is correct, you can get more information about the issue by
searching: index="summary" sourcetype="fortigateresponse" in Search&Reporting.
3. More detailed information can be found in log file:
    $SPLUNK_HOME/var/logs/splunk/FortiGateActions_modalert.log
