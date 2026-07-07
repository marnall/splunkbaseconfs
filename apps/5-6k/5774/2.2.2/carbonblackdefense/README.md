# Carbon Black Defense

Publisher: Splunk <br>
Connector Version: 2.2.2 <br>
Product Vendor: Carbon Black <br>
Product Name: Defense <br>
Minimum Product Version: 5.2.0

This app integrates with an instance of Carbon Black defense to run investigative and generic actions

There are four different sets of credentials for this app - a SIEM key, a Custom API Key, an
Organization Key, and an API key. The action **get notifications** uses the SIEM key. This means the
**siem_connector_id** and the **siem_key** asset configuration parameters are required to run the
**get notifications** action. The actions **list processes** , **get event** , **list events** ,
**list devices** , **update device** , and **get alert** requires Custom API Key along with
Organization Key meaning the **custom_api_connecter_id** , **custom_api_key** , and **org_key** are
required to run these actions. All other actions use the API key, meaning that the
**api_connector_id** and **api_key** asset configuration parameters are required for those
actions.

**NOTE:** Test connectivity will only check the API credentials, it will NOT check the SIEM Key
credentials, Organization Key, and Custom Key credentials.

**To Generate Keys**\
To get started with the Carbon black Defense API to integrate with Phantom, log into the Carbon
black Defense web portal and go to Settings then API Access. From here you can retrieve ORG KEY, API
ID which is used as API Connector ID in Phantom app asset, and API Secret Key which is used as API
Key in Phantom app asset. To Generate SIEM Connector ID and SIEM Key select SIEM in the **Access
Level type** . To Generate API Connector ID and API Key select Live Response in the **Access Level
type** . To Generate Custom API Connector ID and Custom API Key select Custom in the **Access Level
type** and accordingly select **Custom Access Level** which has appropriate permissions.

**Custom Access Levels required the following permissions**

- For 'org.search.events' allow permission to 'CREATE' and 'READ'.
- For 'device' allow permissions for 'READ'.
- For 'device.policy' allow permissions for 'UPDATE'.
- For 'device.bg-scan' allow permissions for 'EXECUTE'.
- For 'device.bypass' allow permissions for 'EXECUTE'.
- For 'device.quarantine' allow permissions for 'EXECUTE'.
- For 'org.kits' allow permissions for 'EXECUTE'.
- For 'device.uninstall' allow permissions for 'EXECUTE'.
- For 'device.deregistered' allow permissions for 'DELETE'.
- For 'org.alerts' allow permissions for 'READ'.
- For 'org.alerts.dismiss' allow permissions for 'EXECUTE'.
- For 'org.alerts.notes' allow permissions for 'CREATE', 'READ', and 'DELETE'.
- For 'org.search.events', allow permission for 'CREATE' and 'READ'.

## Port Information

The app uses HTTP/HTTPS protocol for communicating with the Carbon Black Defense Server. Below are
the default ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration variables

This table lists the configuration variables required to operate Carbon Black Defense. These variables are specified when configuring a Defense asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_url** | required | string | API URL (e.g. https://defense.conferdeploy.net) |
**api_connector_id** | optional | password | API Connector ID |
**api_key** | optional | password | API Key |
**siem_connector_id** | optional | password | SIEM Connector ID |
**siem_key** | optional | password | SIEM Key |
**custom_api_connector_id** | optional | password | Custom API Connector ID |
**custom_api_key** | optional | password | Custom API Key |
**org_key** | optional | password | Organization Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the supplied API Key <br>
[list devices](#action-list-devices) - List devices connected to CB Defense <br>
[update device](#action-update-device) - Change the policy of a device connected to CB Defense <br>
[list policies](#action-list-policies) - List policies that exist on CB Defense <br>
[add policy](#action-add-policy) - Create a new policy on CB Defense <br>
[delete policy](#action-delete-policy) - Delete a policy on CB Defense <br>
[add rule](#action-add-rule) - Add a rule to a policy on CB Defense <br>
[delete rule](#action-delete-rule) - Delete a rule from a policy on CB Defense <br>
[list processes](#action-list-processes) - List processes that match supplied filter criteria <br>
[list events](#action-list-events) - List events that match supplied filter criteria <br>
[get event](#action-get-event) - Get information about an event <br>
[get alert](#action-get-alert) - Get information about an alert <br>
[get notifications](#action-get-notifications) - Get notifications from CB Defense <br>
[update policy](#action-update-policy) - Updates an existing policy on the Carbon Black Defense server <br>
[get policy](#action-get-policy) - Retrieves an existing policy from the Carbon Black Defense server

## action: 'test connectivity'

Validate the supplied API Key

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list devices'

List devices connected to CB Defense

Type: **investigate** <br>
Read only: **True**

The results of this action can be paged using the <b>start</b> and the <b>limit</b> parameters. For example, to return the first 10 results, set the <b>start</b> to 1 and the <b>limit</b> to 10. To return the next 10 results, set the <b>start</b> to 11 and keep the <b>limit</b> at 10. This Action requires Custom API Key, Custom API Connector ID, and Organization Key.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start** | optional | Number of first result to return | numeric | |
**limit** | optional | Maximum number of results to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 2 10 |
action_result.parameter.start | numeric | | 1 0 |
action_result.data.\*.name | string | | SERVER-18 |
action_result.data.\*.email | string | | test@example.com |
action_result.data.\*.status | string | | REGISTERED |
action_result.data.\*.base_device | string | | |
action_result.data.\*.nsx_enabled | string | | |
action_result.data.\*.quarantined | boolean | | False True |
action_result.data.\*.cloud_provider_tags | string | | |
action_result.data.\*.auto_scaling_group_name | string | | |
action_result.data.\*.virtual_private_cloud_id | string | | |
action_result.data.\*.cloud_provider_account_id | string | | |
action_result.data.\*.cloud_provider_resource_id | string | | |
action_result.data.\*.nsx_distributed_firewall_policy | string | | |
action_result.data.\*.activation_code | string | | 8YIBKS |
action_result.data.\*.activation_code_expiry_time | string | | 2021-08-19T07:53:22.248Z |
action_result.data.\*.ad_group_id | numeric | | 0 |
action_result.data.\*.appliance_name | string | | |
action_result.data.\*.appliance_uuid | string | | |
action_result.data.\*.av_ave_version | string | | 8.3.64.2 |
action_result.data.\*.av_engine | string | | 4.14.4.487-ave.8.3.64.2:avpack.8.5.2.16:vdf.8.18.39.78:vdfdate.20210817 |
action_result.data.\*.av_last_scan_time | string | | |
action_result.data.\*.av_master | boolean | | True False |
action_result.data.\*.av_pack_version | string | | 8.5.2.16 |
action_result.data.\*.av_product_version | string | | 4.14.4.487 |
action_result.data.\*.av_status | string | | ONDEMAND_SCAN_DISABLED |
action_result.data.\*.av_update_servers | string | | |
action_result.data.\*.av_vdf_version | string | | 8.18.39.78 |
action_result.data.\*.cluster_name | string | | |
action_result.data.\*.current_sensor_policy_name | string | | default |
action_result.data.\*.datacenter_name | string | | |
action_result.data.\*.deployment_type | string | | WORKLOAD |
action_result.data.\*.deregistered_time | string | | |
action_result.data.\*.device_meta_data_item_list.\*.key_name | string | | OS_MAJOR_VERSION |
action_result.data.\*.device_meta_data_item_list.\*.key_value | string | | Windows |
action_result.data.\*.device_meta_data_item_list.\*.position | numeric | | 0 |
action_result.data.\*.device_owner_id | numeric | | 706666 |
action_result.data.\*.encoded_activation_code | string | | HVNXRFWQA!L |
action_result.data.\*.esx_host_name | string | | |
action_result.data.\*.esx_host_uuid | string | | |
action_result.data.\*.first_name | string | | Ant |
action_result.data.\*.golden_device | string | | |
action_result.data.\*.golden_device_id | string | | |
action_result.data.\*.id | numeric | `cb defense device id` | 4486274 |
action_result.data.\*.last_contact_time | string | | 2021-08-17T07:29:58.365Z |
action_result.data.\*.last_device_policy_changed_time | string | | |
action_result.data.\*.last_device_policy_requested_time | string | | 2021-08-12T11:37:19.009Z |
action_result.data.\*.last_external_ip_address | string | `ip` `ipv6` | 146.247.47.49 |
action_result.data.\*.last_internal_ip_address | string | `ip` `ipv6` | 192.168.110.10 |
action_result.data.\*.last_location | string | | OFFSITE |
action_result.data.\*.last_name | string | | Ducker |
action_result.data.\*.last_policy_updated_time | string | | 2021-08-12T10:29:55.890Z |
action_result.data.\*.last_reported_time | string | | 2021-08-17T03:57:32.748Z |
action_result.data.\*.last_reset_time | string | | |
action_result.data.\*.last_shutdown_time | string | | |
action_result.data.\*.linux_kernel_version | string | | |
action_result.data.\*.login_user_name | string | | CORP\\Administrator |
action_result.data.\*.mac_address | string | | 00505601c507 |
action_result.data.\*.middle_name | string | | |
action_result.data.\*.organization_id | numeric | | 1105 |
action_result.data.\*.organization_name | string | | cb-internal-alliances.com |
action_result.data.\*.os | string | | WINDOWS |
action_result.data.\*.os_version | string | | Server 2012 R2 x64 |
action_result.data.\*.passive_mode | boolean | | True False |
action_result.data.\*.policy_id | numeric | `cb defense policy id` | 6525 |
action_result.data.\*.policy_name | string | | default |
action_result.data.\*.policy_override | boolean | | True False |
action_result.data.\*.registered_time | string | | 2021-08-12T07:56:56.442Z |
action_result.data.\*.scan_last_action_time | string | | |
action_result.data.\*.scan_last_complete_time | string | | |
action_result.data.\*.scan_status | string | | |
action_result.data.\*.sensor_kit_type | string | | WINDOWS |
action_result.data.\*.sensor_out_of_date | boolean | | True False |
action_result.data.\*.sensor_pending_update | boolean | | True False |
action_result.data.\*.sensor_states | string | | ACTIVE |
action_result.data.\*.sensor_version | string | | 3.7.0.1253 |
action_result.data.\*.target_priority | string | | MEDIUM |
action_result.data.\*.uninstall_code | string | | 46C4CAHC |
action_result.data.\*.vcenter_host_url | string | | |
action_result.data.\*.vcenter_name | string | | |
action_result.data.\*.vcenter_uuid | string | | |
action_result.data.\*.vdi_base_device | string | | |
action_result.data.\*.virtual_machine | boolean | | True False |
action_result.data.\*.virtualization_provider | string | | VMW_ESX |
action_result.data.\*.vm_ip | string | | |
action_result.data.\*.vm_name | string | | |
action_result.data.\*.vm_uuid | string | | |
action_result.data.\*.vulnerability_score | numeric | | 0 |
action_result.data.\*.vulnerability_severity | string | | |
action_result.data.\*.windows_platform | string | | |
action_result.summary.num_devices | numeric | | 2 10 |
action_result.message | string | | Num devices: 2 Num devices: 10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update device'

Change the policy of a device connected to CB Defense

Type: **generic** <br>
Read only: **False**

This Action requires Custom API Key, Custom API Connector ID, and Organization Key.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**device_id** | required | ID of device to update | string | `cb defense device id` |
**policy_id** | required | ID of policy to assign to device | string | `cb defense policy id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.device_id | string | `cb defense device id` | 342556 |
action_result.parameter.policy_id | string | `cb defense policy id` | 2343 |
action_result.data.\*.message | string | | |
action_result.summary.device_id | string | `cb defense device id` | 123445234 |
action_result.message | string | | Successfully updated device's policy |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list policies'

List policies that exist on CB Defense

Type: **investigate** <br>
Read only: **True**

This Action requires API Key and API Connector ID.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.orgId | numeric | | 1105 |
action_result.data.\*.vdiAutoDeregInactiveIntervalMs | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.id | numeric | `cb defense policy id` | 6525 |
action_result.data.\*.latestRevision | numeric | | 1488926710902 1628764195890 |
action_result.data.\*.name | string | | default |
action_result.data.\*.policy.avSettings.apc.enabled | boolean | | True False |
action_result.data.\*.policy.avSettings.apc.maxExeDelay | numeric | | 45 |
action_result.data.\*.policy.avSettings.apc.maxFileSize | numeric | | 4 |
action_result.data.\*.policy.avSettings.apc.riskLevel | numeric | | 4 |
action_result.data.\*.policy.avSettings.features.\*.enabled | boolean | | True False |
action_result.data.\*.policy.avSettings.features.\*.name | string | | SIGNATURE_UPDATE |
action_result.data.\*.policy.avSettings.onAccessScan.profile | string | | NORMAL AGGRESSIVE |
action_result.data.\*.policy.avSettings.onDemandScan.profile | string | | NORMAL |
action_result.data.\*.policy.avSettings.onDemandScan.scanCdDvd | string | | AUTOSCAN |
action_result.data.\*.policy.avSettings.onDemandScan.scanUsb | string | | AUTOSCAN |
action_result.data.\*.policy.avSettings.onDemandScan.schedule.days | string | | |
action_result.data.\*.policy.avSettings.onDemandScan.schedule.rangeHours | numeric | | 0 |
action_result.data.\*.policy.avSettings.onDemandScan.schedule.recoveryScanIfMissed | boolean | | True False |
action_result.data.\*.policy.avSettings.onDemandScan.schedule.startHour | numeric | | 0 |
action_result.data.\*.policy.avSettings.signatureUpdate.schedule.fullIntervalHours | numeric | | 0 |
action_result.data.\*.policy.avSettings.signatureUpdate.schedule.initialRandomDelayHours | numeric | | 4 |
action_result.data.\*.policy.avSettings.signatureUpdate.schedule.intervalHours | numeric | | 4 |
action_result.data.\*.policy.avSettings.updateServers.servers.\*.flags | numeric | | 0 |
action_result.data.\*.policy.avSettings.updateServers.servers.\*.regId | string | | |
action_result.data.\*.policy.avSettings.updateServers.servers.\*.server | string | `url` | http://defense.phantom.local http://updates.cdc.carbonblack.io/update |
action_result.data.\*.policy.avSettings.updateServers.serversForOffSiteDevices | string | `url` | http://defense.phantom.local http://updates.cdc.carbonblack.io/update |
action_result.data.\*.policy.directoryActionRules | string | | |
action_result.data.\*.policy.directoryActionRules.\*.actions.FILE_UPLOAD | boolean | | True False |
action_result.data.\*.policy.directoryActionRules.\*.actions.PROTECTION | boolean | | True False |
action_result.data.\*.policy.directoryActionRules.\*.path | string | `file path` | |
action_result.data.\*.policy.id | numeric | | -1 |
action_result.data.\*.policy.knownBadHashAutoDeleteDelayMs | string | | |
action_result.data.\*.policy.rules | string | | |
action_result.data.\*.policy.rules.\*.action | string | | DENY TERMINATE |
action_result.data.\*.policy.rules.\*.application.type | string | | REPUTATION |
action_result.data.\*.policy.rules.\*.application.value | string | `file path` `file name` | COMPANY_BLACK_LIST KNOWN_MALWARE |
action_result.data.\*.policy.rules.\*.id | numeric | | 1 402 |
action_result.data.\*.policy.rules.\*.operation | string | | RUN |
action_result.data.\*.policy.rules.\*.required | boolean | | True False |
action_result.data.\*.policy.sensorSettings.\*.name | string | | ALLOW_UNINSTALL |
action_result.data.\*.policy.sensorSettings.\*.value | string | | true |
action_result.data.\*.priorityLevel | string | | MEDIUM |
action_result.data.\*.systemPolicy | boolean | | True False |
action_result.data.\*.version | numeric | | 2 |
action_result.summary.num_policies | numeric | | 33 93 |
action_result.message | string | | Num policies: 33 Num policies: 93 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add policy'

Create a new policy on CB Defense

Type: **generic** <br>
Read only: **False**

The <b>json_fields</b> parameter can be used to configure other fields in the created policy. This parameter takes a JSON dictionary with the format of the policy field seen <a href="https://developer.carbonblack.com/reference/cb-defense/1/rest-api/#create-new-policy">here</a>. In some negative scenarios action will fail with an API error message "Error creating policy - Error modifying policy" but policy will be created on the server with the given name. This Action requires API Key and API Connector ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name | string | |
**description** | required | Description | string | |
**priority** | required | Priority Level | string | |
**json_fields** | optional | Other configuration fields in JSON format. Defaults to '{"sensorSettings": []}' if left empty | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.description | string | | This is going to be deleted very soon |
action_result.parameter.json_fields | string | | {"sensorSettings":[{"name":"ALLOW_UNINSTALL","value":"true"}]} |
action_result.parameter.name | string | | Phantom policy 3 |
action_result.parameter.priority | string | | MEDIUM |
action_result.data.\*.message | string | | Success |
action_result.data.\*.policyId | numeric | `cb defense policy id` | 13145 |
action_result.data.\*.success | boolean | | True False |
action_result.summary.policy_id | numeric | `cb defense policy id` | 13145 |
action_result.message | string | | Policy id: 74507 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete policy'

Delete a policy on CB Defense

Type: **generic** <br>
Read only: **False**

This Action requires API Key and API Connector ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID | string | `cb defense policy id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `cb defense policy id` | 13145 |
action_result.data.\*.message | string | | Success |
action_result.data.\*.success | boolean | | True False |
action_result.summary.policy_id | string | `cb defense policy id` | 13145 |
action_result.message | string | | Policy successfully deleted |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add rule'

Add a rule to a policy on CB Defense

Type: **generic** <br>
Read only: **False**

This Action requires API Key and API Connector ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | ID | string | `cb defense policy id` |
**rules** | required | JSON dictionary containing rules configuration | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `cb defense policy id` | 12864 |
action_result.parameter.rules | string | | {"action":"TERMINATE","application":{"type":"REPUTATION","value":"COMPANY_BLACK_LIST"},"operation":"RANSOM","required":true,"id":1} |
action_result.data.\*.message | string | | Success |
action_result.data.\*.ruleId | numeric | | 1 |
action_result.data.\*.success | boolean | | True False |
action_result.summary.rule_id | numeric | | 1 |
action_result.message | string | | Rule id: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete rule'

Delete a rule from a policy on CB Defense

Type: **generic** <br>
Read only: **False**

This Action requires API Key and API Connector ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | Policy ID | string | `cb defense policy id` |
**rule_id** | required | Rule ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.policy_id | string | `cb defense policy id` | 12864 |
action_result.parameter.rule_id | string | | 145634 |
action_result.data.\*.message | string | | Success |
action_result.data.\*.success | boolean | | True False |
action_result.summary.rule_id | string | | 13145 |
action_result.message | string | | Rule successfully deleted |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list processes'

List processes that match supplied filter criteria

Type: **investigate** <br>
Read only: **True**

The examples for the <b>search_span</b> parameter are <b>1d</b>, <b>1w</b>, <b>2y</b>, <b>2h</b>, <b>1m</b>, or <b>50s</b> (where y=year, w=week, d=day, h=hour, m=minute, s=second). The results of this action can be paged using the <b>start</b> and <b>limit</b> parameters. For example, to return the first 10 results, set the <b>start</b> to 1 and the <b>limit</b> to 10. To return the next 10 results, set the <b>start</b> to 11 and keep the <b>limit</b> at 10. This Action requires Custom API Key, Custom API Connector ID, and Organization Key.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | optional | IP | string | `ip` `ipv6` |
**host_name** | optional | Host Name | string | `host name` |
**owner** | optional | Owner | string | |
**search_span** | optional | Number of days back to search | string | |
**start** | optional | Number of first result to return | numeric | |
**limit** | optional | Maximum number of results to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.host_name | string | `host name` | win7-endpoint |
action_result.parameter.ip | string | `ip` `ipv6` | 10.10.10.10 64.235.99.234 |
action_result.parameter.limit | numeric | | 3 50 |
action_result.parameter.owner | string | | win7-endpoint\\root |
action_result.parameter.search_span | string | | 1w |
action_result.parameter.start | numeric | | 1 |
action_result.data.\*.legacy | boolean | | True False |
action_result.data.\*.enriched | boolean | | True False |
action_result.data.\*.blocked_name | string | | c:\\program files\\process hacker 2\\processhacker.exe |
action_result.data.\*.blocked_effective_reputation | string | | KNOWN_MALWARE |
action_result.data.\*.alert_category | string | | THREAT |
action_result.data.\*.alert_id | string | `cb defense alert id` | 469db8ea-f9e5-49d3-88f5-ac596da1fb24 |
action_result.data.\*.backend_timestamp | string | | 2021-08-17T06:45:33.031Z |
action_result.data.\*.childproc_count | numeric | | 0 |
action_result.data.\*.crossproc_count | numeric | | 3 |
action_result.data.\*.device_group_id | numeric | | 0 |
action_result.data.\*.device_id | numeric | `cb defense device id` | 4242869 |
action_result.data.\*.device_name | string | | bas-carbonblack |
action_result.data.\*.device_policy_id | numeric | | 6525 |
action_result.data.\*.device_timestamp | string | | 2021-08-17T06:44:13.537Z |
action_result.data.\*.filemod_count | numeric | | 0 |
action_result.data.\*.ingress_time | numeric | | 1629182722628 |
action_result.data.\*.modload_count | numeric | | 4 |
action_result.data.\*.netconn_count | numeric | | 0 |
action_result.data.\*.org_id | string | | 7DESJ9GN |
action_result.data.\*.parent_guid | string | | 7DESJ9GN-0040bdb5-000014a4-00000000-1d793334a75d6d9 |
action_result.data.\*.parent_pid | numeric | | 5284 |
action_result.data.\*.process_guid | string | | 7DESJ9GN-0040bdb5-00000f08-00000000-1d793334a79e887 |
action_result.data.\*.process_hash | string | `sha256` | 80b110b91730729be60c7d79c55fff0ec893fd4cfb5f44d04c433ee8e95c5e20 |
action_result.data.\*.process_name | string | `file name` `file path` | c:\\windows\\system32\\conhost.exe |
action_result.data.\*.process_pid | numeric | | 3768 |
action_result.data.\*.process_terminated | boolean | | True False |
action_result.data.\*.process_username | string | | NT AUTHORITY\\SYSTEM |
action_result.data.\*.regmod_count | numeric | | 0 |
action_result.data.\*.scriptload_count | numeric | | 0 |
action_result.data.\*.watchlist_hit | string | | uxgHiAbKT2aQQlzFZWQT4Q:FFAGQQZQRmOhg0clEA5V1g-c46f2504-fce8-4aac-836b-1fb5b4cd0997:3 |
action_result.summary.num_results | numeric | | 85 3 50 |
action_result.message | string | | Num results: 85 Num results: 3 Num results: 50 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list events'

List events that match supplied filter criteria

Type: **investigate** <br>
Read only: **True**

The parameters <b>ip</b>, <b>host_name</b>, <b>hash</b>, <b>application</b>, and <b>owner</b> apply only to the device the event came from. Thus, for example, the <b>ip</b> parameters cannot be used to search for a destination IP. The examples for the <b>search_span</b> parameter are <b>1d</b>, <b>1w</b>, <b>2y</b>, <b>2h</b>, <b>1m</b>, or <b>50s</b> (where y=year, w=week, d=day, h=hour, m=minute, s=second). This Action requires Custom API Key, Custom API Connector ID, and Organization Key.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | optional | IP | string | `ip` `ipv6` |
**host_name** | optional | Host Name | string | `host name` |
**hash** | optional | SHA-256 Hash | string | `hash` `sha256` |
**application** | optional | Application Name | string | |
**event_type** | optional | Event Type | string | |
**owner** | optional | Owner | string | |
**search_span** | optional | Number of days back to search | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.application | string | | chrome.exe |
action_result.parameter.event_type | string | | NETWORK |
action_result.parameter.hash | string | `hash` `sha256` | 454563634 |
action_result.parameter.host_name | string | `host name` | chrome.exe |
action_result.parameter.ip | string | `ip` `ipv6` | 146.247.47.49 |
action_result.parameter.owner | string | | ant1@vmware.com |
action_result.parameter.search_span | string | | 1w |
action_result.data.\*.event_network_inbound | boolean | | False True |
action_result.data.\*.event_network_location | string | | |
action_result.data.\*.event_network_protocol | string | | TCP |
action_result.data.\*.event_network_local_ipv4 | string | | |
action_result.data.\*.event_network_remote_ipv4 | string | | |
action_result.data.\*.event_network_remote_port | numeric | | 1514 |
action_result.data.\*.backend_timestamp | string | | 2021-08-16T16:14:21.260Z |
action_result.data.\*.device_group_id | numeric | | 0 |
action_result.data.\*.device_id | numeric | `cb defense device id` | 4486274 |
action_result.data.\*.device_name | string | | corp\\controlcenter |
action_result.data.\*.device_policy_id | numeric | | 6525 |
action_result.data.\*.device_timestamp | string | | 2021-08-16T16:13:19.408Z |
action_result.data.\*.enriched | boolean | | True False |
action_result.data.\*.enriched_event_type | string | | SYSTEM_API_CALL |
action_result.data.\*.event_description | string | | The application "<share><link hash="c7db4ae8175c33a47baa3ddfa089fad17bc8e362f21e835d78ab22c9231fe370">C:\\Windows\\system32\\svchost.exe -k netsvcs</link></share>" attempted to open the process "c:\\windows\\system32\\wbem\\wmiprvse.exe", by calling the function "OpenProcess". The operation was successful. |
action_result.data.\*.event_id | string | `cb defense event id` | f39a55e8feac11eb9c368d6106d24432 |
action_result.data.\*.event_type | string | | crossproc |
action_result.data.\*.ingress_time | numeric | | 1629130444544 |
action_result.data.\*.legacy | boolean | | True False |
action_result.data.\*.org_id | string | | 7DESJ9GN |
action_result.data.\*.parent_guid | string | | 7DESJ9GN-00447482-000001d4-00000000-1d78798b26efeb8 |
action_result.data.\*.parent_pid | numeric | | 468 |
action_result.data.\*.process_guid | string | | 7DESJ9GN-00447482-00000330-00000000-1d78798b4d88021 |
action_result.data.\*.process_hash | string | `sha256` | c7db4ae8175c33a47baa3ddfa089fad17bc8e362f21e835d78ab22c9231fe370 |
action_result.data.\*.process_name | string | `file name` `file path` | c:\\windows\\system32\\svchost.exe |
action_result.data.\*.process_pid | numeric | | 816 |
action_result.data.\*.process_username | string | | NT AUTHORITY\\SYSTEM |
action_result.summary.num_results | numeric | | 10 |
action_result.message | string | | Num results: 10 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get event'

Get information about an event

Type: **investigate** <br>
Read only: **True**

This Action requires Custom API Key, Custom API Connector ID, and Organization Key.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Event ID | string | `cb defense event id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `cb defense event id` | 3077d242391711e8b9b1afced5871817 71a57a17fb4411eb935515fc69969bb2,76eb0a47bfb4411eb935515fc69969bb2,58642d5afb4411eb9c368d6106d24432 |
action_result.data.\*.netconn_ipv4 | numeric | | |
action_result.data.\*.netconn_port | numeric | | 80 |
action_result.data.\*.netconn_domain | string | | |
action_result.data.\*.netconn_inbound | boolean | | False True |
action_result.data.\*.netconn_location | string | | |
action_result.data.\*.netconn_protocol | string | | |
action_result.data.\*.netconn_local_ipv4 | numeric | | |
action_result.data.\*.netconn_local_port | numeric | | |
action_result.data.\*.event_network_inbound | boolean | | False True |
action_result.data.\*.event_network_location | string | | |
action_result.data.\*.event_network_protocol | string | | TCP |
action_result.data.\*.event_network_local_ipv4 | string | | |
action_result.data.\*.event_network_remote_ipv4 | string | | |
action_result.data.\*.event_network_remote_port | numeric | | |
action_result.data.\*.backend_timestamp | string | | 2021-08-12T08:08:37.994Z |
action_result.data.\*.childproc_cmdline | string | `file path` | "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe" --type=utility --utility-sub-type=chrome.mojom.UtilWin --field-trial-handle=1160,885411660734948521,13489737458596992732,131072 --lang=en-US --service-sandbox-type=none --mojo-platform-channel-handle=2192 /prefetch:8 |
action_result.data.\*.childproc_cmdline_length | numeric | | 278 |
action_result.data.\*.childproc_effective_reputation | string | | TRUSTED_WHITE_LIST |
action_result.data.\*.childproc_effective_reputation_source | string | | CLOUD |
action_result.data.\*.childproc_guid | string | | 7DESJ9GN-00447482-00000b78-00000000-1d78f512c4f9892 |
action_result.data.\*.childproc_hash | string | `sha256` | 2198a7b58bccb758036b969ddae6cc2ece07565e2659a7c541a313a0492231a3 |
action_result.data.\*.childproc_name | string | `file name` `file path` | c:\\program files (x86)\\google\\chrome\\application\\chrome.exe |
action_result.data.\*.childproc_pid | numeric | | 2936 |
action_result.data.\*.childproc_reputation | string | | TRUSTED_WHITE_LIST |
action_result.data.\*.device_external_ip | string | `ip` `ipv6` | 146.247.47.49 |
action_result.data.\*.device_group_id | numeric | | 0 |
action_result.data.\*.device_id | numeric | | 4486274 |
action_result.data.\*.device_installed_by | string | `email` | ant1@vmware.com |
action_result.data.\*.device_internal_ip | string | `ip` `ipv6` | 192.168.110.10 |
action_result.data.\*.device_location | string | | OFFSITE |
action_result.data.\*.device_name | string | | controlcenter |
action_result.data.\*.device_os | string | | WINDOWS |
action_result.data.\*.device_os_version | string | | Server 2012 R2 x64 |
action_result.data.\*.device_policy | string | | default |
action_result.data.\*.device_policy_id | numeric | | 6525 |
action_result.data.\*.device_target_priority | string | | MEDIUM |
action_result.data.\*.device_timestamp | string | | 2021-08-12T08:08:02.934Z |
action_result.data.\*.document_guid | string | | DJ9-V4MJTwWEyJUqfPgZMw |
action_result.data.\*.enriched | boolean | | True False |
action_result.data.\*.enriched_event_type | string | | CREATE_PROCESS |
action_result.data.\*.event_description | string | | The application "<share><link hash="cbc104fcc03cb2acbdafc2fe2669e8da54993f8d21d8851d4d80ecec26a3a9f0">C:\\program files (x86)\\google\\chrome\\application\\chrome.exe</link></share>" invoked the application "<share><link hash="cbc104fcc03cb2acbdafc2fe2669e8da54993f8d21d8851d4d80ecec26a3a9f0">C:\\program files (x86)\\google\\chrome\\application\\chrome.exe</link></share>". The operation was successful. |
action_result.data.\*.event_id | string | `md5` | 71a57a17fb4411eb935515fc69969bb2 |
action_result.data.\*.event_report_code | string | | SUB_RPT_NONE |
action_result.data.\*.event_type | string | | childproc |
action_result.data.\*.ingress_time | numeric | | 1628755707444 |
action_result.data.\*.legacy | boolean | | True False |
action_result.data.\*.org_id | string | | 7DESJ9GN |
action_result.data.\*.parent_effective_reputation | string | | TRUSTED_WHITE_LIST |
action_result.data.\*.parent_effective_reputation_source | string | | CLOUD |
action_result.data.\*.parent_guid | string | | 7DESJ9GN-00447482-00000dac-00000000-1d78798ce2b1d4e |
action_result.data.\*.parent_hash | string | `sha256` | dfbea9e8c316d9bc118b454b0c722cd674c30d0a256340200e2c3a7480cba674 |
action_result.data.\*.parent_name | string | `file name` `file path` | c:\\windows\\explorer.exe |
action_result.data.\*.parent_pid | numeric | | 3500 |
action_result.data.\*.parent_reputation | string | | TRUSTED_WHITE_LIST |
action_result.data.\*.process_cmdline | string | `file path` | C:\\WINDOWS\\system32\\svchost.exe -k DcomLaunch -p |
action_result.data.\*.process_cmdline_length | numeric | | 48 |
action_result.data.\*.process_effective_reputation | string | | TRUSTED_WHITE_LIST |
action_result.data.\*.process_effective_reputation_source | string | | CLOUD |
action_result.data.\*.process_guid | string | | 7DESJ9GN-00447482-00001544-00000000-1d78e6aaa23023a |
action_result.data.\*.process_hash | string | `sha256` | 643ec58e82e0272c97c2a59f6020970d881af19c0ad5029db9c958c13b6558c7 |
action_result.data.\*.process_name | string | `file name` `file path` | c:\\program files (x86)\\google\\chrome\\application\\chrome.exe |
action_result.data.\*.process_pid | numeric | | 856 |
action_result.data.\*.process_reputation | string | | TRUSTED_WHITE_LIST |
action_result.data.\*.process_sha256 | string | `sha256` | cbc104fcc03cb2acbdafc2fe2669e8da54993f8d21d8851d4d80ecec26a3a9f0 |
action_result.data.\*.process_start_time | string | | 2021-08-11T04:38:00.281Z |
action_result.data.\*.process_username | string | | NT AUTHORITY\\SYSTEM |
action_result.summary.num_results | numeric | | 2 |
action_result.message | string | | Successfully retrieved event data. |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get alert'

Get information about an alert

Type: **investigate** <br>
Read only: **True**

This Action requires Custom API Key, Custom API Connector ID, and Organization Key.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | Alert ID/Legacy alert ID | string | `cb defense alert id` `cb defense legacy alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `cb defense alert id` `cb defense legacy alert id` | 469db8ea-f9e5-49d3-88f5-ac596da1fb24 2DAEF827 |
action_result.data.\*.num_found | numeric | | 1 |
action_result.data.\*.num_available | numeric | | 1 |
action_result.data.\*.reason_code | string | | |
action_result.data.\*.sensor_action | string | | DENY |
action_result.data.\*.policy_applied | string | | APPLIED |
action_result.data.\*.device_location | string | | OFFSITE |
action_result.data.\*.threat_activity_c2 | string | | NOT_ATTEMPTED |
action_result.data.\*.created_by_event_id | string | | fa7c0730ffa911ebbf18076f4da5904e |
action_result.data.\*.threat_activity_dlp | string | | NOT_ATTEMPTED |
action_result.data.\*.threat_activity_phish | string | | NOT_ATTEMPTED |
action_result.data.\*.blocked_threat_category | string | | NON_MALWARE |
action_result.data.\*.threat_cause_parent_guid | string | | |
action_result.data.\*.threat_cause_process_guid | string | | 7DESJ9GN-004400c2-00000dfc-00000000-1d793b6b9f735ed |
action_result.data.\*.not_blocked_threat_category | string | | UNKNOWN |
action_result.data.\*.threat_cause_cause_event_id | string | | fa7c0730ffa911ebbf18076f4da5904e |
action_result.data.\*.threat_cause_actor_process_pid | string | | 3580-132737127044036077-0 |
action_result.data.\*.category | string | | THREAT |
action_result.data.\*.count | numeric | | 0 |
action_result.data.\*.create_time | string | | 2021-08-11T05:23:59.873Z |
action_result.data.\*.device_id | numeric | `cb defense device id` | 4483137 |
action_result.data.\*.device_name | string | | KognosCBTest-1 |
action_result.data.\*.device_os | string | | WINDOWS |
action_result.data.\*.device_os_version | string | | |
action_result.data.\*.device_username | string | `email` `user name` | rahul@kognos.io |
action_result.data.\*.document_guid | string | | ce-dT2QTQ1-EVBEbCtI_2Q |
action_result.data.\*.first_event_time | string | | 2021-08-11T05:20:53.355Z |
action_result.data.\*.id | string | `cb defense alert id` | e56278e1-a480-4de4-b70a-10df6b96b37b |
action_result.data.\*.ioc_field | string | | netconn_ipv4 |
action_result.data.\*.ioc_hit | string | `ip` `ipv6` | 52.239.193.68 |
action_result.data.\*.ioc_id | string | | a1866c54-72c3-463c-b14b-e73667636397 |
action_result.data.\*.last_event_time | string | | 2021-08-11T05:20:53.355Z |
action_result.data.\*.last_update_time | string | | 2021-08-11T05:23:59.873Z |
action_result.data.\*.legacy_alert_id | string | `cb defense legacy alert id` | 2DAEF827 |
action_result.data.\*.notes_present | boolean | | True False |
action_result.data.\*.org_key | string | | 7DESJ9GN |
action_result.data.\*.policy_id | numeric | | 6525 |
action_result.data.\*.policy_name | string | | default |
action_result.data.\*.process_guid | string | | 7DESJ9GN-00446841-00000d2c-00000000-1d78e702a57d6cc |
action_result.data.\*.process_name | string | `file name` | waappagent.exe |
action_result.data.\*.reason | string | | Process waappagent.exe was detected by the report "Phishing Host" in watchlist "RecordedFutureRiskyIPs" |
action_result.data.\*.report_id | string | | zNosh8EQAWbgZXnKGhdFQ-b1a38674-dc27-47f5-90ab-c8e9e44b4d66 |
action_result.data.\*.report_name | string | | Phishing Host |
action_result.data.\*.run_state | string | | RAN |
action_result.data.\*.severity | numeric | | 8 |
action_result.data.\*.tags | string | | |
action_result.data.\*.target_value | string | | MEDIUM |
action_result.data.\*.threat_cause_actor_md5 | string | `md5` | a88a65cc81ba9c1bb5cb5e0b707607d8 |
action_result.data.\*.threat_cause_actor_name | string | `file path` `file name` | c:\\windowsazure\\packages\\waappagent.exe |
action_result.data.\*.threat_cause_actor_sha256 | string | `sha256` | 89aae87b3ca69d0642c112464fe5e93870894b01ea9ac4b8023ca2679ae7b58d |
action_result.data.\*.threat_cause_reputation | string | | TRUSTED_WHITE_LIST |
action_result.data.\*.threat_cause_threat_category | string | | UNKNOWN |
action_result.data.\*.threat_cause_vector | string | | UNKNOWN |
action_result.data.\*.threat_id | string | `md5` | 996364C5CE500D8A7DE479F20139CAEF |
action_result.data.\*.threat_indicators.\*.process_name | string | `file name` | waappagent.exe |
action_result.data.\*.threat_indicators.\*.sha256 | string | `sha256` | 89aae87b3ca69d0642c112464fe5e93870894b01ea9ac4b8023ca2679ae7b58d |
action_result.data.\*.threat_indicators.\*.ttps | string | | a1866c54-72c3-463c-b14b-e73667636397 |
action_result.data.\*.type | string | | WATCHLIST |
action_result.data.\*.watchlists.\*.id | string | | 7dXUbCjfRS5pqjfc5Vv3w |
action_result.data.\*.watchlists.\*.name | string | | RecordedFutureRiskyIPs |
action_result.data.\*.workflow.changed_by | string | | Carbon Black |
action_result.data.\*.workflow.comment | string | | |
action_result.data.\*.workflow.last_update_time | string | | 2021-08-11T05:23:21.252Z |
action_result.data.\*.workflow.remediation | string | | |
action_result.data.\*.workflow.state | string | | OPEN |
action_result.summary.device | string | | KognosCBTest-1 |
action_result.message | string | | Device: win7 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get notifications'

Get notifications from CB Defense

Type: **investigate** <br>
Read only: **True**

This action retrieves the current list of notifications from CB Defense. Once a notification is retrieved, it cannot be retrieved again. This Action requires SIEM Key and SIEM Connector ID.

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.deviceInfo.deviceHostName | string | `host name` | |
action_result.data.\*.deviceInfo.deviceId | numeric | `cb defense device id` | 844355 |
action_result.data.\*.deviceInfo.deviceName | string | | hedwards-mac2 |
action_result.data.\*.deviceInfo.deviceType | string | | MAC |
action_result.data.\*.deviceInfo.deviceVersion | string | | MAC OS X 10.10.5 |
action_result.data.\*.deviceInfo.email | string | | hedwards |
action_result.data.\*.deviceInfo.externalIpAddress | string | `ip` `ipv6` | 10.10.10.10 |
action_result.data.\*.deviceInfo.groupName | string | | default |
action_result.data.\*.deviceInfo.internalIpAddress | string | `ip` `ipv6` | 192.168.1.2 |
action_result.data.\*.deviceInfo.targetPriorityCode | numeric | | 0 |
action_result.data.\*.deviceInfo.targetPriorityType | string | | MEDIUM |
action_result.data.\*.eventDescription | string | | [Global Alert Notification] [Confer has detected a threat against your company.] [https://defense.phantom.local#device/844355/incident/38AW1VQY] [The application sh invoked a system application (ifconfig).] [Incident id: 38AW1VQY] [Threat score: 3] [Group: default] [Email: hedwards] [Name: hedwards-mac2] [Type and OS: MAC MAC OS X 10.10.5] [Severity: Monitored] |
action_result.data.\*.eventTime | numeric | | 1526409575253 |
action_result.data.\*.ruleName | string | | Global Alert Notification |
action_result.data.\*.threatInfo.incidentId | string | | 38AW1VQY |
action_result.data.\*.threatInfo.indicators.\*.applicationName | string | | sh |
action_result.data.\*.threatInfo.indicators.\*.indicatorName | string | | RUN_SYSTEM_UTILITY |
action_result.data.\*.threatInfo.indicators.\*.sha256Hash | string | `sha256` | 035ee8aaff5c5282925974215e7bd28cad51e788c64431bb933364011e637fcd |
action_result.data.\*.threatInfo.score | numeric | | 3 |
action_result.data.\*.threatInfo.summary | string | | The application sh invoked a system application (ifconfig). |
action_result.data.\*.threatInfo.time | numeric | | 1526410075759 |
action_result.data.\*.type | string | | THREAT |
action_result.data.\*.url | string | `url` | https://defense.phantom.local/investigate?s[searchWindow]=ALL&s[c][DEVICE_ID][0]=844355&s[c][INCIDENT_ID][0]=38AW1VQY |
action_result.summary.num_notifications | numeric | | 2 |
action_result.message | string | | Num notifications: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update policy'

Updates an existing policy on the Carbon Black Defense server

Type: **generic** <br>
Read only: **False**

This Action requires API Key and API Connector ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy** | required | JSON object containing the policy details (see https://developer.carbonblack.com/reference/cb-defense/1/rest-api/#create-new-policy) | string | |
**policy_id** | required | The ID of the policy to replace. This ID must match the ID in the request URL | numeric | `cb defense policy id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.policy | string | | {"key": "value"} |
action_result.parameter.policy_id | string | `cb defense policy id` | 2343456356 |
action_result.data.\*.message | string | | Success |
action_result.data.\*.success | boolean | | True False |
action_result.summary.policy_id | string | `cb defense policy id` | 53253 |
action_result.message | string | | Policy updated successfully |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get policy'

Retrieves an existing policy from the Carbon Black Defense server

Type: **investigate** <br>
Read only: **True**

This Action requires API Key and API Connector ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_id** | required | The ID of the policy to retrieve | numeric | `cb defense policy id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.policy_id | string | `cb defense policy id` | 3436345 |
action_result.data.\*.message | string | | Success |
action_result.data.\*.success | boolean | | True False |
action_result.data.\*.policyInfo.orgId | numeric | | 1105 |
action_result.data.\*.policyInfo.policy.avSettings.onDemandScan.profile | string | | NORMAL |
action_result.data.\*.policyInfo.policy.knownBadHashAutoDeleteDelayMs | string | | |
action_result.data.\*.policyInfo.vdiAutoDeregInactiveIntervalMs | string | | |
action_result.data.\*.policyInfo.description | string | | |
action_result.data.\*.policyInfo.id | numeric | | |
action_result.data.\*.policyInfo.latestRevision | numeric | | |
action_result.data.\*.policyInfo.name | string | | |
action_result.data.\*.policyInfo.policy.avSettings.apc.enabled | boolean | | |
action_result.data.\*.policyInfo.policy.avSettings.apc.maxExeDelay | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.apc.maxFileSize | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.apc.riskLevel | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.features.\*.enabled | boolean | | |
action_result.data.\*.policyInfo.policy.avSettings.features.\*.name | string | | |
action_result.data.\*.policyInfo.policy.avSettings.onAccessScan.profile | string | | |
action_result.data.\*.policyInfo.policy.avSettings.onDemandScan.scanCdDvd | string | | |
action_result.data.\*.policyInfo.policy.avSettings.onDemandScan.scanUsb | string | | |
action_result.data.\*.policyInfo.policy.avSettings.onDemandScan.schedule.days | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.onDemandScan.schedule.rangeHours | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.onDemandScan.schedule.recoveryScanIfMissed | boolean | | |
action_result.data.\*.policyInfo.policy.avSettings.onDemandScan.schedule.startHour | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.signatureUpdate.schedule.fullIntervalHours | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.signatureUpdate.schedule.initialRandomDelayHours | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.signatureUpdate.schedule.intervalHours | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.updateServers.servers.\*.flags | numeric | | |
action_result.data.\*.policyInfo.policy.avSettings.updateServers.servers.\*.regId | string | | |
action_result.data.\*.policyInfo.policy.avSettings.updateServers.servers.\*.server.\*.name | string | | |
action_result.data.\*.policyInfo.policy.avSettings.updateServers.serversForOffSiteDevices.\*.name | string | | |
action_result.data.\*.policyInfo.policy.id | numeric | `cb defense policy id` | |
action_result.data.\*.policyInfo.policy.rules.\*.action | string | | |
action_result.data.\*.policyInfo.policy.rules.\*.application.type | string | | |
action_result.data.\*.policyInfo.policy.rules.\*.application.value | string | | |
action_result.data.\*.policyInfo.policy.rules.\*.id | numeric | | |
action_result.data.\*.policyInfo.policy.rules.\*.operation | string | | |
action_result.data.\*.policyInfo.policy.rules.\*.required | boolean | | |
action_result.data.\*.policyInfo.policy.sensorSettings.\*.name | string | | |
action_result.data.\*.policyInfo.policy.sensorSettings.\*.value | string | | |
action_result.data.\*.policyInfo.priorityLevel | string | | |
action_result.data.\*.policyInfo.systemPolicy | boolean | | |
action_result.data.\*.policyInfo.version | numeric | | |
action_result.summary.policy_id | string | `cb defense policy id` | 13145 |
action_result.message | string | | Policy retrieved successfully |
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
