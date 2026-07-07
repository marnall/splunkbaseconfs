# Zabbix

Publisher: Splunk Community \
Connector Version: 1.0.2 \
Product Vendor: Zabbix LLC \
Product Name: Zabbix \
Minimum Product Version: 5.4.0

Splunk SOAR connector for Zabbix

### Configuration variables

This table lists the configuration variables required to operate Zabbix. These variables are specified when configuring a Zabbix asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL including the port, e.g. http://zabbix.mydomain:8080 |
**verify_server_cert** | optional | boolean | Verify server certificate when using https |
**username** | required | string | Username |
**password** | required | password | Password |
**endpoint** | required | string | Endpoint for RPC API calls |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[get host info](#action-get-host-info) - Get information about an endpoint \
[execute script](#action-execute-script) - Execute a script against an agent

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get host info'

Get information about an endpoint

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**host** | required | Hostname/IP address or Host ID | string | `host name` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.host | string | `host name` `ip` | |
action_result.status | string | | |
action_result.data.\*.host_info | string | | |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'execute script'

Execute a script against an agent

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**host** | required | Host name (exact) or host ID | string | |
**script** | required | Script name (exact) or script ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.host | string | | |
action_result.parameter.script | string | | |
action_result.status | string | | |
action_result.data.\*.output | string | | |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

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
