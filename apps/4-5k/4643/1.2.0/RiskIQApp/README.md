RiskIQ Digital Footprint Legacy App For Splunk
=====================

OVERVIEW
--------
RiskIQ Digital Footprint Legacy App For Splunk helps in visualizing and analyzing data collected by RiskIQ Digital Footprint Add-on For Splunk.

* Author - RiskIQ
* Version - 1.2.0
* Build - 29
* Creates Index - False
* Prerequisites - This application is dependent on RiskIQ Digital Footprint Add-on For Splunk
* Compatible with:
   Splunk Enterprise version: 7.2, 7.3, 8.0
   OS: Platform independent

RELEASE NOTES:
Version 1.2.0

* Added fixed sourcetype to reduce the scope of searching in datamodel.

RELEASE NOTES:
Version 1.1.0

* Moved `getcves` custom command and riskiq_cve and riskiq_ddosasns lookups to RiskIQ Digital Footprint Add-on For Splunk

TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
------------------------------------------

This app has been distributed in two parts. 
  1. `RiskIQ Digital Footprint Add-on For Splunk`, which collects data from RiskIQ API. 
  2. `RiskIQ Digital Footprint Legacy App For Splunk` helps in visualizing and analyzing RiskIQ data.

This app can be set up in two ways: 
  1. Standalone Mode: 
     * Install both the `RiskIQ Digital Footprint Legacy App For Splunk` and `RiskIQ Digital Footprint Add-on For Splunk`. 
  2. Clustered Environment: 
     * Install the `RiskIQ Digital Footprint Legacy App For Splunk` and `RiskIQ Digital Footprint Add-on For Splunk` on search head. 
     * To setup `RiskIQ Digital Footprint Add-on For Splunk` on the search head follow below setps:
       1. On Search head deployer, Go to `$SPLUNK_HOME$/etc/shcluster/apps/TA-RiskIQ/local`.
       2. Create `app.conf` file and add below stanza.
            ```
            [install]
            is_configured = 1
            ```
       3. Save the file and push the bundle to search head.
     * Install the `RiskIQ Digital Footprint Add-on For Splunk` on heavy forwarder. 
     * User needs to create `riqsummary` index on the indexer.
     * User needs to set up Add-on to start data collection on heavy forwarder. 


INSTALLATION
------------
* Install the App bundle by:
  * Download the App package.
  * In the UI navigate to: `Apps->Manage Apps`.
  * In the top right corner select `Install app from file`.
  * Select `Choose File` and select the App package.
  * Select `Upload` and follow the prompts.

CONFIGURATION
-------------
* User needs to create an index from UI, follow the below steps.
  1. Go to `Settings->Indexes`.
  2. Click on `New Index`.
  3. Type `riqsummary` in `Index Name` field.
  4. Select `Events` option in `Index Data Type` field.
  5. Select `RiskIQ Digital Footprint Legacy App For Splunk` from dropdown `App` field.
  6. click on `Save` button.

DASHBOARDS
----------
1. Insights - Overview
2. RiskIQ - At Risk Frameworks
3. RiskIQ - At Risk Servers
4. Certificates
5. Insecure Login Pages
6. Broken Redirects

SAVED SEARCHES, REPORTS, AND ALERTS
--------------
* `AssetLookup` - Creates an updated asset lookup file for integration with Splunk ES.
* `RIQHostsDiffs` - Daily diff for added and disappeared hosts. Populates the summary index.
* `RIQWebSiteDiffs` - Daily diff for added and disappeared URLs. Populates the summary index.
* `RIQCertDiffs` - Daily diff for added and disappeared Certs. Populates the summary index.
* `Threat - RIQNewlyDiscoveredHosts - Rule` - Uncovers newly detected hosts. A Notable Event is created for every new host detected today, so a host which was not visible previous 5 days but is detected today.
* `Identity - RIQNewRegistrationEmail - Rule` - Discovers newly provisioned email addresses for the internet presence: Domains, certificates, etc.
* `Threat - RIQExpiredCertificates - Rule` - Identifies expired certificates on your digital footprint. A Notable Event is created for every expired certificate detected today. There is a 10 day suppression period, so if the certificate is not cleaned up within 10 days, a new Notable Event will be created.
* `Audit - RIQPIIFound - Rule` - Insecure login form found on open internet.
* `Threat - RIQMalwareDetected - Rule` - Reports potential Malware detected on your digital footprint.
* `Threat - RIQDomainInfringement - Rule` - Potential Domain infringement detected.
* `Threat - RIQRecentDetectedVulnerability - Rule` - Vulnerabilities newly detected in last 10 days.
* `Threat - RIQDefacementEvent - Rule` - Detects defacement events as published by RiskIQApp.

Note: By default all the savedsearches are disabled you can enable it by following the below steps:
  1. Go to `Settings->Searches, reports, and alerts`.
  2. Select `RiskIQ Digital Footprint Legacy App For Splunk` in the App filter.
  3. Now Click on the `Edit` button of the saved search that you want to enable.
  4. Click on the `enable` option from the dropdown.
  5. Click on the `Enable` button from the confirmation popup.

DATA MODEL CONFIGURATION
------------------------
* The Data Model used in this application is not accelerated. Admin should manually accelerate the Data Model.
* The Data Model used in this application should be accelerated to achieve better performance in loading dashboard panels. 
* Admin can enable/disable acceleration or change the acceleration period by the following steps:
  1. On Splunk's menu bar, Click on Settings -> Data models.
  2. From the list for Data models, Search for RiskIQ data model, click "Edit" in the "Action" column of the row for the Data model for which acceleration needs to be enabled or disabled.
  3. From the list of actions select Edit Acceleration. This will display the pop-up menu for Edit Acceleration.
  4. Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
  5. If acceleration is enabled, select the summary range to specify acceleration period.
  6. To save acceleration changes click on the save button.
* Warning: Acceleration may increase storage and processing costs.

REBUILDING DATA MODEL
---------------------
* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
  1. On Splunk's menu bar, Click on Settings -> Data models.
  2. From the list for Data models, expand the row by clicking ">" arrow in the first column of the row for the Data model for which acceleration needs to be rebuild. This will display an extra Data Model information in "Acceleration" section.
  3. From the "Acceleration" section click on "Rebuild" link.
  4. Monitor the status of "Rebuild" in the field "Status" of "Acceleration" section. Reload the page to get latest rebuild status.

EULA
-------
Custom EULA for RiskIQ. https://www.riskiq.com/msa/

SUPPORT
------------------------------
Contact - support@riskiq.com


Copyright 2016 - 2020 RiskIQ


