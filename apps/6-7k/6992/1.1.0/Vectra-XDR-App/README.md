# Vectra XDR App

## OVERVIEW
* The Vectra XDR App builds a dashboard from data provided by Vectra XDR Technology Add-on for Splunk.
* Author - Vectra AI
* Version - 1.1.0

## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox
* OS: Linux (CentOs, Ubuntu) and Windows
* Splunk Enterprise version: 9.3.x, 9.2.x, 9.1.x
* Supported Splunk Deployment: Splunk Cluster, Splunk Standalone, and Distributed Deployment

## RELEASE NOTES
### Version 1.0.0
* TM-4754 - Remove d_link_status in Health dashboard as it does not reflect the correct state when the senor has multiple interfaces.
  
### Version 1.0.0
* Initial Version
* Added dashboards for vizualising entities, detections, audit, lockdown and health data.

## REQUIREMENTS
* This application should be installed on Search Head.
* Adjust the index containing data collected from the Add-on in the macro `vectra_xdr_index_macro`.


## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This App can be set up in two ways:

1. Standalone Mode: Install the app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2. Distributed Environment: Install App on search head.


## INSTALLATION OF APP

* Follow the below-listed steps to install an Add-on from the bundle:
    * Download the App package.
    * From the UI navigate to Apps->Manage Apps.
    * In the top right corner select Install app from file.
    * Select Choose File and select the App package.
    * Select Upload and follow the prompts.

    OR

* Directly from the Find More Apps section provided in Splunk Home Dashboard

## CONFIGURATION

* The App does not require any specific configuration to make.

## CONFIGURE MACROS
 * If the user has selected a index except for main in "Data Input" configuration, then no need to perform this step. But if the user has given any other index in "Data Input" configuration, then do the below steps.
    * Go to Settings->Advanced search->Search macros
    * Select "Vectra XDR App" in App context
    * Update the `vectra_xdr_index_macro` macro.

## TROUBLESHOOTING

* To check the data collected by data collection in index use query like "index=<your_index_name> sourcetype=`vectra:cloud:lockdown`/`vectra:cloud:audits`/`vectra:cloud:detections`/`vectra:cloud:entity:scoring`/`vectra:cloud:health`".
* To troubleshoot Vectra XDR App please check $SPLUNK_HOME/var/log/splunk/ta_vectra_saas_\*.log\* files.
* If the dashboard is not getting populated make sure index in macro.conf is updated correctly.


## UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/Vectra-XDR-App
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## END USER LICENSE AGREEMENT
* http://www.apache.org/licenses/LICENSE-2.0

## SUPPORT
* Email: <support@vectra.ai>

## Copyright: (c) 2023 Vectra AI, Inc. All rights reserved.