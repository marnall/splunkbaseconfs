# Tufin SecureTrack

Publisher: Splunk \
Connector Version: 2.0.8 \
Product Vendor: Tufin \
Product Name: Tufin SecureTrack \
Minimum Product Version: 4.9.39220

This app supports investigative actions on Tufin SecureTrack

### Configuration variables

This table lists the configuration variables required to operate Tufin SecureTrack. These variables are specified when configuring a Tufin SecureTrack asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Server URL (e.g. https://10.10.10.10) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate credentials provided for connectivity \
[lookup ip](#action-lookup-ip) - Lookup IP/CIDR info \
[trace route](#action-trace-route) - Check connectivity between source and destination network

## action: 'test connectivity'

Validate credentials provided for connectivity

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'lookup ip'

Lookup IP/CIDR info

Type: **investigate** \
Read only: **True**

This action can also be used to check if the specified IP is blocked by testing the value of the <b>action_result.summary.is_blocked</b> response data path.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP/CIDR to lookup | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | 10.0.0.0/8 |
action_result.data.\*.@xsi.type | string | | cloudSecurityRuleDTO |
action_result.data.\*.acceleration_breaker | boolean | | False True |
action_result.data.\*.action | string | | Accept |
action_result.data.\*.additional_parameter.\*.display_name | string | | Cloud |
action_result.data.\*.additional_parameter.\*.id | numeric | | 1079 |
action_result.data.\*.additional_parameter.\*.name | string | | Cloud(tag) |
action_result.data.\*.application.\*.display_name | string | | Any |
action_result.data.\*.application.\*.id | numeric | | 517075 |
action_result.data.\*.application.\*.name | string | | Any |
action_result.data.\*.authentication_rule | boolean | | False True |
action_result.data.\*.binding.acl.global | boolean | | False True |
action_result.data.\*.binding.acl.interfaces.acl_name | string | | outside |
action_result.data.\*.binding.acl.interfaces.device_id | numeric | | 123 |
action_result.data.\*.binding.acl.interfaces.direction | string | | INSIDE |
action_result.data.\*.binding.acl.interfaces.global | boolean | | False True |
action_result.data.\*.binding.acl.interfaces.id | numeric | | 11961 |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.ip | string | `ip` | 10.100.0.7 |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.netmask | string | `ip` | 255.255.255.0 |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.precedence | string | | |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.vendorAttachmentPolicy | string | | |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.visibility | string | | |
action_result.data.\*.binding.acl.interfaces.name | string | | outside |
action_result.data.\*.binding.acl.name | string | | outside |
action_result.data.\*.binding.cloudSecurityGroupDTO.access_allowed | boolean | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.any_zone | boolean | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.application_id | numeric | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.class_name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.comment | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.deviceName | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.device_id | numeric | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.display_name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.domain_name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.display | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.id | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.link.@href | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.member | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.type | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.global | boolean | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.id | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.implicit | boolean | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.management_domain | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.display | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.id | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.link.@href | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.member | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.type | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.nat_info.id | numeric | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.nat_info.interface_name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.type_on_device | string | | |
action_result.data.\*.binding.default | boolean | | False True |
action_result.data.\*.binding.device_policy_id | numeric | | |
action_result.data.\*.binding.direction | string | | inbound |
action_result.data.\*.binding.display_name | string | | sg email server (inbound) |
action_result.data.\*.binding.from_collection | string | | |
action_result.data.\*.binding.from_type | string | | |
action_result.data.\*.binding.from_zone.\*.global | boolean | | False True |
action_result.data.\*.binding.from_zone.\*.id | numeric | | 2833 |
action_result.data.\*.binding.from_zone.\*.name | string | | RnD |
action_result.data.\*.binding.from_zone.global | boolean | | True False |
action_result.data.\*.binding.from_zone.id | numeric | | 2822 |
action_result.data.\*.binding.from_zone.name | string | | untrust |
action_result.data.\*.binding.ip_type.ipv4 | boolean | | |
action_result.data.\*.binding.ip_type.ipv6 | boolean | | |
action_result.data.\*.binding.nat_stage | string | | |
action_result.data.\*.binding.nat_type | string | | |
action_result.data.\*.binding.policy.admin_domain | string | `domain` | root |
action_result.data.\*.binding.policy.admin_domain_id | numeric | | 122 |
action_result.data.\*.binding.policy.id | numeric | | 741 |
action_result.data.\*.binding.policy.itg | string | | ALL |
action_result.data.\*.binding.policy.itg_id | numeric | | 125 |
action_result.data.\*.binding.policy.name | string | | SiteB_Policy |
action_result.data.\*.binding.policy.unique_active_in_itg | boolean | | False True |
action_result.data.\*.binding.policy_map_name | string | | |
action_result.data.\*.binding.postnat_iface | string | | |
action_result.data.\*.binding.prenat_iface | string | | |
action_result.data.\*.binding.rule_count | numeric | | 12 |
action_result.data.\*.binding.security_rule_count | numeric | | 12 |
action_result.data.\*.binding.to_collection | string | | |
action_result.data.\*.binding.to_type | string | | |
action_result.data.\*.binding.to_zone.\*.global | boolean | | False True |
action_result.data.\*.binding.to_zone.\*.id | numeric | | 2833 |
action_result.data.\*.binding.to_zone.\*.name | string | | RnD |
action_result.data.\*.binding.to_zone.global | boolean | | True False |
action_result.data.\*.binding.to_zone.id | numeric | | 2823 |
action_result.data.\*.binding.to_zone.name | string | | trust |
action_result.data.\*.binding.uid | string | | {e226d116-78ea-4b5c-91c8-b07092686647}_inbound_@\_105 |
action_result.data.\*.comment | string | | Do not touch ! access to CP ! |
action_result.data.\*.cp_uid | string | | |
action_result.data.\*.dest_networks_negated | boolean | | False True |
action_result.data.\*.dest_services_negated | boolean | | False True |
action_result.data.\*.device_id | numeric | | 105 |
action_result.data.\*.disabled | boolean | | False True |
action_result.data.\*.dst_network.\*.display_name | string | | sg email server |
action_result.data.\*.dst_network.\*.id | numeric | | 197544 |
action_result.data.\*.dst_network.\*.name | string | | sg-0c7d7665 |
action_result.data.\*.dst_service.\*.DM_INLINE_members.member.\*.display_name | string | `url` | https |
action_result.data.\*.dst_service.\*.DM_INLINE_members.member.\*.id | numeric | | 1733217 |
action_result.data.\*.dst_service.\*.DM_INLINE_members.member.\*.name | string | | https (tcp) |
action_result.data.\*.dst_service.\*.display_name | string | | Any |
action_result.data.\*.dst_service.\*.id | numeric | | 1776562 |
action_result.data.\*.dst_service.\*.name | string | | Any |
action_result.data.\*.external | boolean | | False True |
action_result.data.\*.fmg_from_zone | string | | Any |
action_result.data.\*.fmg_to_zone | string | | Any |
action_result.data.\*.id | numeric | | 152690 |
action_result.data.\*.implicit | boolean | | False True |
action_result.data.\*.install.\*.display_name | string | | sg email server |
action_result.data.\*.install.\*.id | numeric | | 197544 |
action_result.data.\*.install.\*.name | string | | sg-0c7d7665 |
action_result.data.\*.ip_type | string | | IPv4 |
action_result.data.\*.name | string | | |
action_result.data.\*.option | string | | LOG_SESSION |
action_result.data.\*.order | numeric | | 1 |
action_result.data.\*.priority | numeric | | 116 |
action_result.data.\*.rule_number | numeric | | 1 |
action_result.data.\*.rule_type | string | | universal |
action_result.data.\*.src_network.\*.DM_INLINE_members.member.\*.display_name | string | | m_50.1.1.202 |
action_result.data.\*.src_network.\*.DM_INLINE_members.member.\*.id | numeric | | 187585 |
action_result.data.\*.src_network.\*.DM_INLINE_members.member.\*.name | string | | b2JqZWN0AA==;bV81MC4xLjEuMjAyAA== |
action_result.data.\*.src_network.\*.display_name | string | | 10.10.253.0/24 |
action_result.data.\*.src_network.\*.id | numeric | | 197659 |
action_result.data.\*.src_network.\*.name | string | | 982d7eb7457cd420838b9068a2127c74 |
action_result.data.\*.src_networks_negated | boolean | | False True |
action_result.data.\*.src_services_negated | boolean | | False True |
action_result.data.\*.textual_rep | string | | access-list outside extended permit ip any host 10.10.10.200 |
action_result.data.\*.time.display_name | string | | Any |
action_result.data.\*.time.id | numeric | | 887 |
action_result.data.\*.time.name | string | | Any |
action_result.data.\*.track.interval | string | | 300 sec |
action_result.data.\*.track.level | string | | LOG |
action_result.data.\*.type | string | | rule |
action_result.data.\*.uid | string | | {33c00a35-95e4-4e5d-8fba-f6279540deb1} |
action_result.data.\*.users.\*.display_name | string | | Any |
action_result.data.\*.users.\*.id | numeric | | 728 |
action_result.data.\*.users.\*.name | string | | Any |
action_result.data.\*.vpn.display_name | string | | Any |
action_result.data.\*.vpn.id | numeric | | 1064 |
action_result.data.\*.vpn.name | string | | Any |
action_result.summary.is_blocked | boolean | | False True |
action_result.summary.total_rules | numeric | | 353 |
action_result.message | string | | Total rules: 353, Is blocked: False |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'trace route'

Check connectivity between source and destination network

Type: **investigate** \
Read only: **True**

One of the <b>source_ip</b> or <b>destination_ip</b> parameters need to be specified. If <b>source_ip</b> or <b>destination_ip</b> parameter is not specified, the action will use 'Any'. This action returns a list of all enabled rules, which matches the specified source and destination network. The rules are sorted according to rule order. <br/>Supported <b>protocol</b>: <ul><li>Any</li><li>TCP</li><li>UDP</li><li>ICMP</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**source_ip** | optional | Source IP/CIDR | string | `ip` |
**destination_ip** | optional | Destination IP/CIDR | string | `ip` |
**protocol** | optional | Protocol (Default: Any) | string | |
**port** | optional | Port | numeric | `port` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.destination_ip | string | `ip` | 10.200.0.0/255.255.0.0 |
action_result.parameter.port | string | `port` | |
action_result.parameter.protocol | string | | Any |
action_result.parameter.source_ip | string | `ip` | 172.16.90.90/32 |
action_result.data.\*.@xsi.type | string | | securityRuleDTO |
action_result.data.\*.acceleration_breaker | boolean | | False True |
action_result.data.\*.action | string | | Accept |
action_result.data.\*.additional_parameter.\*.display_name | string | | strict |
action_result.data.\*.additional_parameter.\*.id | numeric | | 989 |
action_result.data.\*.additional_parameter.\*.name | string | | strict(vulnerability)@predefined |
action_result.data.\*.additional_parameter.display_name | string | | SecureTrack |
action_result.data.\*.additional_parameter.id | numeric | | 999 |
action_result.data.\*.additional_parameter.name | string | | SecureTrack(log_forwarding_profile) |
action_result.data.\*.application.\*.display_name | string | | Any |
action_result.data.\*.application.\*.id | numeric | | 478176 |
action_result.data.\*.application.\*.name | string | | Any |
action_result.data.\*.authentication_rule | boolean | | False True |
action_result.data.\*.binding.acl.global | boolean | | False True |
action_result.data.\*.binding.acl.interfaces.\*.acl_name | string | | inside |
action_result.data.\*.binding.acl.interfaces.\*.device_id | numeric | | 1 |
action_result.data.\*.binding.acl.interfaces.\*.direction | string | | INSIDE |
action_result.data.\*.binding.acl.interfaces.\*.global | boolean | | True False |
action_result.data.\*.binding.acl.interfaces.\*.id | numeric | | 11726 |
action_result.data.\*.binding.acl.interfaces.\*.interface_ips.interface_ip.ip | string | `ip` | 10.1.1.2 |
action_result.data.\*.binding.acl.interfaces.\*.interface_ips.interface_ip.netmask | string | `ip` | 255.255.255.252 |
action_result.data.\*.binding.acl.interfaces.\*.name | string | | GigabitEthernet2 |
action_result.data.\*.binding.acl.interfaces.acl_name | string | | outside |
action_result.data.\*.binding.acl.interfaces.device_id | numeric | | 123 |
action_result.data.\*.binding.acl.interfaces.direction | string | | INSIDE |
action_result.data.\*.binding.acl.interfaces.global | boolean | | False True |
action_result.data.\*.binding.acl.interfaces.id | numeric | | 11961 |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.ip | string | `ip` | 10.100.0.7 |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.netmask | string | `ip` | 255.255.255.0 |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.precedence | string | | |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.vendorAttachmentPolicy | string | | |
action_result.data.\*.binding.acl.interfaces.interface_ips.interface_ip.visibility | string | | |
action_result.data.\*.binding.acl.interfaces.name | string | | outside |
action_result.data.\*.binding.acl.name | string | | inside |
action_result.data.\*.binding.cloudSecurityGroupDTO.access_allowed | boolean | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.any_zone | boolean | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.application_id | numeric | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.class_name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.comment | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.deviceName | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.device_id | numeric | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.display_name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.domain_name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.display | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.id | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.link.@href | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.member | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.exclusion.\*.type | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.global | boolean | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.id | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.implicit | boolean | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.management_domain | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.display | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.id | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.link.@href | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.member | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.member.\*.type | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.nat_info.id | numeric | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.nat_info.interface_name | string | | |
action_result.data.\*.binding.cloudSecurityGroupDTO.type_on_device | string | | |
action_result.data.\*.binding.default | boolean | | False True |
action_result.data.\*.binding.device_policy_id | numeric | | |
action_result.data.\*.binding.direction | string | | inbound |
action_result.data.\*.binding.display_name | string | | DMZ_NSG2 (inbound) |
action_result.data.\*.binding.from_collection | string | | |
action_result.data.\*.binding.from_type | string | | |
action_result.data.\*.binding.from_zone.\*.global | boolean | | False True |
action_result.data.\*.binding.from_zone.\*.id | numeric | | 2830 |
action_result.data.\*.binding.from_zone.\*.name | string | | bobo |
action_result.data.\*.binding.from_zone.global | boolean | | True False |
action_result.data.\*.binding.from_zone.id | numeric | | 2826 |
action_result.data.\*.binding.from_zone.name | string | | any |
action_result.data.\*.binding.ip_type | string | | IPV4 |
action_result.data.\*.binding.ip_type.ipv4 | boolean | | |
action_result.data.\*.binding.ip_type.ipv6 | boolean | | |
action_result.data.\*.binding.nat_stage | string | | |
action_result.data.\*.binding.nat_type | string | | |
action_result.data.\*.binding.policy.admin_domain | string | `domain` | root |
action_result.data.\*.binding.policy.admin_domain_id | numeric | | 122 |
action_result.data.\*.binding.policy.id | numeric | | 735 |
action_result.data.\*.binding.policy.itg | string | | ALL |
action_result.data.\*.binding.policy.itg_id | numeric | | 125 |
action_result.data.\*.binding.policy.name | string | | default |
action_result.data.\*.binding.policy.unique_active_in_itg | boolean | | False True |
action_result.data.\*.binding.policy_map_name | string | | |
action_result.data.\*.binding.postnat_iface | string | | |
action_result.data.\*.binding.prenat_iface | string | | |
action_result.data.\*.binding.rule_count | numeric | | 1 |
action_result.data.\*.binding.security_rule_count | numeric | | 1 |
action_result.data.\*.binding.to_collection | string | | |
action_result.data.\*.binding.to_type | string | | |
action_result.data.\*.binding.to_zone.\*.global | boolean | | |
action_result.data.\*.binding.to_zone.\*.id | numeric | | |
action_result.data.\*.binding.to_zone.\*.name | string | | |
action_result.data.\*.binding.to_zone.global | boolean | | True False |
action_result.data.\*.binding.to_zone.id | numeric | | 2832 |
action_result.data.\*.binding.to_zone.name | string | | any |
action_result.data.\*.binding.uid | string | | {7d1619c8-961f-4652-91f8-dc61bcb16b4d} |
action_result.data.\*.comment | numeric | | 2 |
action_result.data.\*.cp_uid | string | | |
action_result.data.\*.dest_networks_negated | boolean | | False True |
action_result.data.\*.dest_services_negated | boolean | | False True |
action_result.data.\*.device_id | numeric | | 80 |
action_result.data.\*.device_name | string | | FortiManager |
action_result.data.\*.disabled | boolean | | False True |
action_result.data.\*.dst_network.\*.display_name | string | | all |
action_result.data.\*.dst_network.\*.id | numeric | | 174261 |
action_result.data.\*.dst_network.\*.name | string | | all(root) |
action_result.data.\*.dst_service.\*.display_name | string | | ALL |
action_result.data.\*.dst_service.\*.id | numeric | | 1681210 |
action_result.data.\*.dst_service.\*.name | string | | ALL(root) |
action_result.data.\*.external | boolean | | False True |
action_result.data.\*.fmg_from_zone | string | | Any |
action_result.data.\*.fmg_to_zone | string | | Any |
action_result.data.\*.id | numeric | | 118068 |
action_result.data.\*.implicit | boolean | | False True |
action_result.data.\*.install.\*.display_name | string | | DMZ_NSG2 |
action_result.data.\*.install.\*.id | numeric | | 196839 |
action_result.data.\*.install.\*.name | string | | DMZ_NSG2 |
action_result.data.\*.ip_type | string | | IPv4 |
action_result.data.\*.name | string | | rule_1 |
action_result.data.\*.option | string | | LOG_SESSION |
action_result.data.\*.order | numeric | | 1 |
action_result.data.\*.priority | numeric | | 65500 |
action_result.data.\*.rule_number | numeric | | 1 |
action_result.data.\*.rule_type | string | | universal |
action_result.data.\*.src_network.\*.display_name | string | | all |
action_result.data.\*.src_network.\*.id | numeric | | 174261 |
action_result.data.\*.src_network.\*.name | string | | all(root) |
action_result.data.\*.src_networks_negated | boolean | | False True |
action_result.data.\*.src_services_negated | boolean | | False True |
action_result.data.\*.textual_rep | string | | ip access-list extended inside deny ip any any |
action_result.data.\*.time.display_name | string | | Any |
action_result.data.\*.time.id | numeric | | 887 |
action_result.data.\*.time.name | string | | Any |
action_result.data.\*.track.interval | string | | |
action_result.data.\*.track.level | string | | LOG |
action_result.data.\*.type | string | | rule |
action_result.data.\*.uid | string | | {d4376bed-5749-48cb-93ce-353283d68d51} |
action_result.data.\*.users.\*.display_name | string | | Any |
action_result.data.\*.users.\*.id | numeric | | 670 |
action_result.data.\*.users.\*.name | string | | Any |
action_result.data.\*.vpn.display_name | string | | Any |
action_result.data.\*.vpn.id | numeric | | 1064 |
action_result.data.\*.vpn.name | string | | Any |
action_result.summary.allowed_traffic | boolean | | False True |
action_result.summary.total_rules | numeric | | 104 |
action_result.message | string | | Total rules: 104, Allowed traffic: True |
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
