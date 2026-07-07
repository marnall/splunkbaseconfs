[comment]: # "Auto-generated SOAR connector documentation"
# Cisco ASA

Publisher: Splunk Community  
Connector Version: 3\.0\.0  
Product Vendor: Cisco Systems  
Product Name: Cisco ASA  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.1\.0  

This app supports containment actions in addition to investigative actions on a Cisco ASA device

[comment]: # "File: README.md"
[comment]: # "Copyright (c) 2014-2022 Splunk Inc."
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""
It uses ssh to login to the ASA box and carry out cli commands on it. The app takes care of the ssh
session but ssh access has to be enabled on the ASA box.


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Cisco ASA asset in SOAR.

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
[block ip](#action-block-ip) - Block an IP  
[unblock ip](#action-unblock-ip) - Unblock an IP  
[list sessions](#action-list-sessions) - List the current VPN sessions  
[terminate session](#action-terminate-session) - Terminates all VPN sessions of a user  

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
action\_result\.data\.\*\.command | string | 
action\_result\.data\.\*\.output | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
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
action\_result\.data\.\*\.command | string | 
action\_result\.data\.\*\.output | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'block ip'
Block an IP

Type: **contain**  
Read only: **False**

This action requires parameters like 'access\_list' and 'interface' to be specified\. It's usually a good idea to run 'get config' and 'get version' before to get this information\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**dest** |  required  | Dest IP address, can be 'any' or in CIDR format | string |  `ip` 
**src** |  required  | Source IP address, can be 'any' or in CIDR format | string |  `ip` 
**direction** |  required  | Rule direction | string | 
**access\_list** |  required  | Access\-list name | string | 
**interface** |  required  | Interface name to apply the rule on | string | 
**line** |  optional  | Line \#; position of the rule, defaults to '1' | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.access\_list | string | 
action\_result\.parameter\.dest | string |  `ip` 
action\_result\.parameter\.direction | string | 
action\_result\.parameter\.interface | string | 
action\_result\.parameter\.line | numeric | 
action\_result\.parameter\.src | string |  `ip` 
action\_result\.data | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'unblock ip'
Unblock an IP

Type: **correct**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**dest** |  required  | Dest IP address, can be 'any' or in CIDR format | string |  `ip` 
**src** |  required  | Source IP address, can be 'any' or in CIDR format | string |  `ip` 
**direction** |  required  | Rule direction | string | 
**access\_list** |  required  | Access\-list name | string | 
**interface** |  required  | Interface name to apply the rule on | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.access\_list | string | 
action\_result\.parameter\.dest | string |  `ip` 
action\_result\.parameter\.direction | string | 
action\_result\.parameter\.interface | string | 
action\_result\.parameter\.src | string |  `ip` 
action\_result\.data | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list sessions'
List the current VPN sessions

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.data\.\*\.users\.\*\.BytesRx | string | 
action\_result\.data\.\*\.users\.\*\.BytesTx | string | 
action\_result\.data\.\*\.users\.\*\.Duration | string | 
action\_result\.data\.\*\.users\.\*\.Encryption | string | 
action\_result\.data\.\*\.users\.\*\.GroupPolicy | string | 
action\_result\.data\.\*\.users\.\*\.Hashing | string | 
action\_result\.data\.\*\.users\.\*\.Inactivity | string | 
action\_result\.data\.\*\.users\.\*\.Index | string | 
action\_result\.data\.\*\.users\.\*\.License | string | 
action\_result\.data\.\*\.users\.\*\.LoginTime | string | 
action\_result\.data\.\*\.users\.\*\.NACResult | string | 
action\_result\.data\.\*\.users\.\*\.Protocol | string | 
action\_result\.data\.\*\.users\.\*\.PublicIP | string |  `ip` 
action\_result\.data\.\*\.users\.\*\.TunnelGroup | string | 
action\_result\.data\.\*\.users\.\*\.Username | string |  `user name` 
action\_result\.data\.\*\.users\.\*\.VLAN | string | 
action\_result\.data\.\*\.users\.\*\.VLANMapping | string | 
action\_result\.summary\.total\_users | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'terminate session'
Terminates all VPN sessions of a user

Type: **contain**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**username** |  required  | User to logoff | string |  `user name` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.username | string |  `user name` 
action\_result\.data | string | 
action\_result\.summary\.sessions\_terminated | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 