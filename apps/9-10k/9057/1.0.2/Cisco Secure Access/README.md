# Cisco Secure Access

Publisher: Splunk <br>
Connector Version: 1.0.2 <br>
Product Vendor: Cisco <br>
Product Name: Cisco Secure Access <br>
Minimum Product Version: 7.0.0

Cisco Secure Access API actions for Splunk SOAR

This connector uses the Cisco Secure Access API with OAuth 2.0 client credentials.
Create an API key in Cisco Secure Access and configure the Splunk SOAR asset with
the generated client ID and client secret.

## Prerequisites

- A Cisco Secure Access tenant with access to the APIs used by the connector.
- A Cisco Secure Access API key that includes the OAuth scopes required for the
  actions you plan to run.
- Network connectivity from Splunk SOAR to the configured Cisco Secure Access API
  base URL. The default base URL is `https://api.sse.cisco.com`.
- The SOAR asset must be configured with the API key's client ID and client
  secret.

## Asset Configuration

The following asset fields are used for Cisco Secure Access authentication and
action behavior:

- **Base URL** - Cisco Secure Access API base URL. The default value is
  `https://api.sse.cisco.com`.
- **Client ID** - Client ID from the Cisco Secure Access API key.
- **Client Secret** - Client secret from the Cisco Secure Access API key.
- **Auth Header Name** - HTTP header used for the bearer token. The default
  value is `Authorization`. The connector always sends the value as
  `Bearer <token>`.
- **Default Destination List ID** - Optional destination list ID used by the
  destination list add and remove actions when an action parameter value is not
  provided.

## Cisco API Scopes

Cisco documents the required OAuth scopes in the Secure Access API reference for
each endpoint. Test Connectivity only verifies that the connector can request an
OAuth token from `/auth/v2/token`. A successful Test Connectivity result does not
guarantee that the API key has permission to run every action. If an action fails
with `401 Unauthorized` or `403 Forbidden`, verify that the API key is valid and
contains the scope listed for that action below.

### Action-Specific Scope Reference

| Action | Required Cisco OAuth Scope |
| --- | --- |
| `test connectivity` | No action API scope. Requires valid client credentials for `/auth/v2/token`. |
| `list destination lists` | `policies.destinationLists:read` |
| `list destination lists` with **list_destinations** enabled | `policies.destinationLists:read` and `policies.destinations:read` |
| `create destination list` | `policies.destinationLists:write` |
| `add to destination list` | `policies.destinations:write` and `policies.destinations:read` |
| `remove destinations from list` | `policies.destinations:write` |
| `list managed devices` | `deployments.networkdevices:read` |
| `get network device` | `deployments.networkdevices:read` |
| `delete managed device` | `deployments.networkdevices:write` |
| `list virtual appliances` | `deployments.virtualappliances:read` |
| `list sites` | `deployments.sites:read` |
| `list roaming computers` | `deployments.roamingcomputers:read` |
| `get roaming computer` | `deployments.roamingcomputers:read` |
| `list network tunnel groups` | `deployments.networktunnelgroups:read` |
| `get network tunnel group` | `deployments.networktunnelgroups:read` |
| `list resource connectors` | `deployments.resourceconnectors:read` |
| `get domain status` | `investigate.investigate:read` |
| `get domain risk score` | `investigate.investigate:read` |
| `get passive dns` | `investigate.investigate:read` |
| `list identities` | `deployments.identities:read` |
| `update identities` | `deployments.identities:write` |
| `list certificates for device` | `admin.ztna.devices:read` |
| `list certificates for user` | `admin.ztna.users:read` |
| `make request` | Depends on the Cisco Secure Access endpoint being called. |
| `create rule` | `policies.rules:write` |
| `list firewall rules` | `policies.rules:read` |
| `list swg override device settings` | `deployments.devices.swg:read` |
| `set swg override device settings` | `deployments.devices.swg:write` |
| `delete swg override device settings` | `deployments.devices.swg:write` |
| `list vpn sessions` | `admin.vpn:read` |

## Useful Cisco Documentation

- [Cisco Secure Access API Authentication](https://developer.cisco.com/docs/cloud-security/secure-access-api-authentication/)
- [Cisco Secure Access API Getting Started](https://developer.cisco.com/docs/cloud-security/secure-access-api-getting-started/)
- [Create Authorization Token](https://developer.cisco.com/docs/cloud-security/create-authorization-token/)
- [Destination Lists API](https://developer.cisco.com/docs/cloud-security/get-destination-lists/)
- [Network Devices API](https://developer.cisco.com/docs/cloud-security/list-network-devices/)
- [Investigate API](https://developer.cisco.com/docs/cloud-security/get-domain-status-and-categorization/)
- [Policy Rules API](https://developer.cisco.com/docs/cloud-security/list-rules/)
- [SWG Device Settings API](https://developer.cisco.com/docs/cloud-security/list-swg-override-device-settings/)
- [VPN Connections API](https://developer.cisco.com/docs/cloud-security/list-vpn-connections/)

### Configuration variables

This table lists the configuration variables required to operate Cisco Secure Access. These variables are specified when configuring a Cisco Secure Access asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base Url |
**client_id** | required | string | Client ID for authentication |
**client_secret** | required | password | Client Secret key for authentication |
**auth_header_name** | required | string | HTTP header name for the Bearer token (value is always sent as 'Bearer {token}') |
**default_destination_list_id** | optional | string | Default destination list ID to use for automated domain/URL blocking |

### Supported Actions

[test connectivity](#action-test-connectivity) - Test OAuth authentication to Cisco Secure Access. <br>
[list destination lists](#action-list-destination-lists) - List Cisco Secure Access destination lists. <br>
[create destination list](#action-create-destination-list) - Create a Cisco Secure Access destination list. <br>
[add to destination list](#action-add-to-destination-list) - Add one domain, URL, or IP destination to a destination list. <br>
[remove destinations from list](#action-remove-destinations-from-list) - Remove one or more destination entries from a destination list. <br>
[list managed devices](#action-list-managed-devices) - List managed network devices registered in Cisco Secure Access. <br>
[delete managed device](#action-delete-managed-device) - Delete one managed network device by origin ID. <br>
[get network device](#action-get-network-device) - Get details for one managed network device by origin ID. <br>
[list virtual appliances](#action-list-virtual-appliances) - List virtual appliances in the organization <br>
[list sites](#action-list-sites) - List sites in the organization <br>
[get roaming computer](#action-get-roaming-computer) - Get posture and security details for a roaming computer <br>
[list roaming computers](#action-list-roaming-computers) - List roaming computers in the organization <br>
[list network tunnel groups](#action-list-network-tunnel-groups) - List network tunnel groups in the organization <br>
[get network tunnel group](#action-get-network-tunnel-group) - Get a network tunnel group by ID <br>
[list resource connectors](#action-list-resource-connectors) - List resource connectors in the organization <br>
[get domain status](#action-get-domain-status) - Get the status and categorization of a domain <br>
[get domain risk score](#action-get-domain-risk-score) - Get the risk score for a domain <br>
[get passive dns](#action-get-passive-dns) - Get passive DNS records for a domain <br>
[list identities](#action-list-identities) - List device or security group tag identities <br>
[update identities](#action-update-identities) - Create or update device or security group tag identities <br>
[list certificates for device](#action-list-certificates-for-device) - List latest ZTNA certificates for a specific user device. <br>
[list certificates for user](#action-list-certificates-for-user) - List latest ZTNA device certificates for a user. <br>
[make request](#action-make-request) - Send an authenticated request to a Cisco Secure Access API endpoint. <br>
[create rule](#action-create-rule) - Create an access policy rule. <br>
[list firewall rules](#action-list-firewall-rules) - List access policy rules. <br>
[list swg override device settings](#action-list-swg-override-device-settings) - List Cisco Secure Web Gateway override settings for managed devices. <br>
[set swg override device settings](#action-set-swg-override-device-settings) - Set Cisco Secure Web Gateway override settings for managed devices. <br>
[delete swg override device settings](#action-delete-swg-override-device-settings) - Delete Cisco Secure Web Gateway override settings for managed devices. <br>
[list vpn sessions](#action-list-vpn-sessions) - List active VPN sessions

## action: 'test connectivity'

Test OAuth authentication to Cisco Secure Access.

Type: **test** <br>
Read only: **True**

Verifies that the configured asset can authenticate to Cisco Secure Access with OAuth credentials.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list destination lists'

List Cisco Secure Access destination lists.

Type: **generic** <br>
Read only: **True**

Lists destination list metadata. Set list_destinations to true to also fetch destination entries for each list. Use destination list IDs from this action when adding or removing destinations.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**list_destinations** | optional | If true, also fetch and embed each list's destination entries. Default false (returns list metadata only). | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.list_destinations | boolean | | |
action_result.data.\*.destinationLists.\*.id | numeric | | |
action_result.data.\*.destinationLists.\*.organizationId | numeric | | |
action_result.data.\*.destinationLists.\*.access | string | | |
action_result.data.\*.destinationLists.\*.isGlobal | boolean | | True False |
action_result.data.\*.destinationLists.\*.name | string | | |
action_result.data.\*.destinationLists.\*.thirdpartyCategoryId | numeric | | |
action_result.data.\*.destinationLists.\*.createdAt | numeric | | |
action_result.data.\*.destinationLists.\*.modifiedAt | numeric | | |
action_result.data.\*.destinationLists.\*.isMspDefault | boolean | | True False |
action_result.data.\*.destinationLists.\*.markedForDeletion | boolean | | True False |
action_result.data.\*.destinationLists.\*.bundleTypeId | numeric | | |
action_result.data.\*.destinationLists.\*.destinationCount | numeric | | |
action_result.data.\*.destinationLists.\*.domainCount | numeric | | |
action_result.data.\*.destinationLists.\*.urlCount | numeric | | |
action_result.data.\*.destinationLists.\*.ipv4Count | numeric | | |
action_result.data.\*.destinationLists.\*.ipv6Count | numeric | | |
action_result.data.\*.destinationLists.\*.applicationCount | numeric | | |
action_result.data.\*.destinationLists.\*.destinations.\*.id | string | | |
action_result.data.\*.destinationLists.\*.destinations.\*.type | string | | |
action_result.data.\*.destinationLists.\*.destinations.\*.createdAt | string | | |
action_result.data.\*.destinationLists.\*.destinations.\*.destination | string | | |
action_result.data.\*.destinationLists.\*.destinations.\*.comment | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create destination list'

Create a Cisco Secure Access destination list.

Type: **generic** <br>
Read only: **False**

Creates a non-global destination list for Access policies. The request sets isGlobal=false and bundleTypeId=2. Optional destinations_json must be a JSON array of no more than 500 domain, URL, or IPv4 destinations. Cisco Secure Access does not support creating thirdparty_block destination lists through this API.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of the destination list. | string | |
**access** | required | Access classification for the list (used with access rules). Cannot create lists with access type thirdparty_block via this API. | string | |
**destinations_json** | optional | Optional JSON array of up to 500 destinations, e.g. [{"destination":"cisco.com","type":"domain","comment":"optional"}]. type: domain, url, or ipv4. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.name | string | | |
action_result.parameter.access | string | | |
action_result.parameter.destinations_json | string | | |
action_result.data.\*.destinationList.id | numeric | | |
action_result.data.\*.destinationList.organizationId | numeric | | |
action_result.data.\*.destinationList.access | string | | |
action_result.data.\*.destinationList.isGlobal | boolean | | True False |
action_result.data.\*.destinationList.name | string | | |
action_result.data.\*.destinationList.thirdpartyCategoryId | numeric | | |
action_result.data.\*.destinationList.createdAt | numeric | | |
action_result.data.\*.destinationList.modifiedAt | numeric | | |
action_result.data.\*.destinationList.isMspDefault | boolean | | True False |
action_result.data.\*.destinationList.markedForDeletion | boolean | | True False |
action_result.data.\*.destinationList.bundleTypeId | numeric | | |
action_result.data.\*.destinationList.destinationCount | numeric | | |
action_result.data.\*.destinationList.domainCount | numeric | | |
action_result.data.\*.destinationList.urlCount | numeric | | |
action_result.data.\*.destinationList.ipv4Count | numeric | | |
action_result.data.\*.destinationList.ipv6Count | numeric | | |
action_result.data.\*.destinationList.applicationCount | numeric | | |
action_result.data.\*.destinationList.destinations.\*.id | string | | |
action_result.data.\*.destinationList.destinations.\*.type | string | | |
action_result.data.\*.destinationList.destinations.\*.createdAt | string | | |
action_result.data.\*.destinationList.destinations.\*.destination | string | | |
action_result.data.\*.destinationList.destinations.\*.comment | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add to destination list'

Add one domain, URL, or IP destination to a destination list.

Type: **generic** <br>
Read only: **False**

Adds one destination entry per run. Provide a destination list ID from List Destination Lists, or configure a default destination list ID on the asset. The destination can be a domain, URL, or IP address.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**destination_list_id** | optional | Destination List ID. If not provided, the default destination list ID will be used. | numeric | |
**destination** | required | Destination URL, domain, or IP address | string | |
**comment** | optional | Comment for the destination | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.destination_list_id | numeric | | |
action_result.parameter.destination | string | | |
action_result.parameter.comment | string | | |
action_result.data.\*.addedDestinationId | string | | |
action_result.data.\*.destinationList.id | numeric | | |
action_result.data.\*.destinationList.organizationId | numeric | | |
action_result.data.\*.destinationList.access | string | | |
action_result.data.\*.destinationList.isGlobal | boolean | | True False |
action_result.data.\*.destinationList.name | string | | |
action_result.data.\*.destinationList.thirdpartyCategoryId | numeric | | |
action_result.data.\*.destinationList.createdAt | numeric | | |
action_result.data.\*.destinationList.modifiedAt | numeric | | |
action_result.data.\*.destinationList.isMspDefault | boolean | | True False |
action_result.data.\*.destinationList.markedForDeletion | boolean | | True False |
action_result.data.\*.destinationList.bundleTypeId | numeric | | |
action_result.data.\*.destinationList.destinationCount | numeric | | |
action_result.data.\*.destinationList.domainCount | numeric | | |
action_result.data.\*.destinationList.urlCount | numeric | | |
action_result.data.\*.destinationList.ipv4Count | numeric | | |
action_result.data.\*.destinationList.ipv6Count | numeric | | |
action_result.data.\*.destinationList.applicationCount | numeric | | |
action_result.data.\*.destinationList.destinations.\*.id | string | | |
action_result.data.\*.destinationList.destinations.\*.type | string | | |
action_result.data.\*.destinationList.destinations.\*.createdAt | string | | |
action_result.data.\*.destinationList.destinations.\*.destination | string | | |
action_result.data.\*.destinationList.destinations.\*.comment | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove destinations from list'

Remove one or more destination entries from a destination list.

Type: **generic** <br>
Read only: **False**

Removes destination entries by destination entry ID, not by destination value. Get entry IDs from List Destination Lists with list_destinations enabled or from Add To Destination List output. Provide a destination list ID or configure a default destination list ID on the asset.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**destination_list_id** | optional | The ID of the Destination List to remove destinations from. If not provided, the default destination list ID will be used. | numeric | |
**destination_ids** | required | Comma-separated destination IDs to remove (e.g. 60582,60583). | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.destination_list_id | numeric | | |
action_result.parameter.destination_ids | string | | |
action_result.data.\*.destinationList.id | numeric | | |
action_result.data.\*.destinationList.organizationId | numeric | | |
action_result.data.\*.destinationList.access | string | | |
action_result.data.\*.destinationList.isGlobal | boolean | | True False |
action_result.data.\*.destinationList.name | string | | |
action_result.data.\*.destinationList.thirdpartyCategoryId | numeric | | |
action_result.data.\*.destinationList.createdAt | numeric | | |
action_result.data.\*.destinationList.modifiedAt | numeric | | |
action_result.data.\*.destinationList.isMspDefault | boolean | | True False |
action_result.data.\*.destinationList.markedForDeletion | boolean | | True False |
action_result.data.\*.destinationList.bundleTypeId | numeric | | |
action_result.data.\*.destinationList.destinationCount | numeric | | |
action_result.data.\*.destinationList.domainCount | numeric | | |
action_result.data.\*.destinationList.urlCount | numeric | | |
action_result.data.\*.destinationList.ipv4Count | numeric | | |
action_result.data.\*.destinationList.ipv6Count | numeric | | |
action_result.data.\*.destinationList.applicationCount | numeric | | |
action_result.data.\*.destinationList.destinations.\*.id | string | | |
action_result.data.\*.destinationList.destinations.\*.type | string | | |
action_result.data.\*.destinationList.destinations.\*.createdAt | string | | |
action_result.data.\*.destinationList.destinations.\*.destination | string | | |
action_result.data.\*.destinationList.destinations.\*.comment | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list managed devices'

List managed network devices registered in Cisco Secure Access.

Type: **generic** <br>
Read only: **True**

Lists Cisco Secure Access managed network devices. Use the originId returned by this action as the lookup or delete identifier for a device.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.data.\*.devices.\*.originId | numeric | | |
action_result.data.\*.devices.\*.deviceId | string | | |
action_result.data.\*.devices.\*.deviceKey | string | | |
action_result.data.\*.devices.\*.name | string | | |
action_result.data.\*.devices.\*.serialNumber | string | | |
action_result.data.\*.devices.\*.createdAt | string | | |
action_result.data.\*.devices.\*.organizationId | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete managed device'

Delete one managed network device by origin ID.

Type: **generic** <br>
Read only: **False**

Deletes a managed network device using its originId. Get the originId from List Managed Devices.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**origin_id** | required | Origin ID of the network device to remove (obtain from the List Managed Devices action). | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.origin_id | numeric | | |
action_result.data.\*.success | boolean | | True False |
action_result.data.\*.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get network device'

Get details for one managed network device by origin ID.

Type: **generic** <br>
Read only: **True**

Retrieves one managed network device using its originId. Get the originId from List Managed Devices.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**origin_id** | required | Origin ID of the network device (obtain from the List Managed Devices action). | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.origin_id | numeric | | |
action_result.data.\*.originId | numeric | | |
action_result.data.\*.deviceId | string | | |
action_result.data.\*.deviceKey | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.serialNumber | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.organizationId | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list virtual appliances'

List virtual appliances in the organization

Type: **generic** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.data.\*.virtualAppliances.\*.originId | numeric | | |
action_result.data.\*.virtualAppliances.\*.name | string | | |
action_result.data.\*.virtualAppliances.\*.isUpgradable | boolean | | True False |
action_result.data.\*.virtualAppliances.\*.health | string | | |
action_result.data.\*.virtualAppliances.\*.type | string | | |
action_result.data.\*.virtualAppliances.\*.stateUpdatedAt | string | | |
action_result.data.\*.virtualAppliances.\*.siteId | numeric | | |
action_result.data.\*.virtualAppliances.\*.createdAt | string | | |
action_result.data.\*.virtualAppliances.\*.modifiedAt | string | | |
action_result.data.\*.virtualAppliances.\*.state_syncing | string | | |
action_result.data.\*.virtualAppliances.\*.internalIPs.\* | string | | |
action_result.data.\*.virtualAppliances.\*.externalIP | string | | |
action_result.data.\*.virtualAppliances.\*.hostType | string | | |
action_result.data.\*.virtualAppliances.\*.uptime | numeric | | |
action_result.data.\*.virtualAppliances.\*.version | string | | |
action_result.data.\*.virtualAppliances.\*.domains.\* | string | | |
action_result.data.\*.virtualAppliances.\*.lastSyncTime | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list sites'

List sites in the organization

Type: **generic** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.data.\*.sites.\*.originId | numeric | | |
action_result.data.\*.sites.\*.name | string | | |
action_result.data.\*.sites.\*.siteId | numeric | | |
action_result.data.\*.sites.\*.isDefault | boolean | | True False |
action_result.data.\*.sites.\*.modifiedAt | string | | |
action_result.data.\*.sites.\*.createdAt | string | | |
action_result.data.\*.sites.\*.type | string | | |
action_result.data.\*.sites.\*.internalNetworkCount | numeric | | |
action_result.data.\*.sites.\*.vaCount | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get roaming computer'

Get posture and security details for a roaming computer

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**device_id** | required | The device ID (deviceId) of the roaming computer, e.g. AB00C7DCEC99D211. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.device_id | string | | |
action_result.data.\*.originId | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.deviceId | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.status | string | | |
action_result.data.\*.swgStatus | string | | |
action_result.data.\*.lastSyncStatus | string | | |
action_result.data.\*.lastSyncSwgStatus | string | | |
action_result.data.\*.lastSync | string | | |
action_result.data.\*.appliedBundle | numeric | | |
action_result.data.\*.hasIpBlocking | boolean | | True False |
action_result.data.\*.version | string | | |
action_result.data.\*.osVersion | string | | |
action_result.data.\*.osVersionName | string | | |
action_result.data.\*.anyconnectDeviceId | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list roaming computers'

List roaming computers in the organization

Type: **generic** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.data.\*.roamingComputers.\*.originId | numeric | | |
action_result.data.\*.roamingComputers.\*.name | string | | |
action_result.data.\*.roamingComputers.\*.deviceId | string | | |
action_result.data.\*.roamingComputers.\*.type | string | | |
action_result.data.\*.roamingComputers.\*.status | string | | |
action_result.data.\*.roamingComputers.\*.swgStatus | string | | |
action_result.data.\*.roamingComputers.\*.lastSyncStatus | string | | |
action_result.data.\*.roamingComputers.\*.lastSyncSwgStatus | string | | |
action_result.data.\*.roamingComputers.\*.lastSync | string | | |
action_result.data.\*.roamingComputers.\*.appliedBundle | numeric | | |
action_result.data.\*.roamingComputers.\*.hasIpBlocking | boolean | | True False |
action_result.data.\*.roamingComputers.\*.version | string | | |
action_result.data.\*.roamingComputers.\*.osVersion | string | | |
action_result.data.\*.roamingComputers.\*.osVersionName | string | | |
action_result.data.\*.roamingComputers.\*.anyconnectDeviceId | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list network tunnel groups'

List network tunnel groups in the organization

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**offset** | optional | Index to start reading the collection (0-based). Default 0. | numeric | |
**limit** | optional | Number of records per page (1-200). Default 10. | numeric | |
**filters** | optional | Optional JSON object to filter by name, exactName, region, networkTunnelGroupIds, exactAuthIdPrefix, status, or duplicateCIDRs. See API docs. | string | |
**sort_by** | optional | Sort field: name, status, createdAt, modifiedAt. | string | |
**sort_order** | optional | Sort order: asc or desc. | string | |
**include_statuses** | optional | Include tunnelsStatus for each hub (max 10 tunnel states per hub). | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.offset | numeric | | |
action_result.parameter.limit | numeric | | |
action_result.parameter.filters | string | | |
action_result.parameter.sort_by | string | | |
action_result.parameter.sort_order | string | | |
action_result.parameter.include_statuses | boolean | | |
action_result.data.\*.data.\*.id | numeric | | |
action_result.data.\*.data.\*.name | string | | |
action_result.data.\*.data.\*.organizationId | numeric | | |
action_result.data.\*.data.\*.deviceType | string | | |
action_result.data.\*.data.\*.region | string | | |
action_result.data.\*.data.\*.status | string | | |
action_result.data.\*.data.\*.hubs.\*.id | numeric | | |
action_result.data.\*.data.\*.hubs.\*.name | string | | |
action_result.data.\*.data.\*.hubs.\*.status.time | string | | |
action_result.data.\*.data.\*.hubs.\*.status.status | string | | |
action_result.data.\*.data.\*.routing.type | string | | |
action_result.data.\*.data.\*.createdAt | string | | |
action_result.data.\*.data.\*.modifiedAt | string | | |
action_result.data.\*.offset | numeric | | |
action_result.data.\*.limit | numeric | | |
action_result.data.\*.total | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get network tunnel group'

Get a network tunnel group by ID

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID of the network tunnel group (obtain from the List Network Tunnel Groups action). | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.id | numeric | | |
action_result.data.\*.id | numeric | | |
action_result.data.\*.name | string | | |
action_result.data.\*.organizationId | numeric | | |
action_result.data.\*.deviceType | string | | |
action_result.data.\*.region | string | | |
action_result.data.\*.status | string | | |
action_result.data.\*.hubs.\*.id | numeric | | |
action_result.data.\*.hubs.\*.name | string | | |
action_result.data.\*.hubs.\*.status.time | string | | |
action_result.data.\*.hubs.\*.status.status | string | | |
action_result.data.\*.routing.type | string | | |
action_result.data.\*.createdAt | string | | |
action_result.data.\*.modifiedAt | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list resource connectors'

List resource connectors in the organization

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**offset** | optional | Index to start reading the collection (0-based). Default 0. | numeric | |
**limit** | optional | Maximum number of items to return. Default 10. | numeric | |
**filters** | optional | Optional JSON object to filter by groupId, instanceId, status, confirmed, hasSynced, hasLatestVersion. See API docs. | string | |
**sort_by** | optional | Sort field: instanceId, originIpAddress, createdAt, modifiedAt. | string | |
**sort_order** | optional | Sort order: asc or desc. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.offset | numeric | | |
action_result.parameter.limit | numeric | | |
action_result.parameter.filters | string | | |
action_result.parameter.sort_by | string | | |
action_result.parameter.sort_order | string | | |
action_result.data.\*.data.\*.id | numeric | | |
action_result.data.\*.data.\*.groupId | numeric | | |
action_result.data.\*.data.\*.instanceId | string | | |
action_result.data.\*.data.\*.confirmed | boolean | | True False |
action_result.data.\*.data.\*.enabled | boolean | | True False |
action_result.data.\*.data.\*.version | string | | |
action_result.data.\*.data.\*.sha1 | string | | |
action_result.data.\*.data.\*.hostname | string | | |
action_result.data.\*.data.\*.originIpAddress | string | | |
action_result.data.\*.data.\*.baseVersion | string | | |
action_result.data.\*.data.\*.isLatestBaseVersion | boolean | | True False |
action_result.data.\*.data.\*.upgradeStatus | string | | |
action_result.data.\*.data.\*.status | string | | |
action_result.data.\*.data.\*.statusUpdatedAt | string | | |
action_result.data.\*.data.\*.controlStatusUpdatedAt | string | | |
action_result.data.\*.data.\*.revoked_at | string | | |
action_result.data.\*.data.\*.createdAt | string | | |
action_result.data.\*.data.\*.modifiedAt | string | | |
action_result.data.\*.offset | numeric | | |
action_result.data.\*.limit | numeric | | |
action_result.data.\*.total | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get domain status'

Get the status and categorization of a domain

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain name to look up (e.g. cisco.com). | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.domain | string | | |
action_result.data.\*.domain | string | | |
action_result.data.\*.status | numeric | | |
action_result.data.\*.status_description | string | | |
action_result.data.\*.security_categories.\* | string | | |
action_result.data.\*.content_categories.\* | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get domain risk score'

Get the risk score for a domain

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain name to look up (e.g. cisco.com). | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.domain | string | | |
action_result.data.\*.risk_score | numeric | | |
action_result.data.\*.indicators.\*.indicator | string | | |
action_result.data.\*.indicators.\*.normalized_score | numeric | | |
action_result.data.\*.indicators.\*.score | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get passive dns'

Get passive DNS records for a domain

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | The domain to get passive DNS records for. | string | |
**offset** | optional | Index to start reading the collection (0-based). Default 0. | numeric | |
**limit** | optional | Maximum records to return in one call (1-9999). Default 1000. Use 9999 to retrieve the full set in a single call; the API caps total retrievable records at 10000 per domain. | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.domain | string | | |
action_result.parameter.offset | numeric | | |
action_result.parameter.limit | numeric | | |
action_result.data.\*.passive_dns_records.\*.minTtl | numeric | | |
action_result.data.\*.passive_dns_records.\*.maxTtl | numeric | | |
action_result.data.\*.passive_dns_records.\*.firstSeen | numeric | | |
action_result.data.\*.passive_dns_records.\*.lastSeen | numeric | | |
action_result.data.\*.passive_dns_records.\*.name | string | | |
action_result.data.\*.passive_dns_records.\*.type | string | | |
action_result.data.\*.passive_dns_records.\*.rr | string | | |
action_result.data.\*.passive_dns_records.\*.securityCategories.\* | string | | |
action_result.data.\*.passive_dns_records.\*.contentCategories.\* | string | | |
action_result.data.\*.passive_dns_records.\*.firstSeenISO | string | | |
action_result.data.\*.passive_dns_records.\*.lastSeenISO | string | | |
action_result.data.\*.total_records | numeric | | |
action_result.data.\*.returned_records | numeric | | |
action_result.data.\*.offset | numeric | | |
action_result.data.\*.limit | numeric | | |
action_result.data.\*.has_more_records | boolean | | True False |
action_result.data.\*.next_offset | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list identities'

List device or security group tag identities

Type: **generic** <br>
Read only: **True**

Lists identities by type. Use type=device for device registrations or type=securityGroupTag for security group tag identities.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**type** | required | Identity type to list: 'device' for device registrations, 'securityGroupTag' for security group tags (SGTs). | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.type | string | | |
action_result.data.\*.identities.\*.key | string | | |
action_result.data.\*.identities.\*.label | string | | |
action_result.data.\*.identities.\*.status | string | | |
action_result.data.\*.identities.\*.createdAt | numeric | | |
action_result.data.\*.identities.\*.modifiedAt | numeric | | |
action_result.data.\*.identities.\*.authName | string | | |
action_result.data.\*.identities.\*.tagId | numeric | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update identities'

Create or update device or security group tag identities

Type: **generic** <br>
Read only: **False**

Creates or updates 1-250 identity objects from identities_json. Use type=device for device registrations and type=securityGroupTag for security group tag identities. Device objects use key, label, status, and authName. Security group tag objects use key, label, status, and tagId. Set status to inactive to deactivate an identity.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**type** | required | Identity type: 'device' for identity endpoints, 'securityGroupTag' for SGTs. | string | |
**identities_json** | required | JSON array of identity objects (1-250). Devices: {"key","label","status","authName"}. SGTs: {"key","label","status","tagId"}. status: "active"|"inactive". | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.type | string | | |
action_result.parameter.identities_json | string | | |
action_result.data.\*.success | boolean | | True False |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list certificates for device'

List latest ZTNA certificates for a specific user device.

Type: **generic** <br>
Read only: **True**

Lists the latest ACME-issued ZTNA certificates for one user device by user ID and device ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | The ID of the user (ZTNA). | string | |
**device_id** | required | The ID of the user device. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.user_id | string | | |
action_result.parameter.device_id | string | | |
action_result.data.\*.deviceId | string | | |
action_result.data.\*.certificates.\*.certificateId | string | | |
action_result.data.\*.certificates.\*.status | string | | |
action_result.data.\*.certificates.\*.createdAt | string | | |
action_result.data.\*.certificates.\*.expiresAt | string | | |
action_result.data.\*.certificates.\*.revokedAt | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list certificates for user'

List latest ZTNA device certificates for a user.

Type: **generic** <br>
Read only: **True**

Lists the latest ACME-issued ZTNA device certificates for all devices associated with the specified user ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user_id** | required | The ID of the user (ZTNA). Get all device certificates for this user. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.user_id | string | | |
action_result.data.\*.userId | string | | |
action_result.data.\*.devices.\*.deviceId | string | | |
action_result.data.\*.devices.\*.certificates.\*.certificateId | string | | |
action_result.data.\*.devices.\*.certificates.\*.status | string | | |
action_result.data.\*.devices.\*.certificates.\*.createdAt | string | | |
action_result.data.\*.devices.\*.certificates.\*.expiresAt | string | | |
action_result.data.\*.devices.\*.certificates.\*.revokedAt | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'make request'

Send an authenticated request to a Cisco Secure Access API endpoint.

Type: **generic** <br>
Read only: **False**

Sends an authenticated request using the asset's Cisco Secure Access OAuth credentials. Provide an API path relative to the configured base URL, such as deployments/v2/networkdevices. Do not include the base URL.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**http_method** | required | The HTTP method to use for the request. | string | |
**endpoint** | required | Cisco Secure Access API path, relative to the configured base URL. For example: 'deployments/v2/networkdevices' or 'admin/v2/vpn/userConnections'. Do not include the base URL. | string | |
**headers** | optional | The headers to send with the request (JSON object). An example is {'Content-Type': 'application/json'} | string | |
**query_parameters** | optional | Parameters to append to the URL (JSON object or query string). An example is ?key=value&key2=value2 | string | |
**body** | optional | The body to send with the request (JSON object). An example is {'key': 'value', 'key2': 'value2'} | string | |
**timeout** | optional | The timeout for the request in seconds. | numeric | |
**verify_ssl** | optional | Whether to verify the SSL certificate. Default true. | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.http_method | string | | |
action_result.parameter.endpoint | string | | |
action_result.parameter.headers | string | | |
action_result.parameter.query_parameters | string | | |
action_result.parameter.body | string | | |
action_result.parameter.timeout | numeric | | |
action_result.parameter.verify_ssl | boolean | | |
action_result.data.\*.status_code | numeric | | 200 404 500 |
action_result.data.\*.response_body | string | | {"key": "value"} |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create rule'

Create an access policy rule.

Type: **generic** <br>
Read only: **False**

Creates an access policy rule. rule_conditions_json and rule_settings_json are required JSON arrays. rule_name must be unique and 2-50 characters.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_name** | required | Rule name (2-50 alphanumeric, hyphen, underscore, space). Unique across access rules. | string | |
**rule_action** | required | Action for the rule. | string | |
**rule_conditions_json** | required | JSON array of conditions, e.g. [{"attributeName":"umbrella.destination.all","attributeValue":true,"attributeOperator":"="},{"attributeName":"umbrella.source.all","attributeValue":true,"attributeOperator":"="}] | string | |
**rule_settings_json** | required | JSON array of settings, e.g. [{"settingName":"umbrella.default.traffic","settingValue":"PUBLIC_INTERNET"}] | string | |
**rule_description** | optional | Optional description (max 256 characters). | string | |
**rule_priority** | optional | Optional priority (positive integer, unique across rules). | numeric | |
**rule_is_enabled** | optional | Whether the rule is enabled. Default true. | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.rule_name | string | | |
action_result.parameter.rule_action | string | | |
action_result.parameter.rule_conditions_json | string | | |
action_result.parameter.rule_settings_json | string | | |
action_result.parameter.rule_description | string | | |
action_result.parameter.rule_priority | numeric | | |
action_result.parameter.rule_is_enabled | boolean | | |
action_result.data.\*.organizationId | numeric | | |
action_result.data.\*.ruleId | numeric | | |
action_result.data.\*.ruleName | string | | |
action_result.data.\*.ruleDescription | string | | |
action_result.data.\*.ruleAction | string | | |
action_result.data.\*.rulePriority | numeric | | |
action_result.data.\*.ruleIsDefault | boolean | | True False |
action_result.data.\*.ruleIsEnabled | boolean | | True False |
action_result.data.\*.ruleConditions.\*.attributeName | string | | |
action_result.data.\*.ruleConditions.\*.attributeValue | string | | |
action_result.data.\*.ruleConditions.\*.attributeOperator | string | | |
action_result.data.\*.ruleSettings.\*.settingName | string | | |
action_result.data.\*.ruleSettings.\*.settingValue | string | | |
action_result.data.\*.modifiedBy | string | | |
action_result.data.\*.modifiedAt | string | | |
action_result.data.\*.createdAt | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list firewall rules'

List access policy rules.

Type: **generic** <br>
Read only: **True**

Lists access policy rules. Use rule_name or filters to narrow results when needed.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**offset** | optional | Index to start reading the collection (0-based). Default 0. | numeric | |
**limit** | optional | Number of rules per page. Max 1000. Default 10. | numeric | |
**rule_name** | optional | Filter by rule name or substring (e.g. 'Allow all rule'). | string | |
**filters** | optional | Optional JSON object to filter rules by properties (ruleName, ruleDescription, ruleIsEnabled, ruleAction, ruleConditions, sources, destinations, etc.). Cannot combine ruleConditions with sources/destinations. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.offset | numeric | | |
action_result.parameter.limit | numeric | | |
action_result.parameter.rule_name | string | | |
action_result.parameter.filters | string | | |
action_result.data.\*.count | numeric | | |
action_result.data.\*.firewall_rules.\*.ruleId | numeric | | |
action_result.data.\*.firewall_rules.\*.organizationId | numeric | | |
action_result.data.\*.firewall_rules.\*.ruleName | string | | |
action_result.data.\*.firewall_rules.\*.ruleDescription | string | | |
action_result.data.\*.firewall_rules.\*.ruleAction | string | | |
action_result.data.\*.firewall_rules.\*.rulePriority | numeric | | |
action_result.data.\*.firewall_rules.\*.ruleIsDefault | boolean | | True False |
action_result.data.\*.firewall_rules.\*.ruleIsEnabled | boolean | | True False |
action_result.data.\*.firewall_rules.\*.modifiedBy | string | | |
action_result.data.\*.firewall_rules.\*.modifiedAt | string | | |
action_result.data.\*.firewall_rules.\*.createdAt | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list swg override device settings'

List Cisco Secure Web Gateway override settings for managed devices.

Type: **generic** <br>
Read only: **True**

Lists Cisco Secure Web Gateway override settings for 1-100 device origin IDs. Use origin IDs from managed or roaming device inventory.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**origin_ids** | required | Comma-separated origin IDs of devices (1-100) to list SWG override settings for. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.origin_ids | string | | |
action_result.data.\*.settings.\*.originId | numeric | | |
action_result.data.\*.settings.\*.name | string | | |
action_result.data.\*.settings.\*.value | string | | |
action_result.data.\*.settings.\*.modifiedAt | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'set swg override device settings'

Set Cisco Secure Web Gateway override settings for managed devices.

Type: **generic** <br>
Read only: **False**

Sets Cisco Secure Web Gateway override settings for 1-100 device origin IDs. Use value 1 to enable Secure Web Gateway and value 0 to disable it for the specified devices.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**value** | required | Enable (1) or disable (0) Secure Web Gateway for the devices. | string | |
**origin_ids** | required | Comma-separated origin IDs of devices (1-100). Devices must be registered as roaming computers. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.value | string | | |
action_result.parameter.origin_ids | string | | |
action_result.data.\*.totalCount | numeric | | |
action_result.data.\*.successCount | numeric | | |
action_result.data.\*.failCount | numeric | | |
action_result.data.\*.items.\*.originId | numeric | | |
action_result.data.\*.items.\*.code | numeric | | |
action_result.data.\*.items.\*.message | string | | |
action_result.data.\*.value | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete swg override device settings'

Delete Cisco Secure Web Gateway override settings for managed devices.

Type: **generic** <br>
Read only: **False**

Deletes Cisco Secure Web Gateway override settings for 1-100 device origin IDs. After removal, the organization Secure Web Gateway setting applies.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**origin_ids** | required | Comma-separated origin IDs of devices (1-100) to remove SWG override setting from. Organization SWG setting will apply after removal. | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.parameter.origin_ids | string | | |
action_result.data.\*.status | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list vpn sessions'

List active VPN sessions

Type: **generic** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failure |
action_result.message | string | | |
action_result.data.\*.vpn_sessions.\*.username | string | | |
action_result.data.\*.vpn_sessions.\*.deviceName | string | | |
action_result.data.\*.vpn_sessions.\*.assignedIp | string | | |
action_result.data.\*.vpn_sessions.\*.assignedIpv6 | string | | |
action_result.data.\*.vpn_sessions.\*.publicIp | string | | |
action_result.data.\*.vpn_sessions.\*.sessionId | string | | |
action_result.data.\*.vpn_sessions.\*.loginTime | string | | |
action_result.data.\*.vpn_sessions.\*.profileName | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

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
