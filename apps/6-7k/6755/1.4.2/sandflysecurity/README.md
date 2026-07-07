# Sandfly Security

Publisher: Sandfly Security, Ltd. <br>
Connector Version: 1.4.2 <br>
Product Vendor: Sandfly Security <br>
Product Name: Sandfly Security Agentless Linux Security <br>
Minimum Product Version: 6.3.0

Sandfly Security app to gather information, initiate system scans and other actions on the Sandfly Server

### Configuration variables

This table lists the configuration variables required to operate Sandfly Security. These variables are specified when configuring a Sandfly Security Agentless Linux Security asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**Sandfly Server URL** | required | string | Sandfly Server URL |
**Username** | required | string | Login Username |
**Password** | required | password | Login Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[scan host](#action-scan-host) - Run a Sandfly investigation <br>
[sandfly full investigation](#action-sandfly-full-investigation) - Run a full Sandfly investigation <br>
[sandfly process investigation](#action-sandfly-process-investigation) - Run a Sandfly process investigation <br>
[sandfly file investigation](#action-sandfly-file-investigation) - Run a Sandfly file investigation <br>
[sandfly directory investigation](#action-sandfly-directory-investigation) - Run a Sandfly directory investigation <br>
[sandfly log tamper investigation](#action-sandfly-log-tamper-investigation) - Run a Sandfly log tamper investigation <br>
[sandfly user investigation](#action-sandfly-user-investigation) - Run a Sandfly user investigation <br>
[sandfly recon investigation](#action-sandfly-recon-investigation) - Run a Sandfly recon investigation <br>
[list endpoints](#action-list-endpoints) - List all the endpoints/sensors configured on the device <br>
[get system info](#action-get-system-info) - Get information about an endpoint <br>
[list users](#action-list-users) - List the user accounts on a machine <br>
[list processes](#action-list-processes) - List the running processes on a machine

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'scan host'

Run a Sandfly investigation

Type: **investigate** <br>
Read only: **False**

Run a Sandfly investigation against the target host for the selected types.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | IP or name of the host | string | |
**directory** | optional | Sandfly Type - directory | boolean | |
**file** | optional | Sandfly Type - file | boolean | |
**incident** | optional | Sandfly Type - incident | boolean | |
**log** | optional | Sandfly Type - log | boolean | |
**policy** | optional | Sandfly Type - policy | boolean | |
**process** | optional | Sandfly Type - process | boolean | |
**recon** | optional | Sandfly Type - recon | boolean | |
**user** | optional | Sandfly Type - user | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.directory | boolean | | |
action_result.parameter.file | boolean | | |
action_result.parameter.incident | boolean | | |
action_result.parameter.ip_hostname | string | | |
action_result.parameter.log | boolean | | |
action_result.parameter.policy | boolean | | |
action_result.parameter.process | boolean | | |
action_result.parameter.recon | boolean | | |
action_result.parameter.user | boolean | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'sandfly full investigation'

Run a full Sandfly investigation

Type: **investigate** <br>
Read only: **False**

Run a full Sandfly investigation for all process, file, directory, log, user, incident, policy and recon types.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | IP or Hostname | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'sandfly process investigation'

Run a Sandfly process investigation

Type: **investigate** <br>
Read only: **False**

Run a Sandfly investigation against the target system for the process type.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | IP or Hostname of the target system | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'sandfly file investigation'

Run a Sandfly file investigation

Type: **investigate** <br>
Read only: **False**

Run a Sandfly investigation against the target system for the file type.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | IP or Hostname of the target system | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'sandfly directory investigation'

Run a Sandfly directory investigation

Type: **investigate** <br>
Read only: **False**

Run a Sandfly investigation against the target system for the directory type.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | IP or Hostname of the target system | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'sandfly log tamper investigation'

Run a Sandfly log tamper investigation

Type: **investigate** <br>
Read only: **False**

Run a Sandfly investigation against the target system for the log type.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | IP or Hostname of the target system | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'sandfly user investigation'

Run a Sandfly user investigation

Type: **investigate** <br>
Read only: **False**

Run a Sandfly investigation against the target system for the user type.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | IP or Hostname of the target system | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'sandfly recon investigation'

Run a Sandfly recon investigation

Type: **investigate** <br>
Read only: **False**

Run a Sandfly investigation against the target system for the recon type.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | IP or Hostname of the target system | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list endpoints'

List all the endpoints/sensors configured on the device

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get system info'

Get information about an endpoint

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | Hostname/IP address to get info of | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_hostname | string | `host name` `ip` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list users'

List the user accounts on a machine

Type: **investigate** <br>
Read only: **True**

List all user accounts on the specified system.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | required | Hostname/IP of the machine to list user accounts | string | `ip` `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `ip` `host name` | |
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list processes'

List the running processes on a machine

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_hostname** | optional | Hostname/IP of the machine to list processes on | string | `ip` `host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip_hostname | string | `ip` `host name` | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data | string | | |
action_result.summary | string | | |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
