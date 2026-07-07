# README #

Document to get your Qualys IOC App for Splunk Enterprise up and running.

### About Qualys IOC App for Splunk Enterprise ###

Qualys IOC App for Splunk Enterprise enables customers to search and to visualize Qualys IOC data in Splunk.

Features:

* Splunk Searches

    * Splunk searches on Qualys Detection data

* Dashboards

    * IOC Events details. (with Affected Assets, Count of malwares and TOP Malwares)


* Sample Reports agains Qualys Detection data

    * Report for Porcess

    * Report for Files


# Getting started

Qualys IOC App for Splunk Enterprise needs a TA-QualysCloudPlatform installed on your Splunk setup.

## Installation

The Qualys IOC App for Splunk Enterprise needs to be installed.

1. Go to Splunk interface
2. Login as admin
3. Apps dropdown (top header on left)
4. Manage Apps
5. Install app from file
6. In "Upload an app" window, click "Choose File" button and upload the tarball.
7. Click "Upload" button.

## Initial configuration

The only pre-requisite to use this app is to have TA-QualysCloudPlatform installed, and host_detection input added and enabled in TA-QualysCloudPlatform.

# Troubleshoot

The data that you see in this app is indexed by TA-QualysCloudPlatform. So, if you find any problem, you should see the TA-QualysCloudPlatform log, which is at location SPLUNK_HOME/var/log/splunk/ta_qualyscloudplatform.log

Try this search query in Splunk to get all the log entries:
    source="qualys"

## Contact ##
If you have problems or questions, please contact Qualys support. 

### Contribution guidelines ###
* Writing tests
* Code review
* Other guidelines

