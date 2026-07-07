# F5 BIG-IP LTM

Publisher: Splunk <br>
Connector Version: 2.1.3 <br>
Product Vendor: F5 <br>
Product Name: Local Traffic Manager <br>
Minimum Product Version: 6.1.1

This app implements investigate and generic actions to integrate with an F5 BIG-IP LTM instance to manage pools and nodes

### Configuration variables

This table lists the configuration variables required to operate F5 BIG-IP LTM. These variables are specified when configuring a Local Traffic Manager asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base URL of F5 BIG-IP LTM instance (e.g. https://10.1.16.110) |
**username** | required | string | User name |
**password** | required | password | Password |
**verify_server_cert** | optional | boolean | Verify Server SSL certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using the supplied configuration <br>
[create node](#action-create-node) - Create a new node <br>
[delete node](#action-delete-node) - Delete a node <br>
[remove node](#action-remove-node) - Remove a node from a pool <br>
[create pool](#action-create-pool) - Create a new pool <br>
[delete pool](#action-delete-pool) - Delete an existing pool <br>
[add node](#action-add-node) - Add an existing node to a pool <br>
[disable node](#action-disable-node) - Disable a node <br>
[enable node](#action-enable-node) - Enable a node <br>
[describe node](#action-describe-node) - Get information about a node <br>
[get node stats](#action-get-node-stats) - Get stats of the node <br>
[list nodes](#action-list-nodes) - Fetch a list of nodes (if no value is provided, all nodes will be returned) <br>
[list pools](#action-list-pools) - Fetch a list of configured pools (if no value is provided, all pools will be returned) <br>
[list members](#action-list-members) - Fetch a list of configured node members of a pool (if no value is provided, all node members of a pool will be returned)

## action: 'test connectivity'

Validate the asset configuration for connectivity using the supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'create node'

Create a new node

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**node_name** | required | Name of the node to create | string | `f5 node name` |
**partition_name** | required | Name of the partition | string | `f5 partition name` |
**ip_address** | required | IP address of the new node | string | `ip` `ipv6` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_address | string | `ip` `ipv6` | 1.1.1.1 |
action_result.parameter.node_name | string | `f5 node name` | test |
action_result.parameter.partition_name | string | `f5 partition name` | Common |
action_result.data.\*.address | string | `ip` | 1.1.1.1 |
action_result.data.\*.connectionLimit | numeric | | 0 |
action_result.data.\*.dynamicRatio | numeric | | 1 |
action_result.data.\*.ephemeral | string | | false |
action_result.data.\*.fqdn.addressFamily | string | | ipv4 |
action_result.data.\*.fqdn.autopopulate | string | | disabled |
action_result.data.\*.fqdn.downInterval | numeric | | 5 |
action_result.data.\*.fqdn.interval | string | | 3600 |
action_result.data.\*.fullPath | string | | /Common/test8 |
action_result.data.\*.generation | numeric | | 138 |
action_result.data.\*.kind | string | | tm:ltm:node:nodestate |
action_result.data.\*.logging | string | | disabled |
action_result.data.\*.monitor | string | | default |
action_result.data.\*.name | string | `f5 node name` | test |
action_result.data.\*.partition | string | `f5 partition name` | Common |
action_result.data.\*.rateLimit | string | | disabled |
action_result.data.\*.ratio | numeric | | 1 |
action_result.data.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/node/~Common~test8?ver=15.0.0 |
action_result.data.\*.session | string | | user-enabled |
action_result.data.\*.state | string | | unchecked |
action_result.summary.node_name | string | `f5 node name` | test8 |
action_result.message | string | | Node successfully created |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete node'

Delete a node

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**node_name** | required | Name of the node to delete | string | `f5 node name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.node_name | string | `f5 node name` | test8 |
action_result.data | string | | |
action_result.summary.node_name | string | | test8 |
action_result.message | string | | Successfully deleted node |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove node'

Remove a node from a pool

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**node_name** | required | Name of the node to remove | string | `f5 node name` |
**port** | required | Port number | string | `port` |
**pool_name** | required | Name of the pool to remove the node from | string | `f5 pool name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.node_name | string | `f5 node name` | test8 |
action_result.parameter.pool_name | string | `f5 pool name` | pool3 |
action_result.parameter.port | string | `port` | 80 443 |
action_result.data | string | | |
action_result.summary.node_name | string | `f5 node name` | test pool |
action_result.summary.pool_name | string | `f5 pool name` | pool3 |
action_result.summary.port | string | `port` | 80 |
action_result.message | string | | Node successfully removed from pool |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create pool'

Create a new pool

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**pool_name** | required | Name of the pool to create | string | `f5 pool name` |
**pool_description** | optional | Description of the pool | string | |
**partition_name** | required | Name of the partition | string | `f5 partition name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.partition_name | string | `f5 partition name` | Common |
action_result.parameter.pool_description | string | | test pool creation |
action_result.parameter.pool_name | string | `f5 pool name` | pool3 |
action_result.data.\*.allowNat | string | | yes |
action_result.data.\*.allowSnat | string | | yes |
action_result.data.\*.fullPath | string | | /Common/pool3 |
action_result.data.\*.generation | numeric | | 118 |
action_result.data.\*.ignorePersistedWeight | string | | disabled |
action_result.data.\*.ipTosToClient | string | | pass-through |
action_result.data.\*.ipTosToServer | string | | pass-through |
action_result.data.\*.kind | string | | tm:ltm:pool:poolstate |
action_result.data.\*.linkQosToClient | string | | pass-through |
action_result.data.\*.linkQosToServer | string | | pass-through |
action_result.data.\*.loadBalancingMode | string | | round-robin |
action_result.data.\*.membersReference.isSubcollection | boolean | | True False |
action_result.data.\*.membersReference.link | string | `url` | https://localhost/mgmt/tm/ltm/pool/~Common~pool3/members?ver=15.0.0 |
action_result.data.\*.minActiveMembers | numeric | | 0 |
action_result.data.\*.minUpMembers | numeric | | 0 |
action_result.data.\*.minUpMembersAction | string | | failover |
action_result.data.\*.minUpMembersChecking | string | | disabled |
action_result.data.\*.name | string | `f5 pool name` | pool3 |
action_result.data.\*.partition | string | `f5 partition name` | Common |
action_result.data.\*.queueDepthLimit | numeric | | 0 |
action_result.data.\*.queueOnConnectionLimit | string | | disabled |
action_result.data.\*.queueTimeLimit | numeric | | 0 |
action_result.data.\*.reselectTries | numeric | | 0 |
action_result.data.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/pool/~Common~test1pool?ver=15.0.0 |
action_result.data.\*.serviceDownAction | string | | none |
action_result.data.\*.slowRampTime | numeric | | 10 |
action_result.summary.partition | string | `f5 partition name` | Common |
action_result.summary.pool_description | string | | test pool creation |
action_result.summary.pool_name | string | `f5 pool name` | pool3 |
action_result.message | string | | Successfully created pool |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete pool'

Delete an existing pool

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**pool_name** | required | Name of the pool to delete | string | `f5 pool name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.pool_name | string | `f5 pool name` | gonna-delete-this |
action_result.data | string | | |
action_result.summary.pool_name | string | `f5 pool name` | gonna-delete-this |
action_result.message | string | | Successfully deleted pool |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add node'

Add an existing node to a pool

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**node_name** | required | Name of the node to add | string | `f5 node name` |
**partition_name** | required | Name of the partition to add node | string | `f5 partition name` |
**port** | required | Port number | string | `port` |
**pool_name** | required | Name of the pool to add node member | string | `f5 pool name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.node_name | string | `f5 node name` | test8 |
action_result.parameter.partition_name | string | `f5 partition name` | Common |
action_result.parameter.pool_name | string | `f5 pool name` | pool3 |
action_result.parameter.port | string | `port` | 80 443 |
action_result.data.\*.address | string | `ip` | 4.4.4.4 1.1.1.1 |
action_result.data.\*.connectionLimit | numeric | | 0 |
action_result.data.\*.dynamicRatio | numeric | | 1 |
action_result.data.\*.ephemeral | string | | false |
action_result.data.\*.fqdn.autopopulate | string | | disabled |
action_result.data.\*.fullPath | string | | /Common/test7:80 /Common/test8:443 |
action_result.data.\*.generation | numeric | | 110 |
action_result.data.\*.inheritProfile | string | | enabled |
action_result.data.\*.kind | string | | tm:ltm:pool:members:membersstate |
action_result.data.\*.logging | string | | disabled |
action_result.data.\*.monitor | string | | default |
action_result.data.\*.name | string | `f5 node name` | test7:80 test8:443 |
action_result.data.\*.partition | string | `f5 partition name` | Common |
action_result.data.\*.priorityGroup | numeric | | 0 |
action_result.data.\*.rateLimit | string | | disabled |
action_result.data.\*.ratio | numeric | | 1 |
action_result.data.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/pool/pool1/members/~Common~test7:80?ver=15.0.0 |
action_result.data.\*.session | string | | monitor-enabled user-enabled |
action_result.data.\*.state | string | | checking unchecked |
action_result.summary.node_name | string | | test8:443 |
action_result.summary.pool_name | string | `f5 pool name` | pool3 |
action_result.summary.port | string | `port` | 443 |
action_result.message | string | | Node successfully added to pool |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'disable node'

Disable a node

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**node_name** | required | Name of the node to disable | string | `f5 node name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.node_name | string | `f5 node name` | test8 |
action_result.data.\*.address | string | `ip` | 4.4.4.4 1.1.1.1 |
action_result.data.\*.connectionLimit | numeric | | 0 |
action_result.data.\*.description | string | | This node was created for testing |
action_result.data.\*.dynamicRatio | numeric | | 1 |
action_result.data.\*.ephemeral | string | | false |
action_result.data.\*.fqdn.addressFamily | string | | ipv4 |
action_result.data.\*.fqdn.autopopulate | string | | disabled |
action_result.data.\*.fqdn.downInterval | numeric | | 5 |
action_result.data.\*.fqdn.interval | string | | 3600 |
action_result.data.\*.fullPath | string | | test7 test8 |
action_result.data.\*.generation | numeric | | 115 |
action_result.data.\*.kind | string | | tm:ltm:node:nodestate |
action_result.data.\*.logging | string | | disabled |
action_result.data.\*.monitor | string | | default |
action_result.data.\*.name | string | `f5 node name` | test7 |
action_result.data.\*.rateLimit | string | | disabled |
action_result.data.\*.ratio | numeric | | 1 |
action_result.data.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/node/test7?ver=15.0.0 |
action_result.data.\*.session | string | | user-disabled |
action_result.data.\*.state | string | | unchecked |
action_result.summary.node_name | string | | test8 |
action_result.message | string | | Successfully disabled node |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'enable node'

Enable a node

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**node_name** | required | Name of the node to enable | string | `f5 node name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.node_name | string | `f5 node name` | test8 |
action_result.data.\*.address | string | `ip` | 1.1.1.1 |
action_result.data.\*.connectionLimit | numeric | | 0 |
action_result.data.\*.description | string | | This node was created for testing |
action_result.data.\*.dynamicRatio | numeric | | 1 |
action_result.data.\*.ephemeral | string | | false |
action_result.data.\*.fqdn.addressFamily | string | | ipv4 |
action_result.data.\*.fqdn.autopopulate | string | | disabled |
action_result.data.\*.fqdn.downInterval | numeric | | 5 |
action_result.data.\*.fqdn.interval | string | | 3600 |
action_result.data.\*.fullPath | string | | test8 |
action_result.data.\*.generation | numeric | | 46 |
action_result.data.\*.kind | string | | tm:ltm:node:nodestate |
action_result.data.\*.logging | string | | disabled |
action_result.data.\*.monitor | string | | default |
action_result.data.\*.name | string | `f5 node name` | test8 |
action_result.data.\*.rateLimit | string | | disabled |
action_result.data.\*.ratio | numeric | | 1 |
action_result.data.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/node/nginx1?ver=15.0.0 |
action_result.data.\*.session | string | | user-enabled |
action_result.data.\*.state | string | | unchecked |
action_result.summary.node_name | string | | test8 |
action_result.message | string | | Successfully enabled node |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'describe node'

Get information about a node

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**node_name** | required | Name of the node to describe | string | `f5 node name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.node_name | string | `f5 node name` | test8 |
action_result.data.\*.address | string | `ip` | 1.1.1.1 |
action_result.data.\*.connectionLimit | numeric | | 0 |
action_result.data.\*.dynamicRatio | numeric | | 1 |
action_result.data.\*.ephemeral | string | | false |
action_result.data.\*.fqdn.addressFamily | string | | ipv4 |
action_result.data.\*.fqdn.autopopulate | string | | disabled |
action_result.data.\*.fqdn.downInterval | numeric | | 5 |
action_result.data.\*.fqdn.interval | string | | 3600 |
action_result.data.\*.fullPath | string | | testpath |
action_result.data.\*.generation | numeric | | 45 78 |
action_result.data.\*.kind | string | | tm:ltm:node:nodestate |
action_result.data.\*.logging | string | | disabled |
action_result.data.\*.monitor | string | | default |
action_result.data.\*.name | string | `f5 node name` | test8 |
action_result.data.\*.rateLimit | string | | disabled |
action_result.data.\*.ratio | numeric | | 1 |
action_result.data.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/node/nginx1?ver=15.0.0 |
action_result.data.\*.session | string | | user-disabled user-enabled |
action_result.data.\*.state | string | | unchecked |
action_result.summary.state | string | | unchecked |
action_result.message | string | | State: unchecked |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get node stats'

Get stats of the node

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**node_name** | required | Name of the node | string | `f5 node name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.node_name | string | `f5 node name` | test8 |
action_result.data.\*.addr.description | string | | 1.1.1.1 |
action_result.data.\*.curSessions.value | numeric | | 0 |
action_result.data.\*.monitorRule.description | string | | none |
action_result.data.\*.monitorStatus.description | string | | unchecked |
action_result.data.\*.serverside_bitsIn.value | numeric | | 0 |
action_result.data.\*.serverside_bitsOut.value | numeric | | 0 |
action_result.data.\*.serverside_curConns.value | numeric | | 0 |
action_result.data.\*.serverside_maxConns.value | numeric | | 100 |
action_result.data.\*.serverside_pktsIn.value | numeric | | 0 |
action_result.data.\*.serverside_pktsOut.value | numeric | | 0 |
action_result.data.\*.serverside_totConns.value | numeric | | 0 |
action_result.data.\*.sessionStatus.description | string | | enabled |
action_result.data.\*.status_availabilityState.description | string | | unknown |
action_result.data.\*.status_enabledState.description | string | | enabled |
action_result.data.\*.status_statusReason.description | string | | Node address does not have service checking enabled |
action_result.data.\*.tmName.description | string | | /Common/IIS1 |
action_result.data.\*.totRequests.value | numeric | | 0 |
action_result.summary.num_connections | numeric | | 4 |
action_result.message | string | | Successfully retrieved node stats |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list nodes'

Fetch a list of nodes (if no value is provided, all nodes will be returned)

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**max_results** | optional | Max number of nodes to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.max_results | numeric | | 10 |
action_result.data.\*.address | string | `ip` | 10.1.1.1 |
action_result.data.\*.connectionLimit | numeric | | 0 |
action_result.data.\*.description | string | | IIS1 |
action_result.data.\*.dynamicRatio | numeric | | 1 |
action_result.data.\*.ephemeral | string | | false |
action_result.data.\*.fqdn.addressFamily | string | | ipv4 |
action_result.data.\*.fqdn.autopopulate | string | | disabled |
action_result.data.\*.fqdn.downInterval | numeric | | 5 |
action_result.data.\*.fqdn.interval | string | | 3600 |
action_result.data.\*.fullPath | string | | /Common/test1 |
action_result.data.\*.generation | numeric | | 68 |
action_result.data.\*.kind | string | | tm:ltm:node:nodestate |
action_result.data.\*.logging | string | | disabled |
action_result.data.\*.monitor | string | | default |
action_result.data.\*.name | string | `f5 node name` | test8 |
action_result.data.\*.partition | string | `f5 partition name` | Common |
action_result.data.\*.rateLimit | string | | disabled |
action_result.data.\*.ratio | numeric | | 1 |
action_result.data.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/node/~Common~nginx1?ver=15.0.0 |
action_result.data.\*.session | string | | user-enabled |
action_result.data.\*.state | string | | unchecked |
action_result.summary.node_names | string | | 10.1.17.97, 10.1.17.98, a13 |
action_result.summary.num_nodes | numeric | | 4 |
action_result.message | string | | Node names: 10.1.17.97, 10.1.17.98, a13, Num nodes: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list pools'

Fetch a list of configured pools (if no value is provided, all pools will be returned)

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**max_results** | optional | Max number of pools to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.max_results | numeric | | 10 |
action_result.data.\*.allowNat | string | | yes |
action_result.data.\*.allowSnat | string | | yes |
action_result.data.\*.description | string | | Pool of IIS servers for IT Automation UC1a |
action_result.data.\*.fullPath | string | | /Common/pool1 |
action_result.data.\*.generation | numeric | | 66 |
action_result.data.\*.ignorePersistedWeight | string | | disabled |
action_result.data.\*.ipTosToClient | string | | pass-through |
action_result.data.\*.ipTosToServer | string | | pass-through |
action_result.data.\*.items.\*.addressStatus | string | | yes |
action_result.data.\*.items.\*.autoLasthop | string | | default |
action_result.data.\*.items.\*.cmpEnabled | string | | yes |
action_result.data.\*.items.\*.connectionLimit | numeric | | 0 |
action_result.data.\*.items.\*.creationTime | string | | 2019-08-30T00:04:17Z |
action_result.data.\*.items.\*.destination | string | | /Common/10.1.16.148:80 |
action_result.data.\*.items.\*.enabled | boolean | | True False |
action_result.data.\*.items.\*.evictionProtected | string | | disabled |
action_result.data.\*.items.\*.fullPath | string | | /Common/vip |
action_result.data.\*.items.\*.generation | numeric | | 1 |
action_result.data.\*.items.\*.gtmScore | numeric | | 0 |
action_result.data.\*.items.\*.ipProtocol | string | | tcp |
action_result.data.\*.items.\*.kind | string | | tm:ltm:virtual:virtualstate |
action_result.data.\*.items.\*.lastModifiedTime | string | | 2019-08-30T00:05:23Z |
action_result.data.\*.items.\*.mask | string | `ip` | 255.255.255.255 |
action_result.data.\*.items.\*.mirror | string | | disabled |
action_result.data.\*.items.\*.mobileAppTunnel | string | | disabled |
action_result.data.\*.items.\*.name | string | | vip |
action_result.data.\*.items.\*.nat64 | string | | disabled |
action_result.data.\*.items.\*.partition | string | `f5 partition name` | Common |
action_result.data.\*.items.\*.policiesReference.isSubcollection | boolean | | True False |
action_result.data.\*.items.\*.policiesReference.link | string | `url` | https://localhost/mgmt/tm/ltm/virtual/~Common~vip/policies?ver=15.0.0 |
action_result.data.\*.items.\*.pool | string | | /Common/pool1 |
action_result.data.\*.items.\*.poolReference.link | string | `url` | https://localhost/mgmt/tm/ltm/pool/~Common~pool1?ver=15.0.0 |
action_result.data.\*.items.\*.profilesReference.isSubcollection | boolean | | True False |
action_result.data.\*.items.\*.profilesReference.link | string | `url` | https://localhost/mgmt/tm/ltm/virtual/~Common~vip/profiles?ver=15.0.0 |
action_result.data.\*.items.\*.rateLimit | string | | disabled |
action_result.data.\*.items.\*.rateLimitDstMask | numeric | | 0 |
action_result.data.\*.items.\*.rateLimitMode | string | | object |
action_result.data.\*.items.\*.rateLimitSrcMask | numeric | | 0 |
action_result.data.\*.items.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/virtual/~Common~vip?ver=15.0.0 |
action_result.data.\*.items.\*.serviceDownImmediateAction | string | | none |
action_result.data.\*.items.\*.source | string | | 0.0.0.0/0 |
action_result.data.\*.items.\*.sourceAddressTranslation.type | string | | none |
action_result.data.\*.items.\*.sourcePort | string | | preserve |
action_result.data.\*.items.\*.synCookieStatus | string | | not-activated |
action_result.data.\*.items.\*.translateAddress | string | | enabled |
action_result.data.\*.items.\*.translatePort | string | | enabled |
action_result.data.\*.items.\*.vlansDisabled | boolean | | True False |
action_result.data.\*.items.\*.vsIndex | numeric | | 2 |
action_result.data.\*.kind | string | | tm:ltm:virtual:virtualcollectionstate tm:ltm:pool:poolstate |
action_result.data.\*.linkQosToClient | string | | pass-through |
action_result.data.\*.linkQosToServer | string | | pass-through |
action_result.data.\*.loadBalancingMode | string | | round-robin |
action_result.data.\*.membersReference.isSubcollection | boolean | | True False |
action_result.data.\*.membersReference.link | string | `url` | https://localhost/mgmt/tm/ltm/pool/~Common~pool1/members?ver=15.0.0 |
action_result.data.\*.minActiveMembers | numeric | | 0 |
action_result.data.\*.minUpMembers | numeric | | 0 |
action_result.data.\*.minUpMembersAction | string | | failover |
action_result.data.\*.minUpMembersChecking | string | | disabled |
action_result.data.\*.monitor | string | | /Common/http |
action_result.data.\*.name | string | `f5 pool name` | pool1 |
action_result.data.\*.partition | string | `f5 partition name` | Common |
action_result.data.\*.queueDepthLimit | numeric | | 0 |
action_result.data.\*.queueOnConnectionLimit | string | | disabled |
action_result.data.\*.queueTimeLimit | numeric | | 0 |
action_result.data.\*.reselectTries | numeric | | 0 |
action_result.data.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/virtual?ver=15.0.0 https://localhost/mgmt/tm/ltm/pool/~Common~pool1?ver=15.0.0 |
action_result.data.\*.serviceDownAction | string | | none |
action_result.data.\*.slowRampTime | numeric | | 10 |
action_result.summary.num_pools | numeric | | 2 |
action_result.message | string | | Num pools: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list members'

Fetch a list of configured node members of a pool (if no value is provided, all node members of a pool will be returned)

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**pool_name** | required | Name of the pool | string | `f5 pool name` |
**partition_name** | required | Name of the partition | string | `f5 partition name` |
**max_results** | optional | Max number of members to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.max_results | numeric | | 10 |
action_result.parameter.partition_name | string | `f5 partition name` | Common |
action_result.parameter.pool_name | string | `f5 pool name` | pool1 |
action_result.data.\*.address | string | `ip` | 10.1.17.76 |
action_result.data.\*.connectionLimit | numeric | | 0 |
action_result.data.\*.dynamicRatio | numeric | | 1 |
action_result.data.\*.ephemeral | string | | false |
action_result.data.\*.fqdn.autopopulate | string | | disabled |
action_result.data.\*.fullPath | string | | /Common/test1:80 |
action_result.data.\*.generation | numeric | | 1 |
action_result.data.\*.inheritProfile | string | | enabled |
action_result.data.\*.kind | string | | tm:ltm:pool:members:membersstate |
action_result.data.\*.logging | string | | disabled |
action_result.data.\*.monitor | string | | default |
action_result.data.\*.name | string | `f5 node name` | nginx1:80 |
action_result.data.\*.partition | string | `f5 partition name` | Common |
action_result.data.\*.priorityGroup | numeric | | 0 |
action_result.data.\*.rateLimit | string | | disabled |
action_result.data.\*.ratio | numeric | | 1 |
action_result.data.\*.selfLink | string | `url` | https://localhost/mgmt/tm/ltm/pool/~Common~pool1/members/~Common~nginx1:80?ver=15.0.0 |
action_result.data.\*.session | string | | monitor-enabled |
action_result.data.\*.state | string | | up |
action_result.summary.members | string | | 10.1.17.97:8080, 10.1.17.98:8080, a13:8080 |
action_result.summary.num_members | numeric | | 4 |
action_result.message | string | | Num members: 3, Members: 10.1.17.97:8080, 10.1.17.98:8080, a13:8080 |
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
