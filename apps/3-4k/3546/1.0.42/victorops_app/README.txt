VICTOROPS APP
Version 1.0.42


Splunk + VictorOps extends the alerting and messaging from Splunk Enterprise or Splunk Cloud into the VictorOps Incident Management platform. This allows you to leverage your existing team contact, scheduling, and escalation policies for your Splunk alerts. 

VictorOps is a hub for centralizing the flow of information throughout the incident lifecycle. Driven by IT and DevOps system data, VictorOps provides a unified platform for real-time alerting, collaboration, and documentation.

Using VictorOps, teams resolve incidents faster to help minimize the impact of downtime and speed innovation.


REQUIREMENTS/INSTALLATION
=========================

1. Install Splunk Enterprise
----------------------------

If you haven't already installed Splunk Enterprise, download it at http://www.splunk.com/download. For more information about installing and running Splunk Enterprise and system requirements, see the Installation Manual (http://docs.splunk.com/Documentation/Splunk/latest/Installation).

This app is also compatible with Splunk ITSI.  For more information, refer to the docs here: https://help.victorops.com/knowledge-base/victorops-splunk-itsi-integration/


2. Install the VictorOps app
---------------------------

Install the VictorOps app to the $SPLUNK_HOME/etc/apps folder.  If you have downloaded the tar file from Splunkbase, simply navigate to tha app management area of the Splunk web UI and choose 'Install app from file'.


3. Setup the app
-------------------

From the Splunk interface, click the gear icon to manage apps.  Locate the VictorOps Notifications app and click 'Setup'.  Enter your VictorOps Splunk integration API key and optional routing key.  For more information on finding your VictorOps endpoint key and routing_key, refer to the following docs:

https://help.victorops.com/knowledge-base/new-splunk-integration-guide-victorops/

https://help.victorops.com/knowledge-base/routing-keys/


5. Create a VictorOps alert action
------------------------

For any saved search, create an alert action and select VictorOps.

For more detailed information on verifying the installation, or setting up and testing alerts, refer to https://help.victorops.com/knowledge-base/new-splunk-integration-guide-victorops/#verify-the-integration


USAGE
=====

See https://help.victorops.com/knowledge-base/new-splunk-integration-guide-victorops


COMMUNITY AND FEEDBACK
======================

Questions, comments, suggestions? To provide feedback about this release or to get help with any problems, visit https://victorops.com/contact-support/


LICENSE
=======

Copyright VictorOps, Inc. All Rights Reserved
