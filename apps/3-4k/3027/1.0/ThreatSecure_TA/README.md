## ThreatSecure Network Add-on v1.0

## Overview

* ThreatSecure Add-on to collect syslog data from **ThreatSecure Network Appliance**.

## Hardware and software requirements

* Splunk 6.0+
* ThreatSecure Network 2.0+ with latest *syslog.ftl* file.
* Java Runtime Environment 1.7+
* Supported on Windows, Linux

### Splunk Enterprise system requirements

Because this add-on runs on Splunk Enterprise, all of the Splunk Enterprise system requirements apply.

## Setup

1. From the Splunk web interface, click on **Apps > Manage Apps** to open the Apps Management page.
2. Click **Install app from file**, locate the ***ThreatSecure_TA*** tar file, and click **Upload**.
3. To configure data input from Splunk web interface, click on **Settings > Data inputs** to open Data Input Management page.
4. To add new data input for ThreatSecure, click on **Add new** link.
5. Enter name for data input and port on which this data input should listen for syslog data. Click **Next**.

> **Note:** If you are updating ThreatSecure Add-on, please make sure to disable configured running ThreatSecure data inputs before updating to new version. After updating ThreatSecure Add-on, enable the disabled data inputs configuration.

## Configuration

  ThreatSecure Network Add-on can be configured via **Manager->Data Inputs->ThreatSecure**

## Logging

* Any log entries/errors will get written to $SPLUNK_HOME/var/log/splunk/splunkd.log with prefix "ThreatSecure_TA ::".  
 e.g. : 01-08-2016 18:10:26.578 +0530 INFO  ExecProcessor - message from "/opt/splunk/etc/apps/ThreatSecure_TA/linux_x86_64/bin/threatsecureaddon.sh" ThreatSecure_TA :: Add-on connection established for configuration TSN_LAB. Waiting for syslog on port : 9900

## Known issues

* Keeping the same port number while edit operation (editing port number) on existing enabled configuration, after few seconds configuration gets disabled.

## Troubleshooting

* You are using Splunk 6+.
* Java Runtime Environment is configured.
* Look for any errors in $SPLUNK_HOME/var/log/splunk/splunkd.log by running Splunk in debug mode. To start Splunk in debug mode, below command can be used.  
*splunk start --debug*

## Contact

* [Threat Track Support](http://threatsupport.threattracksecurity.com/support/)
* Technical Support :  *Phone : 844.847.3285*