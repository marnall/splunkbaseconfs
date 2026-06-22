# Infoblox NIOS

Publisher: Infoblox <br>
Connector Version: 1.0.0 <br>
Product Vendor: Infoblox <br>
Product Name: Infoblox NIOS <br>
Minimum Product Version: 6.4.1

This integration enables Splunk SOAR to retrieve IP metadata from Infoblox Grid Manager and manage DNS Firewall protections through RPZs. It allows security teams to define RPZ rules that block DNS resolution for malicious or unauthorized domains, or redirect users to a walled garden by modifying DNS responses

______________________________________________________________________

## Playbooks

- Playbooks for **Infoblox NIOS** are available in the [repository](https://github.com/infobloxopen/infoblox_splunk_soar/tree/main/Infoblox%20NIOS). Refer to the README for detailed instructions on setup and configuration.

______________________________________________________________________

### Configuration variables

This table lists the configuration variables required to operate Infoblox NIOS. These variables are specified when configuring a Infoblox NIOS asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | URL (e.g. https://10.10.10.10) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate credentials provided for connectivity <br>
[update rpz cname rule](#action-update-rpz-cname-rule) - Updates an existing rule in RPZ CNAME to modify DNS behavior <br>
[create rpz cname rule](#action-create-rpz-cname-rule) - Adds a CNAME rule to an existing RPZ to override DNS behavior <br>
[create rpz a rule](#action-create-rpz-a-rule) - Adds an RPZ rule for A (IPv4) responses to block or redirect DNS queries <br>
[ip lookup](#action-ip-lookup) - Returns IPAM info for a given IP <br>
[list host info](#action-list-host-info) - Retrieves host records from Infoblox including hostname, associated IPv4/IPv6 addresses (A/AAAA records), PTR records, DNS view information, and any configured extensible attributes <br>
[create rpz srv rule](#action-create-rpz-srv-rule) - Adds an SRV record override in RPZ for service-based DNS lookups <br>
[create rpz naptr rule](#action-create-rpz-naptr-rule) - Adds a NAPTR override in RPZ to control DNS-based service discovery <br>
[dhcp lease lookup](#action-dhcp-lease-lookup) - Retrieves DHCP lease details for a MAC or IP address <br>
[list network info](#action-list-network-info) - Lists defined IPv4/IPv6 networks and subnets in IPAM <br>
[create rpz aaaa rule](#action-create-rpz-aaaa-rule) - Adds an RPZ rule for AAAA (IPv6) responses to block or redirect DNS queries <br>
[create rpz mx rule](#action-create-rpz-mx-rule) - Adds a mail exchange override rule to an RPZ <br>
[create rpz ptr rule](#action-create-rpz-ptr-rule) - Adds a reverse DNS lookup override in RPZ for an IP <br>
[create rpz txt rule](#action-create-rpz-txt-rule) - Adds a TXT record rule in RPZ to associate text data with a DNS response <br>
[create host record](#action-create-host-record) - Create a host record in Infoblox NIOS <br>
[delete rpz rule](#action-delete-rpz-rule) - Delete a Response Policy Zone (RPZ) rule <br>
[delete response policy zone](#action-delete-response-policy-zone) - Removes an existing Response Policy Zone from Infoblox <br>
[create response policy zone](#action-create-response-policy-zone) - Creates a new Response Policy Zone (RPZ) to define custom DNS responses <br>
[get response policy zone](#action-get-response-policy-zone) - Retrieves Response Policy Zone(s) based on specified criteria <br>
[search rpz rule](#action-search-rpz-rule) - Search for RPZ rules in Infoblox NIOS

## action: 'test connectivity'

Validate credentials provided for connectivity

Type: **test** <br>
Read only: **True**

Note: Even if the credentials are correct, if Infoblox is configured with an ACL that does not allow Splunk SOAR to authenticate to it, you will receive an authentication failure.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'update rpz cname rule'

Updates an existing rule in RPZ CNAME to modify DNS behavior

Type: **correct** <br>
Read only: **False**

Updates an existing rule in RPZ CNAME to modify DNS behavior.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**reference_id** | required | The reference ID of the existing RPZ rule to update | string | `reference id` |
**rule_type** | required | The type of the rule to create | string | |
**name** | required | Specify the name of the rule | string | `domain` `ip` `host name` |
**rp_zone** | required | The zone to assign the rule to | string | |
**comment** | optional | Comment for this rule | string | |
**substitute_name** | optional | The substitute name to assign (required only when Rule Type is 'Substitute (domain name)') | string | |
**view** | optional | The DNS view in which the records are located | string | |
**additional_parameters** | optional | JSON object containing additional parameters to create rpz rule (disable, extattrs, ttl, use_ttl) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"disable": false, "ttl": 3600, "use_ttl": true} |
action_result.parameter.comment | string | | Block test1 |
action_result.parameter.name | string | `domain` `ip` `host name` | test.rpz.block.in |
action_result.parameter.reference_id | string | `reference id` | record:rpz:cname/ZG5zLmJpbmRfY25hbWUkLl9kZWZhdWx0LmNvbS5ycHoucnB6LmJsb2NrLmluLnRlc3QzMg:test.rpz.block.in/default |
action_result.parameter.rp_zone | string | | rpz.block.in |
action_result.parameter.rule_type | string | | Block (No data) |
action_result.parameter.substitute_name | string | | substitute.example.com |
action_result.parameter.view | string | | default |
action_result.data.\*.\_ref | string | `reference id` | record:rpz:cname/ZG5zLmJpbmRfY25hbWUkLl9kZWZhdWx0LmNvbS5ycHoucnB6LmJsb2NrLmluLnRlc3QzMg:test.rpz.block.in/default |
action_result.data.\*.canonical | string | | * |
action_result.data.\*.comment | string | | Block test1 |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | |
action_result.data.\*.is_ipv4 | boolean | | True |
action_result.data.\*.name | string | | test.rpz.block.in |
action_result.data.\*.rp_zone | string | | rpz.block.in |
action_result.data.\*.ttl | numeric | | 3600 |
action_result.data.\*.use_ttl | boolean | | False |
action_result.data.\*.view | string | | default |
action_result.data.\*.zone | string | | rpz.block.in |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create rpz cname rule'

Adds a CNAME rule to an existing RPZ to override DNS behavior

Type: **correct** <br>
Read only: **False**

Adds a CNAME rule to an existing RPZ to override DNS behavior.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_type** | required | The type of the rule to create | string | |
**object_type** | required | The type of the object for which to assign the rule | string | |
**name** | required | Specify the name of the rule | string | `domain` `ip` `host name` |
**rp_zone** | required | The zone to assign the rule to | string | |
**comment** | optional | Comment for this rule | string | |
**substitute_name** | optional | The substitute name to assign (required only when Rule Type is 'Substitute (domain name)') | string | |
**view** | optional | The DNS view in which the records are located | string | |
**additional_parameters** | optional | JSON object containing additional parameters to create rpz rule (disable, extattrs, ttl, use_ttl) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"disable": false, "ttl": 3600, "use_ttl": true} |
action_result.parameter.comment | string | | Block test1 |
action_result.parameter.name | string | `domain` `ip` `host name` | test.rpz.block.in |
action_result.parameter.object_type | string | | Domain Name |
action_result.parameter.rp_zone | string | | rpz.block.in |
action_result.parameter.rule_type | string | | Block (No data) |
action_result.parameter.substitute_name | string | | substitute.example.com |
action_result.parameter.view | string | | default |
action_result.data.\*.\_ref | string | `reference id` | record:rpz:cname/ZG5zLmJpbmRfY25hbWUkLl9kZWZhdWx0LmNvbS5ycHoucnB6LmJsb2NrLmluLnRlc3QzMg:test.rpz.block.in/default |
action_result.data.\*.canonical | string | | * |
action_result.data.\*.comment | string | | Block test1 |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | |
action_result.data.\*.is_ipv4 | boolean | | True |
action_result.data.\*.name | string | | test.rpz.block.in |
action_result.data.\*.rp_zone | string | | rpz.block.in |
action_result.data.\*.ttl | numeric | | 3600 |
action_result.data.\*.use_ttl | boolean | | False |
action_result.data.\*.view | string | | default |
action_result.data.\*.zone | string | | rpz.block.in |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create rpz a rule'

Adds an RPZ rule for A (IPv4) responses to block or redirect DNS queries

Type: **correct** <br>
Read only: **False**

Adds an RPZ rule for A (IPv4) responses to block or redirect DNS queries.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_type** | required | The type of the object for which to create record | string | |
**name** | required | Specify the name of the rule | string | `domain` `ip` `host name` |
**rp_zone** | required | The zone to assign the rule to | string | |
**ipv4_address** | required | The IPv4 address of the substitute rule | string | `ip` |
**comment** | optional | Comment for this rule | string | |
**additional_parameters** | optional | JSON object containing additional parameters to create response policy zone (disable, extattrs, ttl, use_ttl, view) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"disable": false, "ttl": 3600, "use_ttl": true} |
action_result.parameter.comment | string | | Block malicious domain |
action_result.parameter.ipv4_address | string | `ip` | 0.0.0.0 |
action_result.parameter.name | string | `domain` `ip` `host name` | test.rpz.block.in |
action_result.parameter.object_type | string | | Domain Name IP address |
action_result.parameter.rp_zone | string | | rpz.block.in |
action_result.data.\*.\_ref | string | `reference id` | record:rpz:a/ZG5zLmJpbmRfYSQuX2RlZmF1bHQuY29tLnJwei50aHJlYXQsMTEuMi4xMi4xMCwwLjAuMC4w:10.12.2.11.threat.rpz.com/default |
action_result.data.\*.comment | string | | nightly-test-a-sub |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | |
action_result.data.\*.ipv4addr | string | `ip` | 0.0.0.0 |
action_result.data.\*.name | string | | 10.12.2.11.threat.rpz.com |
action_result.data.\*.rp_zone | string | | threat.rpz.com |
action_result.data.\*.ttl | numeric | | 3600 |
action_result.data.\*.use_ttl | boolean | | False |
action_result.data.\*.view | string | | default |
action_result.data.\*.zone | string | | threat.rpz.com |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'ip lookup'

Returns IPAM info for a given IP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_address** | optional | The IP address for which to retrieve information, e.g. "192.168.1.1". Cannot be used in conjunction with network or from/to_ip arguments | string | `ip` `ipv6` |
**network** | optional | The network that the IP belongs to is in FQDN/CIDR format, e.g. "192.168.1.0/24". Cannot be used in conjunction with ip or from/to_ip arguments | string | |
**from_ip** | optional | The beginning of the IP range, e.g. "192.168.1.0". Must be used in conjunction with to_ip | string | `ip` `ipv6` |
**to_ip** | optional | The end of the IP range, e.g. "192.168.1.254". Must be used in conjunction with from_ip | string | `ip` `ipv6` |
**status** | required | The status of the IP device. Used in conjunction with the network or ip argument. Possible values are ACTIVE, UNUSED and USED | string | |
**extended_attributes** | optional | Comma-separated key/value formatted filter for extended attributes, e.g. "Site=New York,OtherProp=MyValue" | string | |
**limit** | optional | Maximum numbers of objects to be returned | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.extended_attributes | string | | Location=DataCenter1,Department=IT |
action_result.parameter.from_ip | string | `ip` `ipv6` | 192.168.1.1 |
action_result.parameter.ip_address | string | `ip` `ipv6` | 192.168.1.100 2001:db8:1234::10 |
action_result.parameter.limit | numeric | | 100 |
action_result.parameter.network | string | | 192.168.1.0/24 |
action_result.parameter.status | string | | ACTIVE UNUSED USED |
action_result.parameter.to_ip | string | `ip` `ipv6` | 192.168.1.254 10.0.0.100 |
action_result.data.\*.\_ref | string | | record:a/ZG5zLmJpbmRfYSQxMDA6192.168.1.100/default |
action_result.data.\*.comment | string | | Server host |
action_result.data.\*.conflict_types.\* | string | | A PTR |
action_result.data.\*.discover_now_status | string | | COMPLETE PENDING FAILED |
action_result.data.\*.duid | string | | 00:01:00:01:24:e0:c5:c5:00:50:56:c0:00:08 00:02:00:00:ab:11:f2:3c:00:00:ab:11:f2:3c |
action_result.data.\*.extattrs | string | | Location=DataCenter1; Department=IT |
action_result.data.\*.ip_address | string | `ip` `ipv6` | 192.168.1.100 10.0.0.5 2001:db8::1 |
action_result.data.\*.is_conflict | boolean | | True False |
action_result.data.\*.is_invalid_mac | boolean | | True False |
action_result.data.\*.mac_address | string | `mac address` | 00:50:56:c0:00:08 aa:bb:cc:dd:ee:ff |
action_result.data.\*.mac_address_duid | string | | 00:50:56:c0:00:08 00:01:00:01:24:e0:c5:c5:00:50:56:c0:00:08 |
action_result.data.\*.names | string | | server01.example.com workstation-05.local |
action_result.data.\*.network | string | | 192.168.1.0/24 10.0.0.0/16 |
action_result.data.\*.network_view | string | | default Internal |
action_result.data.\*.status | string | | ACTIVE UNUSED USED |
action_result.data.\*.types | string | | HOST DHCP, HOST RESERVATION |
action_result.data.\*.usage | string | | DHCP DNS, DHCP DNS |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list host info'

Retrieves host records from Infoblox including hostname, associated IPv4/IPv6 addresses (A/AAAA records), PTR records, DNS view information, and any configured extensible attributes

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | optional | The hostname for the record | string | |
**ipv4_address** | optional | IPv4 address information | string | `ip` |
**ipv6_address** | optional | IPv6 address information | string | `ipv6` |
**limit** | optional | Maximum numbers of objects to be returned | numeric | |
**extended_attributes** | optional | Comma-separated key/value formatted filter for extended attributes, e.g. "Site=New York,OtherProp=MyValue" | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.extended_attributes | string | | Location=DataCenter1,Department=IT Building=HQ,Floor=3 |
action_result.parameter.ipv4_address | string | `ip` | 192.168.1.100 10.0.0.15 |
action_result.parameter.ipv6_address | string | `ipv6` | 2001:db8::1 fe80::1234:5678:9abc:def0 |
action_result.parameter.limit | numeric | | 100 500 1000 |
action_result.parameter.name | string | | server01.example.com workstation05.local |
action_result.data.\*.\_ref | string | | record:host/ZG5zLmJpbmRfYSQxMDA6c2VydmVyMDEuZXhhbXBsZS5jb20:server01.example.com/default |
action_result.data.\*.allow_telnet | boolean | | False True |
action_result.data.\*.comment | string | | Development server |
action_result.data.\*.configure_for_dns | boolean | | True False |
action_result.data.\*.creation_time | numeric | | 1627482000 1635458400 |
action_result.data.\*.ddns_protected | boolean | | True False |
action_result.data.\*.disable | boolean | | True False |
action_result.data.\*.disable_discovery | boolean | | False True |
action_result.data.\*.dns_name | string | | server01.example.com workstation05.local |
action_result.data.\*.extattrs | string | | {"Building":{"value":"HQ"}, "Floor":{"value":"3"}} |
action_result.data.\*.extattrs.IB Discovery Owned.value | string | | admin |
action_result.data.\*.extattrs.Site.value | string | | site-1 |
action_result.data.\*.extattrs_display | string | | Building=HQ, Floor=3 |
action_result.data.\*.ipv4addrs.\*.\_ref | string | | record:host_ipv4addr/ZG5zLmhvc3RfYWRkcmVzcyQuX2RlZmF1bHQuY29tLmV4YW1wbGUuLjE5Mi4xNjguMjAuMjAu:192.168.20.20/example.com/default |
action_result.data.\*.ipv4addrs.\*.configure_for_dhcp | boolean | | True False |
action_result.data.\*.ipv4addrs.\*.host | string | | example.com |
action_result.data.\*.ipv4addrs.\*.ipv4addr | string | | 192.168.20.20 |
action_result.data.\*.ipv4addrs.\*.mac | string | | 00:1a:2b:9c:7d:5e |
action_result.data.\*.ipv4addrs_display | string | | 192.168.1.100 10.0.0.15, 10.0.0.16 |
action_result.data.\*.ipv6addrs.\*.\_ref | string | | record:host_ipv6addr/ZG5zLmhvc3RfYWRkcmVzcyQuX2RlZmF1bHQuY29tLmV4YW1wbGUuLjIwMDE6ZGI4Ojg1YTM6OjhhMmU6MzcwOjc2NS4:2001%3Adb8%3A85a3%3A%3A8a2e%3A370%3A765/example.com/default |
action_result.data.\*.ipv6addrs.\*.configure_for_dhcp | boolean | | True False |
action_result.data.\*.ipv6addrs.\*.host | string | | example.com |
action_result.data.\*.ipv6addrs.\*.ipv6addr | string | | 2001:db8:85a3::8a2e:370:765 |
action_result.data.\*.ipv6addrs_display | string | | 2001:db8::1 fe80::1234:5678:9abc:def0 |
action_result.data.\*.name | string | | server01.example.com workstation05.local |
action_result.data.\*.network_view | string | | default internal |
action_result.data.\*.rrset_order | string | | cyclic |
action_result.data.\*.use_cli_credentials | boolean | | True False |
action_result.data.\*.use_dns_ea_inheritance | boolean | | True False |
action_result.data.\*.use_snmp3_credential | boolean | | True False |
action_result.data.\*.use_snmp_credential | boolean | | True False |
action_result.data.\*.use_ttl | boolean | | True False |
action_result.data.\*.view | string | | default internal external |
action_result.data.\*.zone | string | | example.com local |
action_result.summary | string | | |
action_result.summary.extended_attributes_filter_applied | boolean | | True False |
action_result.summary.ipv4_filter_applied | boolean | | True False |
action_result.summary.ipv6_filter_applied | boolean | | True False |
action_result.summary.limit | numeric | | 100 |
action_result.summary.name_filter_applied | boolean | | True False |
action_result.summary.total_objects | numeric | | 26 |
action_result.summary.total_objects_successful | numeric | | 26 |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create rpz srv rule'

Adds an SRV record override in RPZ for service-based DNS lookups

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Specify the name of the rule | string | |
**priority** | required | The priority of the Substitute (SRV Record) Rule | numeric | |
**rp_zone** | required | The name of a response policy zone in which the record resides | string | |
**port** | required | The port of the Substitute (SRV Record) Rule | numeric | |
**target** | required | Text associated with the record | string | |
**weight** | required | The weight of the Substitute (SRV Record) Rule | numeric | |
**comment** | optional | Comment for this rule | string | |
**additional_parameters** | optional | JSON object containing additional parameters to create response policy zone | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"disable": false, "ttl": 3600, "use_ttl": true} |
action_result.parameter.comment | string | | Block malicious service |
action_result.parameter.name | string | | srv-rule-example |
action_result.parameter.port | numeric | | 8080 |
action_result.parameter.priority | numeric | | 10 |
action_result.parameter.rp_zone | string | | rpz.security.local |
action_result.parameter.target | string | | blocked-service.example.com |
action_result.parameter.weight | numeric | | 5 |
action_result.data.\*.\_ref | string | | record:rpz:srv/ZG5zLmJpbmRfc3J2JC5fZGVmYXVsdC5jb20ucnB6LnNlY3VyaXR5LmxvY2FsLnNydl9ydWxl:srv-rule-example/default |
action_result.data.\*.comment | string | | Block malicious service |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | {"Location": {"value": "DataCenter"}, "Owner": {"value": "Security"}} |
action_result.data.\*.extattrs_display | string | | |
action_result.data.\*.name | string | | srv-rule-example |
action_result.data.\*.port | numeric | | 8080 |
action_result.data.\*.priority | numeric | | 10 |
action_result.data.\*.rp_zone | string | | rpz.security.local |
action_result.data.\*.target | string | | blocked-service.example.com |
action_result.data.\*.ttl | numeric | | 3600 |
action_result.data.\*.use_ttl | boolean | | True |
action_result.data.\*.view | string | | default |
action_result.data.\*.weight | numeric | | 5 |
action_result.data.\*.zone | string | | rpz.security.local |
action_result.summary | string | | Successfully created SRV rule |
action_result.summary.port | numeric | | 741 |
action_result.summary.priority | numeric | | 8 |
action_result.summary.rp_zone | string | | test.example-crest.com |
action_result.summary.rule_name | string | | data.test.example-crest.com |
action_result.summary.rule_reference | string | | record:rpz:srv/ZG5zLmJpbmRfc3J2JC5fZGVmYXVsdC5jb20uZXhhbXBsZS1jcmVzdC50ZXN0L2RhdGEvOC84OC83NDEvZGF0YXBhdGg:data.test.example-crest.com/default |
action_result.summary.weight | numeric | | 88 |
action_result.message | string | | Successfully created SRV rule in RPZ zone rpz.security.local |
summary.total_objects | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create rpz naptr rule'

Adds a NAPTR override in RPZ to control DNS-based service discovery

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Specify the name of the rule | string | |
**rp_zone** | required | The zone to assign the rule to | string | |
**order** | required | Order parameter in NAPTR record defines the sequence of rule application when multiple rules exist | numeric | |
**preference** | required | The preference of the Substitute (NAPTR Record) Rule record | numeric | |
**replacement** | required | The substitute rule object replacement field of the NAPTR record. For non-terminal NAPTR records, this field specifies the next domain name to look up | string | |
**comment** | optional | Comment for this rule | string | |
**additional_parameters** | optional | JSON object containing additional parameters to create response policy zone | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"disable": false, "services": "SIP+D2U", "flags": "U", "regexp": "!^.\*$!sip:blocked@example.com!", "ttl": 3600} |
action_result.parameter.comment | string | | Block malicious service discovery |
action_result.parameter.name | string | | example.naptr.record |
action_result.parameter.order | numeric | | 10 |
action_result.parameter.preference | numeric | | 20 |
action_result.parameter.replacement | string | | blocked.example.com |
action_result.parameter.rp_zone | string | | rpz.security.local |
action_result.data.\*.\_ref | string | | record:rpz:naptr/ZG5zLmJpbmRfbmFwdHIkLl9kZWZhdWx0LmNvbS5ycHoucnB6LnNlY3VyaXR5LmxvY2FsLmV4YW1wbGU:example.naptr.record/default |
action_result.data.\*.comment | string | | Block malicious service discovery |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | {"Location": {"value": "DataCenter"}, "Owner": {"value": "Security"}} |
action_result.data.\*.extattrs_display | string | | |
action_result.data.\*.flags | string | | U |
action_result.data.\*.name | string | | example.naptr.record |
action_result.data.\*.order | numeric | | 10 |
action_result.data.\*.preference | numeric | | 20 |
action_result.data.\*.regexp | string | | !^.\*$!sip:blocked@example.com! |
action_result.data.\*.replacement | string | | blocked.example.com |
action_result.data.\*.rp_zone | string | | rpz.security.local |
action_result.data.\*.services | string | | SIP+D2U |
action_result.data.\*.ttl | numeric | | 3600 |
action_result.data.\*.use_ttl | boolean | | True |
action_result.data.\*.view | string | | default |
action_result.data.\*.zone | string | | rpz.security.local |
action_result.summary | string | | Successfully created NAPTR rule in RPZ zone |
action_result.summary.rp_zone | string | | test.example-crest.com |
action_result.summary.rule_name | string | | testingdata.test.example-crest.com |
action_result.summary.rule_reference | string | | record:rpz:naptr/ZG5zLmJpbmRfbmFwdHIkLl9kZWZhdWx0LmNvbS5leGFtcGxlLWNyZXN0LnRlc3QsdGVzdGluZ2RhdGEsMiwzLCwsLHRlbXAgYW5tZQ:testingdata.test.example-crest.com/default |
action_result.message | string | | Successfully created NAPTR rule in RPZ zone rpz.security.local |
summary.total_objects | numeric | | 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'dhcp lease lookup'

Retrieves DHCP lease details for a MAC or IP address

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip_address** | optional | Lease IP address (IPv4 or IPv6) | string | `ip` `ipv6` |
**hardware** | optional | MAC address for IPv4 leases. Regex or exact search supported | string | `mac address` |
**hostname** | optional | Hostname sent via DHCP option 12. Regex/exact search | string | `host name` |
**ipv6_duid** | optional | IPv6 DUID identifier for IPv6 leases. Regex/exact search | string | |
**protocol** | optional | One of: BOTH, IPV4, IPV6; exact match only | string | |
**fingerprint** | optional | DHCP client fingerprint; caseâ€‘insensitive or regex search | string | |
**username** | optional | User associated with lease request; case-insensitive/regex search | string | |
**limit** | optional | Maximum numbers of objects to be returned | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.fingerprint | string | | Windows 7 Linux |
action_result.parameter.hardware | string | `mac address` | 00:50:56:c0:00:08 aa:bb:cc:dd:ee:ff |
action_result.parameter.hostname | string | `host name` | ubuntu-client windows-pc.domain.local |
action_result.parameter.ip_address | string | `ip` `ipv6` | 10.1.1.25 2001:db8::1 |
action_result.parameter.ipv6_duid | string | | 00:01:00:01:24:e0:c5:c5:00:50:56:c0:00:08 |
action_result.parameter.limit | numeric | | 100 500 |
action_result.parameter.protocol | string | | IPV4 IPV6 |
action_result.parameter.username | string | | jdoe admin |
action_result.data.\*.\_ref | string | | lease/MjE5MjQ6MTAuMS4xLjI1LzA:10.1.1.25/default |
action_result.data.\*.address | string | `ip` `ipv6` | 10.1.1.25 2001:db8::1 |
action_result.data.\*.binding_state | string | | ACTIVE FREE BACKUP |
action_result.data.\*.client_hostname | string | `host name` | ubuntu-client windows-pc.domain.local |
action_result.data.\*.cltt | numeric | | 1672531199 |
action_result.data.\*.ends | numeric | | 1672617599 |
action_result.data.\*.fingerprint | string | | Windows 7 Linux |
action_result.data.\*.hardware | string | `mac address` | 00:50:56:c0:00:08 aa:bb:cc:dd:ee:ff |
action_result.data.\*.ipv6_prefix_bits | numeric | | 64 |
action_result.data.\*.is_invalid_mac | boolean | | False True |
action_result.data.\*.network | string | | 10.1.1.0/24 2001:db8::/64 |
action_result.data.\*.network_view | string | | default internal |
action_result.data.\*.never_ends | boolean | | False |
action_result.data.\*.never_starts | boolean | | False |
action_result.data.\*.next_binding_state | string | | FREE |
action_result.data.\*.protocol | string | | IPV4 IPV6 |
action_result.data.\*.served_by | string | | /member/ZG5zLm1lbWJlcl9kY2hwcHJvcGVydGllcyQyMw:infoblox.localdomain/ |
action_result.data.\*.server_host_name | string | | infoblox.localdomain |
action_result.data.\*.starts | numeric | | 1672531200 |
action_result.data.\*.uid | string | | 01005056c00008 |
action_result.data.\*.variable | string | | |
action_result.summary | string | | Successfully retrieved 5 DHCP lease record(s) |
action_result.message | string | | Successfully retrieved 5 DHCP lease record(s) |
summary.total_objects | numeric | | 5 |
summary.total_objects_successful | numeric | | 5 |

## action: 'list network info'

Lists defined IPv4/IPv6 networks and subnets in IPAM

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**network** | optional | The network address in CIDR notation (e.g., "192.168.1.0/24") | string | |
**limit** | optional | Maximum numbers of objects to be returned | numeric | |
**extended_attributes** | optional | Comma-separated key/value formatted filter for extended attributes, e.g. "Site=New York,OtherProp=MyValue" | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.extended_attributes | string | | Location=DataCenter1,Department=IT Building=HQ,Floor=3 Region=North,Owner=NetworkTeam |
action_result.parameter.limit | numeric | | 100 500 1000 |
action_result.parameter.network | string | | 192.168.1.0/24 10.0.0.0/8 172.16.0.0/16 |
action_result.data.\*.\_ref | string | | network/ZG5zLm5ldHdvcmskMTAuMC4wLjAvOC8w:10.0.0.0/8/default |
action_result.data.\*.authority | boolean | | True False |
action_result.data.\*.bootfile | string | | bootfile.bin pxelinux.0 |
action_result.data.\*.bootserver | string | | tftp.example.com 10.0.0.5 |
action_result.data.\*.cloud_info | string | | AWS-VPC-1 Azure-VNET-2 |
action_result.data.\*.comment | string | | Corporate LAN |
action_result.data.\*.conflict_count | numeric | | 0 2 5 |
action_result.data.\*.ddns_domainname | string | | example.com corp.local |
action_result.data.\*.ddns_generate_hostname | boolean | | True False |
action_result.data.\*.dhcp_utilization | numeric | | 23.5 45.2 78.9 |
action_result.data.\*.dhcp_utilization_status | string | | NORMAL HIGH CRITICAL |
action_result.data.\*.disable | boolean | | False True |
action_result.data.\*.dynamic_hosts | numeric | | 45 120 230 |
action_result.data.\*.extattrs | string | | {"Building":{"value":"HQ"}, "Floor":{"value":"3"}} |
action_result.data.\*.extattrs_display | string | | Building=HQ, Floor=3 |
action_result.data.\*.ipv4addr | string | `ip` | 192.168.1.0 10.0.0.0 172.16.0.0 |
action_result.data.\*.lease_scavenge_time | numeric | | 3600 7200 |
action_result.data.\*.low_water_mark | numeric | | 20 30 40 |
action_result.data.\*.low_water_mark_reset | numeric | | 20 30 40 |
action_result.data.\*.members | string | | member1 member2 |
action_result.data.\*.mgm_private | boolean | | True False |
action_result.data.\*.mgm_private_overridable | boolean | | True False |
action_result.data.\*.netmask | string | | 255.255.255.0 255.0.0.0 255.255.0.0 |
action_result.data.\*.network | string | | 192.168.1.0/24 10.0.0.0/8 172.16.0.0/16 |
action_result.data.\*.network_container | string | | 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 |
action_result.data.\*.network_view | string | | default |
action_result.data.\*.nextserver | string | | tftp.example.com 10.0.0.5 |
action_result.data.\*.options | string | | option1 option2 |
action_result.data.\*.pxe_lease_time | numeric | | 3600 7200 |
action_result.data.\*.recycle_leases | boolean | | True False |
action_result.data.\*.rir | string | | rir1 rir2 |
action_result.data.\*.rir_organization | string | | org1 org2 |
action_result.data.\*.rir_registration_status | string | | registered unregistered |
action_result.data.\*.same_port_control_discovery_blackout | boolean | | True False |
action_result.data.\*.static_hosts | numeric | | 10 50 100 |
action_result.data.\*.total_hosts | numeric | | 100 500 1000 |
action_result.data.\*.unmanaged | boolean | | True False |
action_result.data.\*.unmanaged_count | numeric | | 10 50 100 |
action_result.data.\*.update_dns_on_lease_renewal | boolean | | True False |
action_result.data.\*.utilization | numeric | | 42 65 78 |
action_result.summary | string | | Successfully retrieved 15 network record(s) Successfully retrieved 3 network record(s) |
summary.total_objects | numeric | | 15 |
summary.total_objects_successful | numeric | | 15 |
action_result.message | string | | |

## action: 'create rpz aaaa rule'

Adds an RPZ rule for AAAA (IPv6) responses to block or redirect DNS queries

Type: **correct** <br>
Read only: **False**

Adds an RPZ rule for AAAA (IPv6) responses to block or redirect DNS queries.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_type** | required | The type of the object for which to create record | string | |
**name** | required | Specify the name of the rule | string | `domain` `ipv6` `host name` |
**rp_zone** | required | The zone to assign the rule to | string | |
**ipv6_address** | required | The IPv6 address of the substitute rule | string | `ipv6` |
**comment** | optional | Comment for this rule | string | |
**additional_parameters** | optional | JSON object containing additional parameters to create response policy zone (disable, extattrs, ttl, use_ttl, view) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"disable": false, "ttl": 3600, "use_ttl": true} |
action_result.parameter.comment | string | | Block malicious domain |
action_result.parameter.ipv6_address | string | `ipv6` | |
action_result.parameter.name | string | `domain` `ipv6` `host name` | test.rpz.block.in |
action_result.parameter.object_type | string | | Domain Name |
action_result.parameter.rp_zone | string | | rpz.block.in |
action_result.data.\*.\_ref | string | `reference id` | record:rpz:aaaa/ZG5zLmJpbmRfYWFhYSQuX2RlZmF1bHQuY29tLnJwei50aHJlYXQsMTEuMi4xMi4xMCw6Og:10.12.2.11.threat.rpz.com/default |
action_result.data.\*.comment | string | | nightly-test-aaaa-sub |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | |
action_result.data.\*.ipv6addr | string | `ipv6` | |
action_result.data.\*.name | string | | fd60:e32:f1b9::2.threat.rpz.com |
action_result.data.\*.rp_zone | string | | threat.rpz.com |
action_result.data.\*.ttl | numeric | | 3600 |
action_result.data.\*.use_ttl | boolean | | False |
action_result.data.\*.view | string | | default |
action_result.data.\*.zone | string | | threat.rpz.com |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create rpz mx rule'

Adds a mail exchange override rule to an RPZ

Type: **correct** <br>
Read only: **False**

Adds a mail exchange override rule to an RPZ.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Specify the name of the rule | string | |
**rp_zone** | required | The zone to assign the rule to | string | |
**mail_exchanger** | required | The mail exchanger name in FQDN format | string | |
**preference** | required | Preference value for the rule (0-65535) | numeric | |
**comment** | optional | Comment for this rule | string | |
**additional_parameters** | optional | JSON object containing additional parameters to create response policy zone (disable, extattrs, ttl, use_ttl, view) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"disable": false, "ttl": 3600, "use_ttl": true} |
action_result.parameter.comment | string | | nightly-test-mx-sub |
action_result.parameter.mail_exchanger | string | | 0.0.0.0 |
action_result.parameter.name | string | | nightly1-test-mx-sub.threat.rpz.com |
action_result.parameter.preference | numeric | | 5 |
action_result.parameter.rp_zone | string | | threat.rpz.com |
action_result.data.\*.\_ref | string | `reference id` | record:rpz:mx/ZG5zLmJpbmRfbXgkLl9kZWZhdWx0LmNvbS5ycHoudGhyZWF0Lm5pZ2h0bHkxLXRlc3QtbXgtc3ViLjAuMC4wLjAuNQ:nightly1-test-mx-sub.threat.rpz.com/default |
action_result.data.\*.comment | string | | nightly-test-mx-sub |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | |
action_result.data.\*.mail_exchanger | string | | 0.0.0.0 |
action_result.data.\*.name | string | | nightly1-test-mx-sub.threat.rpz.com |
action_result.data.\*.preference | numeric | | 5 |
action_result.data.\*.rp_zone | string | | threat.rpz.com |
action_result.data.\*.ttl | numeric | | 3600 |
action_result.data.\*.use_ttl | boolean | | False |
action_result.data.\*.view | string | | default |
action_result.data.\*.zone | string | | threat.rpz.com |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create rpz ptr rule'

Adds a reverse DNS lookup override in RPZ for an IP

Type: **correct** <br>
Read only: **False**

Adds a reverse DNS lookup override in RPZ for an IP.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rp_zone** | required | The zone to assign the rule to | string | |
**ptr_dname** | required | The domain name of the RPZ substitute rule object of the PTR record | string | |
**name** | optional | Specify the name of the rule | string | |
**comment** | optional | Comment for this rule | string | |
**ipv4_address** | optional | The IPv4 address of the substitute rule | string | `ip` |
**ipv6_address** | optional | The IPv6 address of the substitute rule | string | `ipv6` |
**additional_parameters** | optional | JSON object containing additional parameters to create response policy zone (disable, extattrs, ttl, use_ttl, view) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"disable": false, "ttl": 3600, "use_ttl": true} |
action_result.parameter.comment | string | | nightly-test-ptr-sub |
action_result.parameter.ipv4_address | string | `ip` | 90.90.90.9 |
action_result.parameter.ipv6_address | string | `ipv6` | fd60:e32:f1b9::2 |
action_result.parameter.name | string | | nightly1-test-ptr-sub.threat.rpz.com |
action_result.parameter.ptr_dname | string | | abcs1.threat.rpz.com |
action_result.parameter.rp_zone | string | | threat.rpz.com |
action_result.data.\*.\_ref | string | `reference id` | record:rpz:ptr/ZG5zLmJpbmRfcHRyJC5fZGVmYXVsdC5jb20ucnB6LnRocmVhdC5hcnBhLmlwNi5mLmQuNi4wLjAuZS4zLjIuZi4xLmIuOS4wLjAuMC4wLjAuMC4wLjAuMC4wLjAuMC4wLjAuMC4wLjAuMC4wLjIuYWJjczEudGhyZWF0LnJwei5jb20:2.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.9.b.1.f.2.3.e.0.0.6.d.f.ip6.arpa.threat.rpz.com/default |
action_result.data.\*.comment | string | | nightly-test-ptr-sub |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | |
action_result.data.\*.ipv4addr | string | `ip` | 90.90.90.9 |
action_result.data.\*.ipv6addr | string | `ipv6` | fd60:e32:f1b9::2 |
action_result.data.\*.name | string | | 2.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.0.9.b.1.f.2.3.e.0.0.6.d.f.ip6.arpa.threat.rpz.com 90.90.90.10.in-addr.arpa.test.example-crest.com |
action_result.data.\*.ptrdname | string | | abcs1.threat.rpz.com |
action_result.data.\*.rp_zone | string | | threat.rpz.com |
action_result.data.\*.ttl | numeric | | 3600 |
action_result.data.\*.use_ttl | boolean | | False |
action_result.data.\*.view | string | | default |
action_result.data.\*.zone | string | | threat.rpz.com |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create rpz txt rule'

Adds a TXT record rule in RPZ to associate text data with a DNS response

Type: **correct** <br>
Read only: **False**

Adds a TXT record rule in RPZ to associate text data with a DNS response.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rp_zone** | required | The zone to assign the rule to | string | |
**name** | required | Specify the name of the rule | string | |
**text** | required | Text associated with the record | string | |
**comment** | optional | Comment for this rule | string | |
**additional_parameters** | optional | JSON object containing additional parameters to create response policy zone (disable, extattrs, ttl, use_ttl, view) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | |
action_result.parameter.comment | string | | |
action_result.parameter.name | string | | |
action_result.parameter.rp_zone | string | | |
action_result.parameter.text | string | | |
action_result.data.\*.\_ref | string | | record:rpz:txt/ZG5zLmJpbmRfdHh0JC5fZGVmYXVsdC5jb20ucnB6LnRocmVhdC5uaWdodGx5LXRlc3QtbXgtc3ViLiJ0ZXN0MSI:nightly-test-mx-sub.threat.rpz.com/default |
action_result.data.\*.comment | string | | nightly-test-mx-sub |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | |
action_result.data.\*.name | string | | nightly-test-mx-sub.threat.rpz.com |
action_result.data.\*.rp_zone | string | | threat.rpz.com |
action_result.data.\*.text | string | | Threat Zone |
action_result.data.\*.ttl | numeric | | 3600 |
action_result.data.\*.use_ttl | boolean | | False |
action_result.data.\*.view | string | | default |
action_result.data.\*.zone | string | | threat.rpz.com |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create host record'

Create a host record in Infoblox NIOS

Type: **generic** <br>
Read only: **False**

This action creates a host record in Infoblox NIOS with the specified name and IP addresses. You can provide IPv4 and/or IPv6 addresses, along with optional parameters such as view, comment, and extended attributes.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | The hostname to create (FQDN) | string | `fqdn` |
**ipv4_addresses** | optional | JSON array of IPv4 address objects. Each object must contain 'ipv4addr' and can optionally include 'mac', 'configure_for_dhcp', etc. Example: [{"ipv4addr":"192.168.1.10","mac":"00:11:22:33:44:55"}] | string | |
**ipv6_addresses** | optional | JSON array of IPv6 address objects. Each object must contain 'ipv6addr' and can optionally include 'duid', 'configure_for_dhcp', etc. Example: [{"ipv6addr":"2001:db8::1"}] | string | |
**view** | optional | The DNS view in which to create the host record | string | |
**comment** | optional | Comment for the host record | string | |
**configure_for_dns** | optional | Configure the host record for DNS | boolean | |
**aliases** | optional | Comma-separated list of aliases for the host record | string | |
**extended_attributes** | optional | Extended attributes in key=value format, separated by commas. Example: Site=Boston,Department=IT | string | |
**additional_parameters** | optional | Additional parameters in JSON format | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"ttl":3600} |
action_result.parameter.aliases | string | | alias1.example.com,alias2.example.com |
action_result.parameter.comment | string | | Creating the host |
action_result.parameter.configure_for_dns | boolean | | True |
action_result.parameter.extended_attributes | string | | Site=Boston,Department=IT |
action_result.parameter.ipv4_addresses | string | | [{"ipv4addr":"192.168.1.10"}] |
action_result.parameter.ipv6_addresses | string | | [{"ipv6addr":"2001:db8::1"}] |
action_result.parameter.name | string | `fqdn` | host1.example.com |
action_result.parameter.view | string | | default |
action_result.data.\*.\_ref | string | | record:host/ZG5zLmhvc3QkLl9kZWZhdWx0LmNvbS5leGFtcGxlLmhvc3Qx:host1.example.com/default |
action_result.data.\*.comment | string | | Created the host |
action_result.data.\*.configure_for_dns | boolean | | True |
action_result.data.\*.disable | boolean | | False |
action_result.data.\*.extattrs | string | | {"Site":{"value":"Boston"},"Department":{"value":"IT"}} |
action_result.data.\*.ipv4addrs | string | | [{"ipv4addr":"192.168.1.10","configure_for_dhcp":false}] |
action_result.data.\*.ipv6addrs | string | | [{"ipv6addr":"2001:db8::1","configure_for_dhcp":false}] |
action_result.data.\*.name | string | `domain name` | host1.example.com |
action_result.data.\*.network_view | string | | default |
action_result.data.\*.view | string | | default |
action_result.data.\*.zone | string | | example.com |
action_result.summary | string | | |
action_result.summary.name | string | | host1.example.com |
action_result.summary.reference_id | string | | record:host/ZG5zLmhvc3QkLl9kZWZhdWx0LmNvbS5leGFtcGxlLmhvc3Qx:host1.example.com/default |
action_result.summary.view | string | | default |
action_result.message | string | | Successfully created host record with reference ID: record:host/ZG5zLmhvc3QkLl9kZWZhdWx0LmNvbS5leGFtcGxlLmhvc3Qx:host1.example.com/default |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete rpz rule'

Delete a Response Policy Zone (RPZ) rule

Type: **correct** <br>
Read only: **False**

This action deletes an RPZ rule using its reference ID. The reference ID should be in the format provided by the Infoblox NIOS API.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ref** | required | Reference ID of the RPZ rule to delete | string | `reference id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ref | string | `reference id` | record:rpz:cname:ipaddress/ZG5zLmJpbmRfY25hbWUkLl9kZWZhdWx0LmNvbS5ycHoudGhyZWF0LnJwei1pcC4xMC4yLjIuMTIuMzI:10.2.2.12.threat.rpz.com/default |
action_result.data.\*.reference_id | string | | |
action_result.summary | string | | |
action_result.message | string | | RPZ rule deleted successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete response policy zone'

Removes an existing Response Policy Zone from Infoblox

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**reference_id** | required | The reference ID of the response policy zone | string | `rpz` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.reference_id | string | `rpz` | zone_rp/ZG5zLnpvbmUkLl9kZWZhdWx0LmlwMi50aHJlYXQuZG5z:dns.threat.ip2/default |
action_result.data.\*.reference_id | string | `rpz` | zone_rp/ZG5zLnpvbmUkLl9kZWZhdWx0LmlwMi50aHJlYXQuZG5z:dns.threat.ip2/default |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'create response policy zone'

Creates a new Response Policy Zone (RPZ) to define custom DNS responses

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**fqdn** | required | The name of this DNS zone in FQDN format | string | `fqdn` |
**substitute_name** | optional | The alternative name of the redirect target is a substitute response policy zone | string | |
**comment** | optional | Comment for the zone | string | |
**rpz_policy** | optional | The override policy of the response policy zone | string | |
**rpz_severity** | optional | The severity of the response policy zone | string | |
**rpz_type** | optional | The type of the RPZ | string | |
**fireeye_rule_mapping** | optional | Rules to map fireeye alerts | string | |
**additional_parameters** | optional | JSON object containing additional parameters to create response policy zone | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.additional_parameters | string | | {"disable": false, "view": "default", "network_view": "default"} |
action_result.parameter.comment | string | | Security RPZ for malware domains |
action_result.parameter.fireeye_rule_mapping | string | | {"malware": "block", "phishing": "redirect"} |
action_result.parameter.fqdn | string | `fqdn` | rpz.security.local |
action_result.parameter.rpz_policy | string | | GIVEN NXDOMAIN SUBSTITUTE |
action_result.parameter.rpz_severity | string | | MAJOR CRITICAL WARNING |
action_result.parameter.rpz_type | string | | LOCAL FEED FIREEYE |
action_result.parameter.substitute_name | string | | walled-garden.example.com |
action_result.data.\*.\_ref | string | `rpz` | zone_rp/ZG5zLnpvbmUkLl9kZWZhdWx0LmNvbS50aHJlYXQucnB6:threat.rpz.com/default |
action_result.data.\*.address | string | | 10.0.0.1 |
action_result.data.\*.comment | string | | Security RPZ for malware domains Threat intelligence feed zone Custom blocking zone for phishing |
action_result.data.\*.disable | boolean | | False True |
action_result.data.\*.display_domain | string | | rpz.security.local |
action_result.data.\*.dns_soa_email | string | | admin@security.local |
action_result.data.\*.extattrs | string | | {"Location": {"value": "DataCenter1"}, "Owner": {"value": "Security"}} |
action_result.data.\*.external_primaries | string | | 8.8.8.8 |
action_result.data.\*.external_secondaries | string | | 8.8.4.4 |
action_result.data.\*.fireeye_rule_mapping | string | | {"malware": "block", "phishing": "redirect"} {"apt": "nxdomain", "botnet": "substitute"} |
action_result.data.\*.fqdn | string | `fqdn` | rpz.security.local |
action_result.data.\*.grid_primary | string | | infoblox-primary.local |
action_result.data.\*.grid_secondaries | string | | dns-backup.threat.zone |
action_result.data.\*.locked | boolean | | False True |
action_result.data.\*.locked_by | string | | admin security_team automated_system |
action_result.data.\*.log_rpz | boolean | | True False |
action_result.data.\*.mask_prefix | numeric | | 8 |
action_result.data.\*.member_soa_mnames | string | | infoblox-primary.local |
action_result.data.\*.member_soa_serials | string | | 2024082901 |
action_result.data.\*.network_view | string | | default |
action_result.data.\*.ns_group | string | | default |
action_result.data.\*.parent | string | | security.local |
action_result.data.\*.prefix | string | | rpz security threat |
action_result.data.\*.primary_type | string | | GRID EXTERNAL NONE |
action_result.data.\*.record_name_policy | string | | default security_policy threat_policy |
action_result.data.\*.rpz_drop_ip_rule_enabled | boolean | | False True |
action_result.data.\*.rpz_drop_ip_rule_min_prefix_length_ipv4 | numeric | | 24 |
action_result.data.\*.rpz_drop_ip_rule_min_prefix_length_ipv6 | numeric | | 64 |
action_result.data.\*.rpz_policy | string | | GIVEN NXDOMAIN SUBSTITUTE |
action_result.data.\*.rpz_priority | numeric | | 100 |
action_result.data.\*.rpz_priority_end | numeric | | 150 |
action_result.data.\*.rpz_severity | string | | MAJOR CRITICAL WARNING |
action_result.data.\*.rpz_type | string | | LOCAL FEED FIREEYE |
action_result.data.\*.set_soa_serial_number | boolean | | |
action_result.data.\*.soa_default_ttl | numeric | | 3600 |
action_result.data.\*.soa_expire | numeric | | 604800 |
action_result.data.\*.soa_negative_ttl | numeric | | |
action_result.data.\*.soa_refresh | numeric | | |
action_result.data.\*.soa_retry | numeric | | |
action_result.data.\*.soa_serial_number | numeric | | |
action_result.data.\*.substitute_name | string | | blocked.domain.com |
action_result.data.\*.use_external_primary | boolean | | False True |
action_result.data.\*.use_grid_zone_timer | boolean | | |
action_result.data.\*.use_log_rpz | boolean | | True False |
action_result.data.\*.use_record_name_policy | boolean | | False True |
action_result.data.\*.use_rpz_drop_ip_rule | boolean | | False True |
action_result.data.\*.view | string | | default internal external |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get response policy zone'

Retrieves Response Policy Zone(s) based on specified criteria

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**fqdn** | optional | The fully qualified domain name of the response policy zone to retrieve | string | `fqdn` |
**view** | optional | Filter by DNS view name | string | |
**comment** | optional | Filter by comment text | string | |
**max_results** | optional | Maximum number of results to return | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | |
action_result.parameter.fqdn | string | `fqdn` | |
action_result.parameter.max_results | numeric | | |
action_result.parameter.view | string | | |
action_result.data.\*.\_ref | string | `reference id` | zone_rp/ZG5zLnpvbmVfcnAkLm5ldC5pbmZvYmxveC5kbnMudGhyZWF0LmlwMQ:dns.threat.ip1/default |
action_result.data.\*.address | string | | 10.0.0.1 |
action_result.data.\*.comment | string | | Malicious domain blocking zone |
action_result.data.\*.disable | boolean | | True False |
action_result.data.\*.display_domain | string | | dns.threat.ip1 |
action_result.data.\*.dns_soa_email | string | | admin.example.com |
action_result.data.\*.extattrs | string | | {"CreatedBy": {"value": "admin"}} |
action_result.data.\*.external_primaries | string | | [{"address": "10.1.1.1", "name": "external-primary"}] |
action_result.data.\*.external_secondaries | string | | [{"address": "10.1.1.2", "name": "external-secondary"}] |
action_result.data.\*.fireeye_rule_mapping | string | | rule1 |
action_result.data.\*.fqdn | string | `fqdn` | dns.threat.ip1 |
action_result.data.\*.grid_primary | string | | {"name": "infoblox.localdomain"} |
action_result.data.\*.grid_secondaries | string | | [{"name": "secondary.infoblox.localdomain"}] |
action_result.data.\*.locked | boolean | | True False |
action_result.data.\*.locked_by | string | | admin |
action_result.data.\*.log_rpz | boolean | | True False |
action_result.data.\*.mask_prefix | numeric | | 24 |
action_result.data.\*.member_soa_mnames | string | | ["ns1.example.com"] |
action_result.data.\*.member_soa_serials | string | | [12345678] |
action_result.data.\*.network_view | string | | |
action_result.data.\*.ns_group | string | | default-ns-group |
action_result.data.\*.parent | string | | example.com |
action_result.data.\*.prefix | string | | |
action_result.data.\*.primary_type | string | | |
action_result.data.\*.record_name_policy | string | | |
action_result.data.\*.rpz_drop_ip_rule_enabled | boolean | | True False |
action_result.data.\*.rpz_drop_ip_rule_min_prefix_length_ipv4 | numeric | | 24 |
action_result.data.\*.rpz_drop_ip_rule_min_prefix_length_ipv6 | numeric | | 64 |
action_result.data.\*.rpz_policy | string | | GIVEN PASSTHRU SUBSTITUTE NXDOMAIN NODATA DISABLED |
action_result.data.\*.rpz_priority | numeric | | 1 |
action_result.data.\*.rpz_priority_end | numeric | | 999 |
action_result.data.\*.rpz_severity | string | | CRITICAL MAJOR WARNING INFORMATIONAL |
action_result.data.\*.rpz_type | string | | FEED FIREEYE LOCAL |
action_result.data.\*.set_soa_serial_number | boolean | | |
action_result.data.\*.soa_default_ttl | numeric | | 3600 |
action_result.data.\*.soa_expire | numeric | | 2419200 |
action_result.data.\*.soa_negative_ttl | numeric | | 900 |
action_result.data.\*.soa_refresh | numeric | | 10800 |
action_result.data.\*.soa_retry | numeric | | 3600 |
action_result.data.\*.soa_serial_number | numeric | | |
action_result.data.\*.substitute_name | string | | dns.threat.ip1 |
action_result.data.\*.use_external_primary | boolean | | True False |
action_result.data.\*.use_grid_zone_timer | boolean | | |
action_result.data.\*.use_log_rpz | boolean | | True False |
action_result.data.\*.use_record_name_policy | boolean | | True False |
action_result.data.\*.use_rpz_drop_ip_rule | boolean | | True False |
action_result.data.\*.view | string | | default |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'search rpz rule'

Search for RPZ rules in Infoblox NIOS

Type: **investigate** <br>
Read only: **True**

This action allows you to search for Response Policy Zone (RPZ) rules in Infoblox NIOS. You can filter by name, view, zone, canonical, or comment.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_type** | required | The Infoblox object type | string | |
**rule_name** | optional | The full rule name (usually the rule name followed by its zone.(e.g. name.domain.com) | string | `domain name` |
**output_fields** | optional | The comma-separated fields to include in the returned object (e.g., address, comment, etc.) | string | |
**limit** | optional | Maximum number of objects to be returned | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.limit | numeric | | 100 |
action_result.parameter.object_type | string | | record:rpz:cname |
action_result.parameter.output_fields | string | | name,view,canonical |
action_result.parameter.rule_name | string | `domain name` | test.threat.rpz.com |
action_result.data.\*.\_ref | string | `reference id` | record:rpz:cname/ZG5zLmJpbmRfY25hbWUkLl9kZWZhdWx0LmNvbS5leGFtcGxlLnRlc3QtYmxvY2tsaXN0LjE5LjIuMi4xMA:10.2.2.19.test-blocklist.example.com/default |
action_result.data.\*.canonical | string | | * |
action_result.data.\*.name | string | `domain name` | 10.2.2.19.test-blocklist.example.com |
action_result.data.\*.view | string | | default |
action_result.summary | string | | |
action_result.summary.total_rules_found | numeric | | 1 |
action_result.message | string | | Successfully retrieved 1 RPZ rule(s) |
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
