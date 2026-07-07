
# ABOUT THIS APP

* Digital Shadows monitors and manages an organization’s digital risk across the widest range of data sources within the visible, deep, and dark web to protect an organization’s business, brand, and reputation. The Digital Shadows SearchLight™ service combines scalable data analytics with human data analysts to manage and mitigate risks associated with an organization’s brand exposure, VIP exposure, cyber threat, data loss, infrastructure exposure, physical threat, and third party risk. SearchLight creates an up-to-the minute view of an organization’s external digital risk with tailored threat intelligence.
* The Digital Shadows App for Splunk builds dashboards on indexed data provided by Digital Shadows Add-On.

# REQUIREMENTS

* Splunk version: 8.0.x, 8.1.x and 8.2.x
* OS Support: Linux (CentOs, Ubuntu) and Windows
* Browser Support: Chrome and Firefox 

# Release Notes

## Version 2.1.0

* Bundled jQuery v3.5.0 in the app package. This version of jQuery has security fixes and will be used by the app independently.

## Version 2.0.1

* Added the build number in app.conf file.

## Version: 2.0.0

* Updated the dashboard queries according to the new sourcetypes.
* Updated the top-level incidents panels.
* Added the correlation search to create a notable event on Enterprise Security.

# RECOMMENDED SYSTEM CONFIGURATION

* Splunk forwarder system should have 12 GB of RAM and a six-core CPU to run this Technology Add-on smoothly.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

* This app has been distributed in two parts.

  1) Add-on app, which takes input from modular input, does indexing on retrieved data into Splunk and provides it to Main app.
  2) Main app, which receives indexed data from Add-on app, runs searches on it and builds dashboard using indexed data.

* This App can be set up in two ways:
  1) **Standalone Mode**: Install main app and Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup

     * Here both the app resides on a single machine.
	 * Add-on needs to be installed and configured on stand alone splunk instance.
     * Main app uses the data collected by Add-on.

   2) **Distributed Environment**: Install main app and Add-on on search head and Add-on on Heavy forwarder.

     * Here also both the apps reside on the search head machine, but only account needs to be configured on search head.
     * Only Add-on needs to be installed and configured on Heavy forwarder system.
     * Execute the following command on Heavy forwarder to forward the collected data to the indexer.
       $SPLUNK_HOME/bin/splunk add forward-server <indexer_ip_address>:9997
     * On Indexer machine, enable event listening on port 9997 (recommended by Splunk).
     * Main app on search head uses the received data and builds dashboards on it.

# INSTALLATION OF APP

* This app can be installed through UI using "Manage Apps" or extract zip file directly into $SPLUNK_HOME/etc/apps/ folder.

# SAVEDSEARCHES

* This application contains the following savedsearches, which is used in forming lookup files. Initially, savedseraches will be disabled. To enable it, one has to go to "Settings"->"Searches, reports, and alerts" and change the "App" filter value to "Digital Shadows App for Splunk(digital-shadows)". Against "digital_shadows_ip_threat_lookup_search" and "Threat - Digital Shadows Get Incidents - Rule" savedseraches click on "Edit"->"Enable"
  * "digital_shadows_ip_threat_lookup_search" - This savedsearch is used to add data to the following "Enterprise Security" lookups; "local_domain_intel", "local_http_intel", "local_file_intel" and "local_ip_intel".
  * "Threat - Digital Shadows Get Incidents - Rule" - This is a sample correlation search. This correlation search is used to create a notable event in "Enterprise Security". These notable events will be generated in every 15 minutes after Enabling the correlation search and can be reviewed on "Incident Review" Dashboard.

# TEST YOUR INSTALL

* Configure Macro:
    
  * If a user has selected a default index in "Data Input" Configuration in Digital Shadows Add-on for Splunk, then no need to perform this step.
    But if a user has given any other index in the "Data Input" Configuration in Digital Shadows Add-on for Splunk, then do the below steps.
    * Go to Settings->Advanced search->Search macros
    * Select "Digital Shadows App for Splunk(digital-shadows)" in App context
    * Click on "get_digitalshadows_index" macro and update definition to index=INDEX_NAME, Where INDEX_NAME should be the same name given at the time of creating data input and then click Save.

* The main app dashboard can take some time to populate the dashboards, once data collection is started. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

	search `get_digitalshadows_index` | stats count by sourcetype
	
If Add-on is freshly installed or upgraded then, you should see new events in "ds:searchlight:alerts", "ds:searchlight:pipeline", "ds:searchlight:intel:incidents", "ds:searchlight:intel:iocs" and "ds:searchlight:credentials" sourcetypes.

# Upgrade

Follow the below steps to upgrade the App to latest version

* Go to Apps > Manage Apps and click the install app from file.
* Click Choose file and select the digital-shadows App installation file.
* Check the Upgrade app checkbox and click on Upload.
* When installation is done, restart the splunk.
* After a successful restart, go to the apps list and open Digital Shadows App for Splunk.

# Uninstall & Cleanup steps

* Remove $SPLUNK_HOME/etc/apps/digital-shadows
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance


# TROUBLESHOOTING

* If you do not see any results in search: 
	* Go to the macro defined from Settings->Advanced search->Search macros
	* Click on "get_digitalshadows_index" macro.
	* Check if the index name matches with the index defined in the "Data Input" step.

* If the problem still persists increase the Time Range filter provided on the top left corner.

# SUPPORT

* Support Offered: Yes
* Support Email: support@digitalshadows.com

### Copyright (C) 2021 Digital Shadows Limited
