# Splunk-CEF-Parser-Command

### Download from Splunkbase
https://splunkbase.splunk.com/app/7701/



## Overview

Splunk App for CEF formatted data parsing with Splunk Custom Command inline in the search from any field or from extracted fields or from _raw data.

The common event format is an event exchange syntax. A sample message formatted as CEF looks as follows in the `Usage` section.

* Author - Vatsal Jagani
* Creates Index - False
* Compatible with:
   * Splunk Cloud
   * Splunk Enterprise version: 10.2.x, 10.0.x, 9.4.x, 9.3.x, 9.2.x
   * OS: Platform Independent
   * Browser: Browser Independent


## What's inside the App

* No of Custom Commands: **1**




## Topology and Setting Up Splunk Environment

This app can be set up in two ways: 
  1. Standalone Mode: 
     * Install the `CEF Parser Search Command`.
  2. Distributed Mode: 
     * Install the `CEF Parser Search Command` on the search head. The App configuration is not required.
     * The App is not-needed on any other component of Splunk.



## Installation

The App only requires to be installed on the Search Head and No configuration is needed.

* From the Splunk Web home screen, click the gear icon next to Apps. 
* Click on `Browse more apps`.
* Search for `CEF Parser Search Command` and click Install. 
* Restart Splunk if you are prompted.



## Configuration

No App configuration is needed.



## Usage

In order to parse CEF data correctly in Splunk, this Splunk App provides a custom Splunk search command:
* It will extract CEF Headers and other extended fields from the event in Splunk.
* User just need to use `cefparser` Splunk command.

Example Search:
```
index=my_index 
| rex field=_raw "regex to extract cef data from full _raw event (?<cef_data>.+)
| cefparser field="cef_data"
| table _time, cef_data, DeviceVendor, DeviceProduct, DeviceVersion, DeviceEventClassID, DeviceName, Severity, DeviceSeverity, src_addr, *
```

Example Event:
```
CEF:0|Splunk|Test|1.0|signature:2|Test event|5|cs1=custom string value cs1Label=custom label src_addr=10.0.0.0 dest_addr=20.0.0.2 src_port=32122 dest_port=80
```

Output Fields:
* "DeviceVendor": "Splunk"
* "DeviceProduct": "Test"
* "DeviceVersion": "1.0"
* "DeviceEventClassID": "signature:2"
* "Name": "Test event"
* "DeviceName": "Test event"
* "Severity": "5"
* "DeviceSeverity": "5"
* "CEFVersion": "0"
* "src_addr": "10.0.0.0"
* "dest_addr": "20.0.0.2"
* "src_port": "32122"
* "dest_port": "80"
* "custom label": "custom string value"



## Uninstall App
-------------
To uninstall app, user can follow below steps:
* SSH to the Splunk instance.
* Go to folder apps($SPLUNK_HOME/etc/apps).
* Remove the `CEF_Parser_Command` folder from `apps` directory.
* Remove the DB Connect Identity, Connection and Inputs that you have created.
* Restart Splunk.


## Open Source Components and License
* Splunklib (Splunk SDK for Python)



## Release Notes

#### Version 1.0.1 (Apr 2026)
* Splunklib (splunk-sdk) updated to version 2.1.1

#### Version 1.0.0 (Dec 2024)
* App built with Splunk App with `cerparser` command.


## Contributors
* Vatsal Jagani


## Support

* Contact - Vatsal Jagani
* License Agreement - https://cdn.splunkbase.splunk.com/static/misc/eula.html
* Copyright - Vatsal Jagani, 2026
