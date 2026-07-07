# Nessus Professional Add-on for Splunk

### Download from Splunkbase
https://splunkbase.splunk.com/app/7464

### Overview
The Nessus Professional Add-on for Splunk helps users to collect Vulnerability and Vulnerability-Plugins data from locally hosted Nessus Professional servers via API.

* Author - CrossRealms International Inc.
* Creates Index - False
* Compatible with:
   * OS: Platform Independent
   * Browser: Google Chrome, Mozilla Firefox, Safari


## What's inside the App

* No of XML Dashboards: **3**
* Approx Total Viz(Charts/Tables/Map) in XML dashboards: **3**
* No of Custom Inputs: **2**


## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT

This app can be set up in two ways: 
  1. Standalone Mode: 
     * Install the `Nessus Professional Add-on for Splunk`.
  2. Distributed Mode: 
     * Install the `Nessus Professional Add-on for Splunk` on the search head. The Add-on configuration is not required on the search head.
     * Install the `Nessus Professional Add-on for Splunk` on the heavy forwarder. Configure the Add-on to collect the required information from the Nessus Professional on the heavy forwarder.
     * The Add-on do not support universal forwarder as it requires python modular inputs to collect the data from Nessus Professional.
     * The Add-on do not require on the Indexer.


## DEPENDENCIES

* The Add-on does not have any external dependencies.


## INSTALLATION

The `Nessus Professional Add-on for Splunk` needs to be installed on the Search Head and heavy forwarder.

* From the Splunk Web home screen, click the gear icon next to Apps. 
* Click on `Browse more apps`.
* Search for `Nessus Professional Add-on for Splunk` and click Install. 
* Restart Splunk if you are prompted.


## DATA COLLECTION & CONFIGURATION

### Generate API Credential on Nessus Professional ###
* User needs to generate ClientID and ClientSecret from Nessus Professional server.
* Reference - <TODO>


### Configure Account ###
* Navigate to `Nessus Professional Add-on for Splunk` > `Configuration` > `Account` on Splunk UI.
* Click on `Add`.
* Add below parameters:

| Parameter | Description |
| --- | --- |
| Account name | Any unique name to distinguish this client-id and secret from other in case of multiple accounts configured in the Add-on. |
| Nessus URL | Nessus Professional URL with IP/hostname and port number, without http/https scheme. (ex. 10.10.10.10:8834) |
| Client Id | Client id received from Nessus Professional. |
| Client Secret | Client secret received from Nessus Professional. |

* Click on `Add`.

* NOTE - If Nessus Professional is running on http instead of https, then user needs to add `http` value for the parameter `http_scheme` in the `ta_nessus_pro_settings.conf` conf file under the stanza `api`.
* NOTE - Additionally if user don't have valid SSL certificate on Nessus Professional and would like to skip the SSL certificate validation then user can add `false` value for `verify_ssl` parameter in the `ta_nessus_pro_settings.conf` conf file under the stanza `api`.


### Configure Data Inputs ###
* Navigate to `Nessus Professional Add-on for Splunk` > `Input` on Splunk UI.
* Click on `Create New Input`.
    * There are two options as described below.
    * Vulnerability Scan Data is what is most useful. But if you need you can even collect Plugin data in Splunk.

#### 1. Nessus Professional Vulnerability Scan Data
* Default and recommended interval is 14400 (4 hour) or more.

#### 2. Nessus Professional Plugin Data
* Default and recommended interval is 604800 (7 days) or more. Interval is long as this input will make thousands of API call to Nessus Professional server.

* Below are parameters that needs to be configured.

| Parameter | Description |
| --- | --- |
| Name | An unique name for the Input. |
| Interval | Interval in seconds, at which the Add-on should collect latest data. Default interval for input is described above. |
| Account to use | Select the account name configured in the Configuration page, which you want to use for data collection. |
| Index | Select/Type the index name in which Nessus Professional data will be stored in Splunk. |
| Start Date | Select the start date from which point onwards you want to collect the data. Data older than that point will be skipped. |



## UNINSTALL APP

To uninstall app, user can follow below steps:
* SSH to the Splunk instance.
* Go to folder apps($SPLUNK_HOME/etc/apps).
* Remove the `TA_Nessus_Pro` folder from `apps` directory.
* Remove the DB Connect Identity, Connection and Inputs that you have created.
* Restart Splunk.


## RELEASE NOTES

Version 1.1.0 (July 2024)
* Fixed the cloud compatibility issue regarding http URL scheme. Now if you have http in the URL of Nessus Professional then user has to configure it from `ta_nessus_pro_settings.conf` file only.


Version 1.0.0 (Jun 2024)
* Created Add-on by UCC Splunk-Python library.
* Added Add-on configuration pages.
* Added data collection inputs.



## OPEN SOURCE COMPONENTS AND LICENSES

* The Add-on is built by UCC framework (https://pypi.org/project/splunk-add-on-ucc-framework/).


## Binary File Declaration

* There are binary files present under the third-party python libraries under the `lib` directory.



CONTRIBUTORS
------------
* Vatsal Jagani


SUPPORT
-------
* Contact - CrossRealms International Inc.
  * US: +1-312-2784445
* License Agreement - https://cdn.splunkbase.splunk.com/static/misc/eula.html
* Copyright - Copyright CrossRealms Internationals, 2024
