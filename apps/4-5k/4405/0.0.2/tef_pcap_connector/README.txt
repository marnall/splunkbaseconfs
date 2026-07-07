Introduction
============

This add-on adds workflows to Splunk events, linking to a Counterflow ThreatEye Forensics appliance that contains
full raw packet info (PCAP data). SOC/NOC users click the "Event Actions" menu of any Splunk event
and choose a ThreatEye Forensics link that opens a new browser window in the Counterflow ThreatEye Forensics UI. Key fields
from the event, like time-frame and IP addresses, are sent to the ThreatEye Forensics unit through the URL.

This add-on could for instance be used together with events generated from Suricata.

Requirements
============

A Counterflow ThreatEye Forensics appliance with release 3.0 or above is required to use this add-on.

Installation
============

To install an add-on within Splunk Enterprise:

1. Log into Splunk Enterprise.
2. Next to the Apps menu, click the Manage Apps icon.
3. Click Install app from file.
4. In the Upload app dialog box, click Choose File.
5. Locate the .tgz file you just downloaded, then click Open or Choose.
6. Click Upload.


Configuration
=============

Initial configuration is needed to link correctly to the Counterflow ThreatEye Forensics appliance. Go to "Manage
apps" and select "View objects" for the "Napatech Packet Capture Integration" add-on. Four workflows
actions are defined, tef_4tuple tef_dst, tef_src and tef_src_dst. For all four
workflow actions, you need to:

1. Replace all occurrences of "threateyeforensics" with a FQDN or IP address of the Counterflow ThreatEye Forensics
   appliance. There are four occurrences.
2. Replace "<Your ThreatEye Forensics UUID>" with the UUID of your ThreatEye Forensics appliance (this can be obtained from
   the ThreatEye Forensics UI). There are four occurrences of UUID.
3. Set the permissions for all four workflow actions as "Object should appear in All apps", and give
   all four workflows global read/write permissions to "everyone".

The workflow action is now available when clicking on an event.

Suricata
========

To monitor Suricata events in Splunk go to "Setting"->"Data inputs"->"Files & directories" and
choose "new". Add the Suricata event log file "/var/log/suricata/eve.json" and choose type json.

The event file is now searchable using source="/var/log/suricata/eve.json".

When clicking on a Suricata event, the workflow action with direct link to the Counterflow ThreatEye Forensics
appliance will appear, and network data related to the Suricata event can be extracted from the
Counterflow ThreatEye Forensics appliance.

Support
=======

For support or to obtain a Counterflow ThreatEye Forensics appliance, contact the Counterflow Sales Engineering group
at support@counterflowai.com
