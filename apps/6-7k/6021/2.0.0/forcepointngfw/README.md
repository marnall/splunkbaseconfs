[comment]: # "Auto-generated SOAR connector documentation"
# Forcepoint

Publisher: Martin Ohl  
Connector Version: 2.0.0  
Product Vendor: Forcepoint  
Product Name: Forcepoint NGFW  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 5.5.0  

This app integrates with Forcepoint Firewall

[comment]: # " File: README.md"
[comment]: # "  Copyright Martin Ohl 2021-2023"
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
# Forcepoint Firewall

This app integrates with Forcepoint Firewall

### Configuration Variables

The below configuration variables are required for this Connector to operate. These variables are
specified when configuring a NGFW asset in SOAR.

| VARIABLE               | REQUIRED | TYPE     | DESCRIPTION                |
|------------------------|----------|----------|----------------------------|
| **base_url**           | required | string   | SMC IP address or hostname |
| **verify_server_cert** | required | boolean  | Verify server certificate  |
| **base_port**          | required | string   | SMC API Port               |
| **auth_key**           | required | password | SMC API Auth Key           |
| **base_version**       | required | string   | SMC Version (e.g. 6.2)     |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity
using supplied configuration  
[block ip](#action-block-ip) - Block an IP

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'block ip'

Block an IP

Type: **contain**  
Read only: **False**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION              | TYPE   | CONTAINS            |
|-----------|----------|--------------------------|--------|---------------------|
| **ip**    | required | IP to block              | string | `        ip       ` |
| **group** | required | Group Name to add the IP | string |                     |

#### Action Output

| DATA PATH                        | TYPE    | CONTAINS            |
|----------------------------------|---------|---------------------|
| action_result.parameter.ip       | string  | `        ip       ` |
| action_result.status             | string  |                     |
| action_result.message            | string  |                     |
| summary.total_objects            | numeric |                     |
| summary.total_objects_successful | numeric |                     |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Forcepoint NGFW asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** |  required  | string | SMC IP address or hostname
**verify_server_cert** |  optional  | boolean | Verify server certificate
**base_port** |  required  | string | SMC API Port
**auth_key** |  required  | password | SMC API Auth Key
**base_version** |  required  | string | SMC Version (e.g. 6.2)

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[block ip](#action-block-ip) - Block an IP  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

Tests api connectivity by making a login/logout call to SMC api.

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'block ip'
Block an IP

Type: **contain**  
Read only: **False**

Updates Bad IP list.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** |  required  | IP to block | string |  `ip` 
**group** |  required  | Group Name to add the IP | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.group | string |  |  
action_result.parameter.ip | string |  `ip`  |  
action_result.data | string |  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  