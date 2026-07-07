# Cisco Secure Firewall

Publisher: Splunk <br>
Connector Version: 1.0.2 <br>
Product Vendor: Cisco Systems <br>
Product Name: Cisco Secure Firewall <br>
Minimum Product Version: 6.3.0

This app interfaces with Cisco Firepower devices to add, update and delete network objects, network object groups, access policies and access rules

This connector supports both cloud and on-prem delivered FMC. Below are the steps for connecting to both

## Connecting to a cloud delivered FMC

1. On Cisco Security Cloud Control navigate to User Management
1. Create a new Api Only User with an Admin role
1. Copy the Api key and enter it in the "Api key for cloud delivered FMC" input box in the SOAR Asset Settings page
1. Specfiy Cloud for the type of FMC you are connecting to
1. Specify your region in the "Region your Cisco Security Cloud Control is deployed in" input box and click Save

## Connecting to an on-prem delivered FMC

1. On the SOAR asset setting page select On-prem for the type of FMC you are connecting to
1. Specify the device ip/hostname of your on-prem FMC along with the username and password used to login to FMC

**Note** that you can optionally specify a default firepower domain that will be queried. You can override this domain when running an action. In addition, cloud versions of FMC only support the default domain. To achieve multi tenancy you must use separate tenants.

### Configuration variables

This table lists the configuration variables required to operate Cisco Secure Firewall. These variables are specified when configuring a Cisco Secure Firewall asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**fmc_type** | required | string | Would you like to connect to an on-prem or cloud delivered FMC |
**firepower_host** | optional | string | Device IP/Hostname of your on-prem FMC |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | optional | string | User with access to the on-prem FMC node |
**password** | optional | password | Password for the on-prem FMC node |
**domain_name** | optional | string | Default firepower domain |
**api_key** | optional | password | Api key for cloud delivered FMC |
**region** | optional | string | Region your Cisco Security Cloud Control is deployed in |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity <br>
[list network objects](#action-list-network-objects) - List network object in FMC <br>
[create network object](#action-create-network-object) - Creates a network object in FMC <br>
[update network object](#action-update-network-object) - Updates a network object in FMC <br>
[delete network object](#action-delete-network-object) - Deletes a network object in FMC <br>
[get network group objects](#action-get-network-group-objects) - Gets all network group objects in FMC host or a specfic network group <br>
[create network group object](#action-create-network-group-object) - Create a network group object <br>
[update network group object](#action-update-network-group-object) - Update a network group object <br>
[delete network group object](#action-delete-network-group-object) - Delete a network group object <br>
[get access control policies](#action-get-access-control-policies) - Gets all or a particular access control policy in the FMC host for a particular domain <br>
[create access control policy](#action-create-access-control-policy) - Create an access control policy <br>
[update access control policy](#action-update-access-control-policy) - Update an access control policy <br>
[delete access control policies](#action-delete-access-control-policies) - Deletes the specified access control policy <br>
[get access control rules](#action-get-access-control-rules) - Gets all access control rules associated with a particular access control policy <br>
[create access control rule](#action-create-access-control-rule) - Creates an access control rule associated with a particular access control policy <br>
[update access control rule](#action-update-access-control-rule) - Updates an access control rule associated with a particular access control policy <br>
[delete access control rules](#action-delete-access-control-rules) - Deletes access control rule associated with a particular access control policy <br>
[list intrusion policies](#action-list-intrusion-policies) - Gets all intrusion polcies in the FMC host for a particular domain <br>
[create intrusion policy](#action-create-intrusion-policy) - Create an intrusion policy <br>
[update intrusion policy](#action-update-intrusion-policy) - Update an intrusion policy <br>
[delete intrusion policy](#action-delete-intrusion-policy) - Deletes the specified access intrusion policy <br>
[list devices](#action-list-devices) - Lists all devices belonging to a particular domain/tenant <br>
[get deployable devices](#action-get-deployable-devices) - List all devices with configuration chnges that are ready to be deployed <br>
[deploy devices](#action-deploy-devices) - Deploy devices that are ready to deploy <br>
[get deployment status](#action-get-deployment-status) - Get status of a deployment

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list network objects'

List network object in FMC

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | optional | Network object name to filter results by | string | |
**type** | optional | Network object type to filter results by | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.name | string | | |
action_result.parameter.type | string | | Network |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | Network |
action_result.data.\*.links.self | string | | |
action_result.data.\*.links.parent | string | | |

## action: 'create network object'

Creates a network object in FMC

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Network object name | string | |
**type** | required | Network object type | string | |
**value** | required | Value of the network object. If type is Range specify value in the following format: ip1-ip2 | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.name | string | | |
action_result.parameter.type | string | | Network |
action_result.parameter.value | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | Network |
action_result.data.\*.links.self | string | | |
action_result.data.\*.links.parent | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.metadata.domain.id | string | | |
action_result.data.\*.metadata.domain.name | string | | |
action_result.data.\*.metadata.domain.type | string | | |
action_result.data.\*.metadata.ipType | string | | |
action_result.data.\*.metadata.domain.lastUser.name | string | | |
action_result.data.\*.metadata.domain.timestamp | numeric | | |
action_result.data.\*.metadata.domain.parentType | string | | |
action_result.data.\*.metadata.overridable | boolean | | |

## action: 'update network object'

Updates a network object in FMC

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_id** | required | Network object id | string | |
**name** | optional | Network object name | string | |
**type** | optional | Network object type. Note this cannot change and is only used to identify the network object value you'd like to update. | string | |
**value** | optional | Value of the network object. If type is Range specify value in the following format: ip1-ip2 | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.object_id | string | | |
action_result.parameter.name | string | | |
action_result.parameter.type | string | | Network |
action_result.parameter.value | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | Network |
action_result.data.\*.links.self | string | | |
action_result.data.\*.links.parent | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.metadata.domain.id | string | | |
action_result.data.\*.metadata.domain.name | string | | |
action_result.data.\*.metadata.domain.type | string | | |
action_result.data.\*.metadata.ipType | string | | |
action_result.data.\*.metadata.domain.lastUser.name | string | | |
action_result.data.\*.metadata.domain.timestamp | numeric | | |
action_result.data.\*.metadata.domain.parentType | string | | |
action_result.data.\*.metadata.overridable | boolean | | |

## action: 'delete network object'

Deletes a network object in FMC

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_id** | required | Network object id | string | |
**type** | required | Network object type | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.object_id | string | | |
action_result.parameter.type | string | | Network |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | Network |
action_result.data.\*.links.self | string | | |
action_result.data.\*.links.parent | string | | |
action_result.data.\*.value | string | | |
action_result.data.\*.metadata.domain.id | string | | |
action_result.data.\*.metadata.domain.name | string | | |
action_result.data.\*.metadata.domain.type | string | | |
action_result.data.\*.metadata.ipType | string | | |
action_result.data.\*.metadata.domain.lastUser.name | string | | |
action_result.data.\*.metadata.domain.timestamp | numeric | | |
action_result.data.\*.metadata.domain.parentType | string | | |
action_result.data.\*.metadata.overridable | boolean | | |

## action: 'get network group objects'

Gets all network group objects in FMC host or a specfic network group

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_name** | optional | Group name to retrieve from FMC | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.group_name | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.uuid | string | | |
action_result.data.\*.name | string | | |

## action: 'create network group object'

Create a network group object

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of the network group | string | |
**network_object_ids** | optional | Network objects attached to the group. Note these ids must already exist in FMC | string | |
**overridable** | optional | Changes to this won't affect parent policies or configurations | boolean | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.name | string | | |
action_result.parameter.network_object_ids | string | | b2df29e8-5e6f-4c5d-9d5e-3fa9b3c9467b, a1c2f7d9-4b5e-42b1-8d9f-2f6b4a8e5e3c |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | NetworkGroup |
action_result.data.\*.links.self | string | | |
action_result.data.\*.objects.id | string | | |
action_result.data.\*.objects.name | string | | |
action_result.data.\*.objects.type | string | | Network |
action_result.data.\*.metadata.domain.id | string | | |
action_result.data.\*.metadata.domain.name | string | | |
action_result.data.\*.metadata.domain.type | string | | |
action_result.data.\*.metadata.domain.lastUser.name | string | | |
action_result.data.\*.metadata.domain.timestamp | numeric | | |
action_result.data.\*.metadata.domain.parentType | string | | |
action_result.data.\*.metadata.overridable | boolean | | |
action_result.parameter.overridable | boolean | | |

## action: 'update network group object'

Update a network group object

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_group_id** | required | Network group to update | string | |
**name** | optional | Name of the network group | string | |
**network_object_ids_to_add** | optional | Network objects to add to the group. Note these ids must already exist in FMC | string | |
**network_object_ids_to_remove** | optional | Network objects to remove from the group. | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.network_group_id | string | | |
action_result.parameter.name | string | | |
action_result.parameter.network_object_ids_to_add | string | | b2df29e8-5e6f-4c5d-9d5e-3fa9b3c9467b, a1c2f7d9-4b5e-42b1-8d9f-2f6b4a8e5e3c |
action_result.parameter.network_object_ids_to_remove | string | | b2df29e8-5e6f-4c5d-9d5e-3fa9b3c9467b, a1c2f7d9-4b5e-42b1-8d9f-2f6b4a8e5e3c |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | NetworkGroup |
action_result.data.\*.links.self | string | | |
action_result.data.\*.objects.id | string | | |
action_result.data.\*.objects.name | string | | |
action_result.data.\*.objects.type | string | | Network |
action_result.data.\*.metadata.domain.id | string | | |
action_result.data.\*.metadata.domain.name | string | | |
action_result.data.\*.metadata.domain.type | string | | |
action_result.data.\*.metadata.domain.lastUser.name | string | | |
action_result.data.\*.metadata.domain.timestamp | numeric | | |
action_result.data.\*.metadata.domain.parentType | string | | |
action_result.data.\*.metadata.overridable | boolean | | |

## action: 'delete network group object'

Delete a network group object

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network_group_id** | required | Network group to update | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.network_group_id | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | NetworkGroup |
action_result.data.\*.links.self | string | | |
action_result.data.\*.objects.id | string | | |
action_result.data.\*.objects.name | string | | |
action_result.data.\*.objects.type | string | | Network |
action_result.data.\*.metadata.domain.id | string | | |
action_result.data.\*.metadata.domain.name | string | | |
action_result.data.\*.metadata.domain.type | string | | |
action_result.data.\*.metadata.domain.lastUser.name | string | | |
action_result.data.\*.metadata.domain.timestamp | numeric | | |
action_result.data.\*.metadata.domain.parentType | string | | |
action_result.data.\*.metadata.overridable | boolean | | |

## action: 'get access control policies'

Gets all or a particular access control policy in the FMC host for a particular domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | optional | Id of the policy to retrieve | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.name | string | | new-policy |
action_result.data.\*.policy_id | string | | 00000000-0000-0ed3-0000-012884902138 |
action_result.parameter.policy_id | string | | |

## action: 'create access control policy'

Create an access control policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of the network group | string | |
**description** | optional | Description of the policy | string | |
**action** | required | Type of action to take on matching traffic | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.name | string | | |
action_result.parameter.description | string | | |
action_result.parameter.action | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | new-policy |
action_result.data.\*.type | string | | AccessPolicy |
action_result.data.\*.links.self | string | | AccessPolicy |
action_result.data.\*.rules.type | string | | AccessRule |
action_result.data.\*.rules.links.self | string | | |
action_result.data.\*.description | string | | |

## action: 'update access control policy'

Update an access control policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Id of the policy to update | string | |
**name** | optional | Name of the policy | string | |
**description** | optional | Description of the policy | string | |
**action** | optional | Type of action to take on matching traffic | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.name | string | | |
action_result.parameter.description | string | | |
action_result.parameter.action | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | new-policy |
action_result.data.\*.type | string | | AccessPolicy |
action_result.data.\*.links.self | string | | AccessPolicy |
action_result.data.\*.rules.type | string | | AccessRule |
action_result.data.\*.rules.links.self | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.defaultAction.id | string | | |
action_result.data.\*.defaultAction.type | string | | AccessPolicyDefaultAction |
action_result.data.\*.defaultAction.action | string | | BLOCK |

## action: 'delete access control policies'

Deletes the specified access control policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Id of the policy to delete | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | new-policy |
action_result.data.\*.type | string | | AccessPolicy |
action_result.data.\*.links.self | string | | AccessPolicy |
action_result.data.\*.rules.type | string | | AccessRule |
action_result.data.\*.rules.links.self | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.defaultAction.id | string | | |
action_result.data.\*.defaultAction.type | string | | AccessPolicyDefaultAction |
action_result.data.\*.defaultAction.action | string | | BLOCK |
action_result.data.\*.securityIntelligence.id | string | | |
action_result.data.\*.securityIntelligence.type | string | | SecurityIntelligencePolicy |
action_result.data.\*.securityIntelligence.links.self | string | | |

## action: 'get access control rules'

Gets all access control rules associated with a particular access control policy

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Access control policy that the rule is apart of | string | |
**rule_id** | optional | Id of the rules | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | new-rule |
action_result.parameter.rule_id | string | | |

## action: 'create access control rule'

Creates an access control rule associated with a particular access control policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Access control policy the rule will be apart of | string | |
**name** | required | Name of the access control rule | string | |
**action** | required | Type of action to take on matching traffic | string | |
**enabled** | optional | Wether the rule is enabled | boolean | |
**source_networks** | optional | Network groups or objects to determine what action to take against traffic based on where it originated from | string | |
**destination_networks** | optional | Network groups or objects to determine what action to take against traffic based on its intended destination | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.name | string | | |
action_result.parameter.action | string | | BLOCK |
action_result.parameter.enabled | boolean | | |
action_result.parameter.source_networks | string | | 00000000-0000-0ed3-0000-012884902229, 00000000-0000-0ed3-0000-012884902491 |
action_result.parameter.destination_networks | string | | 00000000-0000-0ed3-0000-012884902229, 00000000-0000-0ed3-0000-012884902491 |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | AccessRule |
action_result.data.\*.links.self | string | | |
action_result.data.\*.action | string | | BLOCK |
action_result.data.\*.logEnd | boolean | | |
action_result.data.\*.enabled | boolean | | |
action_result.data.\*.logBegin | boolean | | |
action_result.data.\*.logFiles | boolean | | |
action_result.data.\*.metadata.accessPolicy.id | string | | |
action_result.data.\*.metadata.accessPolicy.name | string | | |
action_result.data.\*.metadata.accessPolicy.type | string | | AccessPolicy |
action_result.data.\*.variableSet.id | string | | |
action_result.data.\*.variableSet.name | string | | |
action_result.data.\*.variableSet.type | string | | VariableSet |
action_result.data.\*.sourceNetworks.objects.\*.id | string | | |
action_result.data.\*.sourceNetworks.objects.\*.name | string | | |
action_result.data.\*.sourceNetworks.objects.\*.type | string | | NetworkGroup Network |
action_result.data.\*.sourceNetworks.objects.\*.overridable | boolean | | |
action_result.data.\*.sendEventsToFMC | boolean | | |
action_result.data.\*.destinationNetworks.objects.\*.id | string | | |
action_result.data.\*.destinationNetworks.objects.\*.name | string | | |
action_result.data.\*.destinationNetworks.objects.\*.type | string | | NetworkGroup Network |
action_result.data.\*.destinationNetworks.objects.\*.overridable | boolean | | |

## action: 'update access control rule'

Updates an access control rule associated with a particular access control policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_id** | required | Access control rule to update | string | |
**policy_id** | required | Access control policy that the rule is apart of | string | |
**name** | optional | Name of the access control rule | string | |
**action** | optional | Type of action to take on matching traffic | string | |
**enabled** | optional | Wether the rule is enabled | boolean | |
**source_networks_to_add** | optional | Add these network groups or objects to the rules source networks | string | |
**source_networks_to_remove** | optional | Remove these network groups or objects from the rules source networks | string | |
**destination_networks_to_add** | optional | Add these network groups or objects to the rules destination networks | string | |
**destination_networks_to_remove** | optional | Remove these network groups or objects from the rules destination networks | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.rule_id | string | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.name | string | | |
action_result.parameter.action | string | | BLOCK |
action_result.parameter.enabled | boolean | | |
action_result.parameter.source_networks_to_add | string | | 00000000-0000-0ed3-0000-012884902229, 00000000-0000-0ed3-0000-012884902491 |
action_result.parameter.source_networks_to_remove | string | | 00000000-0000-0ed3-0000-012884902229, 00000000-0000-0ed3-0000-012884902491 |
action_result.parameter.destination_networks_to_add | string | | 00000000-0000-0ed3-0000-012884902229, 00000000-0000-0ed3-0000-012884902491 |
action_result.parameter.destination_networks_to_remove | string | | 00000000-0000-0ed3-0000-012884902229, 00000000-0000-0ed3-0000-012884902491 |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | AccessRule |
action_result.data.\*.links.self | string | | |
action_result.data.\*.action | string | | BLOCK |
action_result.data.\*.logEnd | boolean | | |
action_result.data.\*.enabled | boolean | | |
action_result.data.\*.logBegin | boolean | | |
action_result.data.\*.logFiles | boolean | | |
action_result.data.\*.metadata.domain.id | string | | |
action_result.data.\*.metadata.domain.name | string | | Global |
action_result.data.\*.metadata.domain.type | string | | Domain |
action_result.data.\*.metadata.accessPolicy.id | string | | |
action_result.data.\*.metadata.accessPolicy.name | string | | |
action_result.data.\*.metadata.accessPolicy.type | string | | AccessPolicy |
action_result.data.\*.variableSet.id | string | | |
action_result.data.\*.variableSet.name | string | | |
action_result.data.\*.variableSet.type | string | | VariableSet |
action_result.data.\*.sourceNetworks.objects.\*.id | string | | |
action_result.data.\*.sourceNetworks.objects.\*.name | string | | |
action_result.data.\*.sourceNetworks.objects.\*.type | string | | NetworkGroup Network |
action_result.data.\*.sourceNetworks.objects.\*.overridable | boolean | | |
action_result.data.\*.sendEventsToFMC | boolean | | |
action_result.data.\*.destinationNetworks.objects.\*.id | string | | |
action_result.data.\*.destinationNetworks.objects.\*.name | string | | |
action_result.data.\*.destinationNetworks.objects.\*.type | string | | NetworkGroup Network |
action_result.data.\*.destinationNetworks.objects.\*.overridable | boolean | | |

## action: 'delete access control rules'

Deletes access control rule associated with a particular access control policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_id** | required | Access control rule to delete | string | |
**policy_id** | required | Access control policy that the rule is apart of | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.rule_id | string | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | AccessRule |
action_result.data.\*.links.self | string | | |
action_result.data.\*.action | string | | BLOCK |
action_result.data.\*.logEnd | boolean | | |
action_result.data.\*.enabled | boolean | | |
action_result.data.\*.logBegin | boolean | | |
action_result.data.\*.logFiles | boolean | | |
action_result.data.\*.metadata.domain.id | string | | |
action_result.data.\*.metadata.domain.name | string | | Global |
action_result.data.\*.metadata.domain.type | string | | Domain |
action_result.data.\*.metadata.accessPolicy.id | string | | |
action_result.data.\*.metadata.accessPolicy.name | string | | |
action_result.data.\*.metadata.accessPolicy.type | string | | AccessPolicy |
action_result.data.\*.variableSet.id | string | | |
action_result.data.\*.variableSet.name | string | | |
action_result.data.\*.variableSet.type | string | | VariableSet |
action_result.data.\*.sourceNetworks.objects.\*.id | string | | |
action_result.data.\*.sourceNetworks.objects.\*.name | string | | |
action_result.data.\*.sourceNetworks.objects.\*.type | string | | NetworkGroup Network |
action_result.data.\*.sourceNetworks.objects.\*.overridable | boolean | | |
action_result.data.\*.sendEventsToFMC | boolean | | |
action_result.data.\*.destinationNetworks.objects.\*.id | string | | |
action_result.data.\*.destinationNetworks.objects.\*.name | string | | |
action_result.data.\*.destinationNetworks.objects.\*.type | string | | NetworkGroup Network |
action_result.data.\*.destinationNetworks.objects.\*.overridable | boolean | | |

## action: 'list intrusion policies'

Gets all intrusion polcies in the FMC host for a particular domain

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | optional | Intrusion policy to retrieve | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.name | string | | new-policy |
action_result.data.\*.policy_id | string | | 00000000-0000-0ed3-0000-012884902138 |
action_result.parameter.policy_id | string | | |

## action: 'create intrusion policy'

Create an intrusion policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of the intrusion policy | string | |
**description** | optional | Description of the intrusion policy | string | |
**base_policy** | required | Base intrusion policy ID. Can be found using list intrusion policies | string | |
**inspection_mode** | optional | The inspection mode for the Snort 3 engine | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.name | string | | |
action_result.parameter.description | string | | |
action_result.parameter.base_policy | string | | |
action_result.parameter.inspection_mode | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | new-policy |
action_result.data.\*.type | string | | intrusionpolicy |
action_result.data.\*.basePolicy.id | string | | |
action_result.data.\*.basePolicy.name | string | | Balanced Security and Connectivity |
action_result.data.\*.basePolicy.type | string | | intrusionpolicy |
action_result.data.\*.basePolicy.inspectionMode | string | | DETECTION |
action_result.data.\*.basePolicy.isSystemDefined | boolean | | |
action_result.data.\*.description | string | | |
action_result.data.\*.inspectionMode | string | | DETECTION |

## action: 'update intrusion policy'

Update an intrusion policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Id of the intrusion policy to update | string | |
**name** | optional | Name of the policy | string | |
**description** | optional | Description of the policy | string | |
**base_policy** | optional | Base intrusion policy ID. Can be found using list intrusion policies | string | |
**inspection_mode** | optional | The inspection mode for the Snort 3 engine | string | |
**replicate_inspection_mode** | optional | Whether to replicate inspection_mode from Snort 3 to Snort | boolean | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.name | string | | |
action_result.parameter.description | string | | |
action_result.parameter.base_policy | string | | |
action_result.parameter.inspection_mode | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | new-policy |
action_result.data.\*.type | string | | intrusionpolicy |
action_result.data.\*.basePolicy.id | string | | |
action_result.data.\*.basePolicy.name | string | | Balanced Security and Connectivity |
action_result.data.\*.basePolicy.type | string | | intrusionpolicy |
action_result.data.\*.basePolicy.inspectionMode | string | | DETECTION |
action_result.data.\*.basePolicy.isSystemDefined | boolean | | |
action_result.data.\*.description | string | | |
action_result.data.\*.inspectionMode | string | | DETECTION |
action_result.parameter.replicate_inspection_mode | boolean | | |

## action: 'delete intrusion policy'

Deletes the specified access intrusion policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Id of the policy to delete | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.policy_id | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | new-policy |
action_result.data.\*.type | string | | intrusionpolicy |
action_result.data.\*.basePolicy.id | string | | |
action_result.data.\*.basePolicy.name | string | | Balanced Security and Connectivity |
action_result.data.\*.basePolicy.type | string | | intrusionpolicy |
action_result.data.\*.basePolicy.inspectionMode | string | | DETECTION |
action_result.data.\*.basePolicy.isSystemDefined | boolean | | |
action_result.data.\*.description | string | | |
action_result.data.\*.inspectionMode | string | | DETECTION |

## action: 'list devices'

Lists all devices belonging to a particular domain/tenant

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | SENSOR |
action_result.data.\*.links.self | string | | |

## action: 'get deployable devices'

List all devices with configuration chnges that are ready to be deployed

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.type | string | | SENSOR |

## action: 'deploy devices'

Deploy devices that are ready to deploy

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**devices** | optional | Device IDs of devices to deploy changes to. If left empty all devices with configuration changes will deploy | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.devices | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.type | string | | DeploymentRequest |
action_result.data.\*.version | string | | |
action_result.data.\*.metadata.task.id | string | | |
action_result.data.\*.metadata.task.links.self | string | | https://hostname/api/fmc_config/v1/domain/default/job/taskstatuses/77309722217 |
action_result.data.\*.deviceList.\* | string | | |

## action: 'get deployment status'

Get status of a deployment

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**deployment_id** | required | Id of the deployment | string | |
**domain_name** | optional | Firepower Domain. If none is specified the default domain will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.deployment_id | string | | |
action_result.parameter.domain_name | string | | |
action_result.data.\*.id | string | | DeploymentRequest |
action_result.data.\*.task | string | | TaskStatus |
action_result.data.\*.status | string | | Deploying Deployed |
action_result.data.\*.message | string | | |
action_result.data.\*.deviceList.\* | string | | |

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
