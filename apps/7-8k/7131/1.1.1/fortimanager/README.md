# FortiManager

Publisher: Splunk <br>
Connector Version: 1.1.1 <br>
Product Vendor: Fortinet <br>
Product Name: FortiManager <br>
Minimum Product Version: 6.3.0

This app performs firewall configuration and security policy management actions in FortiManager

## ADOM Locking/Unlocking

Every write action in this connector performs a lock on the Administrative Domain (ADOM) specified in the action parameters before updating or creating a resource on the FortiManager asset. If the locking attempt fails, then the entire action will fail because a lock on the ADOM could not be obtained. This is either because another user or session is actively holding the lock on the ADOM or the ADOM specified in action parameters may be invalid. FortiManager requires ADOM locking before every write operation to ensure no two administrators can make changes simultaneously.

If the locking attempt is successful, then the API call to FortiManager will execute. Afterwards, as part of the action run, the ADOM lock will be released regardless of whether the action succeeds, fails, or exits on an exception.

## Asset Configuration

The two authentication schemes allowed by the connector are either Basic Auth (username and password) or API key. The steps to generate an API key through the FortiManager UI are as follows:

1. Log into the FortiManager UI using an administrator account.
1. Select an ADOM other than 'Global', such as 'root'.
1. Click on 'System Settings' in the left pane.
1. Click on 'Administrators' and click the 'Create New' button.
1. Select 'REST API Admin' in the dropdown of the button.
1. Enter the User Name and any other pertinent information. A trusted host entry is required. Select the Admin Profile and the type of JSON API Access. For SOAR, this would most likely be 'Read-Write' access.
1. Click the 'OK' Button.
1. After the User has been created, click on the user now listed under 'REST API Administrator' to see the user details. Click on 'Regenerate' in the 'Regenerate API Key' form value, then click the 'Generate' button. Copy the generated key and use that value as the API key in the asset configuration. For this authentication scheme, only the base URL and API key are required.

### Configuration variables

This table lists the configuration variables required to operate FortiManager. These variables are specified when configuring a FortiManager asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Base URL of FortiManager instance |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | optional | string | Username |
**password** | optional | password | Password |
**api_key** | optional | password | API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[create firewall policy](#action-create-firewall-policy) - Create an ADOM firewall policy <br>
[list firewall policies](#action-list-firewall-policies) - List ADOM firewall policies <br>
[update firewall policy](#action-update-firewall-policy) - Update an ADOM firewall policy <br>
[install firewall policy](#action-install-firewall-policy) - Install a firewall policy on a device <br>
[create address](#action-create-address) - Create a firewall address object <br>
[delete address](#action-delete-address) - Delete firewall address object <br>
[list addresses](#action-list-addresses) - List firewall address objects <br>
[update address](#action-update-address) - Update existing firewall address object <br>
[block ip](#action-block-ip) - Block ADOM level IP addresses <br>
[unblock ip](#action-unblock-ip) - Unblock ADOM level IP addresses <br>
[delete firewall policy](#action-delete-firewall-policy) - Delete an ADOM firewall policy <br>
[block url](#action-block-url) - Block ADOM level URLs <br>
[unblock url](#action-unblock-url) - Unblock ADOM level URLs <br>
[create address group](#action-create-address-group) - Create address group <br>
[delete address group](#action-delete-address-group) - Delete address group

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'create firewall policy'

Create an ADOM firewall policy

Type: **generic** <br>
Read only: **False**

This action can be used to create a firewall policy within FortiManager. When specifying a firewall policy name, make sure that it is unique. FortiManager requires every firewall policy to have a distinct name, or else the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to create the firewall policy. Choosing 'ADOM' (Administrative Domain Name) of the FortiManager server allows you to perform against that particular ADOM | string | |
**adom** | optional | ADOM name | string | |
**package** | required | The Policy Package name or full folder path to create the firewall policy within | string | |
**name** | required | Policy name to create | string | |
**source_interface** | required | Incoming (ingress) interface to specify for the firewall policy. Interfaces must already exist in the FortiManager server. If specifying more than one, enter as a comma-separated list | string | |
**destination_interface** | required | Outgoing (egress) interface to specify for the firewall policy. Interfaces must already exist in the FortiManager server. If specifying more than one, enter as a comma-separated list | string | |
**source_address** | required | Source IPv4 Addresses, address objects, and/or address group names to specify for the firewall policy. If providing new address objects that are NOT of type Subnet (IPv4/Netmask format) or any new address groups that do not already exist in the FortiManager server, the action will fail. If specifying more than one, enter as a comma-separated list | string | |
**destination_address** | required | Destination IPv4 Addresses, address objects, and/or address group names to specify for the firewall policy. If providing new address objects that are NOT of type Subnet (IPv4/Netmask format) or any new address groups that do not already exist in the FortiManager server, the action will fail. If specifying more than one, enter as a comma-separated list | string | |
**action** | required | Policy action to specify for the firewall policy. Accept: Allows sessions that match the firewall policy. Deny: Blocks sessions that match the firewall policy. IPSec: Firewall policy becomes a policy-based IPsec VPN policy | string | |
**status** | required | 'Enable' or 'Disable' this firewall policy on your FortiManager instance | string | |
**schedule** | required | Name for the schedule to be associated with the firewall policy (e.g. always, none) | string | |
**service** | required | Service and Service group names to create for the firewall policy. If specifying more than one, enter as a comma-separated list | string | |
**inspection_mode** | required | Firewall policy Inspection Mode | string | |
**log_traffic** | required | Enables or disables logging of either all sessions or only security profile sessions | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.policyid | numeric | `fortimanager firewall policy id` | 10 11 |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully added firewall policy |
action_result.summary.status | string | | Successfully added firewall policy |
action_result.parameter.name | string | | soar-adom-firewall-policy |
action_result.parameter.level | string | | ADOM |
action_result.parameter.action | string | | deny |
action_result.parameter.status | string | | enable |
action_result.parameter.package | string | | default |
action_result.parameter.service | string | | ALL |
action_result.parameter.schedule | string | | always |
action_result.parameter.log_traffic | string | | all |
action_result.parameter.source_address | string | | all |
action_result.parameter.inspection_mode | string | | flow |
action_result.parameter.source_interface | string | | any |
action_result.parameter.destination_address | string | | all |
action_result.parameter.destination_interface | string | | any |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.adom | string | | root |

## action: 'list firewall policies'

List ADOM firewall policies

Type: **investigate** <br>
Read only: **True**

This action can be used to retrieve one specific firewall policy or multiple firewall policies. To filter for a specific firewall policy, provide the policy's name and if you would like to display all policies within a package, simply leave the policy name parameter blank.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to list the firewall policies | string | |
**adom** | optional | ADOM name. Only required for 'ADOM' Firewall Policies | string | |
**package** | required | Policy Package name | string | |
**package_path** | optional | The full folder path nested within the policy package | string | |
**policy_name** | optional | Specific firewall policy name whose details you want to retrieve | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.fec | numeric | | 0 |
action_result.data.\*.oid | numeric | | 5105 5142 |
action_result.data.\*.tos | string | | 0x00 |
action_result.data.\*.dsri | numeric | | 0 |
action_result.data.\*.name | string | | soar-footer-firewall-name |
action_result.data.\*.uuid | string | | c33e106e-4117-51ee-1771-7827f531ca41 987cb312-3d16-51ee-a38e-2a5f3b237725 328ee00e-5100-51ee-7bf8-0e865287254f |
action_result.data.\*.wccp | numeric | | 0 |
action_result.data.\*.\_byte | numeric | | 0 |
action_result.data.\*.\_pkts | numeric | | 0 |
action_result.data.\*.nat46 | numeric | | 0 |
action_result.data.\*.nat64 | numeric | | 0 |
action_result.data.\*.natip | string | `ip` | 0.0.0.0 |
action_result.data.\*.action | numeric | | 0 |
action_result.data.\*.status | numeric | | 1 |
action_result.data.\*.cgn-eif | numeric | | 0 |
action_result.data.\*.cgn-eim | numeric | | 0 |
action_result.data.\*.dstaddr | string | | all |
action_result.data.\*.dstintf | string | | any 1-A10 |
action_result.data.\*.obj seq | numeric | | 1 |
action_result.data.\*.rtp-nat | numeric | | 0 |
action_result.data.\*.service | string | | ALL |
action_result.data.\*.srcaddr | string | | all |
action_result.data.\*.srcintf | string | | any 1-A1 |
action_result.data.\*.policyid | numeric | | 1074741825 3 1 |
action_result.data.\*.schedule | string | | always |
action_result.data.\*.tos-mask | string | | 0x00 |
action_result.data.\*.\_hitcount | numeric | | 0 |
action_result.data.\*.\_last_hit | numeric | | 0 |
action_result.data.\*.match-vip | numeric | | 1 |
action_result.data.\*.sgt-check | numeric | | 0 |
action_result.data.\*.\_first_hit | numeric | | 0 |
action_result.data.\*.\_sesscount | numeric | | 0 |
action_result.data.\*.logtraffic | numeric | | 2 |
action_result.data.\*.tos-negate | numeric | | 0 |
action_result.data.\*.anti-replay | numeric | | 1 |
action_result.data.\*.geoip-match | numeric | | 0 |
action_result.data.\*.pcp-inbound | numeric | | 0 |
action_result.data.\*.session-ttl | string | | 0 |
action_result.data.\*.ztna-status | numeric | | 0 |
action_result.data.\*.\_label-color | numeric | | 0 |
action_result.data.\*.pcp-outbound | numeric | | 0 |
action_result.data.\*.profile-type | numeric | | 0 |
action_result.data.\*.vlan-cos-fwd | numeric | | 255 |
action_result.data.\*.vlan-cos-rev | numeric | | 255 |
action_result.data.\*.\_last_session | numeric | | 0 |
action_result.data.\*.email-collect | numeric | | 0 |
action_result.data.\*.geoip-anycast | numeric | | 0 |
action_result.data.\*.policy-expiry | numeric | | 0 |
action_result.data.\*.\_first_session | numeric | | 0 |
action_result.data.\*.dstaddr-negate | numeric | | 0 |
action_result.data.\*.match-vip-only | numeric | | 0 |
action_result.data.\*.policy-offload | numeric | | 1 |
action_result.data.\*.service-negate | numeric | | 0 |
action_result.data.\*.srcaddr-negate | numeric | | 0 |
action_result.data.\*.tcp-mss-sender | numeric | | 0 |
action_result.data.\*.\_global-vpn-tgt | numeric | | 0 |
action_result.data.\*.dstaddr6-negate | numeric | | 0 |
action_result.data.\*.dynamic-shaping | numeric | | 0 |
action_result.data.\*.ip-version-type | string | | ipv4 |
action_result.data.\*.np-acceleration | numeric | | 1 |
action_result.data.\*.permit-any-host | numeric | | 0 |
action_result.data.\*.srcaddr6-negate | numeric | | 0 |
action_result.data.\*.diffserv-forward | numeric | | 0 |
action_result.data.\*.diffserv-reverse | numeric | | 0 |
action_result.data.\*.internet-service | numeric | | 0 |
action_result.data.\*.logtraffic-start | numeric | | 0 |
action_result.data.\*.schedule-timeout | numeric | | 0 |
action_result.data.\*.send-deny-packet | numeric | | 0 |
action_result.data.\*.tcp-mss-receiver | numeric | | 0 |
action_result.data.\*.cgn-session-quota | numeric | | 16777215 |
action_result.data.\*.internet-service6 | numeric | | 0 |
action_result.data.\*.block-notification | numeric | | 0 |
action_result.data.\*.cgn-resource-quota | numeric | | 16 |
action_result.data.\*.policy-expiry-date | string | | 0000-00-00 00:00:00 |
action_result.data.\*.reputation-minimum | numeric | | 0 |
action_result.data.\*.\_global-label-color | numeric | | 0 |
action_result.data.\*.reputation-minimum6 | numeric | | 0 |
action_result.data.\*.internet-service-src | numeric | | 0 |
action_result.data.\*.ztna-policy-redirect | numeric | | 0 |
action_result.data.\*.captive-portal-exempt | numeric | | 0 |
action_result.data.\*.delay-tcp-npu-session | numeric | | 0 |
action_result.data.\*.identity-based-policy | string | | |
action_result.data.\*.internet-service6-src | numeric | | 0 |
action_result.data.\*.policy-behaviour-type | string | | standard |
action_result.data.\*.reputation-direction6 | numeric | | 42 |
action_result.data.\*.ztna-device-ownership | numeric | | 0 |
action_result.data.\*.ztna-tags-match-logic | numeric | | 0 |
action_result.data.\*.radius-mac-auth-bypass | numeric | | 0 |
action_result.data.\*.tcp-session-without-syn | numeric | | 2 |
action_result.data.\*.internet-service6-negate | numeric | | 0 |
action_result.data.\*.internet-service6-src-negate | numeric | | 0 |
action_result.status | string | | success |
action_result.message | string | | Total firewall policies: 1 Total firewall policies: 6 |
action_result.summary.total firewall policies | numeric | | 1 6 |
action_result.parameter.level | string | | ADOM |
action_result.parameter.package | string | | default |
action_result.parameter.policy_name | string | | soar-footer-firewall-name |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.vpn_dst_node | string | | |
action_result.data.\*.vpn_src_node | string | | |
action_result.parameter.adom | string | | root |
action_result.summary.total_firewall_policies | numeric | | 6 1 |
action_result.data.\*.wanopt | numeric | | 0 |
action_result.data.\*.webcache | numeric | | 0 |
action_result.data.\*.disclaimer | numeric | | 0 |
action_result.data.\*.utm-status | numeric | | 0 |
action_result.data.\*.capture-packet | numeric | | 0 |
action_result.data.\*.webcache-https | numeric | | 0 |
action_result.data.\*.ssl-ssh-profile | string | | deep-inspection |
action_result.data.\*.timeout-send-rst | numeric | | 0 |
action_result.data.\*.auto-asic-offload | numeric | | 1 |
action_result.data.\*.passive-wan-health-measurement | numeric | | 0 |
action_result.parameter.package_path | string | | firewall-policy-path |

## action: 'update firewall policy'

Update an ADOM firewall policy

Type: **generic** <br>
Read only: **False**

This action can be used to update an existing firewall policy. Whichever parameters you wish to change, make sure to provide all the values since this action will overwrite all the values. If you leave a parameter blank, it will not be changed.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to update the firewall policy. Choosing 'ADOM' (Administrative Domain Name) of the FortiManager server allows you to perform against that particular ADOM | string | |
**adom** | optional | ADOM name | string | |
**package** | required | The Policy Package name or full folder path to update the firewall policy within | string | |
**name** | required | The policy name that will be updated. Note: this does not update the policy name itself | string | |
**source_interface** | optional | Incoming (ingress) interface to add to the firewall policy. Interfaces must already exist in the FortiManager server. If specifying more than one, enter as a comma-separated list | string | |
**destination_interface** | optional | Outgoing (egress) interface to specify for the firewall policy. Interfaces must already exist in the FortiManager server. If specifying more than one, enter as a comma-separated list | string | |
**source_address** | optional | Source IPv4 Addresses, address objects, and/or address group names to specify for the firewall policy. If specifying more than one, enter as a comma-separated list | string | |
**destination_address** | optional | Destination IPv4 Addresses, address objects, and/or address group names to specify for the firewall policy. If specifying more than one, enter as a comma-separated list | string | |
**action** | optional | Policy action to specify for the firewall policy. Accept: Allows sessions that match the firewall policy. Deny: Blocks sessions that match the firewall policy. IPSec: Firewall policy becomes a policy-based IPsec VPN policy | string | |
**status** | optional | 'Enable' or 'Disable' this firewall policy on your FortiManager instance | string | |
**schedule** | optional | Name for the schedule to be associated with the firewall policy (e.g. always, none) | string | |
**service** | optional | Service and Service group names to create for the firewall policy. If specifying more than one, enter as a comma-separated list | string | |
**inspection_mode** | optional | Firewall policy Inspection Mode | string | |
**log_traffic** | optional | Enables or disables logging of either all sessions or only security profile sessions | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.policyid | numeric | `fortimanager firewall policy id` | 2 |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully updated firewall policy |
action_result.summary.status | string | | Successfully updated firewall policy |
action_result.parameter.adom | string | | root |
action_result.parameter.name | string | | fmg-firewall-policy |
action_result.parameter.level | string | | ADOM |
action_result.parameter.package | string | | default |
action_result.parameter.source_address | string | | 8.8.2.1, gmail.com, 5.2.3.1 |
action_result.parameter.source_interface | string | | wan, wan1 |
action_result.parameter.destination_interface | string | | wan1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.action | string | | ipsec |
action_result.parameter.status | string | | enable |
action_result.parameter.service | string | | ALL |
action_result.parameter.schedule | string | | always |
action_result.parameter.log_traffic | string | | disable |
action_result.parameter.inspection_mode | string | | flow |
action_result.parameter.destination_address | string | | 2.2.2.2 |

## action: 'install firewall policy'

Install a firewall policy on a device

Type: **generic** <br>
Read only: **False**

This action will install a firewall policy package on a device.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level Type | string | |
**adom** | optional | Administrative Domain Name | string | |
**generate_rev** | optional | Generate new ADOM revision before install | boolean | |
**adom_rev_comments** | optional | If 'generate_rev' flag is set, the comment for the new ADOM revision | string | |
**adom_rev_name** | optional | If 'generate_rev' flag is set, the name for the new ADOM revision | string | |
**dev_rev_comments** | optional | Comments for the device configuration revision that will be generated during install | string | |
**policy_pkg** | required | Source package path and name | string | |
**scope_name** | optional | Scope name | string | |
**scope_vdom** | optional | Scope VDOM | string | |
**preview** | optional | Generate preview cache only | boolean | |
**unassign** | optional | Remove global policy from ADOM | boolean | |
**ifpolicy_only** | optional | Only install interface policies | boolean | |
**no_ifpolicy** | optional | Install regular policies only - do not install interface policies | boolean | |
**objs_only** | optional | Install objects only - do not install any policies | boolean | |
**auto_lock_ws** | optional | Automatically lock and unlock workspace when performing security console task | boolean | |
**copy_only** | optional | Only copy to device db | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.id | numeric | | 71 |
action_result.data.\*.pid | numeric | `pid` | 23498 |
action_result.data.\*.src | string | | security console |
action_result.data.\*.adom | numeric | | 170 |
action_result.data.\*.line.\*.ip | string | `ip` | 3.101.53.203 |
action_result.data.\*.line.\*.err | numeric | | 0 |
action_result.data.\*.line.\*.oid | numeric | | 162 |
action_result.data.\*.line.\*.name | string | | bb623[copy] |
action_result.data.\*.line.\*.vdom | string | | FG-traffic |
action_result.data.\*.line.\*.state | string | | error |
action_result.data.\*.line.\*.detail | string | | Aborted due to previous error |
action_result.data.\*.line.\*.end_tm | numeric | | 1729448810 |
action_result.data.\*.line.\*.history.\*.name | string | | bb623[copy] |
action_result.data.\*.line.\*.history.\*.vdom | string | | FG-traffic |
action_result.data.\*.line.\*.history.\*.state | numeric | | 1 |
action_result.data.\*.line.\*.history.\*.detail | string | | 2024-10-20 11:26:50:Start copying policy to devdb, device(bb623), vdomid(FG-traffic) |
action_result.data.\*.line.\*.history.\*.percent | numeric | | 1 |
action_result.data.\*.line.\*.percent | numeric | | 100 |
action_result.data.\*.line.\*.start_tm | numeric | | 1729448807 |
action_result.data.\*.user | string | | u2 |
action_result.data.\*.flags | numeric | | 0 |
action_result.data.\*.state | string | | error |
action_result.data.\*.title | string | | Copy Package 'default' |
action_result.data.\*.end_tm | numeric | | 1729448810 |
action_result.data.\*.num_err | numeric | | 2 |
action_result.data.\*.percent | numeric | | 100 |
action_result.data.\*.num_done | numeric | | 1 |
action_result.data.\*.num_warn | numeric | | 0 |
action_result.data.\*.start_tm | numeric | | 1729448807 |
action_result.data.\*.num_lines | numeric | | 3 |
action_result.data.\*.tot_percent | numeric | | 300 |
action_result.data.\*.total_task_time | string | | 0:00:03.218516 |
action_result.status | string | | success |
action_result.message | string | | Successfully installed firewall policy package |
action_result.summary.status | string | | Successfully installed firewall policy package |
action_result.parameter.adom | string | | new_adom |
action_result.parameter.adom_rev_comments | string | | |
action_result.parameter.adom_rev_name | string | | |
action_result.parameter.dev_rev_comments | string | | |
action_result.parameter.scope_name | string | | bb623 |
action_result.parameter.scope_vdom | string | | root |
action_result.parameter.level | string | | ADOM |
action_result.parameter.preview | numeric | | False |
action_result.parameter.unassign | numeric | | False |
action_result.parameter.copy_only | numeric | | False |
action_result.parameter.objs_only | numeric | | False |
action_result.parameter.policy_pkg | string | | default |
action_result.parameter.no_ifpolicy | numeric | | False |
action_result.parameter.auto_lock_ws | numeric | | False |
action_result.parameter.generate_rev | numeric | | False |
action_result.parameter.ifpolicy_only | numeric | | False |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.ph | ph | | |

## action: 'create address'

Create a firewall address object

Type: **generic** <br>
Read only: **False**

This action can be used to create an address object of either subnet or FQDN type. When specifying an address name, make sure that it is unique. FortiManager requires every address object to have a distinct name, or else the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level Type | string | |
**adom** | optional | Administrative Domain Name | string | |
**address_type** | required | Type of address to create | string | |
**address_name** | required | Address name | string | `fortimanager address name` |
**ip_netmask** | optional | IP address or IP address and netmask. Examples of valid formats: 1.1.1.1, 1.1.1.1/32, 1.1.1.1/255.255.255.255 | string | `ip` `netmask` |
**fqdn** | optional | Fully Qualified Domain Name | string | |
**policy_group_name** | optional | Name of policy group to be added to address | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.adom | string | | root |
action_result.parameter.ip_netmask | string | `ip` `netmask` | 0.0.0.0 |
action_result.parameter.policy_group_name | string | | group1 |
action_result.data.\*.name | string | `fortimanager address name` | test-fqdn |
action_result.status | string | | success failed |
action_result.message | string | | Status: Successfully created address object Object already exists |
action_result.parameter.fqdn | string | | gmail.com |
action_result.parameter.level | string | | Global ADOM |
action_result.parameter.address_name | string | `fortimanager address name` | test-fqdn test-subnet1 |
action_result.parameter.address_type | string | | FQDN Subnet |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 0 |
action_result.summary.status | string | | Successfully created address object |

## action: 'delete address'

Delete firewall address object

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type | string | |
**adom** | optional | ADOM name | string | |
**address_name** | required | Name of address object to delete | string | `fortimanager address name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.url | string | | /pm/config/adom/root/obj/firewall/address/subnet123 |
action_result.data.\*.status.code | numeric | | 0 |
action_result.data.\*.status.message | string | | OK |
action_result.status | string | | success |
action_result.message | string | | Successfully deleted address object |
action_result.parameter.adom | string | | root |
action_result.parameter.level | string | | ADOM |
action_result.parameter.address_name | string | `fortimanager address name` | subnet123 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary.status | string | | Successfully deleted address object |

## action: 'list addresses'

List firewall address objects

Type: **generic** <br>
Read only: **True**

This action can be used to retrieve one specific address object or multiple address objects.<br><br>The filter_by parameter in the list addresses action can take multiple filtering criteria. For example, to filter by multiple address types you can use the following: `[["type", "==", "subnet"],["type", "==", "fqdn"]]`. Note that when using multiple criteria, only one needs to be true in order for the address object to be returned in the results. Therefore, using the previous example, the action will return address objects of both type subnet and FQDN.<br><br>When running the list addresses action adhoc, you can directly type in something like `[["type", "==", "subnet"],["type", "==", "fqdn"]]` into the filter_by parameter. However, if you are incorporating this action into a Classic Playbook, you must directly edit the action's code block in the playbook code editor and enclose the value in quotes, formatting the value like so: `"[["type", "==", "subnet"]]"`. This issue does not persist for Modern Playbooks.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type | string | |
**adom** | optional | ADOM name | string | |
**address_name** | optional | Name of address object to retrieve. If none is specified, this action will return all matching values. | string | `fortimanager address name` |
**filter_by** | optional | Criteria to filter results by. Use the following format to specify filter: \[["{attribute}", "==", "{value}"]\] | string | |
**limit** | optional | Maximum number of addresses to return. Default is 0, which returns all results. | numeric | |
**offset** | optional | The starting point of the results to be returned. | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.oid | numeric | | 5266 |
action_result.data.\*.list | string | | |
action_result.data.\*.name | string | `fortimanager address name` | 192.168.1.1 |
action_result.data.\*.type | string | | netmask |
action_result.data.\*.uuid | string | | 827d7880-5599-51ee-0445-701f26e672f1 |
action_result.data.\*.color | numeric | | 0 |
action_result.data.\*.dirty | string | | dirty |
action_result.data.\*.subnet | string | `netmask` `ip` | 255.255.255.255 |
action_result.data.\*.tagging | string | | |
action_result.data.\*.obj-type | string | | ip |
action_result.data.\*.route-tag | numeric | | 0 |
action_result.data.\*.node-ip-only | string | | disable |
action_result.data.\*.allow-routing | string | | disable |
action_result.data.\*.clearpass-spt | string | | unknown |
action_result.data.\*.fabric-object | string | | disable |
action_result.data.\*.dynamic_mapping | string | | |
action_result.data.\*.associated-interface | string | | any |
action_result.data.\*.sub-type | string | | ems-tag |
action_result.data.\*.comment | string | | IPv4 addresses of Fabric Devices. |
action_result.data.\*.end-ip | string | `ip` | 10.212.134.210 |
action_result.data.\*.start-ip | string | `ip` | 10.212.134.200 |
action_result.data.\*.fqdn | string | | gmail.com |
action_result.data.\*.cache-ttl | numeric | | 0 |
action_result.data.\*.policy-group | string | | test-group |
action_result.data.\*.macaddr | string | | 00:11:22:33:44:58 |
action_result.status | string | | success |
action_result.message | string | | Total address objects: 30 |
action_result.summary.total_address_objects | numeric | | 30 |
action_result.parameter.adom | string | | root |
action_result.parameter.level | string | | ADOM |
action_result.parameter.address_name | string | `fortimanager address name` | |
action_result.parameter.filter_by | string | | |
action_result.parameter.limit | numeric | | 0 |
action_result.parameter.offset | numeric | | 0 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update address'

Update existing firewall address object

Type: **generic** <br>
Read only: **False**

This action can be used to update an existing firewall address object. Note that you can only update the IP/Netmask value if the address is of type Subnet. Similarly, you can only update the FQDN value if the address is of type FQDN. This action does not currently support changing the address type of an address object.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type | string | |
**adom** | optional | ADOM name | string | |
**address_name** | required | Name of address object to update | string | `fortimanager address name` |
**ip_netmask** | optional | Updated IP address and netmask (e.g. 0.0.0.0/32) to assign address object | string | `ip` `netmask` |
**fqdn** | optional | Updated Fully Qualified Domain Name to assign address object | string | |
**policy_group_name** | optional | Name of policy group to be added to address | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.name | string | `fortimanager address name` | test123 gmail |
action_result.status | string | | success |
action_result.message | string | | Successfully updated addresss object |
action_result.parameter.adom | string | | root |
action_result.parameter.level | string | | ADOM |
action_result.parameter.ip_netmask | string | `ip` `netmask` | 1.2.3.4 |
action_result.parameter.address_name | string | `fortimanager address name` | test123 gmail |
action_result.parameter.fqdn | string | | \*gmail.com |
action_result.parameter.policy_group_name | string | | default |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary.status | string | | Successfully updated addresss object |

## action: 'block ip'

Block ADOM level IP addresses

Type: **contain** <br>
Read only: **False**

This action can be used to block IPV4 addresses. By specifying either a single IP address or multiple addresses as a comma-separated list, this action will create address objects if they don't already exist. The address objects will then be added to the specified address group. If the address group does not exist, the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to block IP addresses | string | |
**adom** | required | ADOM name. Only required for 'ADOM' blocking of IP addresses | string | |
**package** | required | Policy package name | string | |
**package_path** | optional | The full folder path nested within the policy package | string | |
**policy_name** | required | Specific firewall policy name for blocking IP addresses | string | |
**address_group_name** | required | Specific address group name for for blocking IP addresses | string | |
**ip_addresses** | required | Comma-separated list of IP addresses to block | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.ips_blocked | string | | 192.168.14.0/24 |
action_result.data.\*.ips_already_blocked | string | `ip` | 192.168.4.4 192.168.20.0/24 |
action_result.data.\*.created_address_objects | string | | 192.168.14.0/24 |
action_result.status | string | | success |
action_result.message | string | | Total ips blocked: 0, Total ips already blocked: 1, Total created address objects: 0, Total address object already exists: 0, Total address object failed: 0 |
action_result.summary.total_ips_blocked | numeric | | 1 0 |
action_result.summary.total_ips_already_blocked | numeric | | 1 |
action_result.summary.total_address_object_failed | numeric | | 0 |
action_result.summary.total_created_address_objects | numeric | | 1 0 |
action_result.summary.total_address_object_already_exists | numeric | | 0 |
action_result.parameter.adom | string | | root |
action_result.parameter.level | string | | ADOM |
action_result.parameter.package | string | | example_policy_package |
action_result.parameter.policy_name | string | | example-fw_policy |
action_result.parameter.ip_addresses | string | | 192.168.4.4,192.168.14.0/24 192.168.20.0/24 |
action_result.parameter.address_group_name | string | | example_test_addr_grp |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.package_path | string | | my_package_folder |

## action: 'unblock ip'

Unblock ADOM level IP addresses

Type: **contain** <br>
Read only: **False**

This action can be used to unblock IPV4 addresses. By specifying either a single IP address or multiple addresses as a comma-separated list, this action will remove any address objects from the specified address group but will NOT delete the address objects from FortiManager. If the address group does not exist, the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to unblock IP addresses | string | |
**adom** | required | ADOM name. Only required for 'ADOM' unblocking of IP addresses | string | |
**package** | required | Policy package name | string | |
**package_path** | optional | The full folder path nested within the policy package | string | |
**policy_name** | required | Specific firewall policy name for unblocking IP addresses | string | |
**address_group_name** | required | Specific address group name for for unblocking IP addresses | string | |
**ip_addresses** | required | Comma-separated list of IP addresses to unblock | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.ips_unblocked | string | | 192.168.14.0/24 |
action_result.data.\*.ips_already_unblocked | string | | 192.168.14.0/24 |
action_result.status | string | | success |
action_result.message | string | | Total ips unblocked: 2, Total ips already unblocked: 0 |
action_result.summary.total_ips_unblocked | numeric | | 2 1 |
action_result.summary.total_ips_already_unblocked | numeric | | 0 |
action_result.parameter.adom | string | | root |
action_result.parameter.level | string | | ADOM |
action_result.parameter.package | string | | example_policy_package |
action_result.parameter.policy_name | string | | example-fw_policy |
action_result.parameter.ip_addresses | string | | 192.168.4.4,192.168.14.0/24 192.168.20.0/24 |
action_result.parameter.address_group_name | string | | example_test_addr_grp |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.package_path | string | | my_package_folder |

## action: 'delete firewall policy'

Delete an ADOM firewall policy

Type: **generic** <br>
Read only: **False**

This action can be used to delete a firewall policy within FortiManager. You must provide the policy ID of the firewall policy you wish to delete. This policy ID can be retrieved from the list firewall policies action.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to create the firewall policy. Choosing 'ADOM' (Administrative Domain Name) of the FortiManager server allows you to perform against that particular ADOM | string | |
**adom** | optional | ADOM name | string | |
**package** | required | The Policy Package name or full folder path of the firewall policy to delete | string | |
**policy_id** | required | Policy ID (can be retrieved from 'List Firewall Policies' action) to delete | string | `fortimanager firewall policy id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.url | string | | /pm/config/adom/root/pkg/default/firewall/policy/28 /pm/config/adom/root/pkg/default/firewall/policy/29 |
action_result.data.\*.status.code | numeric | | 0 |
action_result.data.\*.status.message | string | | OK |
action_result.status | string | | success |
action_result.message | string | | Status: Successfully deleted firewall policy ID: 29 |
action_result.summary.status | string | | Successfully deleted firewall policy ID: 29 |
action_result.parameter.level | string | | ADOM |
action_result.parameter.package | string | | default |
action_result.parameter.policy_id | string | `fortimanager firewall policy id` | 28 29 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.adom | string | | root |

## action: 'block url'

Block ADOM level URLs

Type: **contain** <br>
Read only: **False**

This action can be used to block a URL. A URL of type 'simple' will exactly match a URL, while a 'wildcard' or 'regex' URL can be configured to match different permutations. The URL will be added to the specified web filter profile if it exists, otherwise the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to block URLs. Choosing 'ADOM' (Administrative Domain Name) of the FortiManager server allows you to perform against that particular ADOM | string | |
**adom** | optional | ADOM name | string | |
**web_filter_profile_name** | required | The Web Filter profile name to use to block URLs | string | |
**url** | required | URL to block | string | |
**type** | required | Type of URL format. Wildcard must include a '\*' | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | failed success |
action_result.message | string | | URL already exists in URL filter list Status: Successfully blocked URL |
action_result.parameter.url | string | | www.example1.com www.example.com \*.example.com ^forti.\*\\.com |
action_result.parameter.adom | string | | root |
action_result.parameter.type | string | | simple wildcard regex |
action_result.parameter.level | string | | ADOM |
action_result.parameter.web_filter_profile_name | string | | default |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 0 1 |
action_result.data.\*.id | numeric | | 11 |
action_result.summary.status | string | | Successfully blocked URL |

## action: 'unblock url'

Unblock ADOM level URLs

Type: **contain** <br>
Read only: **False**

This action can be used to unblock a URL. If the URL exists in the web filter profile, it will be removed. If the specified web filter profile does not exist, the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to unblock URLs. Choosing 'ADOM' (Administrative Domain Name) of the FortiManager server allows you to perform against that particular ADOM | string | |
**adom** | optional | ADOM name | string | |
**web_filter_profile_name** | required | The Web Filter profile name to use to unblock URLs | string | |
**url** | required | URL to unblock | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.id | numeric | | 11 |
action_result.status | string | | success failed |
action_result.message | string | | Status: Successfully unblocked URL URL does not exist in URL filter list |
action_result.summary.status | string | | Successfully unblocked URL |
action_result.parameter.url | string | | www.example.com \*.example.com ^forti.\*\\.com |
action_result.parameter.adom | string | | root |
action_result.parameter.level | string | | ADOM |
action_result.parameter.web_filter_profile_name | string | | default |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 0 |

## action: 'create address group'

Create address group

Type: **generic** <br>
Read only: **False**

This action can be used to create a new address group. When specifying an address group name, make sure that it is unique. FortiManager requires every address group to have a distinct name, or else the action will fail.<br><br>The `members` parameter accepts names of existing address objects and address groups, IP/netmask addresses, and FQDN addresses in a comma-separated list. If the IP/netmask or FQDN address does not exist on FortiManager, this action will automatically create an address object with the respective address value and add it to the address group.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to create the address group. Choosing 'ADOM' (Administrative Domain Name) of the FortiManager server allows you to perform the action against that particular ADOM | string | |
**adom** | optional | ADOM name | string | |
**address_group_name** | required | Unique name of address group you want to create | string | `fortimanager address group name` |
**members** | required | Comma-separated list of address objects or address groups to add to the address group. Accepted values include FortiManager address object names, IP/netmask, and FQDN | string | `fortimanager address name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.name | string | `fortimanager address group name` | test-group-adom addrgroup2 |
action_result.status | string | | success |
action_result.message | string | | Successfully created address group |
action_result.summary.status | string | | Successfully created address group |
action_result.parameter.adom | string | | root |
action_result.parameter.level | string | | ADOM |
action_result.parameter.members | string | `fortimanager address name` | all, 1.2.3.7 |
action_result.parameter.address_group_name | string | `fortimanager address group name` | test-group-adom addrgroup2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.members_added | string | `fortimanager address name` | 1.2.3.7 |
action_result.data.\*.address_object_already_exists | string | `fortimanager address name` | 1.2.3.7 |
action_result.data.\*.address_object_failed | string | | |

## action: 'delete address group'

Delete address group

Type: **generic** <br>
Read only: **False**

This action deletes an existing address group. Make sure the address group name entered is valid and exists on your FortiManager asset. If an invalid address group name is used, the action will fail.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**level** | required | Level type at which to create the address group. Choosing 'ADOM' (Administrative Domain Name) of the FortiManager server allows you to perform the action against that particular ADOM | string | |
**adom** | optional | ADOM name | string | |
**address_group_name** | required | Unique name of address group you want to create | string | `fortimanager address group name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.data.\*.url | string | | /pm/config/adom/root/obj/firewall/addrgrp/test-group-adom |
action_result.data.\*.status.code | numeric | | 0 |
action_result.data.\*.status.message | string | | OK |
action_result.status | string | | success |
action_result.message | string | | Successfully deleted address group |
action_result.summary.status | string | | Successfully deleted address group |
action_result.parameter.adom | string | | root |
action_result.parameter.level | string | | ADOM |
action_result.parameter.address_group_name | string | `fortimanager address group name` | test-group-adom |
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
