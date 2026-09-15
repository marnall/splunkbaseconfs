# Carbonio Add-on for Splunk

## Overview

The Carbonio Add-on for Splunk provides field extractions, event types, tags, and CIM-compatible mappings for Carbonio and Zextras service logs.

This add-on is designed to normalize Carbonio-related logs for use in Splunk Search, Splunk Enterprise Security, CIM data models, dashboards, and correlation searches.

## Author

Cyberfox 

## Version

1.0.0

## Supported Sourcetypes

This add-on supports the following sourcetypes:

| Sourcetype | Description |
|---|---|
| `carbonio_audit` | Carbonio audit and authentication events |
| `carbonio` | General Carbonio/Zextras syslog events, including postfix, amavis, zmconfigd, sshd, slapd |
| `carbonio_mail` | Carbonio/Postfix mail transport logs |
| `carbonio_mailbox` | Carbonio mailbox application logs |
| `carbonio_clamd` | ClamAV daemon logs |
| `carbonio_freshclam` | ClamAV Freshclam update logs |
| `carbonio_files` | Carbonio Files service logs |
| `carbonio_docs-connector` | Carbonio Docs Connector logs |
| `carbonio_nginx` | Carbonio Nginx error/service logs |
| `carbonio_nginx.access` | Carbonio Nginx access logs |
| `carbonio_nginx_clamav_signature_provider_access` | ClamAV signature provider access logs |
| `carbonio_preview` | Carbonio Preview service logs |

## CIM Mapping

The add-on provides event types and tags for the following Splunk CIM data models:

### Authentication

The following events are mapped to the Authentication data model:

| Sourcetype | Event | Tags |
|---|---|---|
| `carbonio_audit` | `cmd=Auth` | `authentication`, `default` |
| `carbonio_audit` | `cmd=AdminAuth`, `cmd=DelegateAuth` | `authentication`, `privileged` |
| `carbonio_mailbox` | Authentication failed events | `authentication`, `default` |
| `carbonio_mailbox` | SOAP AuthRequest events | `authentication`, `default` |
| `carbonio_mailbox` | Delegated authentication events | `authentication`, `privileged` |
| `carbonio_files` | Database authentication failed events | `authentication`, `default` |

Common normalized fields:

- `user`
- `src`
- `src_ip`
- `dest`
- `dest_ip`
- `action`
- `app`
- `signature`
- `signature_id`
- `reason`
- `user_agent`
- `authentication_method`
- `authentication_service`

### Email

The following events are mapped to the Email data model:

| Sourcetype | Event | Tags |
|---|---|---|
| `carbonio_mail` | Postfix delivery events | `email`, `delivery` |
| `carbonio_mailbox` | LMTP delivery and mail operation events | `email`, `delivery` |
| `carbonio` | Amavis filtering events | `email`, `filter` |
| `carbonio` | Postfix delivery events | `email`, `delivery` |

Common normalized fields:

- `sender`
- `recipient`
- `src_user`
- `dest_user`
- `message_id`
- `status`
- `action`
- `relay_host`
- `relay_ip`
- `smtp_response`
- `spam_score`
- `spam_flag`

### Network Traffic

The following events are mapped to the Network Traffic data model:

| Sourcetype | Event | Tags |
|---|---|---|
| `carbonio_mail` | SMTP connection, postscreen, smtpd and TLS events | `network`, `communicate` |
| `carbonio` | Postfix postscreen and smtpd connection events | `network`, `communicate` |

Common normalized fields:

- `src`
- `src_ip`
- `src_port`
- `dest`
- `dest_ip`
- `dest_port`
- `transport`
- `protocol`
- `app`
- `action`

### Malware

The following events are mapped to the Malware data model:

| Sourcetype | Event | Tags |
|---|---|---|
| `carbonio_clamd` | ClamAV daemon status and operation events | `malware`, `operations` |
| `carbonio_freshclam` | ClamAV database update events | `malware`, `operations` |

Common normalized fields:

- `signature`
- `signature_id`
- `status`
- `action`
- `clamd_event`
- `update_status`
- `database_file`
- `database_status`
- `signatures_count`
