# Dell EMC PowerFlex Add-on for Splunk #

This is an add-on powered by the Splunk Add-on Builder.

## Overview

Splunk Add-ons typically imports and enriches data from any source, thus creating a rich dataset ready for direct analysis or use in an App. The Dell EMC PowerFlex Add-on for Splunk provides the functionality to collect data from PowerFlex OS using REST endpoints and stores the collected data in Splunk indexes. Additionally, the Add-ons categorizes the data into different source types, parses the data and extracts important fields.

* Author - Crest Data Systems
* Version - 1.0.0
* Build - 1
* Creates Index - False
* Uses Sourcetype: 1) powerflex:instance:<powerflex_instance_name> 2) powerflex:statistics:<powerflex_instance_name> 3) powerflex:alerts
* Uses KV Store - True. This Add-on uses Splunk KV Store for checkpoint mechanism
* Uses Dell EMC PowerFlex OS Rest API version 2.6 and 3.1 to collect the data
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

NOTE: After rebranding to Powerflex, we will not be supporting upgrades from the older versions. Historical data will not be removed in case of updating to the new version.

Caution: After rebranding changes, data will be collected again as we will not be able to use old checkpoint files.

Steps to move to the newly rebranded version:

    1.Install newly branded App and Add-on
    2.Disable old branded App and Add-on
    3.Create new inputs and configuration
    4.Restart Splunk
    5.Enable all inputs if those are disabled
    6.Wait for the data being collected
    7.Restart Splunk
## Configuration

To configure a Dell PowerFlex System:

1.	Log in as administrator and select Dell EMC PowerFlex Add-on for Splunk > Configuration > Systems. 
2.	Click Add option available in the upper-right corner of the GUI. 
3.	 Enter the mandatory details in the Add Systems window and click Add. Refer the following table to enter details

    | Input Name | Required | Description |
    | ---------- | -------- | ----------- |
    | Name | Yes | Unique name for the PowerFlex System. This box will not accept any space in name |
    | Gateway URI  | Yes | The IP address or hostname with port number (if any). Ex, <ip_address>:443 |
    | Username | Yes | The username for the gateway endpoint |
    | Password | Yes | The password for the above gateway endpoint |


To configure an input:

1.	Log in as administrator and select Dell EMC PowerFlex Add-on for Splunk > Inputs. 
2.	Click Create New Input option available in the upper-right corner of the GUI. 
3.	Select required option from the drop-down menu: PowerFlex OS Instance and PowerFlex OS Statistics. 
4.	Enter the mandatory details as specified in the dialog box and click Add. 

PowerFlex OS Instance Details:

    | Input  Name | Required | Description |
    | ----------- | -------- | ----------- |
    | Name                      | Yes | Unique name for the data input |
    | PowerFlex System             | Yes | PowerFlex System for the input |
    | Instances Rest Endpoint   | Yes | Rest endpoint from which the list of instances should be collected. Ex./api/types/Volume/instances |
    | Request Method            | Yes | Request method for instances REST endpoint | 
    | Interval                  | Yes | Interval in seconds or a valid cron schedule at which the data should be collected |
    | Index                     | Yes | Index in which the data should be collected. Defaults to default index |


PowerFlex OS Statistics Details:

    | Input  Name | Required | Description |
    | ----------- | -------- | ----------- |
    | Name                      | Yes | Unique name for the data input |
    | PowerFlex System             | Yes | PowerFlex System for the input |
    | Instances Rest Endpoint   | Yes | The rest endpoint which provides the list of instances for which the statistics should be collected. Ex. /api/types/Volume/instances |
    | Statistics Rest Endpoint  | Yes | Rest endpoint of the statistics which should be collected for instances. Ex. /api/instances/Volume::{id}/relationships/Statistics |
    | Request Method            | Yes | Request method for instances REST endpoint | 
    | Interval                  | Yes | Interval in seconds or a valid cron schedule at which the data should be collected |
    | Index                     | Yes | Index in which the data should be collected. Defaults to default index |


### Establishing secured communication

Generally, for communication with Splunk and PowerFlex OS gateway requires secured communication and trusted SSL certificates. If gateway is not secured with trusted SSL certificates, it can result in communication issues. 
If PowerFlex OS gateways have secured communication, then you do not require secured SSL certificate and hence must disable SSL checks. But in both cases, Splunk verifies to ensure secured communication channel with PowerFlex OS cluster or gateway.

#### Data collection from PowerFlex OS gateway with trusted SSL certificate
Dell EMC PowerFlex Add-on supports HTTPs connection and SSL check for communication between Splunk and PowerFlex OS. 
1.	Obtain required certificates for the successful SSL verification with PowerFlex OS instance. 
2.	Copy this self-signed certificate content (PEM) to SPLUNK_HOME/etc/apps/TA-dell_powerflex/bin/ta_dell_powerflex/requests/cacert.pem. 
3.	Configure required number of PowerFlex OS gateways from Splunk GUI. See, Add Systems.

#### Data collection from PowerFlex OS gateway with non-secured SSL certificate
Note: This method is unsafe and not recommended.

To configure the PowerFlex OS gateway to collect data through unencrypted communication (without certificate checks), you must disable the SSL check flag. 
To disable SSL check flag, complete the following steps:
1.	Create a local folder in TA-dell_powerflex folder.
2.	Update the ta_dell_powerflex_settings.conf and add the following statements:
ssl_verification = 0
http_scheme = http
3.	Restart Splunk Enterprise.
4.	Configure required number of PowerFlex OS gateways from Splunk GUI. See, Add Systems section.
 

## List of Sourcetypes

The Dell EMC PowerFlex Add-on for Splunk provides the search-time knowledge for Dell PowerFlex data in the following formats: 

| Data Source | Sourcetype | API | CIM Models |
| ----------- | ---------- | --- | ---------- |
| Systems Information | powerflex:instance:system | /api/types/System/instances | Inventory |
| Systems Statistics | powerflex:statistics:system | /api/instances/System::{id}/relationships/Statistics | Performance |
| Protection Domain Instances | powerflex:instance:pd | /api/types/ProtectionDomain/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Protection Domain Statistics | powerflex:statistics:pd | /api/instances/ProtectionDomain::{id}/relationships/Statistics | Performance |
| Fault Set Instances | powerflex:instance:faultset | /api/types/FaultSet/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Fault Set Statistics | powerflex:statistics:faultset | /api/instances/FaultSet::{id}/relationships/Statistics | Performance |
| SDS Instances | powerflex:instance:sds | /api/types/Sds/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| SDS Statistics | powerflex:statistics:sds | /api/instances/Sds::{id}/relationships/Statistics | Performance |
| Storage Pool Instances | powerflex:instance:sp | /api/types/StoragePool/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Storage Pool Statistics | powerflex:statistics:sp | /api/instances/StoragePool::{id}/relationships/Statistics | Performance |
| Device Instances | powerflex:instance:device | /api/types/Device/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Device Statistics | powerflex:statistics:device | /api/instances/Device::{id}/relationships/Statistics | Performance |
| Volume Instances | powerflex:instance:volume | /api/types/Volume/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| Volume Statistics | powerflex:statistics:volume | /api/instances/Volume::{id}/relationships/Statistics | Performance |
| VTree Instances | powerflex:instance:vtree | /api/types/VTree/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| VTree Statistics | powerflex:statistics:vtree | /api/instances/VTree::{id}/relationships/Statistics | Performance |
| SDC Instances | powerflex:instance:sdc | /api/types/Sdc/instances?systemId={system id}&sessionTag={session tag}&lastVersion={last version} | Inventory |
| SDC Statistics | powerflex:statistics:sdc | /api/instances/Sdc::{id}/relationships/Statistics | Performance |
| Alerts | powerflex:alerts | /api/types/Alert/instances | Alert |
| Replication Consistency Group Instances| powerflex:instance:rcg | /api/types/ReplicationConsistencyGroup/instances
| Replication Consistency Group Statistics | powerflex:statistics:rcg | /api/instances/ReplicationConsistencyGroup::{id}/relationships/Statistics
| Replication Pair Instances | powerflex:instance:rp | /api/types/ReplicationPair/instances
| Replication Pair Statistics | powerflex:statistics:rp | /api/instances/ReplicationPair::{id}/relationships/Statistics
| SDR Instances | powerflex:instance:sdr | /api/types/Sdr/instances
| SDR Statistics | powerflex:statistics:sdr | /api/instances/Sdr::{id}/relationships/Statistics
| PeerMDM Instances | powerflex:instance:peermdm | /api/types/PeerMdm/instances
| PeerMDM Statistics | powerflex:statistics:peermdm | /api/instances/PeerMdm::{id}/relationships/Statistics


## Troubleshooting
See, Troubleshooting section in Dell EMC PowerFlex Add-on and App for Splunk User Guide. For complete information, see Dell EMC PowerFlex Add-on and App for Splunk User Guide in https://infohub.delltechnologies.com/t/powerflex/ .

## Uninstall App
To uninstall an app, user can follow below steps: SSH to the Splunk instance -> Go to folder apps ($SPLUNK_HOME/etc/apps) -> Remove the TA_dell_powerflex folder from apps directory -> Restart Splunk

## Support

* Support Offered: Yes
* Support Email: dell-support@crestdatasys.com

### Copyright (C) 2020 Dell Technologies Inc. All Rights Reserved.

## Open Source Components And Licenses

Some of the components included in Dell EMC PowerFlex Add-on for Splunk are licensed under free or open source licenses. We wish to thank the contributors to those projects

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


## Release Notes:
* Introduced the following new sourcetypes pertaining to replication data API endpoints:
    * powerflex:instance:peermdm
    * powerflex:statistics:peermdm
    * powerflex:instance:sdr
    * powerflex:statistics:sdr
    * powerflex:instance:rcg
    * powerflex:statistics:rcg
    * powerflex:instance:rp
    * powerflex:statistics:rp