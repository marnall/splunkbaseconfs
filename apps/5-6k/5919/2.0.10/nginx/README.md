# NGINX

Publisher: Splunk \
Connector Version: 2.0.10 \
Product Vendor: F5 \
Product Name: NGINX \
Minimum Product Version: 5.1.0

This app integrates with an NGINX instance to manage upstreams and servers

### Configuration variables

This table lists the configuration variables required to operate NGINX. These variables are specified when configuring a NGINX asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | optional | string | Base URL of NGINX Instance (Required for test connectivity) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | NGINX Username |
**password** | required | password | NGINX Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[remove server](#action-remove-server) - Remove a server from an upstream \
[add server](#action-add-server) - Add a server to an upstream \
[disable server](#action-disable-server) - Disable a server \
[enable server](#action-enable-server) - Enable a server \
[describe server](#action-describe-server) - Get information about an upstream server \
[list servers](#action-list-servers) - List servers under an upstream \
[list upstreams](#action-list-upstreams) - List all configured upstreams

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'remove server'

Remove a server from an upstream

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | optional | URL of NGINX instance | string | `url` |
**upstream_name** | required | Name of the upstream | string | `nginx upstream name` |
**server_id** | required | ID of the server to remove | numeric | `nginx server id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.server_id | numeric | `nginx server id` | 9 |
action_result.parameter.upstream_name | string | `nginx upstream name` | appservers |
action_result.parameter.url | string | `url` | http://10.1.17.75 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully removed server |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add server'

Add a server to an upstream

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | optional | URL of NGINX instance | string | `url` |
**upstream_name** | required | Name of the upstream | string | `nginx upstream name` |
**ip** | required | IP of the server to add | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 10.1.17.79 |
action_result.parameter.upstream_name | string | `nginx upstream name` | appservers |
action_result.parameter.url | string | `url` | http://10.1.17.75 |
action_result.data.\*.backup | boolean | | True False |
action_result.data.\*.down | boolean | | True False |
action_result.data.\*.fail_timeout | string | | 10s |
action_result.data.\*.id | numeric | `nginx server id` | 7 |
action_result.data.\*.max_conns | numeric | | 0 |
action_result.data.\*.max_fails | numeric | | 1 |
action_result.data.\*.route | string | | |
action_result.data.\*.server | string | | 10.1.17.79:80 |
action_result.data.\*.slow_start | string | | 0s |
action_result.data.\*.weight | numeric | | 1 |
action_result.summary.server_id | numeric | `nginx server id` | 7 |
action_result.message | string | | Successfully added server |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'disable server'

Disable a server

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | optional | URL of NGINX instance | string | `url` |
**upstream_name** | required | Name of the upstream containing the server | string | `nginx upstream name` |
**server_id** | required | ID of the server to disable | string | `nginx server id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.server_id | string | `nginx server id` | 0 |
action_result.parameter.upstream_name | string | `nginx upstream name` | appservers |
action_result.parameter.url | string | `url` | http://10.1.17.75 |
action_result.data.\*.backup | boolean | | True False |
action_result.data.\*.down | boolean | | True False |
action_result.data.\*.fail_timeout | string | | 10s |
action_result.data.\*.id | numeric | `nginx server id` | 0 |
action_result.data.\*.max_conns | numeric | | 0 |
action_result.data.\*.max_fails | numeric | | 1 |
action_result.data.\*.route | string | | |
action_result.data.\*.server | string | | 10.1.17.76:80 |
action_result.data.\*.slow_start | string | | 0s |
action_result.data.\*.weight | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | Server successfully updated |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 0 1 |

## action: 'enable server'

Enable a server

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | optional | URL of NGINX instance | string | `url` |
**upstream_name** | required | Name of the upstream containing the server | string | `nginx upstream name` |
**server_id** | required | ID of the server to enable | string | `nginx server id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.server_id | string | `nginx server id` | 0 |
action_result.parameter.upstream_name | string | `nginx upstream name` | appservers |
action_result.parameter.url | string | `url` | http://10.1.17.75 |
action_result.data.\*.backup | boolean | | True False |
action_result.data.\*.down | boolean | | True False |
action_result.data.\*.fail_timeout | string | | 10s |
action_result.data.\*.id | numeric | `nginx server id` | 0 |
action_result.data.\*.max_conns | numeric | | 0 |
action_result.data.\*.max_fails | numeric | | 1 |
action_result.data.\*.route | string | | |
action_result.data.\*.server | string | | 10.1.17.76:80 |
action_result.data.\*.slow_start | string | | 0s |
action_result.data.\*.weight | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | Server successfully updated |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'describe server'

Get information about an upstream server

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | optional | URL of NGINX instance | string | `url` |
**upstream_name** | required | Name of the upstream containing the server | string | `nginx upstream name` |
**server_id** | required | ID of the server to describe | string | `nginx server id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.server_id | string | `nginx server id` | 0 |
action_result.parameter.upstream_name | string | `nginx upstream name` | appservers |
action_result.parameter.url | string | `url` | http://10.1.17.75 |
action_result.data.\*.backup | boolean | | True False |
action_result.data.\*.down | boolean | | True False |
action_result.data.\*.fail_timeout | string | | 10s |
action_result.data.\*.id | numeric | `nginx server id` | 0 |
action_result.data.\*.max_conns | numeric | | 0 |
action_result.data.\*.max_fails | numeric | | 1 |
action_result.data.\*.route | string | | |
action_result.data.\*.server | string | | 10.1.17.76:80 |
action_result.data.\*.slow_start | string | | 0s |
action_result.data.\*.weight | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list servers'

List servers under an upstream

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | optional | URL of NGINX instance | string | `url` |
**upstream_name** | required | Name of upstream | string | `nginx upstream name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.upstream_name | string | `nginx upstream name` | appservers |
action_result.parameter.url | string | `url` | http://10.1.17.75 |
action_result.data.\*.active | numeric | | 0 |
action_result.data.\*.backup | boolean | | True False |
action_result.data.\*.downstart | string | | 2019-08-01T21:55:56.905Z |
action_result.data.\*.downtime | numeric | | 0 |
action_result.data.\*.fails | numeric | | 0 |
action_result.data.\*.header_time | numeric | | 1 |
action_result.data.\*.health_checks.checks | numeric | | 103289 |
action_result.data.\*.health_checks.fails | numeric | | 0 |
action_result.data.\*.health_checks.last_passed | boolean | | True False |
action_result.data.\*.health_checks.unhealthy | numeric | | 0 |
action_result.data.\*.id | numeric | `nginx server id` | 0 |
action_result.data.\*.name | string | `nginx server name` | 10.1.17.76 |
action_result.data.\*.received | numeric | | 1414 |
action_result.data.\*.requests | numeric | | 2 |
action_result.data.\*.response_time | numeric | | 1 |
action_result.data.\*.responses.1xx | numeric | | 0 |
action_result.data.\*.responses.2xx | numeric | | 0 |
action_result.data.\*.responses.3xx | numeric | | 0 |
action_result.data.\*.responses.4xx | numeric | | 2 |
action_result.data.\*.responses.5xx | numeric | | 0 |
action_result.data.\*.responses.total | numeric | | 2 |
action_result.data.\*.selected | string | | 2019-07-18T18:27:54Z |
action_result.data.\*.sent | numeric | | 822 |
action_result.data.\*.server | string | | 10.1.17.76:80 |
action_result.data.\*.state | string | | up |
action_result.data.\*.unavail | numeric | | 0 |
action_result.data.\*.weight | numeric | | 1 |
action_result.summary.num_servers | numeric | | 3 |
action_result.message | string | | Num servers: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list upstreams'

List all configured upstreams

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | optional | URL of NGINX instance | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` | http://10.1.17.75 |
action_result.data.\*.keepalive | numeric | | 0 |
action_result.data.\*.zombies | numeric | | 0 |
action_result.data.\*.zone | string | `nginx upstream name` | appservers |
action_result.summary.num_upstreams | numeric | | 1 |
action_result.message | string | | Num upstreams: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

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
