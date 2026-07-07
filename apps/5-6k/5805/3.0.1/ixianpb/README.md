# Ixia Network Packet Broker

Publisher: Splunk Community \
Connector Version: 3.0.1 \
Product Vendor: Ixia \
Product Name: Network Packet Broker \
Minimum Product Version: 5.1.0

This ixia NPB App supports a variety of actions on the network packet broker platform. This App has been tested with Vision One

**Notes**

- Delete Filter

  - The first priority while deleting a filter is given to the name. If a filter is having name
    "51" and another filter having ID 51 then the filter with the name "51" will be deleted

- Update Filter IP

  - For type Source, the input is expected in the source_ip parameter
  - For type Destination, the input is expected in the destination_ip parameter
  - For type Source or Destination, the input is expected in the source_or_destination_ip
    parameter
  - For type Unidirectional Flow and Bidirectional Flow, the input is expected in both source_ip
    and destination_ip parameters
  - The input should be in JSON (list of the list) format. Eg.
    (\[["X.X.X.X"],["X.X.X.X/X.X.X.X"],["X.X.X.X/Y"]\]) where X = 0-255 and Y = 1-32

- Update Filter MAC

  - For type Source, the input is expected in the 'source_mac' or in 'administration'. First
    preference is given to the 'source_mac' parameter
  - For type Destination, the input is expected in the 'destination_mac' or in 'administration'
    and 'destination_address' parameters. First preference is given to the 'destination_mac'
    parameter
  - For type Source or Destination, the input is expected in the source_or_destination_mac
    parameter
  - For type Unidirectional Flow and Bidirectional Flow, the input is expected in both
    source_mac and destination_mac parameters
  - The input should be in JSON (list of the list) format. Eg.
    (\[["X-X-X-X-X-X"],["Y-Y-Y-Y-Y-Y"]\]) where X = 00-FF and Y = 00-FF

- Update Filter Port

  - For type Source, the input is expected in the source_port parameter
  - For type Destination, the input is expected in the destination_port parameter
  - For type Source or Destination, the input is expected in the source_or_destination_port
    parameter
  - For type Unidirectional Flow and Bidirectional Flow, the input is expected in both
    source_port and destination_port parameters
  - The input should be in JSON (list of the list) format. Eg. (\[["X"],["Y"]\]) where X =
    1-65535 and Y = 1-65535

### Configuration variables

This table lists the configuration variables required to operate Ixia Network Packet Broker. These variables are specified when configuring a Network Packet Broker asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**endpoint** | required | string | Endpoint (e.g. https://10.1.16.31:8000) |
**username** | required | string | Username |
**password** | required | password | Password |
**verify_cert** | optional | boolean | Verify Server SSL certificate |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration parameters \
[delete filter](#action-delete-filter) - Remove a filter from the instance \
[update mode](#action-update-mode) - Update the mode of a filter \
[update operator](#action-update-operator) - Update the operator of a filter \
[update mac](#action-update-mac) - Update the mac address criteria for a filter \
[update port](#action-update-port) - Update the port criteria of a filter \
[update ip](#action-update-ip) - Update the IP address criteria of a filter \
[update vlan replacement](#action-update-vlan-replacement) - Updates the vlan replacement settings of a filter \
[create filter](#action-create-filter) - Creates a new filter on the instance \
[list filters](#action-list-filters) - Fetch a list of the filters from the instance \
[describe filter](#action-describe-filter) - Fetches the details of a specified filter \
[restart](#action-restart) - Restarts Ixia vision one instance

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration parameters

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'delete filter'

Remove a filter from the instance

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_id_or_name** | required | Filter identifier | string | `ixianpb filter id or name` |
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_temporary_data_loss | boolean | | False True |
action_result.parameter.filter_id_or_name | string | `ixianpb filter id or name` | 41 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Filter deleted successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update mode'

Update the mode of a filter

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_id_or_name** | required | Filter identifier | string | `ixianpb filter id or name` |
**mode** | required | Mode of a filter | string | |
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_temporary_data_loss | boolean | | True False |
action_result.parameter.filter_id_or_name | string | `ixianpb filter id or name` | 20 |
action_result.parameter.mode | string | | Pass All |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Filter mode updated successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update operator'

Update the operator of a filter

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_id_or_name** | required | Filter identifier | string | `ixianpb filter id or name` |
**operator** | required | Operator of a filter | string | |
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_temporary_data_loss | boolean | | True False |
action_result.parameter.filter_id_or_name | string | `ixianpb filter id or name` | 122 |
action_result.parameter.operator | string | | OR |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Filter operator updated successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update mac'

Update the mac address criteria for a filter

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_id_or_name** | required | Filter identifier | string | `ixianpb filter id or name` |
**type** | required | Type of MAC address criteria | string | |
**administration** | optional | Admin type | string | |
**destination_address** | optional | Destination address | string | |
**source_mac** | optional | Source MAC addresses to be added | string | |
**destination_mac** | optional | Destination MAC addresses to be added | string | |
**source_or_destination_mac** | optional | Source or destination IP addresses to be added | string | |
**overwrite** | optional | Overwrites all the MAC related rules in the filter with the specified rule in the action run | boolean | |
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.administration | string | | ["LOCAL", "UNIVERSAL"] |
action_result.parameter.allow_temporary_data_loss | boolean | | True False |
action_result.parameter.destination_address | string | | ["GROUP", "INDIVIDUAL"] |
action_result.parameter.destination_mac | string | | \[["00-CC-CC-CC-CC-00"]\] |
action_result.parameter.filter_id_or_name | string | `ixianpb filter id or name` | 122 |
action_result.parameter.overwrite | boolean | | True False |
action_result.parameter.source_mac | string | | \[["00-CC-CC-CC-CC-00"]\] |
action_result.parameter.source_or_destination_mac | string | | \[["00-CC-CC-CC-CC-00"]\] |
action_result.parameter.type | string | | Source |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Updated the mac address criteria for a filter successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update port'

Update the port criteria of a filter

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_id_or_name** | required | Filter identifier | string | `ixianpb filter id or name` |
**type** | required | Type of port criteria | string | |
**source_port** | optional | Source IP addresses to be added | string | |
**destination_port** | optional | Destination IP addresses to be added | string | |
**source_or_destination_port** | optional | Source or destination IP addresses to be added | string | |
**overwrite** | optional | Overwrites all the port related rules in the filter with the specified rule in the action run | boolean | |
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_temporary_data_loss | boolean | | True False |
action_result.parameter.destination_port | string | | \[["8888"]\] |
action_result.parameter.filter_id_or_name | string | `ixianpb filter id or name` | 20 |
action_result.parameter.overwrite | boolean | | True False |
action_result.parameter.source_or_destination_port | string | | \[["8888"]\] |
action_result.parameter.source_port | string | | \[["8888"]\] |
action_result.parameter.type | string | | Source or Destination |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Updated the port criteria for a filter successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update ip'

Update the IP address criteria of a filter

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_id_or_name** | required | Filter identifier | string | `ixianpb filter id or name` |
**type** | required | Type of IP address criteria | string | |
**source_ip** | optional | Source IP addresses to be added | string | |
**destination_ip** | optional | Destination IP addresses to be added | string | |
**source_or_destination_ip** | optional | Source or destination IP addresses to be added | string | |
**overwrite** | optional | Overwrites all the IP related rules in the filter with the specified rule in the action run | boolean | |
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_temporary_data_loss | boolean | | True False |
action_result.parameter.destination_ip | string | | \[["12.12.12.12/14.14.14.14"]\] |
action_result.parameter.filter_id_or_name | string | `ixianpb filter id or name` | 122 |
action_result.parameter.overwrite | boolean | | True False |
action_result.parameter.source_ip | string | | \[["12.12.12.12/14.14.14.14"]\] |
action_result.parameter.source_or_destination_ip | string | | \[["12.12.12.12/14.14.14.14"]\] |
action_result.parameter.type | string | | Destination |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Updated the IP address criteria for a filter successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update vlan replacement'

Updates the vlan replacement settings of a filter

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_id_or_name** | required | Filter identifier | string | `ixianpb filter id or name` |
**vlan_id** | required | VLAN identifier | numeric | |
**enable** | optional | Enables the VLAN replacement | boolean | |
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_temporary_data_loss | boolean | | True False |
action_result.parameter.enable | boolean | | True False |
action_result.parameter.filter_id_or_name | string | `ixianpb filter id or name` | 19 |
action_result.parameter.vlan_id | numeric | | 2 |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Filter VLAN replacement settings updated successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create filter'

Creates a new filter on the instance

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_name** | optional | Name of the filter | string | |
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_temporary_data_loss | boolean | | True False |
action_result.parameter.filter_name | string | `ixianpb filter id or name` | test_filter_action |
action_result.data.\*.id | numeric | `ixianpb filter id or name` | 124 |
action_result.summary | string | | |
action_result.message | string | | Filter created successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list filters'

Fetch a list of the filters from the instance

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_temporary_data_loss | boolean | | True False |
action_result.data.\*.id | numeric | `ixianpb filter id or name` | 17 |
action_result.data.\*.name | string | `ixianpb filter id or name` | F3updated |
action_result.summary.num_filters | numeric | | 98 |
action_result.message | string | | Num filters: 98 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'describe filter'

Fetches the details of a specified filter

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter_id_or_name** | required | Filter identifier | string | `ixianpb filter id or name` |
**allow_temporary_data_loss** | optional | Allow temporary data loss | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.allow_temporary_data_loss | boolean | | False True |
action_result.parameter.filter_id_or_name | string | `ixianpb filter id or name` | 26 |
action_result.data | string | | |
action_result.data.\*.connect_in_access_settings.policy | string | | ALLOW_ALL |
action_result.data.\*.connect_out_access_settings.policy | string | | INHERITED |
action_result.data.\*.created.caused_by | string | | admin |
action_result.data.\*.created.details | string | | |
action_result.data.\*.created.time | numeric | | 1561355693305 |
action_result.data.\*.created.type | string | | CREATE |
action_result.data.\*.criteria.ipv4_dst.addr | string | | 10.10.10.20/16 |
action_result.data.\*.criteria.ipv4_flow.\*.address_sets.\*.addr_a | string | | 10.10.10.20/16 |
action_result.data.\*.criteria.ipv4_flow.\*.address_sets.\*.addr_b | string | | 10.10.10.30/16 |
action_result.data.\*.criteria.ipv4_flow.\*.flow_type | string | | UNI |
action_result.data.\*.criteria.ipv4_src.addr | string | | 12.12.12.13/16 |
action_result.data.\*.criteria.layer4_dst_port.\*.port | string | | 30 |
action_result.data.\*.criteria.logical_operation | string | | OR |
action_result.data.\*.default_name | string | | F11 |
action_result.data.\*.description | string | | |
action_result.data.\*.dest_port_group_list | numeric | | 44 |
action_result.data.\*.dynamic_filter_type | string | | TWO_STAGE |
action_result.data.\*.history.\*.caused_by | string | | admin |
action_result.data.\*.history.\*.details | string | | |
action_result.data.\*.history.\*.props | string | | DEST_PORT_GROUP_LIST |
action_result.data.\*.history.\*.time | numeric | | 1562654725079 |
action_result.data.\*.history.\*.type | string | | MODIFY |
action_result.data.\*.id | numeric | | 26 |
action_result.data.\*.match_count_unit | string | | PACKETS |
action_result.data.\*.misc.access_map.CONNECT_IN_ACCESS_SETTINGS.access_settings.policy | string | | ALLOW_ALL |
action_result.data.\*.misc.access_map.CONNECT_IN_ACCESS_SETTINGS.current_value | string | | All users |
action_result.data.\*.misc.access_map.CONNECT_IN_ACCESS_SETTINGS.expression_text | string | | All users |
action_result.data.\*.misc.access_map.CONNECT_IN_ACCESS_SETTINGS.operation_name | string | | Connect Network Ports |
action_result.data.\*.misc.access_map.CONNECT_IN_ACCESS_SETTINGS.operation_phrase | string | | connect network ports to |
action_result.data.\*.misc.access_map.CONNECT_IN_ACCESS_SETTINGS.user_names | string | | |
action_result.data.\*.misc.access_map.CONNECT_IN_ACCESS_SETTINGS.users_statement | string | | Anyone can perform |
action_result.data.\*.misc.access_map.CONNECT_OUT_ACCESS_SETTINGS.access_settings.policy | string | | INHERITED |
action_result.data.\*.misc.access_map.CONNECT_OUT_ACCESS_SETTINGS.current_value | string | | All users. Inherited from - no network ports connected - |
action_result.data.\*.misc.access_map.CONNECT_OUT_ACCESS_SETTINGS.expression_text | string | | All users |
action_result.data.\*.misc.access_map.CONNECT_OUT_ACCESS_SETTINGS.operation_name | string | | Connect Tool Ports |
action_result.data.\*.misc.access_map.CONNECT_OUT_ACCESS_SETTINGS.operation_phrase | string | | connect tool ports to |
action_result.data.\*.misc.access_map.CONNECT_OUT_ACCESS_SETTINGS.user_names | string | | |
action_result.data.\*.misc.access_map.CONNECT_OUT_ACCESS_SETTINGS.users_statement | string | | Anyone can perform |
action_result.data.\*.misc.access_map.MODIFY_ACCESS_SETTINGS.access_settings.policy | string | | INHERITED |
action_result.data.\*.misc.access_map.MODIFY_ACCESS_SETTINGS.current_value | string | | All users. Inherited from - no network or tool ports connected - |
action_result.data.\*.misc.access_map.MODIFY_ACCESS_SETTINGS.expression_text | string | | All users |
action_result.data.\*.misc.access_map.MODIFY_ACCESS_SETTINGS.operation_name | string | | Modify |
action_result.data.\*.misc.access_map.MODIFY_ACCESS_SETTINGS.operation_phrase | string | | modify |
action_result.data.\*.misc.access_map.MODIFY_ACCESS_SETTINGS.user_names | string | | |
action_result.data.\*.misc.access_map.MODIFY_ACCESS_SETTINGS.users_statement | string | | Anyone can perform |
action_result.data.\*.misc.access_map.RESOURCE_ACCESS_SETTINGS.access_settings.policy | string | | INHERITED |
action_result.data.\*.misc.access_map.RESOURCE_ACCESS_SETTINGS.current_value | string | | All users. Inherited from - no network or tool ports connected - |
action_result.data.\*.misc.access_map.RESOURCE_ACCESS_SETTINGS.expression_text | string | | All users |
action_result.data.\*.misc.access_map.RESOURCE_ACCESS_SETTINGS.operation_name | string | | Attach Resources |
action_result.data.\*.misc.access_map.RESOURCE_ACCESS_SETTINGS.operation_phrase | string | | attach resources to |
action_result.data.\*.misc.access_map.RESOURCE_ACCESS_SETTINGS.user_names | string | | |
action_result.data.\*.misc.access_map.RESOURCE_ACCESS_SETTINGS.users_statement | string | | Anyone can perform |
action_result.data.\*.misc.access_map.VIEW_ACCESS_SETTINGS.access_settings.policy | string | | INHERITED |
action_result.data.\*.misc.access_map.VIEW_ACCESS_SETTINGS.current_value | string | | All users. Inherited from - no network or tool ports connected - |
action_result.data.\*.misc.access_map.VIEW_ACCESS_SETTINGS.expression_text | string | | All users |
action_result.data.\*.misc.access_map.VIEW_ACCESS_SETTINGS.operation_name | string | | View |
action_result.data.\*.misc.access_map.VIEW_ACCESS_SETTINGS.operation_phrase | string | | view |
action_result.data.\*.misc.access_map.VIEW_ACCESS_SETTINGS.user_names | string | | |
action_result.data.\*.misc.access_map.VIEW_ACCESS_SETTINGS.users_statement | string | | Anyone can perform |
action_result.data.\*.misc.access_props | string | | RESOURCE_ACCESS_SETTINGS |
action_result.data.\*.mod_count | numeric | | 14 |
action_result.data.\*.mode | string | | PASS_BY_CRITERIA |
action_result.data.\*.modify_access_settings.policy | string | | INHERITED |
action_result.data.\*.name | string | | F11 |
action_result.data.\*.port_group_list.destination_list.\*.id | numeric | | 39 |
action_result.data.\*.port_group_list.destination_list.\*.name | string | | TestToolDest |
action_result.data.\*.port_group_list.source_list.\*.id | numeric | | 36 |
action_result.data.\*.port_group_list.source_list.\*.name | string | | Test Port Group 1 |
action_result.data.\*.resource_access_settings.policy | string | | INHERITED |
action_result.data.\*.resource_attachment_config.burst_buffer_settings | string | | |
action_result.data.\*.resource_attachment_config.data_masking_settings | string | | |
action_result.data.\*.resource_attachment_config.dedup_settings | string | | |
action_result.data.\*.resource_attachment_config.erspan_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.etag_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.fabric_path_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.filter_criteria | string | | |
action_result.data.\*.resource_attachment_config.filter_match_count_unit | string | | |
action_result.data.\*.resource_attachment_config.filter_mode | string | | |
action_result.data.\*.resource_attachment_config.filtering_direction | string | | |
action_result.data.\*.resource_attachment_config.filtering_options | string | | |
action_result.data.\*.resource_attachment_config.gtp_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.l2gre_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.lisp_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.mpls_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.packet_fragmentation_settings | string | | |
action_result.data.\*.resource_attachment_config.packet_length_trailer_settings | string | | |
action_result.data.\*.resource_attachment_config.port_mode | string | | |
action_result.data.\*.resource_attachment_config.pppoe_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.resource_id | string | | |
action_result.data.\*.resource_attachment_config.timestamp_settings | string | | |
action_result.data.\*.resource_attachment_config.trailer_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.trim_settings | string | | |
action_result.data.\*.resource_attachment_config.vntag_strip_settings | string | | |
action_result.data.\*.resource_attachment_config.vxlan_strip_settings | string | | |
action_result.data.\*.resource_attachment_type | string | | |
action_result.data.\*.snmp_tag | string | | |
action_result.data.\*.source_port_group_list | numeric | | 41 |
action_result.data.\*.view_access_settings.policy | string | | INHERITED |
action_result.data.\*.vlan_replace_setting.enabled | boolean | | True False |
action_result.data.\*.vlan_replace_setting.vlan_id | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | Successfully retrieved filter information |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'restart'

Restarts Ixia vision one instance

Type: **generic** \
Read only: **False**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | System restart request sent successfully |
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
