# Automox

Publisher: Automox \
Connector Version: 1.0.0 \
Product Vendor: Automox \
Product Name: Automox \
Minimum Product Version: 6.3.1.178

Automox is the IT automation platform for modern organizations. Utilizing this app allows for the orchestration of IT operations such as device management, triggering remote
outcomes on endpoints, and basic Automox platform administration

## Steps to create API key

Please see our documentation on how to create an API key [here](https://help.automox.com/hc/en-us/articles/5385455262484-Managing-Keys#ManagingKeys-AddingAPIKeys).

### Configuration variables

This table lists the configuration variables required to operate Automox. These variables are specified when configuring a Automox asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**ax_console_api_key** | required | password | Organization API key |
**page_limit** | optional | numeric | Change how many results are returned on a page (default is 100) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[run policy](#action-run-policy) - Schedule a policy for immediate remediation \
[list policies](#action-list-policies) - List all the policies available in your organization \
[get policy](#action-get-policy) - Get the specified policy in your organization \
[list devices](#action-list-devices) - This action is used to retrieve Automox managed devices \
[list organizations](#action-list-organizations) - This action is used to retrieve Automox organizations \
[get device software](#action-get-device-software) - This action is used to retrieve a list of software installed on a device \
[list software](#action-list-software) - This action is used to retrieve a list of software installed on a device \
[get device](#action-get-device) - Retrieve data for a specific device in the AX Console \
[get device by hostname](#action-get-device-by-hostname) - This action is used to find an Automox device by Hostname \
[get organization user](#action-get-organization-user) - This action is used to retrieve a single user from an Automox organization \
[list organization users](#action-list-organization-users) - This action is used to retrieve users of the Automox organization \
[get device by ip address](#action-get-device-by-ip-address) - This action is used to find an Automox device by IP address \
[list groups](#action-list-groups) - This action is used to list Automox groups \
[get command queues](#action-get-command-queues) - Use this action to return a list of queued up commands for a device \
[remove user from account](#action-remove-user-from-account) - Use this action to remove a user from an account \
[update device](#action-update-device) - Use this action to update a device in the console \
[delete device](#action-delete-device) - Use this action to delete a device from the console

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

Validate the asset configuration for connectivity using supplied configuration. This action calls the /users/self endpoint to validate the API key and the connection to the Automox API.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'run policy'

Schedule a policy for immediate remediation

Type: **generic** \
Read only: **False**

Use this action to run a policy/worklet immediately on a specific device. For example, you can craft an incident response worklet in your console and use this action to call it.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_id** | optional | Organization ID | numeric | `org id` |
**device_id** | required | Device ID | numeric | `device id` |
**policy_id** | required | Policy ID | numeric | `policy id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.parameter.aux_params.device_id | numeric | `device id` | 123456 |
action_result.parameter.path_params.policy_id | numeric | `policy id` | 123456 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list policies'

List all the policies available in your organization

Type: **generic** \
Read only: **False**

List all the policies available in your organization. For example, you can use this action to get policy data (like a Policy ID) that you can use or pass to other actions.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.data.\*.\*.id | numeric | `policy id` | 123456 |
action_result.data.\*.\*.uuid | string | | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.data.\*.\*.name | string | | Apply All Patches |
action_result.data.\*.\*.organization_id | numeric | | 123456 |
action_result.data.\*.\*.create_time | string | | 2023-10-10T15:19:53+0000 |
action_result.data.\*.\*.status | string | | active inactive |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get policy'

Get the specified policy in your organization

Type: **generic** \
Read only: **False**

Get the specified policy in your organization.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_id** | optional | Organization ID | numeric | `org id` |
**policy_id** | required | Policy ID | numeric | `policy id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.parameter.path_params.policy_id | numeric | `policy id` | 123456 |
action_result.data.\*.id | numeric | `policy id` | 123456 |
action_result.data.\*.uuid | string | | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.data.\*.name | string | | Apply All Patches |
action_result.data.\*.organization_id | numeric | | 123456 |
action_result.data.\*.create_time | string | | 2023-10-10T15:19:53+0000 |
action_result.data.\*.status | string | | active inactive |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list devices'

This action is used to retrieve Automox managed devices

Type: **generic** \
Read only: **False**

This action is used to retrieve Automox managed devices. For example, you can use this action to get device data that you can use or pass to other actions.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.query_params.o | string | `org id` | 123456 |
action_result.data.\*.\*.id | numeric | `device id` | 123456 |
action_result.data.\*.\*.uuid | string | | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.data.\*.\*.name | string | `host name` | SERVER01 |
action_result.data.\*.\*.custom_name | string | `custom name` | My Server |
action_result.data.\*.\*.agent_version | string | | 1.45.48 |
action_result.data.\*.\*.connected | string | | True False |
action_result.data.\*.\*.ip_addrs | string | `ip` | 192.168.1.1 192.168.1.1,192.168.1.2 |
action_result.data.\*.\*.ip_addrs_private | string | `ip` | 192.168.1.1 192.168.1.1,192.168.1.2 |
action_result.data.\*.\*.last_logged_in_user | string | | MYSERVER\\admin |
action_result.data.\*.\*.server_group_id | numeric | `server group id` | 123456 |
action_result.data.\*.\*.organization_id | numeric | | 123456 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list organizations'

This action is used to retrieve Automox organizations

Type: **generic** \
Read only: **False**

This action is used to retrieve Automox organizations that the authenticated user belongs to.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.\*.id | numeric | | 123456 |
action_result.data.\*.\*.name | string | | Hank's Propane Accessories |
action_result.data.\*.\*.uuid | string | | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.data.\*.\*.parent_id | numeric | | 123456 |
action_result.data.\*.\*.create_time | string | | 2023-10-10T15:19:53+0000 |
action_result.data.\*.\*.device_count | numeric | | 2 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get device software'

This action is used to retrieve a list of software installed on a device

Type: **generic** \
Read only: **False**

This action is used to retrieve a list of software installed on a device.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**device_id** | required | Device ID | numeric | `device id` |
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.aux_params.device_id | numeric | `device id` | 123456 |
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.data.\*.\*.create_time | string | | 2023-10-10T15:19:53+0000 |
action_result.data.\*.\*.name | string | | KB4052623 NotepadPlusPlus_64 a32ca1d0-ddd4-486b-b708-d941db4fb4aa {ACA17529-C1C0-41AE-8D8A-BAD5FD55FDE1} |
action_result.data.\*.\*.display_name | string | | Update for Windows Defender Antivirus antimalware platform - KB4052623 NotepadPlusPlus Parallels Tools 2024-11 Update for Windows 11 Version 24H2 for ARM64-based Systems (KB5048779) |
action_result.data.\*.\*.id | numeric | | 123456789 |
action_result.data.\*.\*.installed | string | | True False |
action_result.data.\*.\*.organization_id | numeric | | 123456 |
action_result.data.\*.\*.os_name | string | | 11 Pro OS X |
action_result.data.\*.\*.os_version | string | | 10.0.26100 12.2 |
action_result.data.\*.\*.package_id | numeric | | 12345678 |
action_result.data.\*.\*.package_version_id | numeric | | 123456789 |
action_result.data.\*.\*.repo | string | | WindowsUpdate ReportingOnly Microsoft Installed |
action_result.data.\*.\*.server_id | numeric | `device id` | 123456 |
action_result.data.\*.\*.software_id | numeric | | 123456 |
action_result.data.\*.\*.version | string | | 1.0.0 4.18.2001.10 200 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list software'

This action is used to retrieve a list of software installed on a device

Type: **generic** \
Read only: **False**

This action is used to retrieve a list of software installed on a device.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.data.\*.\*.create_time | string | | 2023-10-10T15:19:53+0000 |
action_result.data.\*.\*.name | string | | KB4052623 NotepadPlusPlus_64 a32ca1d0-ddd4-486b-b708-d941db4fb4aa {ACA17529-C1C0-41AE-8D8A-BAD5FD55FDE1} |
action_result.data.\*.\*.display_name | string | | Update for Windows Defender Antivirus antimalware platform - KB4052623 NotepadPlusPlus Parallels Tools 2024-11 Update for Windows 11 Version 24H2 for ARM64-based Systems (KB5048779) |
action_result.data.\*.\*.id | numeric | | 123456789 |
action_result.data.\*.\*.installed | string | | True False |
action_result.data.\*.\*.organization_id | numeric | | 123456 |
action_result.data.\*.\*.os_name | string | | 11 Pro OS X |
action_result.data.\*.\*.os_version | string | | 10.0.26100 12.2 |
action_result.data.\*.\*.package_id | numeric | | 12345678 |
action_result.data.\*.\*.package_version_id | numeric | | 123456789 |
action_result.data.\*.\*.repo | string | | WindowsUpdate ReportingOnly Microsoft Installed |
action_result.data.\*.\*.server_id | numeric | `device id` | 123456 |
action_result.data.\*.\*.software_id | numeric | | 123456 |
action_result.data.\*.\*.version | string | | 1.0.0 4.18.2001.10 200 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get device'

Retrieve data for a specific device in the AX Console

Type: **generic** \
Read only: **False**

Retrieve data for a specific device in the AX Console.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**device_id** | required | Device ID | numeric | `device id` |
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.aux_params.device_id | numeric | `device id` | 123456 |
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.data.\*.id | numeric | `device id` | 123456 |
action_result.data.\*.uuid | string | | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.data.\*.name | string | `host name` | SERVER01 |
action_result.data.\*.custom_name | string | `custom name` | My Server |
action_result.data.\*.agent_version | string | | 1.45.48 |
action_result.data.\*.connected | string | | True False |
action_result.data.\*.ip_addrs | string | `ip` | 192.168.1.1 192.168.1.1,192.168.1.2 |
action_result.data.\*.ip_addrs_private | string | `ip` | 192.168.1.1 192.168.1.1,192.168.1.2 |
action_result.data.\*.last_logged_in_user | string | | MYSERVER\\admin |
action_result.data.\*.server_group_id | numeric | `server group id` | 123456 |
action_result.data.\*.organization_id | numeric | | 123456 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get device by hostname'

This action is used to find an Automox device by Hostname

Type: **generic** \
Read only: **False**

This action is used to find an Automox device by Hostname. It will return multiple matches.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostname** | required | Hostname of device | string | `host name` |
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.aux_params.hostname | string | `host name` | SERVER01 |
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.data.\*.id | numeric | `device id` | 123456 |
action_result.data.\*.uuid | string | | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.data.\*.name | string | `host name` | SERVER01 |
action_result.data.\*.custom_name | string | `custom name` | My Server |
action_result.data.\*.agent_version | string | | 1.45.48 |
action_result.data.\*.connected | string | | True False |
action_result.data.\*.ip_addrs | string | `ip` | 192.168.1.1 192.168.1.1,192.168.1.2 |
action_result.data.\*.ip_addrs_private | string | `ip` | 192.168.1.1 192.168.1.1,192.168.1.2 |
action_result.data.\*.last_logged_in_user | string | | MYSERVER\\admin |
action_result.data.\*.server_group_id | numeric | `server group id` | 123456 |
action_result.data.\*.organization_id | numeric | | 123456 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get organization user'

This action is used to retrieve a single user from an Automox organization

Type: **generic** \
Read only: **False**

This action is used to retrieve a single user from an Automox organization.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_id** | optional | Organization ID | numeric | `org id` |
**user_id** | required | User ID | numeric | `user id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.parameter.path_params.user_id | numeric | `user id` | 123456 |
action_result.data.\*.id | numeric | `user id` | 123456 |
action_result.data.\*.uuid | string | `user uuid` | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.data.\*.name | string | | Jamie Doe |
action_result.data.\*.email | string | `email` | someone@example.com |
action_result.data.\*.orgs_formatted | string | | Hank's Propane Accessories (123456) example (123456), example2 (789012) |
action_result.data.\*.saml_enabled | string | | True False |
action_result.data.\*.sso_enabled | string | | True False |
action_result.data.\*.rbac_roles_formatted | string | | Zone Administrator (123456) Billing Administrator (122233), Zone Administrator (145555), |
action_result.data.\*.tags | string | `tags` | tag1, tag2 tag1 |
action_result.data.\*.account_id | string | `account uuid` | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list organization users'

This action is used to retrieve users of the Automox organization

Type: **generic** \
Read only: **False**

This action is used to retrieve users of the Automox organization.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.data.\*.id | numeric | `user id` | 123456 |
action_result.data.\*.uuid | string | `user uuid` | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.data.\*.name | string | | Jamie Doe |
action_result.data.\*.email | string | `email` | person@somewhere.com |
action_result.data.\*.orgs_formatted | string | | Hank's Propane Accessories (123456) example (123456), example2 (789012) |
action_result.data.\*.saml_enabled | string | | True False |
action_result.data.\*.sso_enabled | string | | True False |
action_result.data.\*.rbac_roles_formatted | string | | Zone Administrator (123456) Billing Administrator (122233), Zone Administrator (145555), |
action_result.data.\*.tags | string | `tags` | tag1, tag2 tag1 |
action_result.data.\*.account_id | string | `account uuid` | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get device by ip address'

This action is used to find an Automox device by IP address

Type: **generic** \
Read only: **False**

This action is used to find an Automox device by IP address. You can provide a private or public IP address. It will return multiple matches.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_address** | required | IP address of device | string | `ip` |
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.aux_params.ip_address | string | `ip` | 192.168.1.1 |
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.data.\*.id | numeric | `device id` | 123456 |
action_result.data.\*.uuid | string | | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.data.\*.name | string | `host name` | SERVER01 |
action_result.data.\*.custom_name | string | `custom name` | My Server |
action_result.data.\*.agent_version | string | | 1.45.48 |
action_result.data.\*.connected | string | | True False |
action_result.data.\*.ip_addrs | string | `ip` | 192.168.1.1 192.168.1.1,192.168.1.2 |
action_result.data.\*.ip_addrs_private | string | `ip` | 192.168.1.1 192.168.1.1,192.168.1.2 |
action_result.data.\*.last_logged_in_user | string | | MYSERVER\\admin |
action_result.data.\*.server_group_id | numeric | `server group id` | 123456 |
action_result.data.\*.organization_id | numeric | | 123456 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list groups'

This action is used to list Automox groups

Type: **generic** \
Read only: **False**

This action is used to list Automox groups.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.data.\*.\*.id | string | | 123456 |
action_result.data.\*.\*.name | string | | My Group |
action_result.data.\*.\*.organization_id | numeric | | 123456 |
action_result.data.\*.\*.parent_server_group_id | numeric | `server group id` | 123456 |
action_result.data.\*.\*.server_count | numeric | | 3 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get command queues'

Use this action to return a list of queued up commands for a device

Type: **generic** \
Read only: **False**

Use this action to return a list of queued up commands for a device.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**device_id** | required | Device ID | numeric | `device id` |
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.aux_params.device_id | numeric | `device id` | 123456 |
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.data.\*.\*.id | numeric | | 123456789 |
action_result.data.\*.\*.server_id | numeric | `device id` | 123456 |
action_result.data.\*.\*.command_id | numeric | | 123456 null |
action_result.data.\*.\*.organization_id | numeric | | 123456 |
action_result.data.\*.\*.args | string | | arg1 arg1, arg2 |
action_result.data.\*.\*.exec_time | string | | 2025-02-03T19:32:22+0000 |
action_result.data.\*.\*.response | string | | |
action_result.data.\*.\*.policy_id | numeric | `policy id` | 123456 |
action_result.data.\*.\*.command_type_name | string | | InstallUpdate |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'remove user from account'

Use this action to remove a user from an account

Type: **contain** \
Read only: **False**

Use this action to remove a user from an account.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account_uuid** | required | Account UUID to retrieve users for | string | `account uuid` |
**user_uuid** | required | UUID of user to delete | string | `user uuid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.path_params.account_uuid | string | `account uuid` | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.parameter.path_params.user_uuid | string | `user uuid` | 8cbea739-abaf-49b3-9400-ad75390d7845 |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'update device'

Use this action to update a device in the console

Type: **contain** \
Read only: **False**

Use this action to update a device in the console.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**device_id** | required | Device ID | numeric | `device id` |
**org_id** | optional | Organization ID | numeric | `org id` |
**exception** | optional | Exclude the device from reports and statistics | boolean | |
**server_group_id** | required | Server group ID to assign device to | numeric | `server group id` |
**tags** | optional | List of tags, comma separated | string | `tags` |
**custom_name** | optional | Custom name to set on device | string | `custom name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.aux_params.device_id | numeric | `device id` | 123456 |
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.parameter.aux_params.exception | boolean | | true false |
action_result.parameter.aux_params.server_group_id | numeric | `server group id` | 123456 |
action_result.parameter.aux_params.tags | string | `tags` | tag1, tag2 tag1 |
action_result.parameter.aux_params.custom_name | string | `custom name` | My Server |
action_result.status | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'delete device'

Use this action to delete a device from the console

Type: **contain** \
Read only: **False**

Use this action to delete a device from the console.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**device_id** | required | Device ID | numeric | `device id` |
**org_id** | optional | Organization ID | numeric | `org id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.aux_params.device_id | numeric | `device id` | 123456 |
action_result.parameter.query_params.o | numeric | `org id` | 123456 |
action_result.status | string | | |
action_result.message | string | | |
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
