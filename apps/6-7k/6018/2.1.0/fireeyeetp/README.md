# Fireeye ETP

Publisher: Robert Drouin \
Connector Version: 2.1.0 \
Product Vendor: Fireeye \
Product Name: Fireeye Email Threat Prevention \
Minimum Product Version: 5.1.0

Cloud Edition provides RESTful APIs for custom integration. The APIs are provided for Advanced Threats, Email Trace, and Quarantine functionalities

### Configuration variables

This table lists the configuration variables required to operate Fireeye ETP. These variables are specified when configuring a Fireeye Email Threat Prevention asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | The URL for your ETP instance |
**api_key** | optional | password | API key (leave blank if using OAuth) |
**client_id** | optional | string | Auth Client ID |
**client_secret** | optional | password | Auth Secret |
**auth_scopes** | optional | string | Auth scopes (e.g. 'etp.conf.ro etp.trce.rw etp.admn.ro etp.domn.ro etp.accs.rw etp.quar.rw etp.domn.rw etp.rprt.rw etp.accs.ro etp.quar.ro etp.alrt.rw etp.rprt.ro etp.conf.rw etp.trce.ro etp.alrt.ro etp.admn.rw') |
**verify_server_cert** | optional | boolean | Use SSL cert verification |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using the supplied configuration \
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality \
[list alerts](#action-list-alerts) - Get a list of alerts from the ETP instance \
[get alert](#action-get-alert) - Get details about a specific alert from the ETP instance \
[list email attributes](#action-list-email-attributes) - Get all the attributes from a list of email messages \
[get email attributes](#action-get-email-attributes) - Get the attributes of a particular message with the specified Email Security message ID \
[trace email](#action-trace-email) - Search for Email Message by specifying one or more filters \
[trace message](#action-trace-message) - Search for Email Message by specifying the Queue/Message-ID of the Downstream MTA or the Original Message-ID. At least one parameter must be filled out. All fields are filtered by the IN clause where applicable \
[download email](#action-download-email) - Download the email header as a text file and add it to the vault \
[download pcap](#action-download-pcap) - Downloads all the PCAP files of the alert for a specified alert ID and add the files to the vault \
[download malware files](#action-download-malware-files) - Download all malware files of the alert for a specified alert ID and add the files to the vault \
[download case files](#action-download-case-files) - Download all case files of the alert for a specified alert ID and add the files to the vault \
[remediate emails](#action-remediate-emails) - Enqueues the message IDs provided in the request for remediation from the user's Office365 mailbox \
[get quarantined email](#action-get-quarantined-email) - Download the email file present in the quarantine for the given Email Security message ID and add it to the vault \
[unquarantine email](#action-unquarantine-email) - Release the email file(s) present in the Quarantine within ETP \
[delete quarantined email](#action-delete-quarantined-email) - Delete the email file(s) present in quarantine for the given Email Security message ID \
[list quarantined emails](#action-list-quarantined-emails) - Get a list of quarantined emails from a given query filter

## action: 'test connectivity'

Validate the asset configuration for connectivity using the supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** \
Read only: **True**

<p>Ingest alerts from ETP into Phantom. If 'start_time' is not specified, the default is past 10 days. If 'end_time' is not specified, the default is past 10 days.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Container IDs to size the ingestion to | string | |
**start_time** | optional | Start of the time range, in epoch time (milliseconds) | numeric | |
**end_time** | optional | End of the time range, in epoch time (milliseconds) | numeric | |
**container_count** | optional | The maximum number of container records to query for | numeric | |
**artifact_count** | optional | The maximum number of artifact records to query for | numeric | |

#### Action Output

No Output

## action: 'list alerts'

Get a list of alerts from the ETP instance

Type: **investigate** \
Read only: **True**

<p>The email status allows filtering by specific statuses. The valid values for email status are:</p><p><ul><li>ACE: Passthrough</li><li>quarantined</li><li>released</li><li>deleted</li><li>bcc:dropped</li><li>delivered (retroactive)</li><li>dropped (oob retroactive)</li></ul></p><p>If the 'size' parameter value is greater than the mentioned range(1-200), then the max value of range(i.e: 200) will be in consideration.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**legacy_id** | optional | Alert ID as shown in Email Security Web Portal | numeric | `fireeyeetp legacy id` |
**message_id** | optional | ETP Email message ID | string | `fireeyeetp message id` |
**email_status** | optional | Filter by ETP email status. Comma-separated list allowed. See app documentation for a list of acceptable values | string | |
**num_days** | optional | The number of days to get alerts for (ETP Defaults to last 90 days) | numeric | |
**size** | optional | Number of alerts to retrieve per response. Valid range: 1-200 (ETP Defaults to 20) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.legacy_id | numeric | `fireeyeetp legacy id` | 123456789 |
action_result.parameter.message_id | string | `fireeyeetp message id` | 7EFF784241DDFA1a527644d12 |
action_result.parameter.email_status | string | | ACE: Passthrough quarantined released deleted bcc:dropped delivered (retroactive) dropped (oob retroactive) |
action_result.parameter.num_days | numeric | | |
action_result.parameter.size | numeric | | |
action_result.data.\*.attributes.alert.alert_type | string | | at |
action_result.data.\*.attributes.alert.malware_md5 | string | `md5` `hash` | 131d79133e0f05e27095a8d75302d1e7 |
action_result.data.\*.attributes.alert.product | string | | ETP |
action_result.data.\*.attributes.alert.timestamp | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.attributes.ati | string | | |
action_result.data.\*.attributes.email.attachment | string | | |
action_result.data.\*.attributes.email.etp_message_id | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.data.\*.attributes.email.headers.cc | string | `email` | email@example.com |
action_result.data.\*.attributes.email.headers.from | string | `email` | email@example.com |
action_result.data.\*.attributes.email.headers.subject | string | | |
action_result.data.\*.attributes.email.headers.to | string | `email` | email@example.com |
action_result.data.\*.attributes.email.smtp.mail_from | string | `email` | email@example.com |
action_result.data.\*.attributes.email.smtp.rcpt_to | string | `email` | email@example.com |
action_result.data.\*.attributes.email.source_ip | string | `ip` | 1.1.1.1 |
action_result.data.\*.attributes.email.status | string | | ACE: Passthrough quarantined released deleted bcc:dropped delivered (retroactive) dropped (oob retroactive) |
action_result.data.\*.attributes.email.timestamp.accepted | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.attributes.meta.acknowledged | boolean | | True False |
action_result.data.\*.attributes.meta.last_malware | string | | Phish.LIVE.DTI.URL |
action_result.data.\*.attributes.meta.last_modified_on | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.attributes.meta.legacy_id | numeric | `fireeyeetp legacy id` | 123456789 |
action_result.data.\*.attributes.meta.read | boolean | | True False |
action_result.data.\*.attributes.meta.timestamp.db_insert_time | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.attributes.meta.timestamp.es_insert_time | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.id | string | `fireeyeetp alert id` | jsYRfJMuJu1epufQQuC3 |
action_result.data.\*.links.detail | string | | /api/v1/alerts/jsYRfJMuJu1epufQQuC3 |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get alert'

Get details about a specific alert from the ETP instance

Type: **investigate** \
Read only: **True**

<p>Get details about a specific alert by alert ID.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | Alert ID as shown in Email Security Web Portal | string | `fireeyeetp alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.alert_id | string | `fireeyeetp alert id` | kaB6fYTBGTn_991YBM6T |
action_result.data.\*.data.\*.attributes.alert.ack | string | | yes no |
action_result.data.\*.data.\*.attributes.alert.action | string | | notified |
action_result.data.\*.data.\*.attributes.alert.alert_type | string | | at |
action_result.data.\*.data.\*.attributes.alert.explanation.analysis | string | | binary |
action_result.data.\*.data.\*.attributes.alert.explanation.anomaly | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.cnc_service.cnc_service.\*.address | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.cnc_service.cnc_service.\*.channel | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.cnc_service.cnc_service.\*.port | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.cnc_service.cnc_service.\*.protocol | numeric | | |
action_result.data.\*.data.\*.attributes.alert.explanation.cnc_service.cnc_service.\*.sname | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.cnc_service.cnc_service.\*.type | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.application | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.domain | string | | example.com |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.downloaded_at | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.executed_at | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.md5sum | string | `md5` `hash` | 131d79133e0f05e27095a8d75302d1e7 |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.name | string | | Phish.LIVE.DTI.URL |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.origid | numeric | | 123456789 |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.original | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.profile | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.sha1 | string | `sha1` | 4E1243BD22C66E76C2BA9EDDC1F91394E57F9F83 |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.sha256 | string | `sha256` | 9F86D081884C7D659A2FEAA0C55AD015A3BF4F1B2B0B822CD15D6C15B0F00A08 |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.sha512 | string | `sha512` | C6EE9E33CF5C6715A1D148FD73F7318884B41ADCB916021E2BC0E800A5C5DD97F5142178F6AE88C8FDD98E1AFB0CE4C8D2C54B5F37B30B7DA1997BB33B0B8A31 |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.sid | numeric | | 123456789 |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.stype | string | | duplicate-md5sum |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.submitted_at | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.alert.explanation.malware_detected.malware.\*.type | string | | url |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.analysis.ftype | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.analysis.mode | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.analysis.product | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.analysis.verison | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.application.app_name | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.malicious_alert.\*.classtype | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.malicious_alert.\*.display_msg | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.os.arch | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.os.name | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.os.sp | numeric | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.os.verison | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.os_monitor.build | numeric | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.os_monitor.date | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.os_monitor.time | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.os_monitor.verision | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.osinfo | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.cmdline | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.fid.ads | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.fid.fid | numeric | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.filesize | numeric | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.md5sum | string | `md5` `hash` | 131d79133e0f05e27095a8d75302d1e7 |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.mode | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.no_extend | boolean | | True False |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.parentname | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.pid | numeric | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.ppid | numeric | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.sha1sum | string | `sha1` | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.sha256sum | string | `sha256` | 9F86D081884C7D659A2FEAA0C55AD015A3BF4F1B2B0B822CD15D6C15B0F00A08 |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.timestamp | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.os_changes.process_information.\*.value | string | | |
action_result.data.\*.data.\*.attributes.alert.explanation.protocol | string | | |
action_result.data.\*.data.\*.attributes.alert.malware_md5 | string | `md5` `hash` | 131d79133e0f05e27095a8d75302d1e7 |
action_result.data.\*.data.\*.attributes.alert.name | string | | malware-object |
action_result.data.\*.data.\*.attributes.alert.product | string | | ETP |
action_result.data.\*.data.\*.attributes.alert.severity | string | | major |
action_result.data.\*.data.\*.attributes.alert.timestamp | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.ati | string | | |
action_result.data.\*.data.\*.attributes.email.attachment | string | | |
action_result.data.\*.data.\*.attributes.email.etp_message_id | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.data.\*.data.\*.attributes.email.headers.cc | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.email.headers.from | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.email.headers.subject | string | | |
action_result.data.\*.data.\*.attributes.email.headers.to | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.email.smtp.mail_from | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.email.smtp.rcpt_to | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.email.source_ip | string | `ip` | 1.1.1.1 |
action_result.data.\*.data.\*.attributes.email.status | string | | delivered permanent failure quarantined rejected |
action_result.data.\*.data.\*.attributes.email.timestamp.accepted | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.meta.acknowledged | boolean | | True False |
action_result.data.\*.data.\*.attributes.meta.last_malware | string | | Phish.LIVE.DTI.URL |
action_result.data.\*.data.\*.attributes.meta.last_modified_on | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.meta.legacy_id | numeric | `fireeyeetp legacy id` | 123456789 |
action_result.data.\*.data.\*.attributes.meta.read | boolean | | True False |
action_result.data.\*.data.\*.attributes.meta.timestamp.db_insert_time | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.meta.timestamp.es_insert_time | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.id | string | `fireeyeetp alert id` | jsYRfJMuJu1epufQQuC3 |
action_result.data.\*.data.\*.links.detail | string | | /api/v1/alerts/jsYRfJMuJu1epufQQuC3 |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list email attributes'

Get all the attributes from a list of email messages

Type: **investigate** \
Read only: **True**

<p>Gets a list of messages that include specified message attributes that are accessible in the Email Security portal.</p><p>If the 'size' parameter value is greater than the mentioned range(1-200), then the max value of range(i.e: 200) will be in consideration.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**size** | optional | The number of alerts to include in a response. Valid range: 1-200 (ETP Defaults to 20) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.size | numeric | | |
action_result.data.\*.data.\*.attributes.acceptedDateTime | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.countryCode | string | | us |
action_result.data.\*.data.\*.attributes.domain | string | | domain.local |
action_result.data.\*.data.\*.attributes.downStreamMsgID | string | `fireeyeetp downstream message id` | 250 2.6.0 <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> [InternalId=23782507632821, Hostname=outlook.com] 89009 bytes in 0.136, 564.397 KB/sec Queued mail for delivery |
action_result.data.\*.data.\*.attributes.emailSize | numeric | | 9.87 |
action_result.data.\*.data.\*.attributes.lastModifiedDateTime | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.originalMessageID | string | `fireeyeetp original message id` | <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> |
action_result.data.\*.data.\*.attributes.recipientHeader | string | | email@example.com |
action_result.data.\*.data.\*.attributes.recipientSMTP | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.rejectionReason.code | string | | ETP210 |
action_result.data.\*.data.\*.attributes.rejectionReason.description | string | | recipient rejected |
action_result.data.\*.data.\*.attributes.senderHeader | string | | email@example.com |
action_result.data.\*.data.\*.attributes.senderIP | string | `ip` | 1.1.1.1 |
action_result.data.\*.data.\*.attributes.senderSMTP | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.status | string | | delivered permanent failure quarantined rejected |
action_result.data.\*.data.\*.attributes.subject | string | | |
action_result.data.\*.data.\*.attributes.verdicts.AS | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.AT | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.AV | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.ActionYARA | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.PV | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.YARA | string | | pass fail no match |
action_result.data.\*.data.\*.id | string | `fireeyeetp message id` | jsYRfJMuJu1epufQQuC3 |
action_result.data.\*.data.\*.included.\*.attributes.name | string | | domain.local |
action_result.data.\*.data.\*.included.\*.type | string | `domain` | |
action_result.data.\*.data.\*.type | string | | trace |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get email attributes'

Get the attributes of a particular message with the specified Email Security message ID

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**etp_message_id** | required | The ID of the Email Security message | string | `fireeyeetp message id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.etp_message_id | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.data.\*.data.\*.attributes.acceptedDateTime | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.countryCode | string | | us |
action_result.data.\*.data.\*.attributes.domain | string | | domain.local |
action_result.data.\*.data.\*.attributes.downStreamMsgID | string | `fireeyeetp downstream message id` | 250 2.6.0 <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> [InternalId=23782507632821, Hostname=outlook.com] 89009 bytes in 0.136, 564.397 KB/sec Queued mail for delivery |
action_result.data.\*.data.\*.attributes.emailSize | numeric | | 9.21 |
action_result.data.\*.data.\*.attributes.lastModifiedDateTime | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.originalMessageID | string | `fireeyeetp original message id` | <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> |
action_result.data.\*.data.\*.attributes.recipientHeader | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.recipientSMTP | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.rejectionReason.code | string | | ETP210 |
action_result.data.\*.data.\*.attributes.rejectionReason.description | string | | recipient rejected |
action_result.data.\*.data.\*.attributes.senderHeader | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.senderIP | string | `ip` | 1.1.1.1 |
action_result.data.\*.data.\*.attributes.senderSMTP | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.status | string | | delivered permanent failure quarantined rejected |
action_result.data.\*.data.\*.attributes.subject | string | | |
action_result.data.\*.data.\*.attributes.verdicts.AS | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.AT | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.AV | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.ActionYARA | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.PV | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.YARA | string | | pass fail no match |
action_result.data.\*.data.\*.id | string | `fireeyeetp message id` | jsYRfJMuJu1epufQQuC3 |
action_result.data.\*.data.\*.included.\*.attributes.name | string | | domain.local |
action_result.data.\*.data.\*.included.\*.type | string | | domain |
action_result.data.\*.data.\*.type | string | | trace |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'trace email'

Search for Email Message by specifying one or more filters

Type: **investigate** \
Read only: **True**

<p>At least one parameter must be filled out. All fields are filtered by the IN clause where applicable searching always an AND.</p><p>The modified date always uses the greater than or equal to. For example, if you want to search for the last 7 days, put a timestamp from 7 days ago. IE. 2017-10-03T00:00:00.000Z. Also, note that the DatetTime stamps need to be in UTC otherwise the results will be off. ETP assumes all DateTime stamps are in UTC.</p><p>The status field allows for the following values<ul><li>accepted</li><li>deleted</li><li>delivered</li><li>delivered (retroactive)</li><li>dropped</li><li>dropped oob</li><li>dropped (oob retroactive)</li><li>permanent failure</li><li>processing</li><li>quarantined</li><li>rejected</li><li>temporary failure</li></ul></p><p>The tags field allows for the following values<ul><li>auto_remediation</li><li>impersonation</li><li>manual_remediation</li></ul></p><p>If the 'size' parameter value is greater than the mentioned range(1-300), then the max value of range(i.e: 300) will be in consideration.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domains** | optional | Specific domain(s) to search by. Comma-separated list allowed | string | `domain` |
**modified_date** | optional | Datetime stamp to limit the search period | string | |
**recipients** | optional | The recipients of the email. The maximum allowed per request is 10. Comma-separated list allowed | string | `email` |
**sender** | optional | The sender of the email. The maximum allowed per request is 10. Comma-separated list allowed | string | `email` |
**status** | optional | ETP status to search by. Comma-separated list allowed | string | |
**subject** | optional | The subject of the email to search for | string | |
**tags** | optional | Tags from ETP that are associated with an email | string | |
**size** | optional | The number of alerts to include in a response. Valid range: 1-300 (ETP Defaults to 20) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.domains | string | `domain` | domain.local |
action_result.parameter.modified_date | string | | 2017-10-03T00:00:00.000Z |
action_result.parameter.recipients | string | `email` | example@email.com |
action_result.parameter.sender | string | `email` | example@email.com |
action_result.parameter.status | string | | accepted deleted delivered delivered (retroactive) dropped dropped oob dropped (oob retroactive) permanent failure processing quarantined rejected temporary failure |
action_result.parameter.subject | string | | |
action_result.parameter.tags | string | | auto_remediation impersonation manual_remediation |
action_result.parameter.size | numeric | | |
action_result.data.\*.data.\*.attributes.acceptedDateTime | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.countryCode | string | | us |
action_result.data.\*.data.\*.attributes.domain | string | | domain.local |
action_result.data.\*.data.\*.attributes.downStreamMsgID | string | `fireeyeetp downstream message id` | 250 2.6.0 <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> [InternalId=23782507632821, Hostname=outlook.com] 89009 bytes in 0.136, 564.397 KB/sec Queued mail for delivery |
action_result.data.\*.data.\*.attributes.emailSize | numeric | | 9.21 |
action_result.data.\*.data.\*.attributes.lastModifiedDateTime | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.originalMessageID | string | `fireeyeetp original message id` | <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> |
action_result.data.\*.data.\*.attributes.recipientHeader | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.recipientSMTP | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.rejectionReason.code | string | | ETP210 |
action_result.data.\*.data.\*.attributes.rejectionReason.description | string | | recipient rejected |
action_result.data.\*.data.\*.attributes.senderHeader | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.senderIP | string | `ip` | 1.1.1.1 |
action_result.data.\*.data.\*.attributes.senderSMTP | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.status | string | | delivered permanent failure quarantined rejected |
action_result.data.\*.data.\*.attributes.subject | string | | |
action_result.data.\*.data.\*.attributes.verdicts.AS | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.AT | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.AV | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.ActionYARA | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.PV | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.YARA | string | | pass fail no match |
action_result.data.\*.data.\*.id | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.data.\*.data.\*.included.\*.attributes.name | string | | domain.local |
action_result.data.\*.data.\*.included.\*.type | string | | domain |
action_result.data.\*.data.\*.type | string | | trace |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'trace message'

Search for Email Message by specifying the Queue/Message-ID of the Downstream MTA or the Original Message-ID. At least one parameter must be filled out. All fields are filtered by the IN clause where applicable

Type: **investigate** \
Read only: **True**

<p>If the 'size' parameter value is greater than the mentioned range(1-300), then the max value of range(i.e: 300) will be in consideration.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**original_message_id** | optional | The email's Original-Message-ID header value | string | `fireeyeetp original message id` |
**downstream_message_id** | optional | The email's Downstream-Message-ID header value | string | `fireeyeetp downstream message id` |
**size** | optional | The number of alerts to include in a response. Valid range: 1-300 (ETP Defaults to 20) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.original_message_id | string | `fireeyeetp original message id` | <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> |
action_result.parameter.downstream_message_id | string | `fireeyeetp downstream message id` | 250 2.6.0 <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> [InternalId=23782507632821, Hostname=outlook.com] 89009 bytes in 0.136, 564.397 KB/sec Queued mail for delivery |
action_result.parameter.size | numeric | | |
action_result.data.\*.data.\*.attributes.acceptedDateTime | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.countryCode | string | | us |
action_result.data.\*.data.\*.attributes.domain | string | | domain.local |
action_result.data.\*.data.\*.attributes.downStreamMsgID | string | `fireeyeetp downstream message id` | 250 2.6.0 <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> [InternalId=23782507632821, Hostname=outlook.com] 89009 bytes in 0.136, 564.397 KB/sec Queued mail for delivery |
action_result.data.\*.data.\*.attributes.emailSize | numeric | | 9.21 |
action_result.data.\*.data.\*.attributes.lastModifiedDateTime | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.attributes.originalMessageID | string | `fireeyeetp original message id` | <97be1b3701c4b71faec8bf7b6.13bf5ad01b.20200614582589.d1f0cfbf6b.ad7426e6@mail.net> |
action_result.data.\*.data.\*.attributes.recipientHeader | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.recipientSMTP | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.rejectionReason.code | string | | ETP210 |
action_result.data.\*.data.\*.attributes.rejectionReason.description | string | | recipient rejected |
action_result.data.\*.data.\*.attributes.senderHeader | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.senderIP | string | `ip` | 1.1.1.1 |
action_result.data.\*.data.\*.attributes.senderSMTP | string | `email` | email@example.com |
action_result.data.\*.data.\*.attributes.status | string | | delivered permanent failure quarantined rejected |
action_result.data.\*.data.\*.attributes.subject | string | | |
action_result.data.\*.data.\*.attributes.verdicts.AS | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.AT | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.AV | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.ActionYARA | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.PV | string | | pass fail no match |
action_result.data.\*.data.\*.attributes.verdicts.YARA | string | | pass fail no match |
action_result.data.\*.data.\*.id | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.data.\*.data.\*.included.\*.attributes.name | string | | domain.local |
action_result.data.\*.data.\*.included.\*.type | string | | domain |
action_result.data.\*.data.\*.type | string | | trace |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'download email'

Download the email header as a text file and add it to the vault

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**etp_message_id** | required | The ID of the Email Security message to download | string | `fireeyeetp message id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.etp_message_id | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'download pcap'

Downloads all the PCAP files of the alert for a specified alert ID and add the files to the vault

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | The ID of the Email Security message to download | string | `fireeyeetp alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.alert_id | string | `fireeyeetp alert id` | kaB6fYTBGTn_991YBM6T |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'download malware files'

Download all malware files of the alert for a specified alert ID and add the files to the vault

Type: **investigate** \
Read only: **True**

<p>These files can contain viruses or other malicious software. Be cautious when opening these files!</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | The ID of the Email Security message to download | string | `fireeyeetp alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.alert_id | string | `fireeyeetp alert id` | kaB6fYTBGTn_991YBM6T |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'download case files'

Download all case files of the alert for a specified alert ID and add the files to the vault

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | The ID of the Email Security message to download | string | `fireeyeetp alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.alert_id | string | `fireeyeetp alert id` | kaB6fYTBGTn_991YBM6T |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remediate emails'

Enqueues the message IDs provided in the request for remediation from the user's Office365 mailbox

Type: **contain** \
Read only: **False**

<p><b>Note: There is no <i>undo</i> functionality with this action!</b></p><p>The permissions the API account needs to have to use this function are, <b>etp.email_trace.update</b> and <b>etp.email_trace.delete</b>. If the API user does not have these permissions you will not be able to use this action.</p><p></p><p>Any ETP Messages that have a status from the list given below are ignored and no action will be taken on them. <p><ul><li>Deleted</li><li>Dropped</li><li>Dropped(OOB)</li><li>Dropped (OOB Retroactive)</li><li>Rejected</li><li>Split</li><li>Permanent Failure</li></ul></p></p><p>The action_override parameter allows you to override the default action for remediating an email. It is important to note that if you select Delete, that it is a permanent delete in Office365.</p><p>The move_to parameter allows you to move the identified emails to a specific folder. If the folder is not in the user's mailbox, a new custom folder will be created and then the email will be moved into the new folder. Common Office365 folders are <p><ul><li>junk email</li><li>junkemail</li><li>deleted items</li><li>deleteditems</li></ul> These folder names are not case sensitive.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**etp_message_ids** | required | A comma-separated list of ETP Message IDs | string | `fireeyeetp message id` |
**action_override** | optional | Allows you to override the default action | string | |
**move_to** | optional | When 'move' is chosen for action_override, this parameter is mandatory and allows you to specify the folder to move the email to | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.etp_message_ids | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.parameter.action_override | string | | Delete Quarantine Move |
action_result.parameter.move_to | string | | junk email junkemail deleted items deleteditems |
action_result.data.\*.data.successful | string | | |
action_result.data.\*.data.failed | string | | |
action_result.data.\*.data.failure_reasons.\*.reason | string | | |
action_result.data.\*.data.failure_reasons.\*.message_ids | string | | 7EFF784241DDFA1a527644d12 |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get quarantined email'

Download the email file present in the quarantine for the given Email Security message ID and add it to the vault

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**etp_message_id** | required | The ID of the Email Security message to download | string | `fireeyeetp message id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.etp_message_id | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unquarantine email'

Release the email file(s) present in the Quarantine within ETP

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**etp_message_id** | required | The ID of the Email Security message to unquarantine. Allows for a comma-separated string of IDs | string | `fireeyeetp message id` |
**is_not_spam** | optional | Report as not spam to the Spam Engines | boolean | |
**headers_only** | optional | Share only the email headers with Spam Engines | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.etp_message_id | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.parameter.is_not_spam | boolean | | True False |
action_result.parameter.headers_only | boolean | | True False |
action_result.data.\*.response | string | | Email is submitted for release |
action_result.data.\*.message | string | | Invalid etp message ID or the message ID does not exist in quarantine |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete quarantined email'

Delete the email file(s) present in quarantine for the given Email Security message ID

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**etp_message_id** | required | The ID of the Email Security message to delete. Allows a comma-separated string of IDs | string | `fireeyeetp message id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.etp_message_id | string | `fireeyeetp message id` | D1670833091CA91B5359A4969 |
action_result.data.\*.data.\*.deleted | boolean | | True False |
action_result.data.\*.data.\*.failed_message_ids | string | | 7EFF784241DDFA1a527644d12 |
action_result.data.\*.data.\*.operation | string | | deleted |
action_result.data.\*.data.\*.successful_message_ids | string | | 7EFF784241DDFA1a527644d12 |
action_result.data.\*.data.\*.type | string | | quarantine |
action_result.data | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list quarantined emails'

Get a list of quarantined emails from a given query filter

Type: **investigate** \
Read only: **True**

<p>When specifying a date in either the to or from dates, the date is assumed to be in UTC. The ETP server runs on UTC so if you are not converting the timestamp to that time the results will be off.</p><p>If the 'size' parameter value is greater than the mentioned range(1-200), then the max value of range(i.e: 200) will be in consideration.</p>

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**from_date** | required | Start date to use to search the by. Date in YYYY-MM-DDTHH:MM:SS.SSSSSS in UTC | string | |
**to_date** | optional | End date to use to search by. Date in YYYY-MM-DDTHH:MM:SS.SSSSSS in UTC | string | |
**domains** | optional | Specific domain(s) to search by. Comma-separated list allowed | string | `domain` |
**email_server** | optional | Specific email server to search by | string | `ip` |
**from** | optional | Email address of the sender to search by | string | `email` |
**reason** | optional | Reason the email was quarantined. The strings must be of the following reasons, Action, Advanced Threat, Policy, Spam or Virus. Comma-separated list allowed | string | |
**recipients** | optional | Recipient(s) to search by. Comma-separated list allowed | string | `email` |
**sender_domain** | optional | The senders domain to search by | string | `domain` |
**subject** | optional | The subject of the email to search by | string | |
**size** | required | The number of alerts to include in response. Valid range: 1-200 (ETP Defaults to 20) | numeric | |
**tags** | optional | Tag associated with email. Must be of the follow tags, auto_remediation, impersonation, or manual_remediation. Comma-separated list allowed | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.from_date | string | | 2020-01-01T01:01:01.804 |
action_result.parameter.to_date | string | | 2020-01-01T01:01:01.804 |
action_result.parameter.domains | string | `domain` | domain.local |
action_result.parameter.email_server | string | `ip` | 1.1.1.1 |
action_result.parameter.from | string | `email` | example@email.com |
action_result.parameter.reason | string | | Action Advanced Threat Policy Spam Virus |
action_result.parameter.recipients | string | `email` | example@email.com |
action_result.parameter.sender_domain | string | `domain` | |
action_result.parameter.subject | string | | |
action_result.parameter.size | numeric | | |
action_result.parameter.tags | string | | auto_remediation impersonation manual_remediation |
action_result.data.\*.data.\*.attachments | string | | |
action_result.data.\*.data.\*.cc | string | `email` | email@example.com |
action_result.data.\*.data.\*.country_code | string | | us |
action_result.data.\*.data.\*.domain | string | | domain.local |
action_result.data.\*.data.\*.from | string | `email` | email@example.com |
action_result.data.\*.data.\*.message_id | string | `fireeyeetp message id` | 7EFF784241DDFA1a527644d12 |
action_result.data.\*.data.\*.recipients | string | `email` | email@example.com |
action_result.data.\*.data.\*.released.\*.email_id | string | | email@example.com |
action_result.data.\*.data.\*.released.\*.is_released | numeric | | 1 |
action_result.data.\*.data.\*.released.\*.key | string | | 131d79133e0f05e27095a8d75302d1e7 |
action_result.data.\*.data.\*.sender_domain | string | | domain.local |
action_result.data.\*.data.\*.sender_ip | string | `ip` | 1.1.1.1 |
action_result.data.\*.data.\*.subject | string | | |
action_result.data.\*.data.\*.timestamp_quarantine | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.timestamp_sent | string | | 2020-01-01T01:01:01.804 |
action_result.data.\*.data.\*.to | string | `email` | email@example.com |
action_result.data.\*.data.\*.verdict_as | string | | pass fail no match |
action_result.data.\*.data.\*.verdict_av | string | | pass fail no match |
action_result.data.\*.data.\*.verdict_ex | string | | pass fail no match |
action_result.data.\*.data.\*.verdict_pv | string | | pass fail no match |
action_result.status | string | | success failed |
action_result.message | string | | |
action_result.summary | string | | |
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
