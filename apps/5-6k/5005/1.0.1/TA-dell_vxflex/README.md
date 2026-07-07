# Dell EMC VxFlex integrated rack Add-on for Splunk #

This is an add-on powered by the Splunk Add-on Builder.

## Overview

Splunk Add-ons typically imports and enriches data from any source, thus creating a rich dataset ready for direct analysis or use in an App. The Dell EMC VxFlex integrated rack Add-on for Splunk provides the functionality to collect data from VxFlex OS using REST endpoints and stores the collected data in Splunk indexes. Additionally, the Add-ons categorizes the data into different source types, parses the data and extracts important fields.

* Author - Crest Data Systems
* Version - 1.0.1
* Build - 85
* Creates Index - False
* Uses Sourcetype: 1) vxflex:instance:<vxlfex_instance_name> 2) vxflex:statistics:<vxlfex_instance_name> 3) vxflex:alerts
* Uses KV Store - True. This Add-on uses Splunk KV Store for checkpoint mechanism
* Uses Dell EMC VxFlex OS Rest API version 2.6 and 3.1 to collect the data
* Compatible with:
    * Splunk Enterprise version: 7.2, 7.3 and 8.0
    * OS: CentOS, Windows
    * Browser: Google Chrome, Mozilla Firefox

## Recommended System Configuration

Splunk forwarder system should have 12 GB of RAM and a six-core CPU to run this Technology Add-on smoothly.

## Installation

This Add-on is supported on all the tiers of distributed Splunk platform deployment and also on standalone Splunk instance. Below table provides the reference for installing the Add-on on distributed Splunk deployment:


| Splunk instance type  | Supported  | Required | Comments |
| --------------------- | ---------- | --------- | -------- |
| Search Heads          | Yes | Yes | This Add-on is required on Search Heads as it contains search time extractions. This Add-on also contains alert actions. To use these actions user need to configure the Add-on on Search Head.|
|Indexers               | Yes | No | All parsing will be done on heavy forwarder only.|
| Heavy Forwarders      | Yes |Yes | This Add-on supports only heavy forwarder for data collection.| 


To install the App based on your deployment, refer the following links:

* [Single-instance Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Singleserverinstall)
* [Distributed Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Distributedinstall)
* [Splunk Cloud](https://docs.splunk.com/Documentation/AddOns/latest/Overview/SplunkCloudinstall)


## Configuration

To configure a Dell VxFlex System:

1.	Log in as administrator and select Dell EMC VxFlex integrated rack Add-on for Splunk > Configuration > Systems. 
2.	Click Add option available in the upper-right corner of the GUI. 
3.	 Enter the mandatory details in the Add Systems window and click Add. Refer the following table to enter details

    | Input Name | Required | Description |
    | ---------- | -------- | ----------- |
    | Name | Yes | Unique name for the VxFlex System. This box will not accept any space in name |
    | Gateway URI  | Yes | The IP address or hostname with port number (if any). Ex, <ip_address>:443 |
    | Username | Yes | The username for the gateway endpoint |
    | Password | Yes | The password for the above gateway endpoint |


To configure an input:

1.	Log in as administrator and select Dell EMC VxFlex integrated rack Add-on for Splunk > Inputs. 
2.	Click Create New Input option available in the upper-right corner of the GUI. 
3.	Select required option from the drop-down menu: VxFlex OS Instance and VxFlex OS Statistics. 
4.	Enter the mandatory details as specified in the dialog box and click Add. 

VxFlex OS Instance Details:

    | Input  Name | Required | Description |
    | ----------- | -------- | ----------- |
    | Name                      | Yes | Unique name for the data input |
    | VxFlex System             | Yes | VxFlex System for the input |
    | Instances Rest Endpoint   | Yes | Rest endpoint from which the list of instances should be collected. Ex./api/types/Volume/instances |
    | Request Method            | Yes | Request method for instances REST endpoint | 
    | Interval                  | Yes | Interval in seconds or a valid cron schedule at which the data should be collected |
    | Index                     | Yes | Index in which the data should be collected. Defaults to default index |


VxFlex OS Statistics Details:

    | Input  Name | Required | Description |
    | ----------- | -------- | ----------- |
    | Name                      | Yes | Unique name for the data input |
    | VxFlex System             | Yes | VxFlex System for the input |
    | Instances Rest Endpoint   | Yes | The rest endpoint which provides the list of instances for which the statistics should be collected. Ex. /api/types/Volume/instances |
    | Statistics Rest Endpoint  | Yes | Rest endpoint of the statistics which should be collected for instances. Ex. /api/instances/Volume::{id}/relationships/Statistics |
    | Request Method            | Yes | Request method for instances REST endpoint | 
    | Interval                  | Yes | Interval in seconds or a valid cron schedule at which the data should be collected |
    | Index                     | Yes | Index in which the data should be collected. Defaults to default index |


### Establishing secured communication

Generally, for communication with Splunk and VxFlex OS gateway requires secured communication and trusted SSL certificates. If gateway is not secured with trusted SSL certificates, it can result in communication issues. 
If VxFlex OS gateways have secured communication, then you do not require secured SSL certificate and hence must disable SSL checks. But in both cases, Splunk verifies to ensure secured communication channel with VxFlex OS cluster or gateway.

#### Data collection from VxFlex OS gateway with trusted SSL certificate
Dell EMC VxFlex integrated rack Add-on supports HTTPs connection and SSL check for communication between Splunk and VxFlex OS. 
1.	Obtain required certificates for the successful SSL verification with VxFlex OS instance. 
2.	Copy this self-signed certificate content (PEM) to SPLUNK_HOME/etc/apps/TA-dell_vxflex/bin/ta_dell_vxflex/requests/cacert.pem. 
3.	Configure required number of VxFlex OS gateways from Splunk GUI. See, Add Systems.

#### Data collection from VxFlex OS gateway with non-secured SSL certificate
Note: This method is unsafe and not recommended.

To configure the VxFlex OS gateway to collect data through unencrypted communication (without certificate checks), you must disable the SSL check flag. 
To disable SSL check flag, complete the following steps:
1.	Create a local folder in TA-dell_vxflex folder.
2.	Update the ta_dell_vxflex_settings.conf and add the following statements:
ssl_verification = 0
http_scheme = http
3.	Restart Splunk Enterprise.
4.	Configure required number of VxFlex OS gateways from Splunk GUI. See, Add Systems section.
 

## List of Sourcetypes

The Dell EMC VxFlex integrated rack Add-on for Splunk provides the search-time knowledge for Dell VxFlex data in the following formats: 

| Data Source | Sourcetype | API | CIM Models |
| ----------- | ---------- | --- | ---------- |
| Systems Information | vxflex:instance:system | /api/types/System/instances | Inventory |
| Systems Statistics | vxflex:statistics:system | /api/instances/System::{id}/relationships/Statistics | Performance |
| Protection Domain Instances | vxflex:instance:pd | /api/types/ProtectionDomain/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Protection Domain Statistics | vxflex:statistics:pd | /api/instances/ProtectionDomain::{id}/relationships/Statistics | Performance |
| Fault Set Instances | vxflex:instance:faultset | /api/types/FaultSet/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Fault Set Statistics | vxflex:statistics:faultset | /api/instances/FaultSet::{id}/relationships/Statistics | Performance |
| SDS Instances | vxflex:instance:sds | /api/types/Sds/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| SDS Statistics | vxflex:statistics:sds | /api/instances/Sds::{id}/relationships/Statistics | Performance |
| Storage Pool Instances | vxflex:instance:sp | /api/types/StoragePool/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Storage Pool Statistics | vxflex:statistics:sp | /api/instances/StoragePool::{id}/relationships/Statistics | Performance |
| Device Instances | vxflex:instance:device | /api/types/Device/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Device Statistics | vxflex:statistics:device | /api/instances/Device::{id}/relationships/Statistics | Performance |
| Volume Instances | vxflex:instance:volume | /api/types/Volume/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Volume Statistics | vxflex:statistics:volume | /api/instances/Volume::{id}/relationships/Statistics | Performance |
| VTree Instances | vxflex:instance:vtree | /api/types/VTree/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| VTree Statistics | vxflex:statistics:vtree | /api/instances/VTree::{id}/relationships/Statistics | Performance |
| SDC Instances | vxflex:instance:sdc | /api/types/Sdc/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| SDC Statistics | vxflex:statistics:sdc | /api/instances/Sdc::{id}/relationships/Statistics | Performance |
| Alerts | vxflex:alerts | /api/types/Alert/instances | Alert |

## Release Notes

### V1.0.1

* Added python3 default flag in restmap.conf and inputs.conf


### V1.0.0

* Ability to configure multiple systems
* Data collection with 2 types of modular inputs. 1) VxFlex Instance 2) VxFlex Statistics
* Data normalization & CIM mapping
* Proxy support

## Troubleshooting
See, Troubleshooting section in Dell EMC VxFlex integrated rack Add-on and App for Splunk User Guide. For complete information, see Dell EMC VxFlex integrated rack Add-on and App for Splunk User Guide in https://infohub.delltechnologies.com/t/vxflex/ .

## Support

* Support Offered: Yes
* Support Email: dell-support@crestdatasys.com

### Copyright (C) 2020 Dell Technologies Inc. All Rights Reserved.

## Open Source Components And Licenses

Some of the components included in Dell EMC VxFlex integrated rack Add-on for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects

| Component name | Version | Source | License |
|----------------|---------|------|---------|
| requests          | 2.22.0    | https://github.com/requests/requests/ | https://github.com/requests/requests/blob/master/LICENSE |
| six               | 1.13.0    | https://github.com/benjaminp/six      | https://github.com/benjaminp/six/blob/master/LICENSE      |
| jsonpath-rw       | 1.4.0     | https://github.com/kennknowles/python-jsonpath-rw | https://github.com/kennknowles/python-jsonpath-rw/blob/master/LICENSE |
| jsonschema        | 3.1.1     | https://github.com/Julian/jsonschema | https://github.com/Julian/jsonschema/blob/master/COPYING |
| munch             | 2.5.0     | https://github.com/Infinidat/munch | https://github.com/Infinidat/munch/blob/develop/LICENSE.txt | 
| functools32       | 3.2.3-2   | https://github.com/MiCHiLU/python-functools32 | https://github.com/michilu/python-functools32/blob/master/LICENSE |
| schematics        | 2.1.0     | https://github.com/schematics/schematics | https://github.com/schematics/schematics/blob/master/LICENSE | 
| sortedcontainers  | 2.1.0     | https://pypi.python.org/pypi/sortedcontainers | http://www.apache.org/licenses/LICENSE-2.0 |
| jinja2            | 2.10.3    | https://github.com/pallets/jinja | https://github.com/pallets/jinja/blob/master/LICENSE.rst |
| PySocks           | 1.7.1     | https://pypi.python.org/pypi/PySocks | https://github.com/Anorov/PySocks/blob/master/LICENSE |
| decorator         | 4.1.2     | https://github.com/micheles/decorator | https://github.com/micheles/decorator/blob/master/LICENSE.txt |
