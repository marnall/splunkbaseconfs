[comment]: # "Auto-generated SOAR connector documentation"
# Varonis DSP

Publisher: Varonis  
Connector Version: 1\.0\.1  
Product Vendor: Varonis  
Product Name: Data Security Platform  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.4\.0  

Varonis DSP for Splunk SOAR

[comment]: # " File: README.md"
[comment]: # ""
[comment]: # "    Copyright (c) Varonis, 2023"
[comment]: # ""
[comment]: # "This unpublished material is proprietary to Varonis DSP. All"
[comment]: # "rights reserved. The methods and techniques described herein are"
[comment]: # "considered trade secrets and/or confidential. Reproduction or"
[comment]: # "distribution, in whole or in part, is forbidden except by express"
[comment]: # "written permission of Varonis DSP."
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



### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Data Security Platform asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**username** |  required  | string | Name of Varonis user
**password** |  required  | password | Password
**base\_url** |  required  | string | The Base URL to connect to Search service
**ingest\_artifacts** |  required  | boolean | Should artifacts be ingested?
**ingest\_period** |  required  | string | First fetch time
**severity** |  optional  | string | Minimum severity of alerts to fetch
**threat\_model** |  optional  | string | Varonis threat model name
**alert\_status** |  optional  | string | Varonis alert status

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[get alerts](#action-get-alerts) - Get alerts from Varonis DA  
[update alert status](#action-update-alert-status) - Update Varonis alert status command  
[close alert](#action-close-alert) - Close Varonis alert command  
[get alerted events](#action-get-alerted-events) - Get alerted events from Varonis DA  
[on poll](#action-on-poll) - Callback action for the on\_poll ingest functionality  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'get alerts'
Get alerts from Varonis DA

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**threat\_model\_name** |  optional  | List of requested threat models to retrieve | string | 
**page** |  optional  | Page number \(default 1\) | numeric | 
**max\_results** |  optional  | The max number of alerts to retrieve \(up to 50\) | numeric | 
**start\_time** |  optional  | Start time of the range of alerts | string | 
**end\_time** |  optional  | End time of the range of alerts | string | 
**alert\_status** |  optional  | List of required alerts status | string | 
**alert\_severity** |  optional  | List of alerts severity | string | 
**device\_name** |  optional  | List of device names | string | 
**user\_domain\_name** |  optional  | User domain name | string | 
**user\_name** |  optional  | List of user names | string |  `user name` 
**sam\_account\_name** |  optional  | List of sam account names | string | 
**email** |  optional  | List of emails | string |  `email` 
**last\_days** |  optional  | Number of days you want the search to go back to | numeric | 
**descending\_order** |  optional  | Indicates whether alerts should be ordered in newest to oldest order | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action\_result\.status | string |  |   success  failed 
action\_result\.parameter\.alert\_severity | string |  |  
action\_result\.parameter\.alert\_status | string |  |  
action\_result\.parameter\.descending\_order | boolean |  |  
action\_result\.parameter\.device\_name | string |  |  
action\_result\.parameter\.email | string |  `email`  |  
action\_result\.parameter\.end\_time | string |  |  
action\_result\.parameter\.last\_days | numeric |  |  
action\_result\.parameter\.max\_results | numeric |  |  
action\_result\.parameter\.page | numeric |  |  
action\_result\.parameter\.sam\_account\_name | string |  |  
action\_result\.parameter\.start\_time | string |  |  
action\_result\.parameter\.threat\_model\_name | string |  |  
action\_result\.parameter\.user\_domain\_name | string |  |  
action\_result\.parameter\.user\_name | string |  `user name`  |  
action\_result\.data\.\*\.AbnormalLocation | string |  |  
action\_result\.data\.\*\.BlacklistLocation | boolean |  |  
action\_result\.data\.\*\.By\.Department | string |  |  
action\_result\.data\.\*\.By\.PrivilegedAccountType | string |  |  
action\_result\.data\.\*\.By\.SamAccountName | string |  |  
action\_result\.data\.\*\.Category | string |  |  
action\_result\.data\.\*\.CloseReason | string |  |  
action\_result\.data\.\*\.Country | string |  |  
action\_result\.data\.\*\.Device\.ContainMaliciousExternalIP | boolean |  |  
action\_result\.data\.\*\.Device\.IPThreatTypes | string |  |  
action\_result\.data\.\*\.Device\.Name | string |  |  
action\_result\.data\.\*\.EventUTC | string |  |  
action\_result\.data\.\*\.ID | string |  `varonis alert id`  |  
action\_result\.data\.\*\.Name | string |  |  
action\_result\.data\.\*\.NumOfAlertedEvents | numeric |  |  
action\_result\.data\.\*\.On\.Asset | string |  |   DNS 
action\_result\.data\.\*\.On\.ContainsFlaggedData | boolean |  |  
action\_result\.data\.\*\.On\.ContainsSensitiveData | boolean |  |  
action\_result\.data\.\*\.On\.FileServerOrDomain | string |  |   DNS 
action\_result\.data\.\*\.On\.Platform | string |  |   DNS 
action\_result\.data\.\*\.Severity | string |  |   High 
action\_result\.data\.\*\.State | string |  |  
action\_result\.data\.\*\.Status | string |  |   Open 
action\_result\.data\.\*\.Time | string |  |   2022\-11\-11T19\:35\:00 
action\_result\.data\.\*\.UserName | string |  `user name`  |  
action\_result\.summary | string |  |  
action\_result\.message | string |  |  
summary\.total\_objects | numeric |  |  
summary\.total\_objects\_successful | numeric |  |    

## action: 'update alert status'
Update Varonis alert status command

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**status** |  required  | Alert's new status | string | 
**alert\_id** |  required  | Array of alert IDs to be updated | string |  `varonis alert id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action\_result\.status | string |  |   success  failed 
action\_result\.parameter\.alert\_id | string |  `varonis alert id`  |  
action\_result\.parameter\.status | string |  |  
action\_result\.data | string |  |  
action\_result\.summary | string |  |  
action\_result\.message | string |  |  
summary\.total\_objects | numeric |  |  
summary\.total\_objects\_successful | numeric |  |    

## action: 'close alert'
Close Varonis alert command

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**close\_reason** |  required  | Alert's close reason | string | 
**alert\_id** |  required  | Array of alert IDs to be closed | string |  `varonis alert id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action\_result\.status | string |  |   success  failed 
action\_result\.parameter\.alert\_id | string |  `varonis alert id`  |  
action\_result\.parameter\.close\_reason | string |  |  
action\_result\.data | string |  |  
action\_result\.summary | string |  |  
action\_result\.message | string |  |  
summary\.total\_objects | numeric |  |  
summary\.total\_objects\_successful | numeric |  |    

## action: 'get alerted events'
Get alerted events from Varonis DA

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert\_id** |  required  | List of alert IDs | string |  `varonis alert id` 
**page** |  optional  | Page number \(default 1\) | numeric | 
**max\_results** |  optional  | The max number of events to retrieve \(up to 5k\) | numeric | 
**descending\_order** |  optional  | Indicates whether events should be ordered in newest to oldest order | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action\_result\.status | string |  |   success  failed 
action\_result\.parameter\.alert\_id | string |  `varonis alert id`  |  
action\_result\.parameter\.descending\_order | boolean |  |  
action\_result\.parameter\.max\_results | numeric |  |  
action\_result\.parameter\.page | numeric |  |  
action\_result\.data\.\*\.ByUser\.DisabledAccount | boolean |  |  
action\_result\.data\.\*\.ByUser\.Domain | string |  `domain`  |  
action\_result\.data\.\*\.ByUser\.LockoutAccounts | boolean |  |  
action\_result\.data\.\*\.ByUser\.Name | string |  `user name`  |  
action\_result\.data\.\*\.ByUser\.SAMAccountName | string |  |  
action\_result\.data\.\*\.ByUser\.StaleAccount | boolean |  |  
action\_result\.data\.\*\.ByUser\.UserAccountType | string |  |  
action\_result\.data\.\*\.ByUser\.UserType | string |  |  
action\_result\.data\.\*\.Country | string |  |  
action\_result\.data\.\*\.Description | string |  |  
action\_result\.data\.\*\.Details\.IsBlacklist | boolean |  |  
action\_result\.data\.\*\.Details\.Operation | string |  |  
action\_result\.data\.\*\.ExternalIP | string |  `ip`  |  
action\_result\.data\.\*\.ID | string |  |  
action\_result\.data\.\*\.IPReputation | string |  |  
action\_result\.data\.\*\.IPThreatType | string |  |  
action\_result\.data\.\*\.IsMaliciousIP | boolean |  |  
action\_result\.data\.\*\.OnObject\.DestinationDevice | string |  |  
action\_result\.data\.\*\.OnObject\.DestinationIP | string |  `ip`  |  
action\_result\.data\.\*\.OnObject\.FileServerOrDomain | string |  |  
action\_result\.data\.\*\.OnObject\.IsDisabledAccount | boolean |  |  
action\_result\.data\.\*\.OnObject\.IsLockOutAccount | boolean |  |  
action\_result\.data\.\*\.OnObject\.IsSensitive | boolean |  |  
action\_result\.data\.\*\.OnObject\.Name | string |  |  
action\_result\.data\.\*\.OnObject\.ObjectType | string |  |  
action\_result\.data\.\*\.OnObject\.Path | string |  |  
action\_result\.data\.\*\.OnObject\.Platform | string |  |  
action\_result\.data\.\*\.OnObject\.SAMAccountName | string |  |  
action\_result\.data\.\*\.OnObject\.UserAccountType | string |  |  
action\_result\.data\.\*\.SourceIP | string |  `ip`  |  
action\_result\.data\.\*\.State | string |  |  
action\_result\.data\.\*\.Status | string |  |  
action\_result\.data\.\*\.Type | string |  |  
action\_result\.data\.\*\.UTCTime | string |  |  
action\_result\.summary | string |  |  
action\_result\.message | string |  |  
summary\.total\_objects | numeric |  |  
summary\.total\_objects\_successful | numeric |  |    

## action: 'on poll'
Callback action for the on\_poll ingest functionality

Type: **ingest**  
Read only: **True**

The default start\_time is the past 5 days\. The default end\_time is now\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container\_id** |  optional  | Parameter ignored for this app | string | 
**start\_time** |  optional  | Parameter ignored for this app | numeric | 
**end\_time** |  optional  | Parameter ignored for this app | numeric | 
**container\_count** |  optional  | Maximum number of containers to create | numeric | 
**artifact\_count** |  optional  | Maximum number of artifacts to create per container | numeric | 

#### Action Output
No Output