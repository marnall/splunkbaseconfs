# Cisco ISE

Publisher: Splunk <br>
Connector Version: 3.2.1 <br>
Product Vendor: Cisco Systems <br>
Product Name: Cisco ISE <br>
Minimum Product Version: 6.3.0

This app implements investigative and containment actions on a Cisco ISE device

## Asset Configuration For Authentication

- ERS uses HTTPS port 9060 which is closed by default. Clients trying to access this port without
  enabling ERS first will face a timeout from the server. Therefore, the first requirement is to
  enable ERS from the Cisco ISE admin UI. Go to Administration > Settings > ERS Settings and
  enable the Enable ERS for Read/Write radio button
- Go to Administration > System > Admin Users. Now add an account by clicking Add > Create an
  admin user. Then enter name and password and select ERS Admin in Admin Group and then press
  save.
- Go to Administration > System > Admin Users. Now add an account by clicking Add > Create an
  admin user. Then enter name and password and select MnT Admin in Admin Group and then press
  save.
- Configurations expect user with MnT Admin Access group in username/password fields and user in
  ERS Admin group in ERS username/password fields or user with both MnT Admin or ERS Admin access
  group in username/password field.
- Also, you can add both MnT Admin and ERS Admin Access groups to a user and use that credentials
  in username/password. The App will use username/password if ERS username/password is not
  provided

## Note

1. The actions "quarantine system" and "unquarantine system" are removed in the version 3.0.0.
   Users are advised to use "apply policy" and "clear policy" actions to achieve the same objective
1. ERS credentials are required for actions
   - list endpoints
   - get device info
   - update device info
   - get resources
   - delete resource
   - create resource
   - update resource
   - apply policy
   - create policy
1. If resource is **Guest User** in resource related actions, it is required to use **Sponsor Account** credentials to access the GuestAPI, For creating sponsor account refer this document: [Set Up Admin and Sponsor Account for ERS](https://www.cisco.com/c/en/us/support/docs/security/identity-services-engine/215476-configure-ise-guest-accounts-with-rest-a.html)
1. Once you have internal user created from step #3, Add username and password in **ers_username** and **ers_password** in asset configuration respectively.
1. An ISE node can assume any or all of the following personas: Administration, Policy Service, and
   Monitoring. For detailed info: [Types of
   nodes](https://www.cisco.com/en/US/docs/security/ise/1.0/user_guide/ise10_dis_deploy.html#wp1123452)
   - All actions can run on Administration node.
   - Actions create resource, update resource, delete resource, list resource, get resources,
     list sessions, update device info, get device info, and list endpoints can run on Monitoring
     node
   - Actions quarantine device, unquarantine device, apply policy, clear policy, and terminate
     session can run on Policy Service node
1. For create resource action, user needs to provide valid json with required fields of that
   specified resource (For more details head over to [API
   Reference](https://developer.cisco.com/docs/identity-services-engine/v1/#!endpoint) ). Examples
   as below
   - Endpoint

     ```
     {
         "ERSEndPoint": {
             "name": "name",
             "description": "MyEndpoint",
             "mac": "11:22:33:44:55:66"
         }
     }
     ```

   - Endpoint identity groups

     ```
     {
         "EndPointGroup": {
             "name": "Cisco-Meraki-Device",
             "description": "Identity Group for Profile: Cisco-Meraki-Device",
             "systemDefined": "true"
         }
     }
     ```

   - Guest users

     ```
     {
         "GuestUser": {
             "name": "guestUser",
             "guestInfo": {
               "userName": "DS3ewdsa34wWE",
               "password": "asdlkj324ew", # pragma: allowlist secret
               "enabled": true
             },
             "guestAccessInfo": {
                 "validDays": 90
             }
         }
     }
     ```

   - User identity groups

     ```
     {
         "IdentityGroup": {
             "name": "GuestType_Weekly (default)",
             "parent": "NAC Group:NAC:IdentityGroups:User Identity Groups"
         }
     }
     ```

   - Internal users

     ```
     {
         "InternalUser": {
             "name": "name",
             "enabled": true,
             "password": "*******",
             "changePassword": true,
             "passwordIDStore": "Internal Users" # pragma: allowlist secret
         }
     }
     ```

   - Network devices

     ```
     {
           "NetworkDevice": {
                 "name": "ISE_EST_Local_Host",
                 "authenticationSettings": {
                     "enableKeyWrap": true,
                     "enableMultiSecret": true,
                     "keyEncryptionKey": 1234567890123456,
                     "keyInputFormat": "ASCII"
                 },
                 "coaPort": 0,
                 "snmpsettings": {
                     "pollingInterval": 3600,
                     "linkTrapQuery": true,
                     "macTrapQuery": true,
                     "originatingPolicyServicesNode": "Auto"
                 },
                 "trustsecsettings": {
                     "deviceAuthenticationSettings": {},
                     "sgaNotificationAndUpdates": {},
                     "deviceConfigurationDeployment": {},
                     "pushIdSupport": false
                 },
                 "tacacsSettings": {
                     "sharedSecret": "aaa" # pragma: allowlist secret
                 },
                 "profileName": "Cisco",
                 "NetworkDeviceIPList": [
                     {
                         "ipaddress": "127.0.0.1",
                         "mask": 32
                     }
                 ]
           }
     }
     ```

   - Network device groups

     ```
     {
         "NetworkDeviceGroup": {
             "name": "Device Type#All Device Types"
         }
     }
     ```

   - Security groups

     ```
     {
         "Sgt": {
             "name": "Employees",
             "value": 4
         }
     }
     ```

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Cisco ISE server. Below are the default
ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Cisco ISE. These variables are specified when configuring a Cisco ISE asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**device** | required | string | Device IP/Hostname |
**ha_device** | optional | string | Device IP/Hostname for a High Availability node if available |
**username** | required | string | Username |
**password** | required | password | Password |
**ers_user** | optional | string | Username for ERS APIs |
**ers_password** | optional | password | Password for ERS APIs |
**verify_server_cert** | optional | boolean | Verify server certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity. This action logs into the device using a REST API call to check the connection and credentials <br>
[list endpoints](#action-list-endpoints) - List the endpoints configured on the system <br>
[get device info](#action-get-device-info) - Get information about a specific endpoint <br>
[update device info](#action-update-device-info) - Update information or attributes for a specific endpoint <br>
[list sessions](#action-list-sessions) - List the sessions currently available on the Monitoring node <br>
[terminate session](#action-terminate-session) - Terminate sessions <br>
[list resources](#action-list-resources) - Lists all the resources configured on the system of a particular resource <br>
[get resources](#action-get-resources) - Get the information about resource if resource_id is provided. Fetch the list of resources match with the key-value filter <br>
[delete resource](#action-delete-resource) - Delete a resource <br>
[create resource](#action-create-resource) - Create a resource <br>
[update resource](#action-update-resource) - Update a resource <br>
[apply policy](#action-apply-policy) - Apply policy on selected Ip address or MAC address <br>
[clear policy](#action-clear-policy) - Clear policy on selected Ip address or MAC address <br>
[list policies](#action-list-policies) - Lists all the ANC policies available <br>
[add policy](#action-add-policy) - Add a new ANC Policy <br>
[delete policy](#action-delete-policy) - Delete a policy <br>
[list anc endpoints](#action-list-anc-endpoints) - List the endpoints with anc configured on the system <br>
[anc device info](#action-anc-device-info) - Get information about a specific endpoint with assigned anc policy

## action: 'test connectivity'

Validate the asset configuration for connectivity. This action logs into the device using a REST API call to check the connection and credentials

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list endpoints'

List the endpoints configured on the system

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**mac_address** | optional | Mac Address to filter on (6 bytes, colon separated) | string | `mac address` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.mac_address | string | `mac address` | 11:11:11:11:11:11 |
action_result.data.\*.SearchResult.resources.\*.id | string | `ise endpoint id` `ise resource id` | b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.SearchResult.resources.\*.link.href | string | `url` | https://10.11.11.11:9060/ers/config/endpoint/b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.SearchResult.resources.\*.link.rel | string | | self |
action_result.data.\*.SearchResult.resources.\*.link.type | string | | application/xml |
action_result.data.\*.SearchResult.resources.\*.name | string | | 8C:85:90:17:D6:39 |
action_result.data.\*.SearchResult.total | numeric | | 1 |
action_result.summary.Endpoints found | string | | 9 1 |
action_result.summary.endpoints_found | numeric | | 1 |
action_result.message | string | | 9 Endpoints found 1 Endpoints found |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get device info'

Get information about a specific endpoint

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpoint_id** | required | ISE Endpoint ID for device | string | `ise endpoint id` `ise resource id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpoint_id | string | `ise endpoint id` `ise resource id` | 44443c00-2222-1111-bbbb-00505687777f b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.ERSEndPoint.customAttributes.customAttributes.ITSecurityBlock | string | | true |
action_result.data.\*.ERSEndPoint.description | string | | description |
action_result.data.\*.ERSEndPoint.groupId | string | | aaaaae00-8888-1111-9999-525400b41111 |
action_result.data.\*.ERSEndPoint.id | string | `ise endpoint id` `ise resource id` | b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.ERSEndPoint.identityStore | string | | |
action_result.data.\*.ERSEndPoint.identityStoreId | string | | |
action_result.data.\*.ERSEndPoint.link.href | string | `url` | https://10.11.11.11:9060/ers/config/endpoint/b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.ERSEndPoint.link.rel | string | | self |
action_result.data.\*.ERSEndPoint.link.type | string | | application/xml |
action_result.data.\*.ERSEndPoint.mac | string | | 8C:85:90:17:D6:39 |
action_result.data.\*.ERSEndPoint.name | string | | 8C:85:90:17:D6:39 |
action_result.data.\*.ERSEndPoint.portalUser | string | | |
action_result.data.\*.ERSEndPoint.profileId | string | | 99663000-8888-11e6-9999-525400b48888 |
action_result.data.\*.ERSEndPoint.staticGroupAssignment | boolean | | True False |
action_result.data.\*.ERSEndPoint.staticProfileAssignment | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Endpoint found |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update device info'

Update information or attributes for a specific endpoint

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpoint_id** | required | ISE Endpoint ID for device | string | `ise endpoint id` `ise resource id` |
**attribute** | optional | Attribute to update for the Endpoint | string | |
**attribute_value** | optional | Value to put in the attribute for the Endpoint | string | |
**custom_attribute** | optional | Custom attribute to update for the Endpoint | string | |
**custom_attribute_value** | optional | Value to put in the custom attribute for the Endpoint | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.attribute | string | | ITSecurityBlock |
action_result.parameter.attribute_value | string | | True |
action_result.parameter.custom_attribute | string | | CustomAttribute |
action_result.parameter.custom_attribute_value | string | | True |
action_result.parameter.endpoint_id | string | `ise endpoint id` `ise resource id` | 44443c00-2222-1111-bbbb-00505687777f |
action_result.data.\*.UpdatedFieldsList.updatedField.\*.field | string | | customAttributes |
action_result.data.\*.UpdatedFieldsList.updatedField.\*.newValue | string | | {ITSecurityBlock=True} |
action_result.data.\*.UpdatedFieldsList.updatedField.\*.oldValue | string | | {ITSecurityBlock=False} |
action_result.summary | string | | |
action_result.message | string | | Endpoint Updated |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph_0 | ph | | |

## action: 'list sessions'

List the sessions currently available on the Monitoring node

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.acct_session_id | string | | |
action_result.data.\*.audit_session_id | string | `ise session id` | |
action_result.data.\*.calling_station_id | string | `mac address` | |
action_result.data.\*.framed_ip_address | string | `ip` | |
action_result.data.\*.framed_ipv6_address | string | | |
action_result.data.\*.is_quarantined | string | | |
action_result.data.\*.nas_ip_address | string | `nas server` | |
action_result.data.\*.server | string | `ise server` | |
action_result.data.\*.user_name | string | `user name` | |
action_result.summary | string | | |
action_result.summary.sessions_found | numeric | | 0 |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'terminate session'

Terminate sessions

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**macaddress** | required | MAC address of device to terminate sessions of | string | `mac address` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.macaddress | string | `mac address` | 11:11:11:11:11:11 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list resources'

Lists all the resources configured on the system of a particular resource

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource** | required | Resource type of the resources to fetch | string | |
**max_results** | optional | Total number of observables to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.max_results | numeric | | 2 |
action_result.parameter.resource | string | | Endpoints |
action_result.data.\*.description | string | | Default portal used by sponsors to create and manage accounts for authorized visitors to securely access the network |
action_result.data.\*.id | string | `ise resource id` | 44443c00-2222-1111-bbbb-00505687777f |
action_result.data.\*.link.href | string | `url` | https://10.11.11.11:9060/ers/config/portal/44443c00-2222-1111-bbbb-00505687777f |
action_result.data.\*.link.rel | string | | self |
action_result.data.\*.link.type | string | | application/xml |
action_result.data.\*.name | string | | Sponsor Portal (default) |
action_result.summary.resources_returned | numeric | | 5 |
action_result.message | string | | Resources returned: 5 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get resources'

Get the information about resource if resource_id is provided. Fetch the list of resources match with the key-value filter

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource** | required | Resource type of the resource to fetch | string | |
**resource_id** | optional | Resource ID | string | `ise resource id` |
**key** | optional | Key | string | |
**value** | optional | Value | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.key | string | | mac |
action_result.parameter.resource | string | | Endpoints |
action_result.parameter.resource_id | string | `ise resource id` | 44443c00-2222-1111-bbbb-00505687777f |
action_result.parameter.value | string | | 00:00:00:00:00:00 |
action_result.data.\*.description | string | | This endpoint for test |
action_result.data.\*.groupId | string | | 44443c00-2222-1111-bbbb-00505687777f |
action_result.data.\*.id | string | `ise resource id` | 44443c00-2222-1111-bbbb-00505687777f |
action_result.data.\*.identityStore | string | | |
action_result.data.\*.identityStoreId | string | | |
action_result.data.\*.link.href | string | `url` | https://10.11.11.11:9060/ers/config/endpoint/d335f970-10e0-11ea-8f06-ce112ec9f8fa |
action_result.data.\*.link.rel | string | | self |
action_result.data.\*.link.type | string | | application/xml |
action_result.data.\*.mac | string | | 00:00:00:00:00:00 |
action_result.data.\*.name | string | | 00:00:00:00:00:00 |
action_result.data.\*.portalUser | string | | |
action_result.data.\*.profileId | string | | d335f970-10e0-11ea-8f06-ce112ec9f8fa |
action_result.data.\*.staticGroupAssignment | boolean | | True False |
action_result.data.\*.staticProfileAssignment | boolean | | True False |
action_result.summary.resource_id | string | `ise resource id` | d335f970-10e0-11ea-8f06-ce112ec9f8fa |
action_result.summary.resources_returned | numeric | | 0 |
action_result.message | string | | Resource id: d335f970-10e0-11ea-8f06-ce112ec9f8fa |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete resource'

Delete a resource

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource** | required | Resource type of the resource to be deleted | string | |
**resource_id** | required | Resource ID | string | `ise resource id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource | string | | Endpoints |
action_result.parameter.resource_id | string | `ise resource id` | 44443c00-2222-1111-bbbb-00505687777f |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Resource deleted successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create resource'

Create a resource

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource** | required | Resource type of the resource to be created | string | |
**resource_json** | required | JSON which contains all values needed to create a resource | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.resource | string | | Endpoints |
action_result.parameter.resource_json | string | | { "ERSEndPoint": { "name": "name", "description": "MyEndpoint", "mac": "11:22:33:44:55:66" } } |
action_result.data | string | | |
action_result.summary | string | | Resource created successfully |
action_result.message | string | | Resource created successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update resource'

Update a resource

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**resource** | required | Resource type of the resource to be created | string | |
**resource_id** | required | ID of resource | string | `ise resource id` |
**key** | required | Key of resource which needs to be updated | string | |
**value** | required | New value of key | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.key | string | | mac |
action_result.parameter.resource | string | | Endpoints |
action_result.parameter.resource_id | string | `ise resource id` | 44443c00-2222-1111-bbbb-00505687777f |
action_result.parameter.value | string | | 11:11:11:11:11:11 |
action_result.data | string | | |
action_result.summary | string | | Resource created successfully |
action_result.message | string | | Resource updated successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'apply policy'

Apply policy on selected Ip address or MAC address

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_name** | required | Policy Name | string | |
**ip_mac_address** | required | MAC or IP Address of the device | string | `mac address` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_mac_address | string | `mac address` `ip` | 11:11:11:11:11:11 |
action_result.parameter.policy_name | string | | testPolicy |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Policy applied |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'clear policy'

Clear policy on selected Ip address or MAC address

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_name** | required | Policy Name | string | |
**ip_mac_address** | required | MAC or IP Address of the device | string | `mac address` `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip_mac_address | string | `mac address` `ip` | 11:11:11:11:11:11 |
action_result.parameter.policy_name | string | | testPolicy |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Policy cleared |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list policies'

Lists all the ANC policies available

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.actions | string | | |
action_result.data.\*.id | string | `ise policy id` | policy_name |
action_result.data.\*.link.href | string | | https://10.0.0.0:9060/ers/config/ancpolicy/policy_name |
action_result.data.\*.link.rel | string | | self |
action_result.data.\*.link.type | string | | application/json |
action_result.data.\*.name | string | | policy_name |
action_result.summary | string | | |
action_result.summary.policies_found | numeric | | |
action_result.message | string | | Policies found: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add policy'

Add a new ANC Policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Policy Name | string | |
**action_type** | required | Policy action type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.action_type | string | | QUARANTINE |
action_result.parameter.name | string | | policy_name |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Policy created |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete policy'

Delete a policy

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_name** | required | Policy Name | string | `ise policy id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.policy_name | string | `ise policy id` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Policy deleted |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list anc endpoints'

List the endpoints with anc configured on the system

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.SearchResult.resources.\*.id | string | `ise endpoint id` `ise resource id` | b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.SearchResult.resources.\*.link.href | string | `url` | https://10.11.11.11:9060/ers/config/endpoint/b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.SearchResult.resources.\*.link.rel | string | | self |
action_result.data.\*.SearchResult.resources.\*.link.type | string | | application/xml |
action_result.data.\*.SearchResult.total | numeric | | 1 |
action_result.summary.Endpoints found | string | | 9 1 |
action_result.summary.endpoints_found | numeric | | 1 |
action_result.message | string | | 9 Endpoints found 1 Endpoints found |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'anc device info'

Get information about a specific endpoint with assigned anc policy

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**endpoint_id** | required | ISE Endpoint ID for device | string | `ise endpoint id` `ise resource id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.endpoint_id | string | `ise endpoint id` `ise resource id` | 44443c00-2222-1111-bbbb-00505687777f b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.ErsAncEndpoint.id | string | `ise endpoint id` `ise resource id` | b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.ErsAncEndpoint.policyName | string | `anc policy name` | portbounce |
action_result.data.\*.ErsAncEndpoint.link.href | string | `url` | https://10.11.11.11:9060/ers/config/endpoint/b0007940-ffff-eeee-bbbb-000c29d5f0ff |
action_result.data.\*.ErsAncEndpoint.link.rel | string | | self |
action_result.data.\*.ErsAncEndpoint.link.type | string | | application/xml |
action_result.data.\*.ErsAncEndpoint.macAddress | string | | 8C:85:90:17:D6:39 |
action_result.summary | string | | |
action_result.message | string | | Endpoint found |
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
