[comment]: # "Auto-generated SOAR connector documentation"
# Cisco Catalyst

Publisher: Splunk Community  
Connector Version: 2\.0\.0  
Product Vendor: Cisco Systems  
Product Name: Cisco Catalyst  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.1\.0  

This app supports containment actions like 'set system vlan' in addition to investigative actions like 'get config' and 'get version' on a Cisco Catalyst switch

[comment]: # " "
[comment]: # "    File: README.md"
[comment]: # "    Copyright (c) 2014-2022 Splunk Inc."
[comment]: # ""
[comment]: # "    Licensed under Apache 2.0 (https://www.apache.org/licenses/LICENSE-2.0.txt)"
[comment]: # ""
[comment]: # ""
It uses ssh to login to the Catalyst switch and carry out cli commands on it. The app takes care of
the ssh session but ssh access has to be enabled on the catalyst switch.


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Cisco Catalyst asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**device** |  required  | string | Device IP/Hostname
**username** |  required  | string | Username
**password** |  required  | password | Password
**enable\_password** |  required  | password | Password used to enter the 'enable' mode

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity\. This action runs a few commands on the device to check the connection and credentials  
[get config](#action-get-config) - Gets the current running config of the device  
[get version](#action-get-version) - Gets the software version information of the device  
[vlan host](#action-vlan-host) - Set the vlan of the port on which the host is connected  

## action: 'test connectivity'
Validate the asset configuration for connectivity\. This action runs a few commands on the device to check the connection and credentials

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'get config'
Gets the current running config of the device

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.data\.\*\.command | string | 
action\_result\.data\.\*\.output | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get version'
Gets the software version information of the device

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.data\.\*\.command | string | 
action\_result\.data\.\*\.output | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'vlan host'
Set the vlan of the port on which the host is connected

Type: **contain**  
Read only: **False**

This action takes as input either a MAC address or an IP\. If an IP is specified, it will try to get the MAC address for that IP\. It executes the 'show ip device tracking ip \{ip\} \| include \{ip\} ' command to get to the MAC address\. If this call fails to get any data, that means the device currently does not have any information about the IP\. It then proceeds to ping the IP from the device \(action parameters permitting\)\. Once the MAC address is known, the port that the MAC address is connected to is queried by running the 'show mac address\-table address \{mac\_addr\} \| include \{mac\_addr\} ' command\. This command gives back a switchport\. Once the switchport is known, the vlan of the switchport is modified to the required value\. If the switchport happens to be a trunk port, then the vlan is only changed if the action parameters permit it\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip\_macaddress** |  required  | MAC or IP address of device to query | string |  `mac address`  `ip` 
**ping\_ip** |  optional  | Ping IP if not found on device | boolean | 
**vlan\_id** |  required  | VLAN Id | numeric | 
**override\_trunk** |  optional  | Set VLAN even if port is a trunk port | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.override\_trunk | boolean | 
action\_result\.parameter\.ip\_macaddress | string |  `mac address`  `ip` 
action\_result\.parameter\.ping\_ip | boolean | 
action\_result\.parameter\.vlan\_id | string | 
action\_result\.message | string | 
action\_result\.summary\.mac\_address | string |  `mac address` 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 