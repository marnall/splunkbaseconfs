Splunk App for Incident Intelligence
Version 1.0.7


Splunk + Incident Intelligence extends the alerting and messaging from Splunk Enterprise or Splunk Cloud into the Incident Intelligence Incident Management platform. This allows you to leverage your existing team contact, scheduling, and escalation policies for your Splunk alerts.

Incident Intelligence is a hub for centralizing the flow of information throughout the incident lifecycle. Driven by IT and DevOps system data, Incident Intelligence provides a unified platform for real-time alerting, collaboration, and documentation.

Using Incident Intelligence, teams resolve incidents faster to help minimize the impact of downtime and speed innovation.


REQUIREMENTS/INSTALLATION
=========================

1. Install Splunk Enterprise
----------------------------

If you haven't already installed Splunk Enterprise, download it at http://www.splunk.com/download. For more information about installing and running Splunk Enterprise and system requirements, see the Installation Manual (http://docs.splunk.com/Documentation/Splunk/latest/Installation).

This app is also compatible with Splunk ITSI.  For more information, refer to the docs here: TBD

If you wish to build it from GitLab, run below command from outside of the directory where `splunk-incident-intelligence-app` is cloned and copied the directory to `splunk_incident_intelligence_app`.
rm -fr splunk_incident_intelligence_app.tar.gz ; COPYFILE_DISABLE=1 tar cv --exclude='*DS_Store' --exclude='.git*' --exclude='.idea*' splunk_incident_intelligence_app > splunk_incident_intelligence_app.tar.gz;


2. Install the Splunk App for Incident Intelligence
---------------------------

The app is available at https://classic.splunkbase.splunk.com/app/6721. Install the Splunk App for Incident Intelligence to the $SPLUNK_HOME/etc/apps folder.  If you have downloaded the tar file from Splunkbase, simply navigate to tha app management area of the Splunk web UI and choose 'Install app from file'.


3. Setup the app
-------------------

From the Splunk interface, click the gear icon to manage apps.  Locate the Splunk App for Incident Intelligence and click 'Setup'.  Enter your Incident Intelligence Splunk integration Org Id and Org Level Access Token.  For more information on finding your Incident Intelligence Org Id and Org Level Access Token, refer to the following docs:

Links: https://docs.splunk.com/observability/incident-intelligence/incident-intelligence-overview.html#nav-Splunk-Incident-Intelligence-overview

5. Create a Incident Intelligence alert action
------------------------

For any saved search, create an alert action and select Incident Intelligence.

For more detailed information on verifying the installation, or setting up and testing alerts, refer to TBD Link


USAGE
=====

See TBD Link


COMMUNITY AND FEEDBACK
======================

Questions, comments, suggestions? To provide feedback about this release or to get help with any problems, visit TBD Link


LICENSE
=======

Copyright Splunk, Inc. All Rights Reserved
