# Cisco ESA

Publisher: Splunk <br>
Connector Version: 3.0.2 <br>
Product Vendor: Cisco <br>
Product Name: Cisco ESA <br>
Minimum Product Version: 5.4.0

This app supports investigation on the Cisco Email Security Appliance (ESA) device

### Configuration variables

This table lists the configuration variables required to operate Cisco ESA. These variables are specified when configuring a Cisco ESA asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | URL (e.g. https://10.10.10.10:6443) |
**verify_server_cert** | optional | boolean | Verify server certificate |
**username** | required | string | Username |
**password** | required | password | Password |
**ssh_username** | optional | string | SSH Username (Used for dictionary related actions) |
**ssh_password** | optional | password | SSH Password (Used for dictionary related actions) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate credentials provided for connectivity <br>
[decode url](#action-decode-url) - Process Cisco encoded URL <br>
[get report](#action-get-report) - Retrieve statistical reports from ESA <br>
[list dictionary items](#action-list-dictionary-items) - List all entries of an ESA dictionary <br>
[add dictionary item](#action-add-dictionary-item) - Add an entry to an ESA dictionary <br>
[remove dictionary item](#action-remove-dictionary-item) - Remove an entry from an ESA dictionary

## action: 'test connectivity'

Validate credentials provided for connectivity

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'decode url'

Process Cisco encoded URL

Type: **investigate** <br>
Read only: **True**

Parse and decode URL from "secure-web.cisco.com" to get the redirected URL.<ul><li>It will accept the entire URL:<p><code>http://secure-web.cisco.com/{random_chars}/https%3A%2F%2Fmy.phantom.us%2F4.1%2Fdocs%2Fapp_reference%2Fphantom_ciscoesa</code></li><li>Everything except the protocol:<p><code>secure-web.cisco.com/{random_chars}/https%3A%2F%2Fmy.phantom.us%2F4.1%2Fdocs%2Fapp_reference%2Fphantom_ciscoesa</code></li><li>Or just the quoted section:<p><code>https%3A%2F%2Fmy.phantom.us%2F4.1%2Fdocs%2Fapp_reference%2Fphantom_ciscoesa</code></li></ul>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**encoded_url** | required | Encoded URL to process | string | `url` `encoded url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.encoded_url | string | `url` `encoded url` | https://www.w3schools.com/tags/ref_urlencode.ASP#:~:text=URL%20Encoding%20(Percent%20Encoding)&text=URLs%20can%20only%20be%20sent,followed%20by%20two%20hexadecimal%20digits. |
action_result.data.\*.decoded_url | string | `url` | https://www.w3schools.com/tags/ref_urlencode.ASP#:~:text=URL Encoding (Percent Encoding)&text=URLs can only be sent,followed by two hexadecimal digits. |
action_result.summary | string | | |
action_result.message | string | | Decoded entire URL Parsed from secure-web.cisco.com URL and decoded |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get report'

Retrieve statistical reports from ESA

Type: **investigate** <br>
Read only: **True**

This action is used to query "Query-based Reports" which counts various events in your appliance against a user-specified entity such as IP address, domain name, etc. for a specified duration.<br>If <b>start_time</b> and <b>end_time</b> are not given, then the report will be queried for the last 250 days.<br>If either <b>start_time</b> or <b>end_time</b> is provided, then the report will be queried for 250 days relative to the given parameter.<br>Following is the mapping of the report title and its corresponding entity that can be provided to filter reports:<table><tbody><tr class='plain'><th>Report Title</th><th>Entity Value</th></tr><tr><td>Internal Users</td><td>Email ID of the internal user (e.g. user@example.com)</td></tr><tr><td>Incoming Mail: Domains</td><td>Domain name (e.g. abc.com)</td></tr><tr><td>Incoming Mail: IP Addresses</td><td>IPv4 or IPv6 address</td></tr><tr><td>Incoming Mail: Network Owners</td><td>Name of the network owner (e.g. Xyz Corporation)</td></tr><tr><td>Outgoing Senders: Domains</td><td>Domain name (e.g. abc.com)</td></tr><tr><td>Outgoing Senders: IP Addresses</td><td>IPv4 or IPv6 address</td></tr><tr><td>Outgoing Destinations</td><td>Domain name (e.g. abc.com)</td></tr><tr><td>Outgoing Content Filters</td><td>Name of the outgoing Content Filter</td></tr><tr><td>Virus Types</td><td>Name of virus</td></tr><tr><td>Inbound SMTP Authentication</td><td>Domain name (e.g. abc.com)</td></tr><tr><td>Data Loss Prevention (DLP) Outgoing Policy</td><td>Name of the DLP policy</td></tr></tbody></table><br>The action supports limiting the number of items returned using the <b>limit</b> parameter. If the <b>limit</b> parameter is 0, then the action will fetch no data for the selected report(s). If the limit is not specified, the action will fetch by default 10 items for all specified reports. For a particular report, if the limit specified is greater than the available data, the action will fetch all data for that report.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**report_title** | required | Report Title | string | `ciscoesa report title` |
**filter_by** | optional | Entity to filter the results | string | |
**filter_value** | optional | Entity value to filter the results | string | |
**starts_with** | optional | Retrieve items starting with specified filter value | boolean | |
**start_time** | optional | Start time (YYYY-MM-DDTHH:00) | string | |
**end_time** | optional | End time (YYYY-MM-DDTHH:00) | string | |
**limit** | optional | Maximum number of items to retrieve | numeric | |
**offset** | optional | Starting index of overall result set | numeric | |
**order_by** | optional | The attribute by which to order the data in the response | string | |
**order_dir** | optional | Sort direction of results | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.end_time | string | | 2001-12-12T11:00 |
action_result.parameter.filter_by | string | | ip_address |
action_result.parameter.filter_value | string | | Test Policy |
action_result.parameter.limit | numeric | | 11 |
action_result.parameter.offset | numeric | | 0 |
action_result.parameter.order_by | string | | bulk_mail |
action_result.parameter.order_dir | string | | asc |
action_result.parameter.report_title | string | `ciscoesa report title` | DLP Outgoing Policy |
action_result.parameter.start_time | string | | 2001-11-12T11:00 |
action_result.parameter.starts_with | boolean | | Test |
action_result.data.\*.data.blocked_dmarc.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.blocked_dmarc.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.blocked_invalid_recipient.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.blocked_invalid_recipient.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.blocked_reputation.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.blocked_reputation.resultSet.\*.value | numeric | | 42 |
action_result.data.\*.data.blocked_sdr.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.blocked_sdr.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.bulk_mail.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.bulk_mail.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.detected_amp.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.detected_amp.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.detected_spam.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.detected_spam.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.detected_virus.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.detected_virus.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.dns_verified.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.dns_verified.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.last_sender_group.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.last_sender_group.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.last_sender_group_name.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.last_sender_group_name.resultSet.\*.value | string | | UNKNOWNLIST |
action_result.data.\*.data.marketing_mail.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.marketing_mail.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.auth_disallow.\* | string | | |
action_result.data.\*.data.resultSet.auth_fail.\* | string | | |
action_result.data.\*.data.resultSet.auth_success.\* | string | | |
action_result.data.\*.data.resultSet.blocked_dmarc.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.blocked_dmarc.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.blocked_invalid_recipient.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.blocked_invalid_recipient.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.blocked_invalid_recipient.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.blocked_invalid_recipient.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.blocked_invalid_recipient.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.blocked_reputation.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.blocked_reputation.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.blocked_reputation.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.blocked_reputation.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.blocked_reputation.\*.value | numeric | | 42 |
action_result.data.\*.data.resultSet.blocked_reputation.\*.value | numeric | | 24 |
action_result.data.\*.data.resultSet.blocked_reputation.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.blocked_sdr.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.blocked_sdr.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.blocked_sdr.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.blocked_sdr.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.blocked_sdr.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.bulk_mail.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.bulk_mail.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.bulk_mail.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.bulk_mail.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.bulk_mail.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.cert_fail.\* | string | | |
action_result.data.\*.data.resultSet.cert_fallback_fail.\* | string | | |
action_result.data.\*.data.resultSet.cert_fallback_success.\* | string | | |
action_result.data.\*.data.resultSet.cert_success.\* | string | | |
action_result.data.\*.data.resultSet.conn_plain.\* | string | | |
action_result.data.\*.data.resultSet.conn_tls_fail.\* | string | | |
action_result.data.\*.data.resultSet.conn_tls_opt_fail.\* | string | | |
action_result.data.\*.data.resultSet.conn_tls_opt_success.\* | string | | |
action_result.data.\*.data.resultSet.conn_tls_success.\* | string | | |
action_result.data.\*.data.resultSet.conn_tls_total.\* | string | | |
action_result.data.\*.data.resultSet.detected_amp.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.detected_amp.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.detected_amp.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.detected_amp.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.detected_amp.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.detected_spam.\* | string | | |
action_result.data.\*.data.resultSet.detected_spam.\* | string | | |
action_result.data.\*.data.resultSet.detected_spam.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.detected_spam.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.detected_spam.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.detected_spam.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.detected_spam.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.detected_virus.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.detected_virus.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.detected_virus.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.detected_virus.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.detected_virus.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.dns_verified.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.dns_verified.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.dns_verified.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.dns_verified.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.dns_verified.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.encrypted_tls.\* | string | | |
action_result.data.\*.data.resultSet.incoming_bulk_mail.\* | string | | |
action_result.data.\*.data.resultSet.incoming_bulk_mail.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_bulk_mail.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_detected_amp.\* | string | | |
action_result.data.\*.data.resultSet.incoming_detected_amp.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_detected_amp.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_detected_content_filter.\* | string | | |
action_result.data.\*.data.resultSet.incoming_detected_content_filter.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_detected_content_filter.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_detected_ims_spam_increment_over_case.\* | string | | |
action_result.data.\*.data.resultSet.incoming_detected_ims_spam_increment_over_case.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_detected_ims_spam_increment_over_case.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_detected_spam.\* | string | | |
action_result.data.\*.data.resultSet.incoming_detected_spam.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_detected_spam.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_detected_virus.\* | string | | |
action_result.data.\*.data.resultSet.incoming_detected_virus.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_detected_virus.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_graymail.\* | string | | |
action_result.data.\*.data.resultSet.incoming_graymail.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_graymail.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_marketing_mail.\* | string | | |
action_result.data.\*.data.resultSet.incoming_marketing_mail.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_marketing_mail.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_social_mail.\* | string | | |
action_result.data.\*.data.resultSet.incoming_social_mail.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_social_mail.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_threat_content_filter.\* | string | | |
action_result.data.\*.data.resultSet.incoming_threat_content_filter.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.incoming_threat_content_filter.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_total_clean_recipients.\* | string | | |
action_result.data.\*.data.resultSet.incoming_total_clean_recipients.\*.count | numeric | | 2 |
action_result.data.\*.data.resultSet.incoming_total_clean_recipients.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.incoming_total_recipients.\* | string | | |
action_result.data.\*.data.resultSet.incoming_total_recipients.\*.count | numeric | | 2 |
action_result.data.\*.data.resultSet.incoming_total_recipients.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.last_sender_group.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.last_sender_group.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.last_sender_group.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.last_sender_group.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.last_sender_group.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.last_sender_group_name.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.last_sender_group_name.\*.count.value | string | | UNKNOWNLIST |
action_result.data.\*.data.resultSet.last_sender_group_name.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.last_sender_group_name.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.last_sender_group_name.\*.value | string | | UNKNOWNLIST |
action_result.data.\*.data.resultSet.marketing_mail.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.marketing_mail.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.marketing_mail.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.marketing_mail.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.marketing_mail.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.noauth.\* | string | | |
action_result.data.\*.data.resultSet.outgoing_detected_amp.\* | string | | |
action_result.data.\*.data.resultSet.outgoing_detected_amp.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.outgoing_detected_amp.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.outgoing_detected_content_filter.\* | string | | |
action_result.data.\*.data.resultSet.outgoing_detected_content_filter.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.outgoing_detected_content_filter.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.outgoing_detected_ims_spam_increment_over_case.\* | string | | |
action_result.data.\*.data.resultSet.outgoing_detected_ims_spam_increment_over_case.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.outgoing_detected_ims_spam_increment_over_case.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.outgoing_detected_spam.\* | string | | |
action_result.data.\*.data.resultSet.outgoing_detected_spam.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.outgoing_detected_spam.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.outgoing_detected_virus.\* | string | | |
action_result.data.\*.data.resultSet.outgoing_detected_virus.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.outgoing_detected_virus.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.outgoing_threat_content_filter.\* | string | | |
action_result.data.\*.data.resultSet.outgoing_threat_content_filter.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.outgoing_threat_content_filter.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.outgoing_total_clean_recipients.\* | string | | |
action_result.data.\*.data.resultSet.outgoing_total_clean_recipients.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.outgoing_total_clean_recipients.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.outgoing_total_recipients.\* | string | | |
action_result.data.\*.data.resultSet.outgoing_total_recipients.\*.count | numeric | | 0 |
action_result.data.\*.data.resultSet.outgoing_total_recipients.\*.recipient | string | | test@user.com |
action_result.data.\*.data.resultSet.sbrs_score.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.sbrs_score.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.sbrs_score.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.sbrs_score.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.sbrs_score.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.social_mail.\* | string | | |
action_result.data.\*.data.resultSet.social_mail.\* | string | | |
action_result.data.\*.data.resultSet.social_mail.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.social_mail.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.social_mail.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.social_mail.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.social_mail.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.threat_content_filter.\* | string | | |
action_result.data.\*.data.resultSet.threat_content_filter.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.threat_content_filter.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.threat_content_filter.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.total.\* | string | | |
action_result.data.\*.data.resultSet.total_accepted_connections.\* | string | | |
action_result.data.\*.data.resultSet.total_clean_recipients.\* | string | | |
action_result.data.\*.data.resultSet.total_clean_recipients.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.total_clean_recipients.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.total_clean_recipients.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.total_clean_recipients.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.total_clean_recipients.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.total_graymail_recipients.\* | string | | |
action_result.data.\*.data.resultSet.total_graymail_recipients.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.total_graymail_recipients.\*.count.value | numeric | | 0 |
action_result.data.\*.data.resultSet.total_graymail_recipients.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.total_graymail_recipients.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.total_graymail_recipients.\*.value | numeric | | 0 |
action_result.data.\*.data.resultSet.total_recipients.\* | string | | |
action_result.data.\*.data.resultSet.total_recipients.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.total_recipients.\*.count.value | numeric | | 42 |
action_result.data.\*.data.resultSet.total_recipients.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.total_recipients.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.total_recipients.\*.value | numeric | | 42 |
action_result.data.\*.data.resultSet.total_rejected_connections.\* | string | | |
action_result.data.\*.data.resultSet.total_threat_recipients.\* | string | | |
action_result.data.\*.data.resultSet.total_threat_recipients.\*.count.key | string | | unknown domain |
action_result.data.\*.data.resultSet.total_threat_recipients.\*.count.value | numeric | | 42 |
action_result.data.\*.data.resultSet.total_threat_recipients.\*.key | string | | unknown domain |
action_result.data.\*.data.resultSet.total_threat_recipients.\*.recipient | string | | 10.1.16.99 |
action_result.data.\*.data.resultSet.total_threat_recipients.\*.value | numeric | | 42 |
action_result.data.\*.data.resultSet.total_throttled_recipients.\* | string | | |
action_result.data.\*.data.sbrs_score.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.sbrs_score.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.social_mail.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.social_mail.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.threat_content_filter.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.threat_content_filter.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.total_clean_recipients.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.total_clean_recipients.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.total_graymail_recipients.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.total_graymail_recipients.resultSet.\*.value | numeric | | 0 |
action_result.data.\*.data.total_recipients.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.total_recipients.resultSet.\*.value | numeric | | 42 |
action_result.data.\*.data.total_threat_recipients.resultSet.\*.key | string | | unknown domain |
action_result.data.\*.data.total_threat_recipients.resultSet.\*.value | numeric | | 42 |
action_result.data.\*.data.type | string | | mail_sender_domain_detail |
action_result.data.\*.mail_incoming_domain_detail.data.blocked_reputation.\*.count | numeric | | 6702 |
action_result.data.\*.mail_incoming_domain_detail.data.blocked_reputation.\*.recipient | string | | unknown domain |
action_result.data.\*.mail_incoming_domain_detail.data.total_recipients.\*.count | numeric | | 6702 |
action_result.data.\*.mail_incoming_domain_detail.data.total_recipients.\*.recipient | string | | unknown domain |
action_result.data.\*.mail_incoming_domain_detail.data.total_rejected_connections.\*.count | numeric | | 2234 |
action_result.data.\*.mail_incoming_domain_detail.data.total_rejected_connections.\*.recipient | string | | unknown domain |
action_result.data.\*.mail_incoming_domain_detail.data.total_threat_recipients.\*.count | numeric | | 6702 |
action_result.data.\*.mail_incoming_domain_detail.data.total_threat_recipients.\*.recipient | string | | unknown domain |
action_result.data.\*.mail_incoming_domain_detail.uri | string | | /api/v1.0/stats/mail_incoming_domain_detail?duration=2021-07-30T12%3A00%2B00%3A00%2F2022-04-05T12%3A00%2B00%3A00&max=10 |
action_result.data.\*.mail_users_detail.uri | string | | /api/v1.0/stats/mail_users_detail?duration=2021-07-31T10%3A00%2B00%3A00%2F2022-04-06T10%3A00%2B00%3A00&max=10 |
action_result.data.\*.meta.totalCount | numeric | | -1 |
action_result.summary | string | | |
action_result.message | string | | Report queried successfully |
summary.total_objects | numeric | | 12 |
summary.total_objects_successful | numeric | | 34 |

## action: 'list dictionary items'

List all entries of an ESA dictionary

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of dictionary to list | string | `ciscoesa dictionary name` |
**cluster_mode** | optional | Enable machine mode as cluster on ESA | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.cluster_mode | boolean | | True False |
action_result.parameter.name | string | `ciscoesa dictionary name` | Mail_To |
action_result.data.\*.value | string | `ciscoesa item value` | test@user.com |
action_result.data.\*.weight | string | | 1 |
action_result.summary.total_items | numeric | | 36 |
action_result.message | string | | Successfully listed all entries of dictionary |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add dictionary item'

Add an entry to an ESA dictionary

Type: **contain** <br>
Read only: **False**

Per the documentation, the action will handle escaping special regex character prior to adding to the dictionary.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of dictionary to add an item to | string | `ciscoesa dictionary name` |
**value** | required | Value of entry to add to dictionary | string | `ciscoesa item value` |
**commit_message** | required | Commit message to add the item to the dictionary on the server at the end of this action | string | |
**cluster_mode** | optional | Enable machine mode as cluster on ESA | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.cluster_mode | boolean | | True False |
action_result.parameter.commit_message | string | | This is a test message |
action_result.parameter.name | string | `ciscoesa dictionary name` | test_dict |
action_result.parameter.value | string | `ciscoesa item value` | test_value |
action_result.data.\*.message | string | | Successfully added entry to dictionary |
action_result.summary.status | string | | Successfully added entry to dictionary |
action_result.message | string | | Successfully added entry to dictionary |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove dictionary item'

Remove an entry from an ESA dictionary

Type: **correct** <br>
Read only: **False**

Per the documentation, the action will handle escaping special regex character prior to removing from the dictionary.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | Name of dictionary to remove an item from | string | `ciscoesa dictionary name` |
**value** | required | Value of entry to remove from dictionary | string | `ciscoesa item value` |
**commit_message** | required | Commit message to remove the item from the dictionary on the server at the end of this action | string | |
**cluster_mode** | optional | Enable machine mode as cluster on ESA | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.cluster_mode | boolean | | True False |
action_result.parameter.commit_message | string | | This is a test message |
action_result.parameter.name | string | `ciscoesa dictionary name` | test_dict |
action_result.parameter.value | string | `ciscoesa item value` | test_value |
action_result.data.\*.message | string | | Successfully removed entry from dictionary |
action_result.summary.status | string | | Successfully removed entry from dictionary |
action_result.message | string | | Successfully removed entry from dictionary |
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
