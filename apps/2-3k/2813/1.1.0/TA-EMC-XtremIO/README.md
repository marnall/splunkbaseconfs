# EMC XtremIO Add-on for Splunk Enterprise

## Overview

* This technology add-on collects data from EMC XtremIO cluster to be used by the EMC XtremIO App for Splunk Enterprise.
* Author - Crest Data Systems
* Version - 1.1.0


## Compatibility Matrix

|                                     |                                                           |
|-------------------------------------|-----------------------------------------------------------|
| Browser                             | Google Chrome, Mozilla Firefox, Safari                    |
| OS                                  | Platform independent                                      |
| Splunk Enterprise Version           | 8.2.x, 8.1.x, 8.0.x, 7.3.x                                |
| Supported Splunk Deployment         | Splunk Cloud, Splunk Standalone and Distributed Deployment|
| EMC XtremIO Version                 | 2.4 and later                                             |


## Recommended System Configuration

* Splunk search head system should have 8 GB of RAM and a quad-core CPU to run this app smoothly.


## Topology and Setting up Splunk Environment

* This app has been distributed in two parts.

    1) Add-on app, which runs collector scripts and gathers data from EMC XtremIO cluster, does
    indexing on it and provides indexed data to Main app.

    2) Main app, which receives indexed data from Add-on app, runs searches on it and builds
    dashboard using indexed data.

* This App can be set up in two ways:

    1) Deploy to single server instance

        Standalone Mode: Install main app and Add-on app on a single machine.

       * Here both the app resides on a single machine.
       * Main app uses the data collected by Add on app and builds dashboard on it.

    2) Deploy to distributed deployment

       * Install the main app and Add-on on the search head. User does not need to configure the Add-on on search head.
       * Install only Add-on on the heavy forwarder. User needs to configure setup page to collect data from EMC XtremIO cluster.


## Release Notes

* **Version 1.1.0**

    * Made Add-on Python2 and Python3 compatible.
    * Migrated setup.xml to setup dashboard.
    * Added support of Splunk 8.x


## Installation

Follow the below-listed steps to install an Add-On from the UI:

* Download the add-on package.
* From the UI navigate to  `Apps -> Manage Apps`.
* In the top right corner select `Install the app from file`.
* Select `Choose File` and select the App package.
* Select `Upload` and follow the prompts.

  **OR**

* Directly from the `Find More Apps` section provided in Splunk Home Dashboard.


## Upgradation

* Download the App package.
* From the UI navigate to `Apps->Manage Apps`.
* In the top right corner select `Install app from file`.
* Select `Choose File` and select the App package. 
* Check `Upgrade App`.
* Select `Upload` and follow the prompts.

  **OR**

* If a newer version is available on splunkbase, then App/Add-on can be updated from UI also.

    * From the UI navigate to `Apps->Manage Apps` OR click on gear icon.
    * Search for "EMC XtremIO Add-on for Splunk Enterprise".
    * Click on `'Update to <version>'` under Version Column.


## Uninstallation and Cleanup

This section provides the steps to uninstall App from a standalone Splunk platform installation.

* (Optional) If you want to remove data from the Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.

    * $SPLUNK_HOME/bin/splunk stop
    * $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>

* Delete the app and its directory. The app and its directory are typically located in the folder $SPLUNK_HOME/etc/apps/<appname> or run the following command in the CLI:

    * $SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password>

* You may need to remove user-specific directories created for your app by deleting any files found here:
  
    * $SPLUNK_HOME/bin/etc/users/*/<appname>

* Restart the Splunk platform. You can navigate to Settings -> Server controls and click the restart button in Splunk web UI or use the following Splunk CLI command to restart Splunk:

    * $SPLUNK_HOME/bin/splunk restart


## Configuration of Add-on

* After installation, Go to the `Apps->Manage Apps` and open "Setup" screen for **EMC XtremIO Add-on for Splunk Enterprise(TA-EMC-XtremIO).**
* It will open a set up screen which will ask for XtremIO server credentials.
* Please provide Host (IP Address), Username, Password and Confirm Password and save them.
* Splunk REST API will encrypt the password and store it in app itself(local/passwords.conf) in encrypted form, Data collector script will fetch these credentials through REST API to connect to the XtremIO node.


## Data Generator

This app is provided with sample data that can be used to generate dummy data. To simulate this sample data, first of all, download the Splunk Event generator, which is available at https://github.com/splunk/eventgen, & needs to be installed at $SPLUNK_HOME/etc/apps/. This APP uses the Samples provided in Add-on to populate the dummy data for EMC XtremIO environment.


# Open source components and licenses

Some of the components included in "EMC XtremIO Add-on for Splunk Enterprise" are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* requests version 2.25.1 https://pypi.org/project/requests (LICENSE https://github.com/requests/requests/blob/master/LICENSE)
* oauth_hook version 0.4.1 https://pypi.org/project/requests-oauth (LICENSE https://github.com/maraujop/requests-oauth/blob/dev/LICENSE)
* requests_oauth2 version 0.3.0 https://pypi.org/project/requests-oauth2 (LICENSE https://github.com/maraujop/requests-oauth2/blob/master/LICENSE)
* requests_oauthlib version 1.3.0 https://pypi.org/project/requests-oauthlib (LICENSE https://github.com/requests/requests-oauthlib/blob/master/LICENSE)
* six version 1.16.0 https://pypi.org/project/six (LICENSE https://github.com/benjaminp/six/blob/master/LICENSE)
* jQuery version 3.5.0 https://jquery.com (LICENSE https://github.com/jquery/jquery/blob/main/LICENSE.txt)


## Troubleshooting

* If you get any error messages in the Setup page UI, have a look at the messages coming on the config screen. You can also check logs for validation by using the below query:

    * index=_internal source="\*splunkd\*" error

* Once Add-on app is configured to receive data from EMC XtremIO, The main app dashboard can take some time before the data is populated in all panels. A good test to see that you are receiving all of the data is to run this search after several minutes:

    * index="<your_index>" | stats count by sourcetype

* In particular, you should see the sourcetype:

    * emc:xtremio:rest

* If you don't see these source types, please check the splunkd logs. Here is a sample search that will show all the logs generated by splunk:

    * index=_internal source="\*splunkd\*"


## Support Information

* **Email:** dell-support@crestdatasys.com

## Copyright Information

Copyright (C) 2021 Dell Technologies Inc. All Rights Reserved.