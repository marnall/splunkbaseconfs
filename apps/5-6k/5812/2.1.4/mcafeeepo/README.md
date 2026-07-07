# McAfee ePO

Publisher: Splunk \
Connector Version: 2.1.4 \
Product Vendor: McAfee \
Product Name: McAfee ePO \
Minimum Product Version: 5.2.0

This app implements various endpoint based investigative and containment actions by integrating with McAfee ePO

### ePO's Default Permission Set

ePO ships with four default permission sets that provide permissions to ePO functionality. The
default permission sets available are:

- Executive Reviewer
- Global Reviewer
- Group Admin
- Group Reviewer

For all the actions to execute without any dispute any of the following combinations of permissions
will work :

- ( Executive Reviewer , Group Admin )
- ( Global Reviewer , Group Admin )
- ( Executive Reviewer , Global Reviewer , Group Admin )
- ( Executive Reviewer , Global Reviewer , Group Admin , Group Reviewer )

______________________________________________________________________

***Note*** : *All the permission sets mentioned above are for non-admin users. Incase you are an
admin, your permission set is by default set to 'administrator' and have all the access rights.
Administrator can execute all the actions without any additional permissions.*

______________________________________________________________________

### Configuration variables

This table lists the configuration variables required to operate McAfee ePO. These variables are specified when configuring a McAfee ePO asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**username** | required | string | Username |
**password** | required | password | Password |
**ip_hostname** | required | string | Host of ePO Instance |
**port** | required | string | Port Number |
**quarantine_tag** | optional | string | Quarantine Tag |
**verify_server_cert** | optional | boolean | Verify Server Certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate connectivity to McAfee ePO \
[add tag](#action-add-tag) - Add a tag to an endpoint \
[remove tag](#action-remove-tag) - Remove a tag from the endpoint \
[get device info](#action-get-device-info) - Get information about an endpoint \
[quarantine device](#action-quarantine-device) - Send the quarantine tag to the endpoint \
[unquarantine device](#action-unquarantine-device) - Remove the quarantine tag on the endpoint

## action: 'test connectivity'

Validate connectivity to McAfee ePO

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'add tag'

Add a tag to an endpoint

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | Endpoint to apply tag to | string | `ip` `host name` |
**tag** | required | Tag to add | string | `mfeepo tag` |
**wakeup_agent** | optional | Wakeup Agent after adding tag | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `ip` `host name` | test host |
action_result.parameter.tag | string | `mfeepo tag` | test tag |
action_result.parameter.wakeup_agent | boolean | | True False |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully assigned tag |
summary.total_objects | numeric | | 0 |
summary.total_objects_successful | numeric | | 0 |

## action: 'remove tag'

Remove a tag from the endpoint

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | Endpoint to remove tag from | string | `ip` `host name` |
**tag** | required | Tag to remove | string | `mfeepo tag` |
**wakeup_agent** | optional | Wakeup Agent after removing tag | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `ip` `host name` | test host |
action_result.parameter.tag | string | `mfeepo tag` | test tag |
action_result.parameter.wakeup_agent | boolean | | True False |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Removed tag and host received configuration |
summary.total_objects | numeric | | 0 |
summary.total_objects_successful | numeric | | 0 |

## action: 'get device info'

Get information about an endpoint

Type: **investigate** \
Read only: **True**

If a quarantine tag is specified, this will return whether or not the device is currently quarantined.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | Endpoint to get info from | string | `ip` `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `ip` `host name` | |
action_result.data.\*.EPOBranchNode_AutoID | numeric | | |
action_result.data.\*.EPOComputerProperties_CPUSerialNum | string | | |
action_result.data.\*.EPOComputerProperties_CPUSpeed | numeric | | |
action_result.data.\*.EPOComputerProperties_CPUType | string | | |
action_result.data.\*.EPOComputerProperties_ComputerName | string | | |
action_result.data.\*.EPOComputerProperties_DefaultLangID | string | | |
action_result.data.\*.EPOComputerProperties_Description | numeric | | |
action_result.data.\*.EPOComputerProperties_DomainName | string | `domain` | |
action_result.data.\*.EPOComputerProperties_FreeDiskSpace | numeric | | |
action_result.data.\*.EPOComputerProperties_FreeMemory | numeric | | |
action_result.data.\*.EPOComputerProperties_IPAddress | string | | |
action_result.data.\*.EPOComputerProperties_IPHostName | string | `host name` `ip` | |
action_result.data.\*.EPOComputerProperties_IPSubnet | string | | |
action_result.data.\*.EPOComputerProperties_IPSubnetMask | string | | |
action_result.data.\*.EPOComputerProperties_IPV4x | numeric | | |
action_result.data.\*.EPOComputerProperties_IPV6 | string | | |
action_result.data.\*.EPOComputerProperties_IPXAddress | string | | |
action_result.data.\*.EPOComputerProperties_IsPortable | numeric | | |
action_result.data.\*.EPOComputerProperties_LastAgentHandler | numeric | | |
action_result.data.\*.EPOComputerProperties_NetAddress | string | | |
action_result.data.\*.EPOComputerProperties_NumOfCPU | numeric | | |
action_result.data.\*.EPOComputerProperties_OSBitMode | numeric | | |
action_result.data.\*.EPOComputerProperties_OSBuildNum | numeric | | |
action_result.data.\*.EPOComputerProperties_OSOEMID | string | | |
action_result.data.\*.EPOComputerProperties_OSPlatform | string | | |
action_result.data.\*.EPOComputerProperties_OSServicePackVer | string | | |
action_result.data.\*.EPOComputerProperties_OSType | string | | |
action_result.data.\*.EPOComputerProperties_OSVersion | string | | |
action_result.data.\*.EPOComputerProperties_ParentID | numeric | | |
action_result.data.\*.EPOComputerProperties_SubnetAddress | string | | |
action_result.data.\*.EPOComputerProperties_SubnetMask | string | | |
action_result.data.\*.EPOComputerProperties_SystemDescription | string | | |
action_result.data.\*.EPOComputerProperties_SysvolFreeSpace | numeric | | |
action_result.data.\*.EPOComputerProperties_SysvolTotalSpace | numeric | | |
action_result.data.\*.EPOComputerProperties_TimeZone | string | | |
action_result.data.\*.EPOComputerProperties_TotalDiskSpace | numeric | | |
action_result.data.\*.EPOComputerProperties_TotalPhysicalMemory | numeric | | |
action_result.data.\*.EPOComputerProperties_UserName | string | `user name` | |
action_result.data.\*.EPOComputerProperties_UserProperty1 | numeric | | |
action_result.data.\*.EPOComputerProperties_UserProperty2 | numeric | | |
action_result.data.\*.EPOComputerProperties_UserProperty3 | numeric | | |
action_result.data.\*.EPOComputerProperties_UserProperty4 | numeric | | |
action_result.data.\*.EPOComputerProperties_Vdi | numeric | | |
action_result.data.\*.EPOLeafNode_AgentGUID | string | | |
action_result.data.\*.EPOLeafNode_AgentVersion | string | | |
action_result.data.\*.EPOLeafNode_ExcludedTags | string | | |
action_result.data.\*.EPOLeafNode_LastUpdate | string | | |
action_result.data.\*.EPOLeafNode_ManagedState | numeric | | |
action_result.data.\*.EPOLeafNode_Tags.\*.Tag | string | `mfeepo tag` | |
action_result.data.\*.EPO_IP/Hostname | string | `host name` `ip` | |
action_result.data.\*.EPO_Port | string | `port` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 0 |
summary.total_objects_successful | numeric | | 0 |

## action: 'quarantine device'

Send the quarantine tag to the endpoint

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | Endpoint to quarantine | string | `ip` `host name` |
**wakeup_agent** | optional | Wakeup Agent after applying quarantine tag | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `ip` `host name` | |
action_result.parameter.wakeup_agent | boolean | | True False |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 0 |
summary.total_objects_successful | numeric | | 0 |

## action: 'unquarantine device'

Remove the quarantine tag on the endpoint

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | Endpoint to unquarantine | string | `ip` `host name` |
**wakeup_agent** | optional | Wakeup Agent after removing quarantine tag | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `ip` `host name` | |
action_result.parameter.wakeup_agent | boolean | | True False |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 0 |
summary.total_objects_successful | numeric | | 0 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
