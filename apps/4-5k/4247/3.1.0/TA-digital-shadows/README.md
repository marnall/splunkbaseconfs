# ABOUT THIS APP

* The Technology Add-on for Digital Shadows is used to download data from the DigitalShadows Searchlight portal and indexes it in Splunk for further analysis.
* This Add-on uses Splunk KV store for checkpoint mechanism.
* This is an add-on powered by the Splunk Add-on Builder.

# REQUIREMENTS

* Splunk version 8.2.x, 8.1.x, 8.0.x
* Python version: python3
* OS Support: Linux (CentOs, Ubuntu) and Windows
* Browser Support: Chrome and Firefox 
* Appropriate access key and secret key for collecting data from DigitalShadows Searchlight portal

# Release Notes
## Version: 3.1.0

* Upgrade the app using Splunk Add-on Builder v4.1.1 to eliminate security vulnerabilities

## Version 3.0.0
* Added data collection of alerted incidents with alerted=true parameter.
* Changed index-time to be “modified” date for ds:searchlight:intel:incidents and ds:searchlight:alerts sourcetypes.

## Version: 2.1.0

* Upgrade the app using Splunk Add-on Builder v4.0.0 to eliminate security vulnerabilities

## Version: 2.0.0

* Made Add-on Python 2-3 compatible
* Updated sorcetypes according to the Splunk best practice
* Updated the CIM mapping for web, certificate, network, vulnerability data model

# RECOMMENDED SYSTEM CONFIGURATION

* Splunk forwarder system should have 12 GB of RAM and a six-core CPU to run this Technology Add-on smoothly.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This Add-On can be set up in two ways:
 1) **Standalone Mode**: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup


 2) **Distributed Environment**: Install Add-on on search head and Add-on on Heavy forwarder (for REST API).

    * Add-on resides on the search head machine and accounts need to be configured here.
    * Add-on needs to be installed and configured on the Heavy forwarder system.
    * Execute the following command on Heavy forwarder to forward the collected data to the indexer.
      $SPLUNK_HOME/bin/Splunk add forward-server <indexer_ip_address>:9997
    * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
    * Add-on needs to be installed on search head for CIM mapping and Adaptive Response actions.

# INSTALLATION OF APP

* This Add-on can be installed through UI using "Manage Apps" or extract zip file directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION OF APP

* Navigate to Digital Shadows Add-on, click on the "Configuration" page, go to "Account" tab and then click "Add", fill in "Account Name", "Address", "Access Key" and "Secret Key".

* Navigate to Digital Shadows Add-on, click on "Create New Input" and fill the "Name", "Interval", "Index", "DS Account", "Since", "Incident Types", "Verbose Details" and "Global Incidents" fields.

# Upgrading to version 3.0.0

Follow the below steps to upgrade the Add-on to 3.0.0

* Disable all the inputs from the Inputs page of Digital Shadows.
* Install the Digital Shadows Add-on v3.0.0
* Restart Splunk if required and if prompted by Splunk.
* Navigate to the Digital Shadows Add-on for Splunk.
* From the Inputs page, delete the old input. You can also delete the index since we will need a new index due to index-time field changes.
* Now, create a new index and use the new index for creating new input.
* Note: We have added data collection of private incidents with alerted=true in addition to incidents with alerted=false. Creating a new input as described above will pull previously missed incidents due to this filter parameter.

# Upgrading to version 2.1.0

Follow the below steps to upgrade the Add-on to 2.1.0

* Disable all the inputs from the Inputs page of Digital Shadows.
* Install the Digital Shadows Add-on v2.1.0
* Restart the Splunk if required and if prompt by Splunk.
* Navigate to the Digital Shadows Add-on for Splunk.
* From the Inputs page, click on Enabled to enable already created inputs or click on Create New Input to create new inputs with required fields.

# Upgrading to version 2.0.0

Follow the below steps to upgrade the Add-on to 2.0.0

* Go to Apps > Manage Apps and click the install app from file.
* Click Choose file and select the TA-digital-shadows installation file.
* Check the Upgrade app checkbox and click on Upload.
* After a successful restart, go to the apps list and open Digital Shadows Add-on for Splunk.
* From the Inputs page, click on Create New Input to create new inputs with required fields.

# Uninstall & Cleanup steps

* Remove $SPLUNK_HOME/etc/apps/TA-digital-shadows
* Remove $SPLUNK_HOME/var/log/splunk/ta_digital_shadows_digital_shadows_searchlight.log
* Remove $SPLUNK_HOME/var/log/splunk/update_digital_shadows_incident_status_modalert.log
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

# TROUBLESHOOTING

* Environment variable SPLUNK_HOME must be set
* Authentication Failure:
  * Check the network connectivity and make sure that the Digital Shadows server is reachable by executing the “ping <server>” command on a terminal or command prompt.
* Adaptive Response Action Failure:
  * User can view update_digital_shadows_incident_status_modalert.log” file located at $SPLUNK_HOME/var/log/splunk or can execute “index=cim_modactions sourcetype=modular_alerts:update_digital_shadows_incident_status” query to get more details of the failure.
* To troubleshoot Digital Shadows SearchLight mod-input check $SPLUNK_HOME/var/log/splunk/ta_digital_shadows_digital_shadows_searchlight.log file.

# SUPPORT

* Support Offered: Yes
* Support Email: support@digitalshadows.com

### Copyright (C) 2021 Digital Shadows Limited
