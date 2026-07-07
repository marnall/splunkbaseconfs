# Check Point Firewall

Publisher: Splunk <br>
Connector Version: 2.2.2 <br>
Product Vendor: Check Point Software Technologies <br>
Product Name: Check Point Firewall <br>
Minimum Product Version: 5.1.0

This app supports a variety of endpoint and network based containment actions on Check Point Firewall

### Configuration variables

This table lists the configuration variables required to operate Check Point Firewall. These variables are specified when configuring a Check Point Firewall asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | Management Server URL with port (e.g. https://10.10.10.10:443) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | Username |
**password** | required | password | Password |
**domain** | optional | string | Domain |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity <br>
[list policies](#action-list-policies) - List policies <br>
[list layers](#action-list-layers) - List access layers <br>
[block ip](#action-block-ip) - Block an IP/subnet <br>
[unblock ip](#action-unblock-ip) - Unblock an IP/subnet <br>
[list hosts](#action-list-hosts) - List hosts <br>
[add host](#action-add-host) - Add host <br>
[delete host](#action-delete-host) - Delete host <br>
[add network](#action-add-network) - Create network object <br>
[delete network](#action-delete-network) - Delete network object <br>
[update group members](#action-update-group-members) - Update group members <br>
[logout session](#action-logout-session) - Logout of an existing session <br>
[install policy](#action-install-policy) - Executes the install-policy on a given list of targets <br>
[add user](#action-add-user) - Create a new user based on a pre-built template <br>
[delete user](#action-delete-user) - Delete existing user

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** <br>
Read only: **True**

This action logs into the device using a REST API call to check the connection and credentials configured.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list policies'

List policies

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.from | numeric | | |
action_result.data.\*.packages.\*.domain.domain-type | string | | |
action_result.data.\*.packages.\*.domain.name | string | | |
action_result.data.\*.packages.\*.domain.uid | string | | |
action_result.data.\*.packages.\*.name | string | `check point policy` | |
action_result.data.\*.packages.\*.type | string | | |
action_result.data.\*.packages.\*.uid | string | | |
action_result.data.\*.to | numeric | | |
action_result.data.\*.total | numeric | | |
action_result.summary | string | | |
action_result.message | string | | Successfully found 1 policy |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list layers'

List access layers

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.access-layers.\*.domain.domain-type | string | | |
action_result.data.\*.access-layers.\*.domain.name | string | | |
action_result.data.\*.access-layers.\*.domain.uid | string | | |
action_result.data.\*.access-layers.\*.name | string | `check point layer` | |
action_result.data.\*.access-layers.\*.type | string | | |
action_result.data.\*.access-layers.\*.uid | string | | |
action_result.data.\*.from | numeric | | |
action_result.data.\*.to | numeric | | |
action_result.data.\*.total | numeric | | |
action_result.summary | string | | |
action_result.message | string | | Successfully found 1 layer |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'block ip'

Block an IP/subnet

Type: **contain** <br>
Read only: **False**

The <b>ip</b> parameter supports the following formats:<ul><li>Simple IP: For example 123.123.123.123</li><li>IP, Subnet mask: 123.123.0.0 255.255.0.0</li><li>CIDR Notation: 123.123.0.0/16</li></ul>This action takes multiple steps to block an IP/subnet:<ul><li>Log in to the REST endpoint on Check Point to get a session ID.</li><li>Check for an existing network object for the supplied IP/subnet.</li><li>Add the network object if it does not already exist.</li><li>Check for a rule associated with the network object if it already exists.</li><li>Create a rule at the top of the policy that drops all traffic going to the supplied IP/subnet.</li><li>Publish the session.</li><li>Push the changes to the policy's configured firewalls.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to block | string | `ip` |
**policy** | required | Policy | string | `check point policy` |
**layer** | required | Layer | string | `check point layer` |
**skip_install_policy** | optional | Skip the policy installation step | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` | 1.1.1.1 |
action_result.parameter.policy | string | `check point policy` | standard |
action_result.parameter.layer | string | `check point layer` | network |
action_result.status | string | | success failed |
action_result.parameter.skip_install_policy | boolean | | True False |
action_result.data.\*.action-settings.enable-identity-captive-portal | boolean | | |
action_result.data.\*.action.domain.domain-type | string | | |
action_result.data.\*.action.domain.name | string | | |
action_result.data.\*.action.domain.uid | string | | |
action_result.data.\*.action.name | string | | |
action_result.data.\*.destination.\*.subnet4 | string | | 123.123.0.0 |
action_result.data.\*.destination.\*.subnet-mask | string | | 255.255.0.0 |
action_result.data.\*.destination.\*.mask-length4 | numeric | | 16 |
action_result.data.\*.action.type | string | | |
action_result.data.\*.action.uid | string | | |
action_result.data.\*.comments | string | | |
action_result.data.\*.custom-fields.field-1 | string | | |
action_result.data.\*.custom-fields.field-2 | string | | |
action_result.data.\*.custom-fields.field-3 | string | | |
action_result.data.\*.data-direction | string | | |
action_result.data.\*.data-negate | boolean | | |
action_result.data.\*.data.\*.domain.domain-type | string | | |
action_result.data.\*.data.\*.domain.name | string | | |
action_result.data.\*.data.\*.domain.uid | string | | |
action_result.data.\*.data.\*.name | string | | |
action_result.data.\*.data.\*.type | string | | |
action_result.data.\*.data.\*.uid | string | | |
action_result.data.\*.destination-negate | boolean | | |
action_result.data.\*.destination.\*.domain.domain-type | string | | |
action_result.data.\*.destination.\*.domain.name | string | | |
action_result.data.\*.destination.\*.domain.uid | string | | |
action_result.data.\*.destination.\*.name | string | | |
action_result.data.\*.destination.\*.type | string | | |
action_result.data.\*.destination.\*.uid | string | | |
action_result.data.\*.domain.domain-type | string | | |
action_result.data.\*.domain.name | string | | |
action_result.data.\*.domain.uid | string | | |
action_result.data.\*.enabled | boolean | | |
action_result.data.\*.install-on.\*.domain.domain-type | string | | |
action_result.data.\*.install-on.\*.domain.name | string | | |
action_result.data.\*.install-on.\*.domain.uid | string | | |
action_result.data.\*.install-on.\*.name | string | | |
action_result.data.\*.install-on.\*.type | string | | |
action_result.data.\*.install-on.\*.uid | string | | |
action_result.data.\*.meta-info.creation-time.iso-8601 | string | | |
action_result.data.\*.meta-info.creation-time.posix | numeric | | |
action_result.data.\*.meta-info.creator | string | | |
action_result.data.\*.meta-info.last-modifier | string | | |
action_result.data.\*.meta-info.last-modify-time.iso-8601 | string | | |
action_result.data.\*.meta-info.last-modify-time.posix | numeric | | |
action_result.data.\*.meta-info.lock | string | | |
action_result.data.\*.meta-info.validation-state | string | | |
action_result.data.\*.name | string | | |
action_result.data.\*.service-negate | boolean | | |
action_result.data.\*.service.\*.domain.domain-type | string | | |
action_result.data.\*.service.\*.domain.name | string | | |
action_result.data.\*.service.\*.domain.uid | string | | |
action_result.data.\*.service.\*.name | string | | |
action_result.data.\*.service.\*.type | string | | |
action_result.data.\*.service.\*.uid | string | | |
action_result.data.\*.source-negate | boolean | | |
action_result.data.\*.source.\*.domain.domain-type | string | | |
action_result.data.\*.source.\*.domain.name | string | | |
action_result.data.\*.source.\*.domain.uid | string | | |
action_result.data.\*.source.\*.name | string | | |
action_result.data.\*.source.\*.type | string | | |
action_result.data.\*.source.\*.uid | string | | |
action_result.data.\*.time.\*.domain.domain-type | string | | |
action_result.data.\*.time.\*.domain.name | string | | |
action_result.data.\*.time.\*.domain.uid | string | | |
action_result.data.\*.time.\*.name | string | | |
action_result.data.\*.time.\*.type | string | | |
action_result.data.\*.time.\*.uid | string | | |
action_result.data.\*.track-alert | string | | |
action_result.data.\*.track.domain.domain-type | string | | |
action_result.data.\*.track.domain.name | string | | |
action_result.data.\*.track.domain.uid | string | | |
action_result.data.\*.track.name | string | | |
action_result.data.\*.track.type | string | | |
action_result.data.\*.track.uid | string | | |
action_result.data.\*.type | string | | |
action_result.data.\*.uid | string | | |
action_result.data.\*.vpn.\*.domain.domain-type | string | | |
action_result.data.\*.vpn.\*.domain.name | string | | |
action_result.data.\*.vpn.\*.domain.uid | string | | |
action_result.data.\*.vpn.\*.name | string | | |
action_result.data.\*.vpn.\*.type | string | | |
action_result.data.\*.vpn.\*.uid | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully blocked IP |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.layer | string | | f5cec687-05e5-4573-b1dc-08119f24cbc9 |
action_result.data.\*.track.type.uid | string | | 29e53e3d-23bf-48fe-b6b1-d59bd88036f9 |
action_result.data.\*.track.type.name | string | | None |
action_result.data.\*.track.type.type | string | | Track |
action_result.data.\*.track.type.domain.uid | string | | a0bbbc99-adef-4ef8-bb6d-defdefdefdef |
action_result.data.\*.track.type.domain.name | string | | Check Point Data |
action_result.data.\*.track.type.domain.domain-type | string | | data domain |
action_result.data.\*.track.alert | string | | none |
action_result.data.\*.track.accounting | boolean | | False |
action_result.data.\*.track.per-session | boolean | | False |
action_result.data.\*.track.per-connection | boolean | | False |
action_result.data.\*.track.enable-firewall-session | boolean | | False |
action_result.data.\*.content.\*.uid | string | | 97aeb369-9aea-11d5-bd16-0090272ccb30 |
action_result.data.\*.content.\*.name | string | | Any |
action_result.data.\*.content.\*.type | string | | CpmiAnyObject |
action_result.data.\*.content.\*.domain.uid | string | | a0bbbc99-adef-4ef8-bb6d-defdefdefdef |
action_result.data.\*.content.\*.domain.name | string | | Check Point Data |
action_result.data.\*.content.\*.domain.domain-type | string | | data domain |
action_result.data.\*.destination.\*.ipv4-address | string | | 1.1.1.1 |
action_result.data.\*.content-negate | boolean | | False |
action_result.data.\*.content-direction | string | | any |

## action: 'unblock ip'

Unblock an IP/subnet

Type: **correct** <br>
Read only: **False**

The <b>ip</b> parameter supports the following formats:<ul><li>Simple IP: For example 123.123.123.123</li><li>IP, Subnet mask: 123.123.0.0 255.255.0.0</li><li>CIDR Notation: 123.123.0.0/16</li></ul>This action takes multiple steps to unblock an IP/subnet:<ul><li>Log in to the REST endpoint on Check Point to get a session ID.</li><li>Check for an existing network object for the supplied IP/subnet.</li><li>Check for a rule associated with the network object if it exists.</li><li>Delete the rule if it exists.</li><li>Publish the session.</li><li>Push the changes to the policy's configured firewalls.</li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to unblock | string | `ip` |
**policy** | required | Policy | string | `check point policy` |
**layer** | required | Layer | string | `check point layer` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.ip | string | `ip` | 1.1.1.1 |
action_result.parameter.policy | string | `check point policy` | standard |
action_result.parameter.layer | string | `check point layer` | network |
action_result.status | string | | success failed |
action_result.data.\*.message | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully unblocked IP |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list hosts'

List hosts

Type: **correct** <br>
Read only: **False**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.from | numeric | | 1 |
action_result.data.\*.objects.\*.domain.domain-type | string | `domain` | domain |
action_result.data.\*.objects.\*.domain.name | string | | SMC User |
action_result.data.\*.objects.\*.domain.uid | string | | 41e821a0-3720-11e3-aa6e-0800200c9fde |
action_result.data.\*.objects.\*.uid | string | | 3e8a6f97-1755-43f4-8057-870e8a25ddf9 |
action_result.data.\*.objects.\*.name | string | | Host_127.0.0.1 |
action_result.data.\*.objects.\*.ipv4-address | string | `ip` | 127.0.0.1 |
action_result.data.\*.objects.\*.ipv6-address | string | | 2002:7f00:: |
action_result.data.\*.objects.\*.type | string | | host |
action_result.data.\*.to | numeric | | 4 |
action_result.data.\*.total | numeric | | 4 |
action_result.summary | string | | |
action_result.message | string | | Successfully found 1 host |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary.total_number_of_hosts | numeric | | 9 |

## action: 'add host'

Add host

Type: **correct** <br>
Read only: **False**

The <b>ip</b> parameter supports the following formats:<ul><li>IPv4: For example 123.123.123.123</li><li>IPv6: For example 2001:0db8:0000:0000:0000:ff00:0042:7879</li></ul>This action will always prioritize using the <b>ip</b> parameter unless <b>ipv4</b> and/or <b>ipv6</b> parameters are specified. If both ipv4 and ipv6 addresses are required, use the corresponding parameters explicitly.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Object/host name (must be unique in the domain) | string | `check point host name` |
**ip** | optional | IPv4 or IPv6 address to add (if both addresses are required use ipv4 and ipv6 fields explicitly) | string | `ip` `ipv6` |
**ipv4** | optional | IPv4 address to add | string | `ip` |
**ipv6** | optional | IPv6 address to add | string | `ipv6` |
**comments** | optional | Comments string to add | string | |
**groups** | optional | Comma-separated list of group identifiers | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comments | string | | Adding Test user |
action_result.parameter.groups | string | | test group |
action_result.parameter.ip | string | `ip` `ipv6` | 192.0.2.1 |
action_result.parameter.ipv4 | string | `ip` | 192.0.2.1 |
action_result.parameter.ipv6 | string | `ipv6` | 2001:0db8:0000:0000:0000:ff00:0042:7879 |
action_result.parameter.name | string | `check point host name` | test host ipv6 new host |
action_result.data.\*.color | string | | black |
action_result.data.\*.comments | string | | |
action_result.data.\*.domain.domain-type | string | `domain` | domain |
action_result.data.\*.domain.name | string | | SMC User |
action_result.data.\*.domain.uid | string | | 41e821a0-3720-11e3-aa6e-0800200c9fde |
action_result.data.\*.icon | string | | Objects/host |
action_result.data.\*.name | string | `check point host name` | test host ipv6 new host |
action_result.data.\*.uid | string | `check point host uid` | e1485577-3f1d-4ec2-89fc-a98747146d75 b87fa85f-856d-4709-b3cf-05507f5511e7 28c38771-4bf2-46fe-a402-f7dc29707d34 |
action_result.data.\*.ipv4-address | string | `ip` | 192.0.2.1 |
action_result.data.\*.ipv6-address | string | `ipv6` | 2001:db8::ff00:42:7879 |
action_result.data.\*.meta-info.creation-time.iso-8601 | string | | 2021-10-27T13:09-0700 2021-10-27T12:37-0700 2021-10-27T12:51-0700 |
action_result.data.\*.meta-info.creation-time.posix | numeric | | 1635365349344 1635363435459 1635364300075 |
action_result.data.\*.meta-info.creator | string | | admin |
action_result.data.\*.meta-info.last-modifier | string | | admin |
action_result.data.\*.meta-info.last-modify-time.iso-8601 | string | | 2021-10-27T13:09-0700 2021-10-27T12:37-0700 2021-10-27T12:51-0700 |
action_result.data.\*.meta-info.last-modify-time.posix | numeric | | 1635365349344 1635363435459 1635364300075 |
action_result.data.\*.meta-info.lock | string | | unlocked |
action_result.data.\*.meta-info.validation-state | string | | ok |
action_result.data.\*.nat-settings.auto-rule | boolean | | False |
action_result.data.\*.read-only | boolean | | True |
action_result.data.\*.type | string | | host |
action_result.summary | string | | |
action_result.message | string | | Successfully added host |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.groups.\*.uid | string | | 86b77630-acc5-4fa4-9c5e-e88a32a6b317 |
action_result.data.\*.groups.\*.name | string | | Phantom Group 123 |
action_result.data.\*.groups.\*.type | string | | group |
action_result.data.\*.groups.\*.domain.uid | string | | 41e821a0-3720-11e3-aa6e-0800200c9fde |
action_result.data.\*.groups.\*.domain.name | string | | SMC User |
action_result.data.\*.groups.\*.domain.domain-type | string | | domain |

## action: 'delete host'

Delete host

Type: **correct** <br>
Read only: **False**

To delete a host, either specify <b>uid</b> or <b>name</b>. If provided both, this action will prioritize the <b>uid</b> parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uid** | optional | Host's unique identifier | string | `check point host uid` |
**name** | optional | Object/host name | string | `check point host name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.uid | string | `check point host uid` | 7a20fab7-f411-4a1b-a541-58c6d7596934 |
action_result.parameter.name | string | `check point host name` | test host ipv6 ipv4 |
action_result.data.\*.message | string | | OK |
action_result.summary | string | | |
action_result.message | string | | Successfully deleted host |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add network'

Create network object

Type: **contain** <br>
Read only: **False**

For add a network, You must need to specify one <b>subnet</b> and a <b>subnet mask length</b> or <b>subnet mask</b> parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Object/network name (must be unique in the domain) | string | `check point network name` |
**subnet** | optional | IPv4 or IPv6 network address. If both addresses are required use subnet4 and subnet6 fields explicitly | string | `ip` `ipv6` |
**subnet_v4** | optional | IPv4 network address | string | `ip` |
**subnet_v6** | optional | IPv6 network address | string | `ipv6` |
**subnet_mask_length** | optional | IPv4 or IPv6 network mask length. If both masks are required use mask-length4 and mask-length6 fields explicitly. Instead of IPv4 mask length it is possible to specify IPv4 mask itself in subnet-mask field | string | |
**subnet_mask_length_v4** | optional | IPv4 network mask length | string | |
**subnet_mask_length_v6** | optional | IPv6 network mask length | string | |
**subnet_mask** | optional | IPv4 network mask | string | |
**groups** | optional | Comma-separated list of group names or uids | string | |
**comments** | optional | Comments string to add | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comments | string | | Adding new network |
action_result.parameter.groups | string | | test group |
action_result.parameter.name | string | `check point network name` | test host ipv6 new host |
action_result.parameter.subnet | string | `ip` `ipv6` | 10.10.10.0 |
action_result.data.\*.icon | string | | NetworkObjects/network |
action_result.data.\*.name | string | `check point network name` | new network |
action_result.data.\*.uid | string | `check point network uid` | e1485577-3f1d-4ec2-89fc-a98747146d75 b87fa85f-856d-4709-b3cf-05507f5511e7 28c38771-4bf2-46fe-a402-f7dc29707d34 |
action_result.data.\*.subnet4 | string | `check point network uid` | 192.0.2.0 |
action_result.data.\*.subnet6 | string | | 2001:d00:: |
action_result.data.\*.broadcast | string | | allow |
action_result.data.\*.subnet-mask | string | | 255.255.255.0 |
action_result.data.\*.mask-length4 | numeric | | 24 |
action_result.data.\*.mask-length6 | numeric | | 24 |
action_result.parameter.subnet_mask | string | | 255.255.0.0 |
action_result.parameter.subnet_mask_length | numeric | | 24 |
action_result.parameter.subnet_mask_length_v4 | numeric | | 24 |
action_result.parameter.subnet_mask_length_v6 | numeric | | 24 |
action_result.parameter.subnet_v4 | string | `ip` | 8.8.8.8 |
action_result.parameter.subnet_v6 | string | `ipv6` | 2001:0db8:0000:0000:0000:ff00:0042:7879 |
action_result.data.\*.color | string | | black |
action_result.data.\*.comments | string | | |
action_result.data.\*.domain.domain-type | string | `domain` | domain |
action_result.data.\*.domain.name | string | | SMC User |
action_result.data.\*.ipv6-address | string | `ipv6` | 2001:db8::ff00:42:7879 |
action_result.data.\*.domain.uid | string | | 41e821a0-3720-11e3-aa6e-0800200c9fde |
action_result.data.\*.meta-info.creation-time.iso-8601 | string | | 2021-10-27T13:09-0700 2021-10-27T12:37-0700 2021-10-27T12:51-0700 |
action_result.data.\*.meta-info.creation-time.posix | numeric | | 1635365349344 1635363435459 1635364300075 |
action_result.data.\*.meta-info.creator | string | | admin |
action_result.data.\*.meta-info.last-modifier | string | | admin |
action_result.data.\*.meta-info.last-modify-time.iso-8601 | string | | 2021-10-27T13:09-0700 2021-10-27T12:37-0700 2021-10-27T12:51-0700 |
action_result.data.\*.meta-info.last-modify-time.posix | numeric | | 1635365349344 1635363435459 1635364300075 |
action_result.data.\*.meta-info.lock | string | | unlocked |
action_result.data.\*.meta-info.validation-state | string | | ok |
action_result.data.\*.nat-settings.auto-rule | boolean | | False |
action_result.data.\*.read-only | boolean | | True |
action_result.data.\*.type | string | | network |
action_result.summary | string | | |
action_result.message | string | | Successfully added network |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.groups.\*.uid | string | | afa45412-8030-4274-8ae5-f3fe61cd8b7c |
action_result.data.\*.groups.\*.name | string | | group phantom smart console |
action_result.data.\*.groups.\*.type | string | | group |
action_result.data.\*.groups.\*.domain.uid | string | | 41e821a0-3720-11e3-aa6e-0800200c9fde |
action_result.data.\*.groups.\*.domain.name | string | | SMC User |
action_result.data.\*.groups.\*.domain.domain-type | string | | domain |

## action: 'delete network'

Delete network object

Type: **contain** <br>
Read only: **False**

To delete a network, either specify <b>uid</b> or <b>name</b>. If provided both, this action will prioritize the <b>uid</b> parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | optional | Object/host name to be deleted | string | `check point network name` |
**uid** | optional | Object/host uid to be deleted | string | `check point network uid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.message | string | | OK |
action_result.summary | string | | |
action_result.message | string | | Successfully deleted network |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.name | string | `check point network name` | Test Network |
action_result.parameter.uid | string | `check point network uid` | e1485577-3f1d-4ec2-89fc-a98747146d75 |

## action: 'update group members'

Update group members

Type: **generic** <br>
Read only: **False**

Either specify <b>uid</b> or <b>name</b>. If provided both, this action will prioritize the <b>uid</b> parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uid** | optional | Groups unique identifier | string | |
**name** | optional | Object/group name | string | |
**action** | required | Type of operation to perform | string | |
**members** | required | Comma-separated list of network objects identified by name or uid | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.action | string | | add remove |
action_result.parameter.members | string | | Test - 1.1.1.1/32 |
action_result.parameter.uid | string | | 7a20fab7-f411-4a1b-a541-58c6d7596934 |
action_result.parameter.name | string | | test group |
action_result.data.\*.members | string | | |
action_result.data.\*.message | string | | OK |
action_result.data.\*.type | string | | |
action_result.data.\*.uid | string | | 7a20fab7-f411-4a1b-a541-58c6d7596934 |
action_result.data.\*.name | string | | test group |
action_result.summary | string | | |
action_result.message | string | | Successfully updated group |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.icon | string | | General/group |
action_result.data.\*.color | string | | black |
action_result.data.\*.domain.uid | string | | 41e821a0-3720-11e3-aa6e-0800200c9fde |
action_result.data.\*.domain.name | string | | SMC User |
action_result.data.\*.domain.domain-type | string | | domain |
action_result.data.\*.members.\*.uid | string | | eb6a6562-4ed5-4051-9743-f707c86cd505 |
action_result.data.\*.members.\*.name | string | | phantom - 11.1.1.11/32 |
action_result.data.\*.members.\*.type | string | | host |
action_result.data.\*.members.\*.domain.uid | string | | 41e821a0-3720-11e3-aa6e-0800200c9fde |
action_result.data.\*.members.\*.domain.name | string | | SMC User |
action_result.data.\*.members.\*.domain.domain-type | string | | domain |
action_result.data.\*.members.\*.ipv4-address | string | | 11.1.1.11 |
action_result.data.\*.comments | string | | |
action_result.data.\*.meta-info.lock | string | | unlocked |
action_result.data.\*.meta-info.creator | string | | admin |
action_result.data.\*.meta-info.creation-time.posix | numeric | | 1646288981836 |
action_result.data.\*.meta-info.creation-time.iso-8601 | string | | 2022-03-03T11:59+0530 |
action_result.data.\*.meta-info.last-modifier | string | | admin |
action_result.data.\*.meta-info.last-modify-time.posix | numeric | | 1646675997105 |
action_result.data.\*.meta-info.last-modify-time.iso-8601 | string | | 2022-03-07T23:29+0530 |
action_result.data.\*.meta-info.validation-state | string | | ok |
action_result.data.\*.read-only | boolean | | True |

## action: 'logout session'

Logout of an existing session

Type: **correct** <br>
Read only: **False**

This action logs out of the current session unless another session ID is specified.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**session_id** | optional | Session ID to log out from | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.session_id | string | | Us2qnsKc5SGKglzjVqXGfUKIjNOOcZxl7HYINyq0Lz8 TMRsvIBQFDIFwpWQRLskhHD7XCP5pbgHzkmvlHORoOY |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully logged out of session Could not connect to Check Point: Wrong session id. Session may be expired. Please check session id and resend the request. |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 0 |

## action: 'install policy'

Executes the install-policy on a given list of targets

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy** | required | The name of the Policy Package to be installed | string | |
**targets** | required | Comma-separated list of targets that may be identified by their name, or object unique identifier | string | |
**access** | optional | Set to be true in order to install the Access Control policy. By default, the value is true if Access Control policy is enabled on the input policy package, otherwise false | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.access | boolean | | True False |
action_result.parameter.policy | string | | standard |
action_result.parameter.targets | string | | gwg-123 |
action_result.data.\*.task-id | string | | |
action_result.summary | string | | |
action_result.message | string | | Successfully submitted policy installation |

## action: 'add user'

Create a new user based on a pre-built template

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | The name of the user to be created. Must be unique in the domain | string | `check point user name` |
**template** | required | User template name or UID | string | |
**email** | optional | User email | string | |
**phone_number** | optional | User phone number | string | |
**comments** | optional | Comments string | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comments | string | | adding new user |
action_result.parameter.email | string | | testuser@example.com |
action_result.parameter.name | string | `check point user name` | test user |
action_result.parameter.phone_number | string | | 1234567890 |
action_result.parameter.template | string | | default |
action_result.data.\*.email | string | | testuser@example.com |
action_result.data.\*.name | string | `check point user name` | Test user |
action_result.data.\*.type | string | | |
action_result.data.\*.uid | string | `check point user uid` | 97aeb369-9aea-11d5-bd16-0090272ccb30 |
action_result.summary | string | | |
action_result.message | string | | Successfully created user |
action_result.data.\*.icon | string | | Objects/user |
action_result.data.\*.color | string | | black |
action_result.data.\*.domain.uid | string | | 41e821a0-3720-11e3-aa6e-0800200c9fde |
action_result.data.\*.domain.name | string | | SMC User |
action_result.data.\*.domain.domain-type | string | | domain |
action_result.data.\*.to-hour | string | | 23:59 |
action_result.data.\*.comments | string | | |
action_result.data.\*.from-hour | string | | 00:00 |
action_result.data.\*.meta-info.lock | string | | unlocked |
action_result.data.\*.meta-info.creator | string | | admin |
action_result.data.\*.meta-info.creation-time.posix | numeric | | 1646214033562 |
action_result.data.\*.meta-info.creation-time.iso-8601 | string | | 2022-03-02T15:10+0530 |
action_result.data.\*.meta-info.last-modifier | string | | admin |
action_result.data.\*.meta-info.last-modify-time.posix | numeric | | 1646214033562 |
action_result.data.\*.meta-info.last-modify-time.iso-8601 | string | | 2022-03-02T15:10+0530 |
action_result.data.\*.meta-info.validation-state | string | | ok |
action_result.data.\*.read-only | boolean | | True |
action_result.data.\*.encryption.ike | boolean | | True |
action_result.data.\*.encryption.public-key | boolean | | True |
action_result.data.\*.encryption.shared-secret | boolean | | False |
action_result.data.\*.connect-daily | boolean | | True |
action_result.data.\*.expiration-date.posix | numeric | | 1924885800000 |
action_result.data.\*.expiration-date.iso-8601 | string | | 2030-12-31T00:00+0530 |
action_result.data.\*.authentication-method | string | | undefined |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.data.\*.phone-number | string | | 1234567890 |

## action: 'delete user'

Delete existing user

Type: **generic** <br>
Read only: **False**

Either specify <b>uid</b> or <b>name</b>. If provided both, this action will prioritize the <b>uid</b> parameter.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | optional | Name of the user to be deleted | string | `check point user name` |
**uid** | optional | UID of the user to be deleted | string | `check point user uid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary | string | | |
action_result.data.\*.message | string | | OK |
action_result.message | string | | Successfully deleted user |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.parameter.name | string | `check point user name` | Test user |
action_result.parameter.uid | string | `check point user uid` | 28c38771-4bf2-46fe-a402-f7dc29707d34 |

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
