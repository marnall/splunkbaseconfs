# Google Threat Intelligence

Publisher: Google <br>
Connector Version: 1.1.0 <br>
Product Vendor: Google <br>
Product Name: Google Threat Intelligence <br>
Minimum Product Version: 6.4.0

Supercharge Splunk SOAR with Google Threat Intelligence by integrating real-time IOCs, breach insights, and threat actor data from VirusTotal, Mandiant, and Google for automated, context-rich responses

# Integration Overview

Supercharge your Splunk SOAR with Google Threat Intelligence, unifying unparalleled threat analysis directly within your security operations. This app provides context-rich reputation and deep analysis for indicators by fusing three powerful sources: the vast, real-time crowdsourced intelligence of VirusTotal, the frontline breach expertise and actor tracking of Mandiant, and the global threat visibility from Google's own network. Go beyond simple lookups by ingesting curated threat signals from Mandiant-driven Attack Surface Management and Digital Threat Monitoring, along with Google's real-time IOC streams, to automate response with unmatched context and confidence.

# Explanation of Data Ingestion

This integration supports three types of data ingestion: **IOC Stream**, **DTM Alerts**, and **ASM Issues**. If an ingestion type is not selected while configuring asset, data ingestion will not occur. Only one data ingestion type can be configured per asset. To configure multiple data ingestions, set up multiple assets.

The below details describes the configuration and usage of the GTI integration for Splunk SOAR, focusing on the three on-poll ingestion types: **IOC Stream**, **DTM Alerts**, and **ASM Issues**.

______________________________________________________________________

## On-Poll Configuration

### Poll Now Feature

The **Poll Now** action retrieves the most recent 1 hour of data for all three ingestion types: **IOC Stream**, **DTM Alerts**, and **ASM Issues**.

**Important Notes:**

- The *Poll Now* feature **ignores** the following parameters: **Source ID**, **Maximum containers**, and **Maximum artifacts**.
- It does **not** store a checkpoint file, meaning it will always pull the most recent 1 hour of data regardless of previous ingestions.
- When using *Poll Now* for **IOC Stream**, duplicate artifacts may be ingested into the current day's container if those artifacts already exist, since SOAR does **not** automatically remove duplicates.

### Scheduled / Interval Polling

**Recommended Ingestion Interval:**\
Set the ingestion interval to 1 hour for optimal performance and timely data updates. Please note that using very short intervals may negatively impact data ingestion efficiency and the overall performance of your instance.

**Limit Parameter:**\
The `limit` parameter controls the maximum number of records ingested per poll. The maximum allowed value is **1000**; if a higher or invalid value is set, it will be ignored and **1000** will be used.

**Lookback Days Parameter:**\
The `lookback_days` parameter determines how many days back the integration will look for data during the initial poll. The maximum allowed value is **5**; if a higher or invalid value is set, it will be ignored and **5** will be used. Days are calculated as the absolute day difference from the current time.

______________________________________________________________________

## IOC Stream

- **Parameters:**

  - **Descriptors Only:** Includes only object descriptors, not full VT objects (boolean, default: false).
  - **Filter:** Filter string to filter IOCs (string). This is a recommended option for the IOC Stream data ingestion type to filter relevant IOCs and reduce noise.

- **Container Creation:**\
  All IOC Stream data for a given UTC day will be ingested into a single container. A new container is created each day (UTC-based).

______________________________________________________________________

## DTM Alerts

- **Parameters:**

  - **Monitor ID:** Filter alerts by the specified monitor ID(s). Supports multiple comma-separated values (string).
  - **Status:** Filter alerts by status. Possible values: `new`, `read`, `escalated`, `in_progress`, `closed`, `no_action_required`, `duplicate`, `not_relevant`, `tracked_external`. Supports multiple comma-separated values (string).
  - **Alert Type:** Filter alerts by alert type. Possible values: `Compromised Credentials`, `Domain Discovery`, `Forum Post`, `Message`, `Paste`, `Shop Listing`, `Tweet`, `Web Content`. Supports multiple comma-separated values (string).
  - **Search:** Search alerts and triggering documents using a Lucene query with text values joined by AND/OR (string).
  - **Match Value:** Filter alerts by specified match value. Supports multiple comma-separated values (string).
  - **Tags:** Filter alerts by tags. Supports multiple comma-separated values (string).
  - **Severity:** Filter alerts by specified severity. Possible values: `high`, `medium`, `low`. Supports multiple comma-separated values (string).
  - **MScore GTE:** Filter alerts with mscores greater than or equal to the given value (numeric, 0 to 100).

- **Status Mapping of DTM Alerts:**

  | DTM Alert Status | SOAR Container Status |
  |----------------------|----------------------|
  | New | New |
  | Read | Open |
  | Escalated | Open |
  | In Progress | Open |
  | Closed | Closed |
  | No Action Required | Closed |
  | Duplicate | Closed |
  | Not Relevant | Closed |
  | Tracked External | Closed |

- **Severity Mapping of DTM Alerts:**

  | DTM Alert Severity | SOAR Container Severity |
  |--------------------|------------------------|
  | High | High |
  | Medium | Medium |
  | Low | Low |

- **Container Creation:**\
  Each DTM alert will result in the creation of a separate container. One artifact will be created inside the container and will have certain important fields from alert visible inside the artifact. To get complete details about the alert, download the artifact JSON.

- **Container Updates:**\
  Containers or artifacts will **not** be updated if the alert is updated in GTI after ingestion.

- **Closing DTM Alerts in GTI:**\
  When a DTM alert container is closed in Splunk SOAR, the playbook provided in this [repository](https://github.com/virusTotal/gti-soar-playbooks/tree/main/Splunk%20SOAR) automatically closes the corresponding alert in GTI.

______________________________________________________________________

## ASM Issues

- **Parameters:**

  - **Search String:** Search string (fields `last_seen_after`, `last_seen_before`, and `first_seen_after` will be ignored). This is a recommended option for the ASM Issues data ingestion type to filter relevant issues and reduce noise (string).
  - **Project ID:** Project ID (string).

- **Status Mapping of ASM Issues:**

  | ASM Issue Status | SOAR Container Status |
  |---------------------|----------------------|
  | Open | Open |
  | Triaged | Open |
  | In Progress | Open |
  | Closed | Closed |
  | Mitigated | Closed |
  | Resolved | Closed |
  | Duplicate | Closed |
  | Out of Scope | Closed |
  | Benign | Closed |
  | Risk Accepted | Closed |
  | False Positive | Closed |
  | Unable to Reproduce | Closed |
  | Tracked Externally | Closed |

- **Severity Mapping of ASM Issues:**

  | ASM Issue Severity | SOAR Container Severity |
  |--------------------|------------------------|
  | 1 | High |
  | 2 | High |
  | 3 | Medium |
  | 4 | Low |
  | 5 | Low |

- **Container Creation:**\
  Each ASM issue will result in the creation of a separate container. One artifact will be created inside the container and will have certain important fields from issue visible inside the artifact. To get complete details about the issue, download the artifact JSON.

- **Container Updates:**\
  Fields of artifacts inside the container will be updated **only if** the `last_seen` value of the issue changes in GTI. If there are any other updates but the `last_seen` field hasn't changed, the artifact will not be updated.

- **Closing ASM Issues in GTI:**\
  When an ASM issue container is closed in Splunk SOAR, the playbook provided in this [repository](https://github.com/virusTotal/gti-soar-playbooks/tree/main/Splunk%20SOAR) automatically closes the corresponding issue in GTI.

______________________________________________________________________

### Configuration variables

This table lists the configuration variables required to operate Google Threat Intelligence. These variables are specified when configuring a Google Threat Intelligence asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**x-apikey** | required | password | Google Threat Intelligence API Key |
**ingestion_type** | optional | string | Type of data to retrieve and ingest |
**days** | optional | numeric | Lookback Days: Number of days of historical data to retrieve (max: 5) (Applicable for all three ingestion types) |
**limit** | optional | numeric | Limit: Maximum number of objects to fetch per poll (max: 1000) (Applicable for all three ingestion types) |
**descriptors_only** | optional | boolean | Descriptors Only: Includes only object descriptors, not full VT objects (IOC Stream) |
**filter** | optional | string | Filter String (IOC Stream) |
**monitor_id** | optional | string | Monitor ID: Filter alerts by the specified monitor ID(s). Supports multiple comma-separated values (DTM Alerts) |
**status** | optional | string | Status: Filter alerts by status. Supports multiple comma-separated values (DTM Alerts) |
**alert_type** | optional | string | Alert Type: Filter alerts by alert type. Supports multiple comma-separated values (DTM Alerts) |
**search** | optional | string | Search String: Search alerts and triggering documents using a Lucene query with text values joined by AND/OR (DTM Alerts) |
**match_value** | optional | string | Match Value: Filter alerts by specified match value. Supports multiple comma-separated values (DTM Alerts) |
**tags** | optional | string | Tags: Filter alerts by tags. Supports multiple comma-separated values (DTM Alerts) |
**severity** | optional | string | Severity: Filter alerts by specified severity. Supports multiple comma-separated values (DTM Alerts) |
**mscore_gte** | optional | numeric | MScore GTE: Filter alerts with mscores greater than or equal to the given value (DTM Alerts) |
**search_string** | optional | string | Search String (ASM Issues) (Fields last_seen_after, last_seen_before, and first_seen_after will be ignored) |
**project-id** | optional | string | Project ID (ASM Issues) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Test connectivity with Google Threat Intelligence <br>
[on poll](#action-on-poll) - Ingest data from IOC Stream, DTM Alerts, and ASM Issues <br>
[scan private file](#action-scan-private-file) - Privately scan and analyze a file to retrieve associated threat intelligence <br>
[get ioc report](#action-get-ioc-report) - Publicly scan and fetch the report for an IP address, URL, domain, or file <br>
[get comments](#action-get-comments) - Fetch comments for an IP address, URL, domain, or file <br>
[get vulnerability associations](#action-get-vulnerability-associations) - Fetch vulnerabilities related to an IP address, URL, domain, or file <br>
[get file sandbox report](#action-get-file-sandbox-report) - Fetch the behavior report for a given file <br>
[scan private url](#action-scan-private-url) - Privately scan and analyze a URL to retrieve associated threat intelligence <br>
[get curated associations](#action-get-curated-associations) - Fetch curated threat actors, malware families, campaigns, and reports for an IP address, URL, domain, or file <br>
[add comment](#action-add-comment) - Add a comment to an IP address, URL, domain, or file <br>
[delete comment](#action-delete-comment) - Delete a specific comment <br>
[get passive dns data](#action-get-passive-dns-data) - Fetch passive DNS data for a domain or IP address <br>
[get vulnerability report](#action-get-vulnerability-report) - Fetch the vulnerability report for a given vulnerability ID <br>
[update dtm alert status](#action-update-dtm-alert-status) - Update the status of a DTM alert <br>
[update asm issue status](#action-update-asm-issue-status) - Update the status of an ASM issue

## action: 'test connectivity'

Test connectivity with Google Threat Intelligence

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Ingest data from IOC Stream, DTM Alerts, and ASM Issues

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'scan private file'

Privately scan and analyze a file to retrieve associated threat intelligence

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_hash** | required | Vault ID of the file to scan | string | `vault id` `sha1` `sha256` |
**password** | optional | Password to decompress and scan a file contained in a protected ZIP file | string | |
**command_line** | optional | Command line arguments to use when running the file in sandboxes | string | |
**disable_sandbox** | optional | If true, then the file won't be detonated in sandbox environments. False by default | string | |
**enable_internet** | optional | If the file should have internet access when running in sandboxes. False by default | string | |
**intercept_tls** | optional | Intercept HTTPS/TLS/SSL communication; intercept HTTPS to view encrypted URLs, hostnames, and HTTP headers; this is detectable by any sample that checks certificates and makes JA3 hashes unusable | string | |
**retention_period_days** | optional | Number of days the report and file are kept in VT (between 1 and 28); if not set, defaults to the group's retention policy (1 day by default) | numeric | |
**storage_region** | optional | Storage region where the file will be stored; by default, uses the group's private_scanning.storage_region preference; allowed values are US, CA, EU, GB | string | |
**interaction_sandbox** | optional | Select the sandbox desired for interactive use | string | |
**interaction_timeout** | optional | Interaction timeout in seconds, minimum value: 60. (1 minute.) Max value: 1800: (30 minutes) | numeric | |
**locale** | optional | Preferred sandbox locale; on Windows, this selection changes the language and keyboard settings of the analysis machine | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.command_line | string | | |
action_result.parameter.disable_sandbox | string | | false |
action_result.parameter.enable_internet | string | | false |
action_result.parameter.file_hash | string | `vault id` `sha1` `sha256` | null |
action_result.parameter.interaction_sandbox | string | | |
action_result.parameter.interaction_timeout | numeric | | 60 |
action_result.parameter.intercept_tls | string | | false |
action_result.parameter.locale | string | | EN_US |
action_result.parameter.password | string | | |
action_result.parameter.retention_period_days | numeric | | 1 |
action_result.parameter.storage_region | string | | |
action_result.data | string | | |
action_result.data.\*.data.attributes.available_tools.\* | string | | |
action_result.data.\*.data.attributes.crowdsourced_ai_results.\*.analysis | string | | Dummy Anylysis |
action_result.data.\*.data.attributes.crowdsourced_ai_results.\*.category | string | | code_insights |
action_result.data.\*.data.attributes.crowdsourced_ai_results.\*.creation_date | numeric | | 1746434239 |
action_result.data.\*.data.attributes.crowdsourced_ai_results.\*.id | string | | 22e9da87d52f94e2dbb5509dede7945edd213bbe648e740f55bff8b596017cca |
action_result.data.\*.data.attributes.crowdsourced_ai_results.\*.last_modification_date | numeric | | 1746515543 |
action_result.data.\*.data.attributes.crowdsourced_ai_results.\*.source | string | | palm |
action_result.data.\*.data.attributes.crowdsourced_yara_results.\*.author | string | | InQuest Labs |
action_result.data.\*.data.attributes.crowdsourced_yara_results.\*.description | string | | This signature detects the presence of a number of Windows API functionality often seen within embedded executables. When this signature alerts on an executable, it is not an indication of malicious behavior. However, if seen firing in other file types, deeper investigation may be warranted. |
action_result.data.\*.data.attributes.crowdsourced_yara_results.\*.match_date | numeric | | 1746515544 |
action_result.data.\*.data.attributes.crowdsourced_yara_results.\*.rule_name | string | | Windows_API_Function |
action_result.data.\*.data.attributes.crowdsourced_yara_results.\*.ruleset_id | string | | 0122a7f913 |
action_result.data.\*.data.attributes.crowdsourced_yara_results.\*.ruleset_name | string | | Windows_API_Function |
action_result.data.\*.data.attributes.crowdsourced_yara_results.\*.ruleset_version | string | | 0122a7f913|589bbefc22847193cac455858fa15e627d671918 |
action_result.data.\*.data.attributes.crowdsourced_yara_results.\*.source | string | | https://github.com/InQuest/yara-rules-vt |
action_result.data.\*.data.attributes.exiftool.FileType | string | | TXT |
action_result.data.\*.data.attributes.exiftool.FileTypeExtension | string | | txt |
action_result.data.\*.data.attributes.exiftool.LineCount | string | | 43 |
action_result.data.\*.data.attributes.exiftool.MIMEEncoding | string | | us-ascii |
action_result.data.\*.data.attributes.exiftool.MIMEType | string | | text/plain |
action_result.data.\*.data.attributes.exiftool.Newlines | string | | Windows CRLF |
action_result.data.\*.data.attributes.exiftool.WordCount | string | | 136 |
action_result.data.\*.data.attributes.expiration | numeric | | 1746601941 |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.matched_malicious_yara | boolean | | True |
action_result.data.\*.data.attributes.gti_assessment.description | string | | This indicator did not match our detection criteria and there is currently no evidence of malicious activity. |
action_result.data.\*.data.attributes.gti_assessment.severity.value | string | | SEVERITY_NONE |
action_result.data.\*.data.attributes.gti_assessment.threat_score.value | numeric | | 1 |
action_result.data.\*.data.attributes.gti_assessment.verdict.value | string | | VERDICT_UNDETECTED |
action_result.data.\*.data.attributes.javascript_info.tags.\* | string | | malformed |
action_result.data.\*.data.attributes.last_analysis_date | numeric | | 1744802062 |
action_result.data.\*.data.attributes.magic | string | | ASCII text, with very long lines (314u) |
action_result.data.\*.data.attributes.magika | string | | JAVASCRIPT |
action_result.data.\*.data.attributes.md5 | string | `md5` | 3a3b9ad4b635a6e9070b6f78f07462a3 |
action_result.data.\*.data.attributes.meaningful_name | string | | GTI VirusTotal API.postman_collection.json |
action_result.data.\*.data.attributes.names.\* | string | | test_2.js |
action_result.data.\*.data.attributes.sandbox_verdicts.Zenbox.category | string | | suspicious |
action_result.data.\*.data.attributes.sandbox_verdicts.Zenbox.confidence | numeric | | 22 |
action_result.data.\*.data.attributes.sandbox_verdicts.Zenbox.malware_classification.\* | string | | GREYWARE |
action_result.data.\*.data.attributes.sandbox_verdicts.Zenbox.sandbox_name | string | | Zenbox |
action_result.data.\*.data.attributes.sha1 | string | `vault id` `sha1` | bb74a0f57512307536fc0345a5f6f6844aa7dd29 |
action_result.data.\*.data.attributes.sha256 | string | `sha256` | 9ce61f04df346e8d6cba8da4eca52337c751a344ca3f044418e0d5fae8201743 |
action_result.data.\*.data.attributes.size | numeric | | 1708179 |
action_result.data.\*.data.attributes.ssdeep | string | | 6144:7zzpC90UaUAzs1Y8vyRmpuMkUXtZzc69yJVdI4uFAVN7RNa4UTPL3iniLhZWjPTX:3dkOUXaMkUdZz4ejSiiPfoC1Ng7T7I |
action_result.data.\*.data.attributes.tags.\* | string | | javascript |
action_result.data.\*.data.attributes.threat_severity.last_analysis_date | string | | 1746434580 |
action_result.data.\*.data.attributes.threat_severity.level_description | string | | No severity score data |
action_result.data.\*.data.attributes.threat_severity.threat_severity_level | string | | SEVERITY_NONE |
action_result.data.\*.data.attributes.threat_severity.version | numeric | | 5 |
action_result.data.\*.data.attributes.threat_verdict | string | | VERDICT_UNDETECTED |
action_result.data.\*.data.attributes.tlsh | string | | T1DB85C9B7AC1C19BB1A668C69B42D37E6159D23F79C258FE3B9B1E1827541C4600BF323 |
action_result.data.\*.data.attributes.trid.\*.file_type | string | | file seems to be plain text/ASCII |
action_result.data.\*.data.attributes.trid.\*.probability | numeric | | |
action_result.data.\*.data.attributes.type_description | string | | JavaScript |
action_result.data.\*.data.attributes.type_extension | string | | js |
action_result.data.\*.data.attributes.type_tag | string | | javascript |
action_result.data.\*.data.attributes.type_tags.\* | string | | internet |
action_result.data.\*.data.attributes.vhash | string | | b30568954c3bcd9cc79353e2fa75d276 |
action_result.data.\*.data.id | string | | 9ce61f04df346e8d6cba8da4eca52337c751a344ca3f044418e0d5fae8201743 |
action_result.data.\*.data.links.self | string | `url` | https://www.virustotal.com/api/v3/private/files/22e9da87d52f94e2dbb5509dede7945edd213bbe648e740f55bff8b596017cca |
action_result.data.\*.data.type | string | | private_file |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get ioc report'

Publicly scan and fetch the report for an IP address, URL, domain, or file

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity** | required | Entity (IP, URL, Domain, File [Vault ID in SOAR or MD5/SHA1/SHA256]) to get the report | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` |
**password** | optional | Password to decompress and scan a file contained in a protected ZIP file | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` | |
action_result.parameter.password | string | | |
action_result.data | string | | |
action_result.data.\*.data.attributes.as_owner | string | | CLOUDFLARENET |
action_result.data.\*.data.attributes.asn | numeric | | 13335 |
action_result.data.\*.data.attributes.available_tools.\* | string | | |
action_result.data.\*.data.attributes.categories.BitDefender | string | | searchengines |
action_result.data.\*.data.attributes.categories.Forcepoint ThreatSeeker | string | | search engines and portals |
action_result.data.\*.data.attributes.categories.Sophos | string | | search engines |
action_result.data.\*.data.attributes.categories.alphaMountain.ai | string | | Information Technology, Software Downloads (alphaMountain.ai) |
action_result.data.\*.data.attributes.creation_date | numeric | | 874306800 |
action_result.data.\*.data.attributes.downloadable | boolean | | True |
action_result.data.\*.data.attributes.exiftool.FileType | string | | JSON |
action_result.data.\*.data.attributes.exiftool.FileTypeExtension | string | | json |
action_result.data.\*.data.attributes.exiftool.MIMEType | string | | application/json |
action_result.data.\*.data.attributes.expiration_date | numeric | | 1852516800 |
action_result.data.\*.data.attributes.favicon.dhash | string | | 71cc969aba96cc71 |
action_result.data.\*.data.attributes.favicon.raw_md5 | string | | d3c1e781578a47997a9e9c335baf61b6 |
action_result.data.\*.data.attributes.filecondis.dhash | string | | ecfabad4aaa6828a |
action_result.data.\*.data.attributes.filecondis.raw_md5 | string | | 7b16ae7bb64517faa64147f8e2c2fb43 |
action_result.data.\*.data.attributes.first_seen_itw_date | numeric | | 1721257282 |
action_result.data.\*.data.attributes.first_submission_date | numeric | | 1746526695 |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.associated_malware_configuration | boolean | | True |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.google_malware_analysis | boolean | | True |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.google_mobile_malware_analysis | boolean | | True |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.gti_confidence_score | numeric | | 4 |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.malicious_sandbox_verdict | boolean | | |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.mandiant_analyst_benign | boolean | | True |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.mandiant_confidence_score | numeric | | 2 |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.normalised_categories.\* | string | | control-server |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.pervasive_indicator | boolean | | True |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.safebrowsing_verdict | string | | harmless |
action_result.data.\*.data.attributes.gti_assessment.description | string | | This indicator did not match our detection criteria and there is currently no evidence of malicious activity. |
action_result.data.\*.data.attributes.gti_assessment.severity.value | string | | SEVERITY_NONE |
action_result.data.\*.data.attributes.gti_assessment.threat_score.value | numeric | | 1 |
action_result.data.\*.data.attributes.gti_assessment.verdict.value | string | | VERDICT_UNDETECTED |
action_result.data.\*.data.attributes.has_content | boolean | | |
action_result.data.\*.data.attributes.html_meta.referrer.\* | string | | origin |
action_result.data.\*.data.attributes.jarm | string | | 27d40d40d29d40d1dc42d43d00041d4689ee210389f4f6b4b5b1b93f92252d |
action_result.data.\*.data.attributes.last_analysis_date | numeric | | 1746526695 |
action_result.data.\*.data.attributes.last_analysis_results.0xSI_f33d.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.0xSI_f33d.engine_name | string | | 0xSI_f33d |
action_result.data.\*.data.attributes.last_analysis_results.0xSI_f33d.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.0xSI_f33d.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.ADMINUSLabs.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ADMINUSLabs.engine_name | string | | ADMINUSLabs |
action_result.data.\*.data.attributes.last_analysis_results.ADMINUSLabs.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ADMINUSLabs.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.AILabs (MONITORAPP).category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.AILabs (MONITORAPP).engine_name | string | | AILabs (MONITORAPP) |
action_result.data.\*.data.attributes.last_analysis_results.AILabs (MONITORAPP).method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AILabs (MONITORAPP).result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.engine_name | string | | ALYac |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.engine_version | string | | 2.0.0.10 |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.APEX.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.APEX.engine_name | string | | APEX |
action_result.data.\*.data.attributes.last_analysis_results.APEX.engine_update | string | | 20250504 |
action_result.data.\*.data.attributes.last_analysis_results.APEX.engine_version | string | | 6.651 |
action_result.data.\*.data.attributes.last_analysis_results.APEX.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.APEX.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.AVG.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.AVG.engine_name | string | | AVG |
action_result.data.\*.data.attributes.last_analysis_results.AVG.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.AVG.engine_version | string | | 23.9.8494.0 |
action_result.data.\*.data.attributes.last_analysis_results.AVG.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AVG.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Abusix.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Abusix.engine_name | string | | Abusix |
action_result.data.\*.data.attributes.last_analysis_results.Abusix.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Abusix.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.engine_name | string | | Acronis |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.engine_update | string | | 20240328 |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.engine_version | string | | 1.2.0.121 |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.engine_name | string | | AhnLab-V3 |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.engine_version | string | | 3.27.2.10550 |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.engine_name | string | | Alibaba |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.engine_update | string | | 20190527 |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.engine_version | string | | 0.3.0.5 |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.AlienVault.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.AlienVault.engine_name | string | | AlienVault |
action_result.data.\*.data.attributes.last_analysis_results.AlienVault.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AlienVault.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.AlphaSOC.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.AlphaSOC.engine_name | string | | AlphaSOC |
action_result.data.\*.data.attributes.last_analysis_results.AlphaSOC.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AlphaSOC.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.engine_name | string | | Antiy-AVL |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.engine_version | string | | 3.0 |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ArcSight Threat Intelligence.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ArcSight Threat Intelligence.engine_name | string | | ArcSight Threat Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.ArcSight Threat Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ArcSight Threat Intelligence.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.engine_name | string | | Arcabit |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.engine_version | string | | 2022.0.0.18 |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Artists Against 419.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Artists Against 419.engine_name | string | | Artists Against 419 |
action_result.data.\*.data.attributes.last_analysis_results.Artists Against 419.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Artists Against 419.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.AutoShun.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.AutoShun.engine_name | string | | AutoShun |
action_result.data.\*.data.attributes.last_analysis_results.AutoShun.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AutoShun.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.engine_name | string | | Avast-Mobile |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.engine_version | string | | 250506-00 |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Avast.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Avast.engine_name | string | | Avast |
action_result.data.\*.data.attributes.last_analysis_results.Avast.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Avast.engine_version | string | | 23.9.8494.0 |
action_result.data.\*.data.attributes.last_analysis_results.Avast.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Avast.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Avira.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Avira.engine_name | string | | Avira |
action_result.data.\*.data.attributes.last_analysis_results.Avira.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Avira.engine_version | string | | 8.3.3.20 |
action_result.data.\*.data.attributes.last_analysis_results.Avira.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Avira.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Axur.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Axur.engine_name | string | | Axur |
action_result.data.\*.data.attributes.last_analysis_results.Axur.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Axur.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.engine_name | string | | Baidu |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.engine_update | string | | 20190318 |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.engine_version | string | | 1.0.0.2 |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Bfore.Ai PreCrime.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Bfore.Ai PreCrime.engine_name | string | | Bfore.Ai PreCrime |
action_result.data.\*.data.attributes.last_analysis_results.Bfore.Ai PreCrime.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Bfore.Ai PreCrime.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.engine_name | string | | BitDefender |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.engine_version | string | | 7.2 |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.engine_name | string | | BitDefenderFalx |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.engine_update | string | | 20250416 |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.engine_version | string | | 2.0.936 |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.engine_name | string | | Bkav |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.engine_version | string | | 2.0.0.1 |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.BlockList.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.BlockList.engine_name | string | | BlockList |
action_result.data.\*.data.attributes.last_analysis_results.BlockList.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.BlockList.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Blueliv.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Blueliv.engine_name | string | | Blueliv |
action_result.data.\*.data.attributes.last_analysis_results.Blueliv.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Blueliv.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.engine_name | string | | CAT-QuickHeal |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.engine_version | string | | 22.00 |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.CINS Army.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.CINS Army.engine_name | string | | CINS Army |
action_result.data.\*.data.attributes.last_analysis_results.CINS Army.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CINS Army.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CMC Threat Intelligence.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.CMC Threat Intelligence.engine_name | string | | CMC Threat Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.CMC Threat Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CMC Threat Intelligence.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CMC.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.CMC.engine_name | string | | CMC |
action_result.data.\*.data.attributes.last_analysis_results.CMC.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.CMC.engine_version | string | | 2.4.2022.1 |
action_result.data.\*.data.attributes.last_analysis_results.CMC.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CMC.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.CRDF.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.CRDF.engine_name | string | | CRDF |
action_result.data.\*.data.attributes.last_analysis_results.CRDF.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CRDF.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CSIS Security Group.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.CSIS Security Group.engine_name | string | | CSIS Security Group |
action_result.data.\*.data.attributes.last_analysis_results.CSIS Security Group.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CSIS Security Group.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.CTX.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.CTX.engine_name | string | | CTX |
action_result.data.\*.data.attributes.last_analysis_results.CTX.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.CTX.engine_version | string | | 2024.8.29.1 |
action_result.data.\*.data.attributes.last_analysis_results.CTX.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CTX.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Certego.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Certego.engine_name | string | | Certego |
action_result.data.\*.data.attributes.last_analysis_results.Certego.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Certego.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Chong Lua Dao.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Chong Lua Dao.engine_name | string | | Chong Lua Dao |
action_result.data.\*.data.attributes.last_analysis_results.Chong Lua Dao.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Chong Lua Dao.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.engine_name | string | | ClamAV |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.engine_version | string | | 1.4.2.0 |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Cluster25.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Cluster25.engine_name | string | | Cluster25 |
action_result.data.\*.data.attributes.last_analysis_results.Cluster25.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cluster25.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Criminal IP.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Criminal IP.engine_name | string | | Criminal IP |
action_result.data.\*.data.attributes.last_analysis_results.Criminal IP.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Criminal IP.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.engine_name | string | | CrowdStrike |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.engine_update | string | | 20231026 |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.engine_version | string | | 1.0 |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.CyRadar.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.CyRadar.engine_name | string | | CyRadar |
action_result.data.\*.data.attributes.last_analysis_results.CyRadar.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CyRadar.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Cyan.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Cyan.engine_name | string | | Cyan |
action_result.data.\*.data.attributes.last_analysis_results.Cyan.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cyan.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Cyble.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Cyble.engine_name | string | | Cyble |
action_result.data.\*.data.attributes.last_analysis_results.Cyble.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cyble.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.engine_name | string | | Cylance |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.engine_update | string | | 20250424 |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.engine_version | string | | 3.0.0.0 |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.engine_name | string | | Cynet |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.engine_version | string | | 4.0.3.4 |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.DNS8.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.DNS8.engine_name | string | | DNS8 |
action_result.data.\*.data.attributes.last_analysis_results.DNS8.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.DNS8.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.engine_name | string | | DeepInstinct |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.engine_version | string | | 5.0.0.8 |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Dr.Web.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Dr.Web.engine_name | string | | Dr.Web |
action_result.data.\*.data.attributes.last_analysis_results.Dr.Web.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Dr.Web.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.engine_name | string | | DrWeb |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.engine_version | string | | 7.0.67.2170 |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.engine_name | string | | ESET-NOD32 |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.engine_version | string | | 31151 |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ESET.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ESET.engine_name | string | | ESET |
action_result.data.\*.data.attributes.last_analysis_results.ESET.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ESET.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.ESTsecurity.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ESTsecurity.engine_name | string | | ESTsecurity |
action_result.data.\*.data.attributes.last_analysis_results.ESTsecurity.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ESTsecurity.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.engine_name | string | | Elastic |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.engine_version | string | | 4.0.203 |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.EmergingThreats.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.EmergingThreats.engine_name | string | | EmergingThreats |
action_result.data.\*.data.attributes.last_analysis_results.EmergingThreats.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.EmergingThreats.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.engine_name | string | | Emsisoft |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.engine_version | string | | 2024.8.0.61147 |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Ermes.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Ermes.engine_name | string | | Ermes |
action_result.data.\*.data.attributes.last_analysis_results.Ermes.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Ermes.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.engine_name | string | | F-Secure |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.engine_version | string | | 18.10.1547.307 |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Feodo Tracker.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Feodo Tracker.engine_name | string | | Feodo Tracker |
action_result.data.\*.data.attributes.last_analysis_results.Feodo Tracker.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Feodo Tracker.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Forcepoint ThreatSeeker.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Forcepoint ThreatSeeker.engine_name | string | | Forcepoint ThreatSeeker |
action_result.data.\*.data.attributes.last_analysis_results.Forcepoint ThreatSeeker.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Forcepoint ThreatSeeker.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.engine_name | string | | Fortinet |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.engine_version | string | | 7.0.30.0 |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.G-Data.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.G-Data.engine_name | string | | G-Data |
action_result.data.\*.data.attributes.last_analysis_results.G-Data.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.G-Data.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.GCP Abuse Intelligence.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.GCP Abuse Intelligence.engine_name | string | | GCP Abuse Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.GCP Abuse Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.GCP Abuse Intelligence.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.GData.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.GData.engine_name | string | | GData |
action_result.data.\*.data.attributes.last_analysis_results.GData.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.GData.engine_version | string | | GD:27.40226AVA:64.29147 |
action_result.data.\*.data.attributes.last_analysis_results.GData.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.GData.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Google Safebrowsing.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Google Safebrowsing.engine_name | string | | Google Safebrowsing |
action_result.data.\*.data.attributes.last_analysis_results.Google Safebrowsing.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Google Safebrowsing.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Google.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Google.engine_name | string | | Google |
action_result.data.\*.data.attributes.last_analysis_results.Google.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Google.engine_version | string | | 1746520242 |
action_result.data.\*.data.attributes.last_analysis_results.Google.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Google.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.GreenSnow.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.GreenSnow.engine_name | string | | GreenSnow |
action_result.data.\*.data.attributes.last_analysis_results.GreenSnow.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.GreenSnow.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.engine_name | string | | Gridinsoft |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.engine_version | string | | 1.0.216.174 |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Heimdal Security.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Heimdal Security.engine_name | string | | Heimdal Security |
action_result.data.\*.data.attributes.last_analysis_results.Heimdal Security.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Heimdal Security.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Hunt.io Intelligence.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Hunt.io Intelligence.engine_name | string | | Hunt.io Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.Hunt.io Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Hunt.io Intelligence.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.IPsum.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.IPsum.engine_name | string | | IPsum |
action_result.data.\*.data.attributes.last_analysis_results.IPsum.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.IPsum.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.engine_name | string | | Ikarus |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.engine_version | string | | 6.3.30.0 |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.engine_name | string | | Jiangmin |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.engine_version | string | | 16.0.100 |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Juniper Networks.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Juniper Networks.engine_name | string | | Juniper Networks |
action_result.data.\*.data.attributes.last_analysis_results.Juniper Networks.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Juniper Networks.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.engine_name | string | | K7AntiVirus |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.engine_version | string | | 12.234.55658 |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.engine_name | string | | K7GW |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.engine_version | string | | 12.234.55659 |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.engine_name | string | | Kaspersky |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.engine_version | string | | 22.0.1.28 |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.engine_name | string | | Kingsoft |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.engine_version | string | | None |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.engine_name | string | | Lionic |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.engine_version | string | | 8.16 |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Lumu.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Lumu.engine_name | string | | Lumu |
action_result.data.\*.data.attributes.last_analysis_results.Lumu.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Lumu.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.MalwarePatrol.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.MalwarePatrol.engine_name | string | | MalwarePatrol |
action_result.data.\*.data.attributes.last_analysis_results.MalwarePatrol.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.MalwarePatrol.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.MalwareURL.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.MalwareURL.engine_name | string | | MalwareURL |
action_result.data.\*.data.attributes.last_analysis_results.MalwareURL.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.MalwareURL.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.engine_name | string | | Malwarebytes |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.engine_version | string | | 4.5.5.54 |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Malwared.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Malwared.engine_name | string | | Malwared |
action_result.data.\*.data.attributes.last_analysis_results.Malwared.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Malwared.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.engine_name | string | | MaxSecure |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.engine_version | string | | 1.0.0.1 |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.engine_name | string | | McAfee |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.engine_version | string | | 6.0.6.653 |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.engine_name | string | | McAfeeD |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.engine_version | string | | 1.2.0.7977 |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.engine_name | string | | MicroWorld-eScan |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.engine_version | string | | 14.0.409.0 |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.engine_name | string | | Microsoft |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.engine_version | string | | 1.1.25030.1 |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Mimecast.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Mimecast.engine_name | string | | Mimecast |
action_result.data.\*.data.attributes.last_analysis_results.Mimecast.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Mimecast.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.engine_name | string | | NANO-Antivirus |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.engine_version | string | | 1.0.170.26531 |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Netcraft.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Netcraft.engine_name | string | | Netcraft |
action_result.data.\*.data.attributes.last_analysis_results.Netcraft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Netcraft.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.OpenPhish.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.OpenPhish.engine_name | string | | OpenPhish |
action_result.data.\*.data.attributes.last_analysis_results.OpenPhish.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.OpenPhish.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.PREBYTES.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.PREBYTES.engine_name | string | | PREBYTES |
action_result.data.\*.data.attributes.last_analysis_results.PREBYTES.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.PREBYTES.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.engine_name | string | | Paloalto |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.engine_version | string | | 0.9.0.1003 |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Panda.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Panda.engine_name | string | | Panda |
action_result.data.\*.data.attributes.last_analysis_results.Panda.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.Panda.engine_version | string | | 4.6.4.2 |
action_result.data.\*.data.attributes.last_analysis_results.Panda.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Panda.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.PhishFort.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.PhishFort.engine_name | string | | PhishFort |
action_result.data.\*.data.attributes.last_analysis_results.PhishFort.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.PhishFort.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.PhishLabs.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.PhishLabs.engine_name | string | | PhishLabs |
action_result.data.\*.data.attributes.last_analysis_results.PhishLabs.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.PhishLabs.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Phishing Database.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Phishing Database.engine_name | string | | Phishing Database |
action_result.data.\*.data.attributes.last_analysis_results.Phishing Database.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Phishing Database.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Phishtank.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Phishtank.engine_name | string | | Phishtank |
action_result.data.\*.data.attributes.last_analysis_results.Phishtank.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Phishtank.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.PrecisionSec.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.PrecisionSec.engine_name | string | | PrecisionSec |
action_result.data.\*.data.attributes.last_analysis_results.PrecisionSec.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.PrecisionSec.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Quick Heal.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Quick Heal.engine_name | string | | Quick Heal |
action_result.data.\*.data.attributes.last_analysis_results.Quick Heal.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Quick Heal.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Quttera.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Quttera.engine_name | string | | Quttera |
action_result.data.\*.data.attributes.last_analysis_results.Quttera.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Quttera.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Rising.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Rising.engine_name | string | | Rising |
action_result.data.\*.data.attributes.last_analysis_results.Rising.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Rising.engine_version | string | | 25.0.0.28 |
action_result.data.\*.data.attributes.last_analysis_results.Rising.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Rising.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.SCUMWARE.org.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.SCUMWARE.org.engine_name | string | | SCUMWARE.org |
action_result.data.\*.data.attributes.last_analysis_results.SCUMWARE.org.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SCUMWARE.org.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.SOCRadar.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.SOCRadar.engine_name | string | | SOCRadar |
action_result.data.\*.data.attributes.last_analysis_results.SOCRadar.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SOCRadar.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.engine_name | string | | SUPERAntiSpyware |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.engine_version | string | | 5.6.0.1032 |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.SafeToOpen.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.SafeToOpen.engine_name | string | | SafeToOpen |
action_result.data.\*.data.attributes.last_analysis_results.SafeToOpen.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SafeToOpen.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.engine_name | string | | Sangfor |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.engine_update | string | | 20250430 |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.engine_version | string | | 2.22.3.0 |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Sansec eComscan.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Sansec eComscan.engine_name | string | | Sansec eComscan |
action_result.data.\*.data.attributes.last_analysis_results.Sansec eComscan.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Sansec eComscan.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Scantitan.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Scantitan.engine_name | string | | Scantitan |
action_result.data.\*.data.attributes.last_analysis_results.Scantitan.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Scantitan.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Seclookup.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Seclookup.engine_name | string | | Seclookup |
action_result.data.\*.data.attributes.last_analysis_results.Seclookup.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Seclookup.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.SecureBrain.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.SecureBrain.engine_name | string | | SecureBrain |
action_result.data.\*.data.attributes.last_analysis_results.SecureBrain.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SecureBrain.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.engine_name | string | | SentinelOne |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.engine_update | string | | 20250114 |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.engine_version | string | | 25.1.1.1 |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.engine_name | string | | Skyhigh |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.engine_version | string | | v2021.2.0+4045 |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Snort IP sample list.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Snort IP sample list.engine_name | string | | Snort IP sample list |
action_result.data.\*.data.attributes.last_analysis_results.Snort IP sample list.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Snort IP sample list.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.engine_name | string | | Sophos |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.engine_version | string | | 3.0.3.0 |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Spam404.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Spam404.engine_name | string | | Spam404 |
action_result.data.\*.data.attributes.last_analysis_results.Spam404.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Spam404.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.StopForumSpam.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.StopForumSpam.engine_name | string | | StopForumSpam |
action_result.data.\*.data.attributes.last_analysis_results.StopForumSpam.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.StopForumSpam.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Sucuri SiteCheck.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Sucuri SiteCheck.engine_name | string | | Sucuri SiteCheck |
action_result.data.\*.data.attributes.last_analysis_results.Sucuri SiteCheck.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Sucuri SiteCheck.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.engine_name | string | | Symantec |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.engine_version | string | | 1.22.0.0 |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.engine_name | string | | SymantecMobileInsight |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.engine_update | string | | 20250124 |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.engine_version | string | | 2.0 |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.engine_name | string | | TACHYON |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.engine_version | string | | 2025-05-06.02 |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.engine_name | string | | Tencent |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.engine_version | string | | 1.0.0.1 |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ThreatHive.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ThreatHive.engine_name | string | | ThreatHive |
action_result.data.\*.data.attributes.last_analysis_results.ThreatHive.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ThreatHive.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Threatsourcing.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Threatsourcing.engine_name | string | | Threatsourcing |
action_result.data.\*.data.attributes.last_analysis_results.Threatsourcing.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Threatsourcing.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.engine_name | string | | Trapmine |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.engine_update | string | | 20250417 |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.engine_version | string | | 4.0.4.0 |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.engine_name | string | | TrendMicro-HouseCall |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.engine_version | string | | 24.550.0.1002 |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.engine_name | string | | TrendMicro |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.engine_version | string | | 24.550.0.1002 |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.engine_name | string | | Trustlook |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.engine_version | string | | 1.0 |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Trustwave.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Trustwave.engine_name | string | | Trustwave |
action_result.data.\*.data.attributes.last_analysis_results.Trustwave.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Trustwave.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.URLQuery.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.URLQuery.engine_name | string | | URLQuery |
action_result.data.\*.data.attributes.last_analysis_results.URLQuery.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.URLQuery.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.URLhaus.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.URLhaus.engine_name | string | | URLhaus |
action_result.data.\*.data.attributes.last_analysis_results.URLhaus.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.URLhaus.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Underworld.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Underworld.engine_name | string | | Underworld |
action_result.data.\*.data.attributes.last_analysis_results.Underworld.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Underworld.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.engine_name | string | | VBA32 |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.engine_version | string | | 5.3.2 |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.engine_name | string | | VIPRE |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.engine_version | string | | 6.0.0.35 |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.VX Vault.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.VX Vault.engine_name | string | | VX Vault |
action_result.data.\*.data.attributes.last_analysis_results.VX Vault.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.VX Vault.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Varist.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Varist.engine_name | string | | Varist |
action_result.data.\*.data.attributes.last_analysis_results.Varist.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Varist.engine_version | string | | 6.6.1.3 |
action_result.data.\*.data.attributes.last_analysis_results.Varist.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Varist.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.engine_name | string | | ViRobot |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.engine_version | string | | 2014.3.20.0 |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Viettel Threat Intelligence.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Viettel Threat Intelligence.engine_name | string | | Viettel Threat Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.Viettel Threat Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Viettel Threat Intelligence.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.engine_name | string | | VirIT |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.engine_version | string | | 9.5.947 |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ViriBack.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ViriBack.engine_name | string | | ViriBack |
action_result.data.\*.data.attributes.last_analysis_results.ViriBack.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ViriBack.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.engine_name | string | | Webroot |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.engine_update | string | | 20250227 |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.engine_version | string | | 1.9.0.8 |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium Verdict Cloud.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium Verdict Cloud.engine_name | string | | Xcitium Verdict Cloud |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium Verdict Cloud.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium Verdict Cloud.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.engine_name | string | | Xcitium |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.engine_version | string | | 37705 |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Yandex Safebrowsing.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Yandex Safebrowsing.engine_name | string | | Yandex Safebrowsing |
action_result.data.\*.data.attributes.last_analysis_results.Yandex Safebrowsing.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Yandex Safebrowsing.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.engine_name | string | | Yandex |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.engine_version | string | | 5.5.2.24 |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ZeroCERT.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ZeroCERT.engine_name | string | | ZeroCERT |
action_result.data.\*.data.attributes.last_analysis_results.ZeroCERT.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ZeroCERT.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.ZeroFox.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ZeroFox.engine_name | string | | ZeroFox |
action_result.data.\*.data.attributes.last_analysis_results.ZeroFox.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ZeroFox.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.engine_name | string | | Zillya |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.engine_version | string | | 2.0.0.5353 |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.engine_name | string | | ZoneAlarm |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.engine_version | string | | 6.15-102623199 |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.engine_name | string | | Zoner |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.engine_version | string | | 2.2.2.0 |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.engine_name | string | | alibabacloud |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.engine_update | string | | 20250321 |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.engine_version | string | | 2.2.0 |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.alphaMountain.ai.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.alphaMountain.ai.engine_name | string | | alphaMountain.ai |
action_result.data.\*.data.attributes.last_analysis_results.alphaMountain.ai.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.alphaMountain.ai.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.benkow.cc.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.benkow.cc.engine_name | string | | benkow.cc |
action_result.data.\*.data.attributes.last_analysis_results.benkow.cc.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.benkow.cc.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.desenmascara.me.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.desenmascara.me.engine_name | string | | desenmascara.me |
action_result.data.\*.data.attributes.last_analysis_results.desenmascara.me.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.desenmascara.me.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.engine_name | string | | google_safebrowsing |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.engine_version | string | | 1.0 |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.huorong.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.huorong.engine_name | string | | huorong |
action_result.data.\*.data.attributes.last_analysis_results.huorong.engine_update | string | | 20250504 |
action_result.data.\*.data.attributes.last_analysis_results.huorong.engine_version | string | | 05a2669:05a2669:8b1400d:8b1400d |
action_result.data.\*.data.attributes.last_analysis_results.huorong.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.huorong.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.malwares.com URL checker.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.malwares.com URL checker.engine_name | string | | malwares.com URL checker |
action_result.data.\*.data.attributes.last_analysis_results.malwares.com URL checker.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.malwares.com URL checker.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.securolytics.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.securolytics.engine_name | string | | securolytics |
action_result.data.\*.data.attributes.last_analysis_results.securolytics.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.securolytics.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.engine_name | string | | tehtris |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.engine_update | string | | 20250506 |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.engine_version | string | | v0.1.4 |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.zvelo.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.zvelo.engine_name | string | | zvelo |
action_result.data.\*.data.attributes.last_analysis_results.zvelo.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.zvelo.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_stats.confirmed-timeout | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.failure | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.harmless | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.malicious | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.suspicious | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.timeout | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.type-unsupported | numeric | | 15 |
action_result.data.\*.data.attributes.last_analysis_stats.undetected | numeric | | 62 |
action_result.data.\*.data.attributes.last_analysis_stats_string | string | | |
action_result.data.\*.data.attributes.last_dns_records.\*.ttl | numeric | | 300 |
action_result.data.\*.data.attributes.last_dns_records.\*.type | string | | AAAA |
action_result.data.\*.data.attributes.last_dns_records.\*.value | string | | 2607:f8b0:4001:c11::71 |
action_result.data.\*.data.attributes.last_dns_records_date | numeric | | 1746524055 |
action_result.data.\*.data.attributes.last_final_url | string | | https://www.google.com/ |
action_result.data.\*.data.attributes.last_http_response_code | numeric | | 200 |
action_result.data.\*.data.attributes.last_http_response_content_length | numeric | | 198666 |
action_result.data.\*.data.attributes.last_http_response_content_sha256 | string | | 92fc8db0bf5166be24a6901c0fc0ba7fdba020eac33a197bccfebbc32263d58f |
action_result.data.\*.data.attributes.last_http_response_cookies.AEC | string | | AVcja2cquOPrNkwHOugfcDIVqJgU1Bk9HG4qWaxaAjiIHbAY_80XE69wNg |
action_result.data.\*.data.attributes.last_http_response_cookies.NID | string | | 523=Nmm1SfRZ13CGW141MzFEmM5O08sWuuUi7p5ECQtAVO2M2DBetCn42lyDsST-WJG1UO9elk_AtgWFfIjHsAnrMWFDKx6etCgg30uoN9mUFCEC-lCwhLas91eq5x2vW1xP9VRFXYVNnFtB0b3cxz4IrLty9jErZUqpP6MqUWa-E1jEYY4UWsaEURWaLKs |
action_result.data.\*.data.attributes.last_http_response_headers.Accept-CH | string | | Sec-CH-Prefers-Color-Scheme, Downlink, RTT, Sec-CH-UA-Form-Factors, Sec-CH-UA-Platform, Sec-CH-UA-Platform-Version, Sec-CH-UA-Full-Version, Sec-CH-UA-Arch, Sec-CH-UA-Model, Sec-CH-UA-Bitness, Sec-CH-UA-Full-Version-List, Sec-CH-UA-WoW64 |
action_result.data.\*.data.attributes.last_http_response_headers.Alt-Svc | string | | h3=":443"; ma=2592000,h3-29=":443"; ma=2592000 |
action_result.data.\*.data.attributes.last_http_response_headers.Cache-Control | string | | private, max-age=0 |
action_result.data.\*.data.attributes.last_http_response_headers.Content-Encoding | string | | br |
action_result.data.\*.data.attributes.last_http_response_headers.Content-Security-Policy-Report-Only | string | | object-src 'none';base-uri 'self';script-src 'nonce-dVdim92YlfFLLMe2EpyP1g' 'strict-dynamic' 'report-sample' 'unsafe-eval' 'unsafe-inline' https: http:;report-uri https://csp.withgoogle.com/csp/gws/other-hp |
action_result.data.\*.data.attributes.last_http_response_headers.Content-Type | string | | text/html; charset=UTF-8 |
action_result.data.\*.data.attributes.last_http_response_headers.Cross-Origin-Opener-Policy | string | | same-origin-allow-popups; report-to="gws" |
action_result.data.\*.data.attributes.last_http_response_headers.Date | string | | Tue, 06 May 2025 09:31:28 GMT |
action_result.data.\*.data.attributes.last_http_response_headers.Expires | string | | -1 |
action_result.data.\*.data.attributes.last_http_response_headers.P3P | string | | CP="This is not a P3P policy! See g.co/p3phelp for more info." |
action_result.data.\*.data.attributes.last_http_response_headers.Permissions-Policy | string | | unload=() |
action_result.data.\*.data.attributes.last_http_response_headers.Report-To | string | | {"group":"gws","max_age":2592000,"endpoints":[{"url":"https://csp.withgoogle.com/csp/report-to/gws/other"}]} |
action_result.data.\*.data.attributes.last_http_response_headers.Server | string | | gws |
action_result.data.\*.data.attributes.last_http_response_headers.Set-Cookie | string | | Dummy Cookie |
action_result.data.\*.data.attributes.last_http_response_headers.Transfer-Encoding | string | | chunked |
action_result.data.\*.data.attributes.last_http_response_headers.X-Frame-Options | string | | SAMEORIGIN |
action_result.data.\*.data.attributes.last_http_response_headers.X-XSS-Protection | string | | 0 |
action_result.data.\*.data.attributes.last_https_certificate.cert_signature.signature | string | | 59caa8592520904856ba0f0af57249fc4405757e98e824b705df26a13ec5c2f80000f40ddd03b5dbf9f3b3b67c5f929fae1bb0c6d9c6a26d531835aad0ad180cecca3001673e87001988147e0700f61e67dd852af1b37507a5a00f73d0f94125d5e568671bae3198dfa72bfc649b708bd740d64d43ef37b9bfe0ff071e4db91cbc706224b57938c77ca6331d17a7a21816714f2421674e34f471911c420b294273d75a12748d6fc378fe0798421e248bf807aada2b687fc5b031abf334183c8ed84ffc19c404edfd65d1dcae4aa9f0e1ae40d6b1ff2cc063b65cb60c8084f6a5491bef80d01f28d84a3b7930a7fa6c5870bf909090370c2a2449dc55381ef207 |
action_result.data.\*.data.attributes.last_https_certificate.cert_signature.signature_algorithm | string | | sha256RSA |
action_result.data.\*.data.attributes.last_https_certificate.extensions.1.3.6.1.4.1.11129.2.4.2 | string | | 0481f200f0007600cf1156eed52e7caff3875bd9692e9be91a71674ab017ecac |
action_result.data.\*.data.attributes.last_https_certificate.extensions.CA | boolean | | |
action_result.data.\*.data.attributes.last_https_certificate.extensions.authority_key_identifier.keyid | string | | de1b1eed7915d43e3724c321bbec34396d42b230 |
action_result.data.\*.data.attributes.last_https_certificate.extensions.ca_information_access.CA Issuers | string | | http://i.pki.goog/wr2.crt |
action_result.data.\*.data.attributes.last_https_certificate.extensions.ca_information_access.OCSP | string | | http://o.pki.goog/wr2 |
action_result.data.\*.data.attributes.last_https_certificate.extensions.certificate_policies.\* | string | | 2.23.140.1.2.1 |
action_result.data.\*.data.attributes.last_https_certificate.extensions.crl_distribution_points.\* | string | | http://c.pki.goog/wr2/GSyT1N4PBrg.crl |
action_result.data.\*.data.attributes.last_https_certificate.extensions.extended_key_usage.\* | string | | serverAuth |
action_result.data.\*.data.attributes.last_https_certificate.extensions.key_usage.\* | string | | digitalSignature |
action_result.data.\*.data.attributes.last_https_certificate.extensions.subject_alternative_name.\* | string | | \*.google.com |
action_result.data.\*.data.attributes.last_https_certificate.extensions.subject_key_identifier | string | | 38e7e06e8a5fcbf12e3660de676955d7ba477bd2 |
action_result.data.\*.data.attributes.last_https_certificate.issuer.C | string | | US |
action_result.data.\*.data.attributes.last_https_certificate.issuer.CN | string | | WR2 |
action_result.data.\*.data.attributes.last_https_certificate.issuer.O | string | | Google Trust Services |
action_result.data.\*.data.attributes.last_https_certificate.public_key.algorithm | string | | EC |
action_result.data.\*.data.attributes.last_https_certificate.public_key.ec.oid | string | | secp256r1 |
action_result.data.\*.data.attributes.last_https_certificate.public_key.ec.pub | string | | 3059301306072a8648ce3d020106082a8648ce3d0301070342000414d33cad66329930bd593493048ef3613096629085921a70958af78e08b500b5965cee69f8fd1cda2f6af16e44e4e220d46df57eea8f8755b0de233c6bcaae4b |
action_result.data.\*.data.attributes.last_https_certificate.serial_number | string | | b29e43b2ac795ce3099a2e878a3f58c1 |
action_result.data.\*.data.attributes.last_https_certificate.size | numeric | | 3622 |
action_result.data.\*.data.attributes.last_https_certificate.subject.C | string | | US |
action_result.data.\*.data.attributes.last_https_certificate.subject.CN | string | | \*.google.com |
action_result.data.\*.data.attributes.last_https_certificate.subject.L | string | | San Francisco |
action_result.data.\*.data.attributes.last_https_certificate.subject.O | string | | Cloudflare, Inc. |
action_result.data.\*.data.attributes.last_https_certificate.subject.ST | string | | California |
action_result.data.\*.data.attributes.last_https_certificate.thumbprint | string | | 7ecd6a9e9e006a4252cc9d14811c68d4b9c4a473 |
action_result.data.\*.data.attributes.last_https_certificate.thumbprint_sha256 | string | `sha256` | d263c5f65811fcf22b6cdb13d1cc4d3f160a2d0478d36d840f043feaff48e74d |
action_result.data.\*.data.attributes.last_https_certificate.validity.not_after | string | | 2025-06-23 08:54:28 |
action_result.data.\*.data.attributes.last_https_certificate.validity.not_before | string | | 2025-03-31 08:54:29 |
action_result.data.\*.data.attributes.last_https_certificate.version | string | | V3 |
action_result.data.\*.data.attributes.last_https_certificate_date | numeric | | 1746524055 |
action_result.data.\*.data.attributes.last_modification_date | numeric | | 1746526738 |
action_result.data.\*.data.attributes.last_seen_itw_date | numeric | | 1721257282 |
action_result.data.\*.data.attributes.last_submission_date | numeric | | 1746526695 |
action_result.data.\*.data.attributes.last_update_date | numeric | | 1722565053 |
action_result.data.\*.data.attributes.magic | string | | JSON text data |
action_result.data.\*.data.attributes.magika | string | | JSON |
action_result.data.\*.data.attributes.mandiant_ic_score | numeric | | 2 |
action_result.data.\*.data.attributes.md5 | string | `md5` | deef1d19827a8c06f2a4652320250225 |
action_result.data.\*.data.attributes.meaningful_name | string | | google-threat-intelligence-scan-private-file.json |
action_result.data.\*.data.attributes.names.\* | string | | google-threat-intelligence-scan-private-file.json |
action_result.data.\*.data.attributes.network | string | | 1.1.1.0/24 |
action_result.data.\*.data.attributes.outgoing_links.\* | string | | Dummy Link |
action_result.data.\*.data.attributes.popularity_ranks.Alexa.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Alexa.timestamp | numeric | | 1684083480 |
action_result.data.\*.data.attributes.popularity_ranks.Cisco Umbrella.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Cisco Umbrella.timestamp | numeric | | 1746455889 |
action_result.data.\*.data.attributes.popularity_ranks.Cloudflare Radar.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Cloudflare Radar.timestamp | numeric | | 1746455886 |
action_result.data.\*.data.attributes.popularity_ranks.Majestic.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Majestic.timestamp | numeric | | 1746455886 |
action_result.data.\*.data.attributes.popularity_ranks.Quantcast.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Quantcast.timestamp | numeric | | 1585755370 |
action_result.data.\*.data.attributes.popularity_ranks.Statvoo.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Statvoo.timestamp | numeric | | 1684083481 |
action_result.data.\*.data.attributes.rdap.entities.\*.as_event_actor.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.autnums.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.entities.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.events.\*.event_action | string | | last changed |
action_result.data.\*.data.attributes.rdap.entities.\*.events.\*.event_actor | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.events.\*.event_date | string | | 2017-12-11T15:40:13.000+00:00 |
action_result.data.\*.data.attributes.rdap.entities.\*.events.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.handle | string | | 2138514_DOMAIN_COM-VRSN |
action_result.data.\*.data.attributes.rdap.entities.\*.lang | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.networks.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.object_class_name | string | | entity |
action_result.data.\*.data.attributes.rdap.entities.\*.port43 | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.public_ids.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.rdap_conformance.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.remarks.\*.description.\* | string | | Some of the data in this object has been removed. |
action_result.data.\*.data.attributes.rdap.entities.\*.remarks.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.remarks.\*.title | string | | REDACTED FOR PRIVACY |
action_result.data.\*.data.attributes.rdap.entities.\*.remarks.\*.type | string | | object redacted due to authorization |
action_result.data.\*.data.attributes.rdap.entities.\*.roles.\* | string | | administrative |
action_result.data.\*.data.attributes.rdap.entities.\*.status.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.url | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.vcard_array.\*.name | string | | version |
action_result.data.\*.data.attributes.rdap.entities.\*.vcard_array.\*.type | string | | text |
action_result.data.\*.data.attributes.rdap.entities.\*.vcard_array.\*.values.\* | string | | 4.0 |
action_result.data.\*.data.attributes.rdap.events.\*.event_action | string | | expiration |
action_result.data.\*.data.attributes.rdap.events.\*.event_actor | string | | |
action_result.data.\*.data.attributes.rdap.events.\*.event_date | string | | 2028-09-13T07:00:00.000+00:00 |
action_result.data.\*.data.attributes.rdap.events.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.handle | string | | 2138514_DOMAIN_COM-VRSN |
action_result.data.\*.data.attributes.rdap.lang | string | | |
action_result.data.\*.data.attributes.rdap.ldh_name | string | | google.com |
action_result.data.\*.data.attributes.rdap.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.entities.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.events.\*.event_action | string | | last changed |
action_result.data.\*.data.attributes.rdap.nameservers.\*.events.\*.event_actor | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.events.\*.event_date | string | | 2008-06-08T04:46:18.000+00:00 |
action_result.data.\*.data.attributes.rdap.nameservers.\*.events.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.handle | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.lang | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.ldh_name | string | | ns1.google.com |
action_result.data.\*.data.attributes.rdap.nameservers.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.notices.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.object_class_name | string | | nameserver |
action_result.data.\*.data.attributes.rdap.nameservers.\*.port43 | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.remarks.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.status.\* | string | | active |
action_result.data.\*.data.attributes.rdap.nameservers.\*.unicode_name | string | | |
action_result.data.\*.data.attributes.rdap.nask0_state | string | | |
action_result.data.\*.data.attributes.rdap.notices.\*.description.\* | string | | By submitting an RDAP query, you agree that you will use this data only for |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.href | string | | https://www.markmonitor.com/legal/domain-management-terms-and-conditions |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.href_lang.\* | string | | |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.media | string | | |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.rel | string | | related |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.title | string | | |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.type | string | | text/html |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.value | string | | https://www.markmonitor.com/legal/domain-management-terms-and-conditions |
action_result.data.\*.data.attributes.rdap.notices.\*.title | string | | Terms of Use |
action_result.data.\*.data.attributes.rdap.notices.\*.type | string | | |
action_result.data.\*.data.attributes.rdap.object_class_name | string | | domain |
action_result.data.\*.data.attributes.rdap.port43 | string | | whois.markmonitor.com |
action_result.data.\*.data.attributes.rdap.public_ids.\* | string | | |
action_result.data.\*.data.attributes.rdap.punycode | string | | |
action_result.data.\*.data.attributes.rdap.rdap_conformance.\* | string | | rdap_level_0 |
action_result.data.\*.data.attributes.rdap.remarks.\* | string | | |
action_result.data.\*.data.attributes.rdap.secure_dns.delegation_signed | boolean | | |
action_result.data.\*.data.attributes.rdap.secure_dns.ds_data.\* | string | | |
action_result.data.\*.data.attributes.rdap.secure_dns.key_data.\* | string | | |
action_result.data.\*.data.attributes.rdap.secure_dns.max_sig_life | numeric | | |
action_result.data.\*.data.attributes.rdap.secure_dns.zone_signed | boolean | | |
action_result.data.\*.data.attributes.rdap.status.\* | string | | client update prohibited |
action_result.data.\*.data.attributes.rdap.switch_name | string | | |
action_result.data.\*.data.attributes.rdap.type | string | | |
action_result.data.\*.data.attributes.rdap.unicode_name | string | | |
action_result.data.\*.data.attributes.rdap.variants.\* | string | | |
action_result.data.\*.data.attributes.redirection_chain.\* | string | | https://www.dummyurl.com |
action_result.data.\*.data.attributes.registrar | string | | MarkMonitor Inc. |
action_result.data.\*.data.attributes.reputation | numeric | | |
action_result.data.\*.data.attributes.sha1 | string | `vault id` `sha1` | 408eeb7bab699baa4aa58352d1eec911dfc44506 |
action_result.data.\*.data.attributes.sha256 | string | `sha256` | 97997eac8c6143f9fdabf9de53d0b0b9b019c5fde510a67a7bcc2e99034432b0 |
action_result.data.\*.data.attributes.size | numeric | | 3653 |
action_result.data.\*.data.attributes.ssdeep | string | | 96:CXxXKIrUi4Ul+sNd/YNWoOoNXP/R0H9Pz5MQFTSJ/Hf/xI:OvUiQ0YKyXP/R6Pz5vYtBI |
action_result.data.\*.data.attributes.tags | string | | json |
action_result.data.\*.data.attributes.threat_names.\* | string | | |
action_result.data.\*.data.attributes.threat_severity.last_analysis_date | string | | 1746526737 |
action_result.data.\*.data.attributes.threat_severity.level_description | string | | No severity score data |
action_result.data.\*.data.attributes.threat_severity.threat_severity_data.belongs_to_bad_collection | boolean | | True |
action_result.data.\*.data.attributes.threat_severity.threat_severity_data.domain_rank | string | | 1 |
action_result.data.\*.data.attributes.threat_severity.threat_severity_data.has_bad_communicating_files_high | boolean | | True |
action_result.data.\*.data.attributes.threat_severity.threat_severity_data.has_bad_communicating_files_medium | boolean | | True |
action_result.data.\*.data.attributes.threat_severity.threat_severity_level | string | | SEVERITY_NONE |
action_result.data.\*.data.attributes.threat_severity.version | numeric | | 5 |
action_result.data.\*.data.attributes.times_submitted | numeric | | 1 |
action_result.data.\*.data.attributes.title | string | | Google |
action_result.data.\*.data.attributes.tld | string | | com |
action_result.data.\*.data.attributes.tlsh | string | | T19371B6737D1B827301C678E2656B0A4BF322936813D4DD0A9ED8490C065DEB4B1DBBDA |
action_result.data.\*.data.attributes.total_votes.harmless | numeric | | |
action_result.data.\*.data.attributes.total_votes.malicious | numeric | | |
action_result.data.\*.data.attributes.trid.\*.file_type | string | | Generic INI configuration |
action_result.data.\*.data.attributes.trid.\*.probability | numeric | | 100 |
action_result.data.\*.data.attributes.type_description | string | | JSON |
action_result.data.\*.data.attributes.type_extension | string | | json |
action_result.data.\*.data.attributes.type_tag | string | | json |
action_result.data.\*.data.attributes.type_tags.\* | string | | internet |
action_result.data.\*.data.attributes.unique_sources | numeric | | 1 |
action_result.data.\*.data.attributes.url | string | | https://www.google.com/ |
action_result.data.\*.data.attributes.whois | string | | Dummy Whois |
action_result.data.\*.data.attributes.whois_date | numeric | | 1744028954 |
action_result.data.\*.data.id | string | | 97997eac8c6143f9fdabf9de53d0b0b9b019c5fde510a67a7bcc2e99034432b0 |
action_result.data.\*.data.links.self | string | `url` | https://www.virustotal.com/api/v3/files/97997eac8c6143f9fdabf9de53d0b0b9b019c5fde510a67a7bcc2e99034432b0 |
action_result.data.\*.data.type | string | | file |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get comments'

Fetch comments for an IP address, URL, domain, or file

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity** | required | Entity (IP, URL, Domain, File [Vault ID in SOAR or MD5/SHA1/SHA256]) to get the report | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` |
**password** | optional | Password to decompress and scan a file contained in a protected ZIP file | string | |
**limit** | optional | Maximum comments to be fetched | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` | |
action_result.parameter.limit | string | | 40 |
action_result.parameter.password | string | | |
action_result.data | string | | |
action_result.data.\*.attributes.date | numeric | | 1740599030 |
action_result.data.\*.attributes.html | string | | rest |
action_result.data.\*.attributes.tags | string | | |
action_result.data.\*.attributes.text | string | | rest |
action_result.data.\*.attributes.votes.abuse | numeric | | |
action_result.data.\*.attributes.votes.negative | numeric | | |
action_result.data.\*.attributes.votes.positive | numeric | | |
action_result.data.\*.data.\*.type | string | | comment |
action_result.data.\*.id | string | | u-d0e196a0c25d35dd0a84593cbae0f38333aa58529936444ea26453eab28dfc86-ac125607 |
action_result.data.\*.links.next | string | `url` | https://www.virustotal.com/api/v3/urls/d0e196a0c25d35dd0a84593cbae0f38333aa58529936444ea26453eab28dfc86/comments?limit=40&cursor=Cs8BChEKBGRhdGUSCQiG28uAmYbzAhK1AWoRc352aXJ1c3RvdGFsY2xvdWRynwELEgNVUkwiQGQwZTE5NmEwYzI1ZDM1ZGQwYTg0NTkzY2JhZTBmMzgzMzNhYTU4NTI5OTM2NDQ0ZWEyNjQ1M2VhYjI4ZGZjODYMCxIHQ29tbWVudCJJZDBlMTk2YTBjMjVkMzVkZDBhODQ1OTNjYmFlMGYzODMzM2FhNTg1Mjk5MzY0NDRlYTI2NDUzZWFiMjhkZmM4Ni02N2ExNzEwNQwYACAB |
action_result.data.\*.links.self | string | `url` | https://www.virustotal.com/api/v3/comments/u-d0e196a0c25d35dd0a84593cbae0f38333aa58529936444ea26453eab28dfc86-ac125607 |
action_result.data.\*.links.self | string | `url` | https://www.virustotal.com/api/v3/urls/d0e196a0c25d35dd0a84593cbae0f38333aa58529936444ea26453eab28dfc86/comments?cursor=&limit=40 |
action_result.data.\*.meta.count | numeric | | 109 |
action_result.data.\*.meta.cursor | string | | Cs8BChEKBGRhdGUSCQiG28uAmYbzAhK1AWoRc352aXJ1c3RvdGFsY2xvdWRynwELEgNVUkwiQGQwZTE5NmEwYzI1ZDM1ZGQwYTg0NTkzY2JhZTBmMzgzMzNhYTU4NTI5OTM2NDQ0ZWEyNjQ1M2VhYjI4ZGZjODYMCxIHQ29tbWVudCJJZDBlMTk2YTBjMjVkMzVkZDBhODQ1OTNjYmFlMGYzODMzM2FhNTg1Mjk5MzY0NDRlYTI2NDUzZWFiMjhkZmM4Ni02N2ExNzEwNQwYACAB |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get vulnerability associations'

Fetch vulnerabilities related to an IP address, URL, domain, or file

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity** | required | Entity (IP, URL, Domain, File [Vault ID in SOAR or MD5/SHA1/SHA256]) to get the report | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` |
**password** | optional | Password to decompress and scan a file contained in a protected ZIP file | string | |
**limit** | optional | Maximum number of vulnerabilities to fetch | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` | |
action_result.parameter.limit | string | | 1 |
action_result.parameter.password | string | | |
action_result.data | string | | |
action_result.data.\*.attributes.affected_systems.\* | string | | |
action_result.data.\*.attributes.aggregations.files.attack_tactics.\*.count | numeric | | 2 |
action_result.data.\*.attributes.aggregations.files.attack_tactics.\*.value | string | | TA0007 |
action_result.data.\*.attributes.aggregations.files.attack_techniques.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.attack_techniques.\*.prevalence | numeric | | 1e-05 |
action_result.data.\*.attributes.aggregations.files.attack_techniques.\*.total_related | numeric | | 100000 |
action_result.data.\*.attributes.aggregations.files.attack_techniques.\*.value | string | | T1036 |
action_result.data.\*.attributes.aggregations.files.behash.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.behash.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.behash.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.behash.\*.value | string | | e7e221a0d2d4c8b0903da4b5ad1c2288 |
action_result.data.\*.attributes.aggregations.files.compressed_parents.\*.count | numeric | | 4 |
action_result.data.\*.attributes.aggregations.files.compressed_parents.\*.prevalence | numeric | | 0.05405405405405406 |
action_result.data.\*.attributes.aggregations.files.compressed_parents.\*.total_related | numeric | | 74 |
action_result.data.\*.attributes.aggregations.files.compressed_parents.\*.value | string | | 627ca95b8865617b81cb7554247a7e7ebfa2e5995f06b915579f53ab84c43d85 |
action_result.data.\*.attributes.aggregations.files.contacted_domains.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.contacted_domains.\*.prevalence | numeric | | 0.038461538461538464 |
action_result.data.\*.attributes.aggregations.files.contacted_domains.\*.total_related | numeric | | 26 |
action_result.data.\*.attributes.aggregations.files.contacted_domains.\*.value | string | | www.xmlformats.com |
action_result.data.\*.attributes.aggregations.files.contacted_ips.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.contacted_ips.\*.prevalence | numeric | | 8.932559178204556e-05 |
action_result.data.\*.attributes.aggregations.files.contacted_ips.\*.total_related | numeric | | 11195 |
action_result.data.\*.attributes.aggregations.files.contacted_ips.\*.value | string | | 52.109.124.115 |
action_result.data.\*.attributes.aggregations.files.contacted_urls.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.contacted_urls.\*.prevalence | numeric | | 0.0002566735112936345 |
action_result.data.\*.attributes.aggregations.files.contacted_urls.\*.total_related | numeric | | 3896 |
action_result.data.\*.attributes.aggregations.files.contacted_urls.\*.value | string | | http://nexusrules.officeapps.live.com:443/nexus/rules |
action_result.data.\*.attributes.aggregations.files.crowdsourced_yara_results.\*.count | numeric | | 2 |
action_result.data.\*.attributes.aggregations.files.crowdsourced_yara_results.\*.prevalence | numeric | | 0.000541858574911948 |
action_result.data.\*.attributes.aggregations.files.crowdsourced_yara_results.\*.total_related | numeric | | 3691 |
action_result.data.\*.attributes.aggregations.files.crowdsourced_yara_results.\*.value.id | string | | 000e7c738e|SUSP_Doc_WordXMLRels_May22 |
action_result.data.\*.attributes.aggregations.files.crowdsourced_yara_results.\*.value.rule_name | string | | SUSP_Doc_WordXMLRels_May22 |
action_result.data.\*.attributes.aggregations.files.crowdsourced_yara_results.\*.value.ruleset_id | string | | 000e7c738e |
action_result.data.\*.attributes.aggregations.files.crowdsourced_yara_results.\*.value.ruleset_name | string | | gen_doc_follina |
action_result.data.\*.attributes.aggregations.files.crowdsourced_yara_results.\*.value.source | string | | https://github.com/Neo23x0/signature-base |
action_result.data.\*.attributes.aggregations.files.dropped_files_path.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.dropped_files_path.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.dropped_files_path.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.dropped_files_path.\*.value | string | | ${SamplePath}\\~$7cb123c279ce42bfa2194504e62b22ae1dfc4505de872c88c7e022024ddba8.docx |
action_result.data.\*.attributes.aggregations.files.dropped_files_sha256.\*.count | numeric | | 2 |
action_result.data.\*.attributes.aggregations.files.dropped_files_sha256.\*.prevalence | numeric | | 2.8690699909624295e-05 |
action_result.data.\*.attributes.aggregations.files.dropped_files_sha256.\*.total_related | numeric | | 69709 |
action_result.data.\*.attributes.aggregations.files.dropped_files_sha256.\*.value | string | | 284190f542ec0e350b8398bd57856fdb09cccd3f61c037c9c52cb632aa42c98f |
action_result.data.\*.attributes.aggregations.files.embedded_domains.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.embedded_domains.\*.prevalence | numeric | | 2.1897650382114e-05 |
action_result.data.\*.attributes.aggregations.files.embedded_domains.\*.total_related | numeric | | 45667 |
action_result.data.\*.attributes.aggregations.files.embedded_domains.\*.value | string | | ria.ru |
action_result.data.\*.attributes.aggregations.files.embedded_ips.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.embedded_ips.\*.prevalence | numeric | | 1e-05 |
action_result.data.\*.attributes.aggregations.files.embedded_ips.\*.total_related | numeric | | 100000 |
action_result.data.\*.attributes.aggregations.files.embedded_ips.\*.value | string | | 127.0.0.1 |
action_result.data.\*.attributes.aggregations.files.embedded_urls.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.embedded_urls.\*.prevalence | numeric | | 0.003676470588235294 |
action_result.data.\*.attributes.aggregations.files.embedded_urls.\*.total_related | numeric | | 272 |
action_result.data.\*.attributes.aggregations.files.embedded_urls.\*.value | string | | http://127.0.0.1/test.html |
action_result.data.\*.attributes.aggregations.files.file_types.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.file_types.\*.value | string | | docx |
action_result.data.\*.attributes.aggregations.files.filecondis_dhash.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.filecondis_dhash.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.filecondis_dhash.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.filecondis_dhash.\*.value | string | | 10383e3c3c152000 |
action_result.data.\*.attributes.aggregations.files.itw_urls.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.itw_urls.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.itw_urls.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.itw_urls.\*.value | string | | http://codeload.github.com/johnhammond/msdt-follina/zip/refs/heads/main |
action_result.data.\*.attributes.aggregations.files.memory_pattern_urls.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.memory_pattern_urls.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.memory_pattern_urls.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.memory_pattern_urls.\*.value | string | | http://eternallybored.org/misc/netcat/\] |
action_result.data.\*.attributes.aggregations.files.mutexes_created.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.mutexes_created.\*.prevalence | numeric | | 0.0045871559633027525 |
action_result.data.\*.attributes.aggregations.files.mutexes_created.\*.total_related | numeric | | 218 |
action_result.data.\*.attributes.aggregations.files.mutexes_created.\*.value | string | | Local\\SM0:1528:64:WilError_02 |
action_result.data.\*.attributes.aggregations.files.mutexes_opened.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.mutexes_opened.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.mutexes_opened.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.mutexes_opened.\*.value | string | | Local\\CSI_OMTX:{515B6DAD-12AD-4E9E-964B-01C86C437273} |
action_result.data.\*.attributes.aggregations.files.parent_contacted_domains.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.parent_contacted_domains.\*.prevalence | numeric | | 0.038461538461538464 |
action_result.data.\*.attributes.aggregations.files.parent_contacted_domains.\*.total_related | numeric | | 26 |
action_result.data.\*.attributes.aggregations.files.parent_contacted_domains.\*.value | string | | xmlformats.com |
action_result.data.\*.attributes.aggregations.files.popular_threat_category.\*.count | numeric | | 6 |
action_result.data.\*.attributes.aggregations.files.popular_threat_category.\*.value | string | | trojan |
action_result.data.\*.attributes.aggregations.files.popular_threat_name.\*.count | numeric | | 4 |
action_result.data.\*.attributes.aggregations.files.popular_threat_name.\*.value | string | | expl |
action_result.data.\*.attributes.aggregations.files.registry_keys_deleted.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.registry_keys_deleted.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.registry_keys_deleted.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.registry_keys_deleted.\*.value | string | | HKEY_CURRENT_USER\\Software\\Microsoft\\Office\\14.0\\Word\\Resiliency\\StartupItems\\\*{{ |
action_result.data.\*.attributes.aggregations.files.registry_keys_opened.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.registry_keys_opened.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.registry_keys_opened.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.registry_keys_opened.\*.value | string | | HKEY_CURRENT_USER\\Software\\Microsoft\\Office\\14.0\\Word\\Resiliency\\StartupItems\\\*{{ |
action_result.data.\*.attributes.aggregations.files.registry_keys_set.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.registry_keys_set.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.registry_keys_set.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.registry_keys_set.\*.value | string | | 17A9165 |
action_result.data.\*.attributes.aggregations.files.sandbox_verdicts.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.sandbox_verdicts.\*.sandbox_name | string | | DAS-Security Orcas |
action_result.data.\*.attributes.aggregations.files.sandbox_verdicts.\*.value | string | | Clean |
action_result.data.\*.attributes.aggregations.files.suggested_threat_label | string | | trojan.w97m/expl |
action_result.data.\*.attributes.aggregations.files.tags.\*.count | numeric | | 6 |
action_result.data.\*.attributes.aggregations.files.tags.\*.value | string | | cve-2022-30190 |
action_result.data.\*.attributes.aggregations.files.tlshhash.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.tlshhash.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.tlshhash.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.tlshhash.\*.value | string | | T117D27DBBC21D2F7ACD9105FE69CD1637D32DEA0E354F58499198B470F48921A2EB9B0C |
action_result.data.\*.attributes.aggregations.files.vhash.\*.count | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.vhash.\*.prevalence | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.vhash.\*.total_related | numeric | | 1 |
action_result.data.\*.attributes.aggregations.files.vhash.\*.value | string | | 363b323ef58e27f61f69e94ce1d27a4c |
action_result.data.\*.attributes.alt_names.\* | string | | Follina |
action_result.data.\*.attributes.alt_names_details.\*.confidence | string | | possible |
action_result.data.\*.attributes.alt_names_details.\*.description | string | | |
action_result.data.\*.attributes.alt_names_details.\*.first_seen | string | | |
action_result.data.\*.attributes.alt_names_details.\*.last_seen | string | | |
action_result.data.\*.attributes.alt_names_details.\*.value | string | | Follina |
action_result.data.\*.attributes.analysis | string | | Dummy Anylysis |
action_result.data.\*.attributes.autogenerated_tags.\* | string | | contains-pe |
action_result.data.\*.attributes.available_mitigation | string | | Workaround |
action_result.data.\*.attributes.capabilities.\* | string | | |
action_result.data.\*.attributes.cisa_known_exploited.added_date | numeric | | 1655164800 |
action_result.data.\*.attributes.cisa_known_exploited.due_date | numeric | | 1656979200 |
action_result.data.\*.attributes.cisa_known_exploited.ransomware_use | string | | Unknown |
action_result.data.\*.attributes.collection_links.\* | string | | |
action_result.data.\*.attributes.collection_type | string | | vulnerability |
action_result.data.\*.attributes.counters.attack_techniques | numeric | | |
action_result.data.\*.attributes.counters.domains | numeric | | |
action_result.data.\*.attributes.counters.files | numeric | | 18 |
action_result.data.\*.attributes.counters.iocs | numeric | | 18 |
action_result.data.\*.attributes.counters.ip_addresses | numeric | | |
action_result.data.\*.attributes.counters.subscribers | numeric | | |
action_result.data.\*.attributes.counters.urls | numeric | | |
action_result.data.\*.attributes.cpes.\*.end_cpe.product | string | | Windows Server 20H2 |
action_result.data.\*.attributes.cpes.\*.end_cpe.uri | string | | cpe:2.3:o:microsoft:windows_server_20h2:10.0.19042.1766:\*:\*:\*:\*:\*:\*:\* |
action_result.data.\*.attributes.cpes.\*.end_cpe.vendor | string | | Microsoft |
action_result.data.\*.attributes.cpes.\*.end_cpe.version | string | | 10.0.19042.1766 |
action_result.data.\*.attributes.cpes.\*.end_rel | string | | < |
action_result.data.\*.attributes.cpes.\*.start_cpe | string | | |
action_result.data.\*.attributes.cpes.\*.start_rel | string | | |
action_result.data.\*.attributes.creation_date | numeric | | 1653927632 |
action_result.data.\*.attributes.cve_id | string | | CVE-2022-30190 |
action_result.data.\*.attributes.cvss.cvssv2_0.base_score | numeric | | 6.8 |
action_result.data.\*.attributes.cvss.cvssv2_0.temporal_score | numeric | | 5.6 |
action_result.data.\*.attributes.cvss.cvssv2_0.vector | string | | AV:N/AC:M/Au:N/C:P/I:P/A:P/E:F/RL:OF/RC:C |
action_result.data.\*.attributes.cvss.cvssv3_x.base_score | numeric | | 7.8 |
action_result.data.\*.attributes.cvss.cvssv3_x.temporal_score | numeric | | 7.8 |
action_result.data.\*.attributes.cvss.cvssv3_x.vector | string | | CVSS:3.1/AV:L/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H |
action_result.data.\*.attributes.cwe.id | string | | CWE-610 |
action_result.data.\*.attributes.cwe.title | string | | Externally Controlled Reference to a Resource in Another Sphere |
action_result.data.\*.attributes.date_of_disclosure | numeric | | 1653609600 |
action_result.data.\*.attributes.days_to_patch | numeric | | 3 |
action_result.data.\*.attributes.days_to_report | numeric | | 3 |
action_result.data.\*.attributes.description | string | | Dummy Description |
action_result.data.\*.attributes.detection_names.\* | string | | |
action_result.data.\*.attributes.domains_count | numeric | | |
action_result.data.\*.attributes.epss.percentile | numeric | | 0.99764 |
action_result.data.\*.attributes.epss.score | numeric | | 0.92888 |
action_result.data.\*.attributes.executive_summary | string | | * An Externally Controlled Reference to a Resource in Another Sphere vulnerability exists that, when exploited, allows a remote attacker to execute arbitrary code. * This vulnerability has been confirmed to be exploited in the wild. Non-weaponized, proof-of-concept and weaponized code is publicly available. * Mandiant Intelligence considers this a Medium-risk vulnerability due to the potential for arbitrary code execution, offset by user interaction requirements. * Mitigation options include a workaround and a patch. |
action_result.data.\*.attributes.exploit_availability | string | | Publicly Available |
action_result.data.\*.attributes.exploitation.exploit_release_date | numeric | | 1653868800 |
action_result.data.\*.attributes.exploitation.first_exploitation | numeric | | 1651276800 |
action_result.data.\*.attributes.exploitation.tech_details_release_date | numeric | | 1689120000 |
action_result.data.\*.attributes.exploitation_consequence | string | | Code Execution |
action_result.data.\*.attributes.exploitation_state | string | | Confirmed |
action_result.data.\*.attributes.exploitation_vectors.\* | string | | File Share |
action_result.data.\*.attributes.field_sources.\*.field | string | | cvss.cvssv3_x |
action_result.data.\*.attributes.field_sources.\*.source.field_type | string | | Ranked |
action_result.data.\*.attributes.field_sources.\*.source.source_name | string | | Mandiant Intelligence |
action_result.data.\*.attributes.field_sources.\*.source.source_url | string | | |
action_result.data.\*.attributes.field_sources.\*.source.sources.\* | string | | |
action_result.data.\*.attributes.files_count | numeric | | 18 |
action_result.data.\*.attributes.first_seen_details.\* | string | | |
action_result.data.\*.attributes.intended_effects.\* | string | | |
action_result.data.\*.attributes.ip_addresses_count | numeric | | |
action_result.data.\*.attributes.last_modification_date | numeric | | 1743077303 |
action_result.data.\*.attributes.last_seen_details.\* | string | | |
action_result.data.\*.attributes.malware_roles.\* | string | | |
action_result.data.\*.attributes.mati_genids_dict.cve_id | string | | vulnerability--0eeed973-84dd-529a-a65c-4f5548904ead |
action_result.data.\*.attributes.mati_genids_dict.mve_id | string | | vulnerability--17be42ce-815d-59c5-acfb-2aa013071e20 |
action_result.data.\*.attributes.mati_genids_dict.report_id | string | | report--8b5c5925-1c4a-5ddd-98dc-12c849d6fe66 |
action_result.data.\*.attributes.merged_actors.\* | string | | |
action_result.data.\*.attributes.mitigations.\* | string | | |
action_result.data.\*.attributes.motivations.\* | string | | |
action_result.data.\*.attributes.mve_id | string | | MVE-2022-4552 |
action_result.data.\*.attributes.name | string | | CVE-2022-30190 |
action_result.data.\*.attributes.operating_systems.\* | string | | |
action_result.data.\*.attributes.origin | string | | Google Threat Intelligence |
action_result.data.\*.attributes.predicted_risk_rating | string | | |
action_result.data.\*.attributes.priority | string | | P0 |
action_result.data.\*.attributes.private | boolean | | True |
action_result.data.\*.attributes.recent_activity_relative_change | numeric | | 1.3333333333333335 |
action_result.data.\*.attributes.recent_activity_summary.\* | string | | 1 |
action_result.data.\*.attributes.references_count | numeric | | |
action_result.data.\*.attributes.risk_factors.\* | string | | User Interaction Required |
action_result.data.\*.attributes.risk_rating | string | | MEDIUM |
action_result.data.\*.attributes.source_regions_hierarchy.\* | string | | |
action_result.data.\*.attributes.sources.\*.cvss.cvssv2_0 | string | | |
action_result.data.\*.attributes.sources.\*.cvss.cvssv3_x.base_score | numeric | | 7.8 |
action_result.data.\*.attributes.sources.\*.cvss.cvssv3_x.temporal_score | string | | |
action_result.data.\*.attributes.sources.\*.cvss.cvssv3_x.vector | string | | CVSS:3.1/AV:L/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:H/E:P/RL:O/RC:C |
action_result.data.\*.attributes.sources.\*.cvss.cvssv3_x_translated | string | | |
action_result.data.\*.attributes.sources.\*.cvss.cvssv4_x | string | | |
action_result.data.\*.attributes.sources.\*.md5 | string | | 47e3ac48c53e644a3a962d68966728f7 |
action_result.data.\*.attributes.sources.\*.name | string | | Cybersecurity and Infrastructure Security Agency (CISA) |
action_result.data.\*.attributes.sources.\*.published_date | numeric | | 1654114217 |
action_result.data.\*.attributes.sources.\*.source_description | string | | |
action_result.data.\*.attributes.sources.\*.title | string | | |
action_result.data.\*.attributes.sources.\*.unique_id | string | | |
action_result.data.\*.attributes.sources.\*.url | string | | https://github.com/cisagov/vulnrichment/blob/develop/2022/30xxx/CVE-2022-30190.json |
action_result.data.\*.attributes.status | string | | COMPUTED |
action_result.data.\*.attributes.subscribers_count | numeric | | |
action_result.data.\*.attributes.summary_stats.files_detections.avg | numeric | | 39.166666666666664 |
action_result.data.\*.attributes.summary_stats.files_detections.max | numeric | | 45 |
action_result.data.\*.attributes.summary_stats.files_detections.min | numeric | | 24 |
action_result.data.\*.attributes.summary_stats.first_submission_date.avg | numeric | | 1665771247.6666667 |
action_result.data.\*.attributes.summary_stats.first_submission_date.max | numeric | | 1671614307 |
action_result.data.\*.attributes.summary_stats.first_submission_date.min | numeric | | 1654013036 |
action_result.data.\*.attributes.summary_stats.last_submission_date.avg | numeric | | 1671085363.3333333 |
action_result.data.\*.attributes.summary_stats.last_submission_date.max | numeric | | 1685838399 |
action_result.data.\*.attributes.summary_stats.last_submission_date.min | numeric | | 1654157222 |
action_result.data.\*.attributes.tags | string | | observed_in_the_wild |
action_result.data.\*.attributes.tags_details.\*.confidence | string | | possible |
action_result.data.\*.attributes.tags_details.\*.description | string | | |
action_result.data.\*.attributes.tags_details.\*.first_seen | string | | |
action_result.data.\*.attributes.tags_details.\*.last_seen | string | | |
action_result.data.\*.attributes.tags_details.\*.value | string | | observed_in_the_wild |
action_result.data.\*.attributes.targeted_industries.\* | string | | |
action_result.data.\*.attributes.targeted_industries_tree.\* | string | | |
action_result.data.\*.attributes.targeted_informations.\* | string | | |
action_result.data.\*.attributes.targeted_regions.\* | string | | |
action_result.data.\*.attributes.targeted_regions_hierarchy.\* | string | | |
action_result.data.\*.attributes.technologies.\* | string | | |
action_result.data.\*.attributes.threat_scape.\* | string | | |
action_result.data.\*.attributes.top_icon_md5.\* | string | | |
action_result.data.\*.attributes.urls_count | numeric | | |
action_result.data.\*.attributes.vendor_fix_references.\*.cvss | string | | |
action_result.data.\*.attributes.vendor_fix_references.\*.md5 | string | | |
action_result.data.\*.attributes.vendor_fix_references.\*.name | string | | Dell Inc. |
action_result.data.\*.attributes.vendor_fix_references.\*.published_date | numeric | | 1664409600 |
action_result.data.\*.attributes.vendor_fix_references.\*.source_description | string | | |
action_result.data.\*.attributes.vendor_fix_references.\*.title | string | | DSA-2022-270: Dell Unisphere for PowerMax, Dell Unisphere for PowerMax vApp, Dell Solutions Enabler vApp, Dell Unisphere 360, Dell VASA Provider vApp, and Dell PowerMax EMB Mgmt Security Update for Multiple Vulnerabilities |
action_result.data.\*.attributes.vendor_fix_references.\*.unique_id | string | | DSA-2022-270 |
action_result.data.\*.attributes.vendor_fix_references.\*.url | string | | https://www.dell.com/support/kbdoc/en-us/000203837/dsa-2022-270-dell-unisphere-for-powermax-dell-unisphere-for-powermax-vapp-dell-solutions-enabler-vapp-dell-unisphere-360-dell-vasa-provider-vapp-and-dell-powermax-emb-mgmt-security-update-for-multiple-vulnerabilities |
action_result.data.\*.attributes.version_history.\*.date | numeric | | 1743077303 |
action_result.data.\*.attributes.version_history.\*.version_notes.\* | string | | sources: Added https://thehackernews.com/2025/03/top-3-ms-office-exploits-hackers-use-in.html |
action_result.data.\*.attributes.vulnerable_products | string | | |
action_result.data.\*.attributes.workarounds.\* | string | | Dummy Value |
action_result.data.\*.context_attributes.role | string | | viewer |
action_result.data.\*.context_attributes.shared_with_me | boolean | | |
action_result.data.\*.id | string | | vulnerability--cve-2022-30190 |
action_result.data.\*.links.self | string | `url` | https://www.virustotal.com/api/v3/collections/vulnerability--cve-2022-30190 |
action_result.data.\*.links.self | string | `url` | https://www.virustotal.com/api/v3/files/12cbf4da6d555229e3a514f2d5a599cb13f148e7b5365a80706f6c9bb38a2615/vulnerabilities?limit=10 |
action_result.data.\*.meta.count | numeric | | 1 |
action_result.data.\*.type | string | | collection |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get file sandbox report'

Fetch the behavior report for a given file

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_hash** | required | Vault ID of the file or file hash | string | `vault id` `sha1` `sha256` `md5` |
**password** | optional | Password to decompress and scan a file contained in a protected ZIP file | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_hash | string | `vault id` `sha1` `sha256` `md5` | |
action_result.parameter.password | string | | |
action_result.data | string | | |
action_result.data.\*.data.\*.attributes.analysis_date | numeric | | 1661473860 |
action_result.data.\*.data.\*.attributes.behash | string | | eb90f9e100a681a7558a39189be8c486 |
action_result.data.\*.data.\*.attributes.command_executions.\* | string | | |
action_result.data.\*.data.\*.attributes.dns_lookups.\*.hostname | string | | portal.sbn.co.th |
action_result.data.\*.data.\*.attributes.dns_lookups.\*.resolved_ips.\* | string | | 127.0.0.1 |
action_result.data.\*.data.\*.attributes.files_deleted.\* | string | | C:\\Users\\Admin\\AppData\\Roaming\\\_\_tmp_rar_sfx_access_check_226718 |
action_result.data.\*.data.\*.attributes.files_dropped.\*.path | string | | C:\\Users\\Admin\\AppData\\Roaming\\\_\_tmp_rar_sfx_access_check_226718 |
action_result.data.\*.data.\*.attributes.files_dropped.\*.sha256 | string | | e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 |
action_result.data.\*.data.\*.attributes.files_opened.\* | string | | C:\\Users\\Admin\\AppData\\Roaming\\\_\_tmp_rar_sfx_access_check_226718 |
action_result.data.\*.data.\*.attributes.files_written.\* | string | | C:\\Users\\Admin\\AppData\\Roaming\\acrotray.exe |
action_result.data.\*.data.\*.attributes.has_evtx | boolean | | |
action_result.data.\*.data.\*.attributes.has_html_report | boolean | | |
action_result.data.\*.data.\*.attributes.has_memdump | boolean | | |
action_result.data.\*.data.\*.attributes.has_pcap | boolean | | True |
action_result.data.\*.data.\*.attributes.ip_traffic.\*.destination_ip | string | | 184.30.152.141 |
action_result.data.\*.data.\*.attributes.ip_traffic.\*.destination_port | numeric | | 443 |
action_result.data.\*.data.\*.attributes.ip_traffic.\*.transport_layer_protocol | string | | TCP |
action_result.data.\*.data.\*.attributes.last_modification_date | numeric | | 1662048884 |
action_result.data.\*.data.\*.attributes.memory_pattern_domains.\* | string | | |
action_result.data.\*.data.\*.attributes.memory_pattern_ips.\* | string | | |
action_result.data.\*.data.\*.attributes.memory_pattern_urls.\* | string | | |
action_result.data.\*.data.\*.attributes.mitre_attack_techniques.\*.id | string | | T1082 |
action_result.data.\*.data.\*.attributes.mitre_attack_techniques.\*.severity | string | | IMPACT_SEVERITY_MEDIUM |
action_result.data.\*.data.\*.attributes.mitre_attack_techniques.\*.signature_description | string | | collect system hardware fingerprint info |
action_result.data.\*.data.\*.attributes.modules_loaded.\* | string | | 5442.exe |
action_result.data.\*.data.\*.attributes.mutexes_created.\* | string | | 2AC1A572DB6944B0A65C38C4140AF2F4ffc70FA6134 |
action_result.data.\*.data.\*.attributes.mutexes_opened.\* | string | | CicLoadWinStaWinSta0 |
action_result.data.\*.data.\*.attributes.processes_created.\* | string | | |
action_result.data.\*.data.\*.attributes.processes_terminated.\* | string | | 5442.exe |
action_result.data.\*.data.\*.attributes.processes_tree.\*.children.\*.children.\*.name | string | | C:\\Users\\Admin\\AppData\\Roaming\\acrotray.exe |
action_result.data.\*.data.\*.attributes.processes_tree.\*.children.\*.children.\*.process_id | string | | 2984 |
action_result.data.\*.data.\*.attributes.processes_tree.\*.children.\*.children.\*.time_offset | numeric | | 959 |
action_result.data.\*.data.\*.attributes.processes_tree.\*.children.\*.name | string | | C:\\Users\\Admin\\AppData\\Roaming\\acrotray.exe |
action_result.data.\*.data.\*.attributes.processes_tree.\*.children.\*.process_id | string | | 3784 |
action_result.data.\*.data.\*.attributes.processes_tree.\*.children.\*.time_offset | numeric | | 8063 |
action_result.data.\*.data.\*.attributes.processes_tree.\*.name | string | | 5442.exe |
action_result.data.\*.data.\*.attributes.processes_tree.\*.process_id | string | | 3724 |
action_result.data.\*.data.\*.attributes.registry_keys_opened.\* | string | | \\Registry\\Machine\\System\\CurrentControlSet\\Control\\Nls\\Locale\\Alternate Sorts |
action_result.data.\*.data.\*.attributes.registry_keys_set.\*.key | string | | \\Registry\\Machine\\System\\CurrentControlSet\\Control\\Session Manager |
action_result.data.\*.data.\*.attributes.registry_keys_set.\*.value | string | | PendingFileRenameOperations |
action_result.data.\*.data.\*.attributes.sandbox_name | string | | DAS-Security Orcas |
action_result.data.\*.data.\*.attributes.services_opened.\* | string | | Sens |
action_result.data.\*.data.\*.attributes.tags | string | | RUNTIME_MODULES |
action_result.data.\*.data.\*.attributes.tls.\*.issuer.C | string | | IL |
action_result.data.\*.data.\*.attributes.tls.\*.issuer.CN | string | | goproxy.github.io |
action_result.data.\*.data.\*.attributes.tls.\*.issuer.L | string | | Lod |
action_result.data.\*.data.\*.attributes.tls.\*.issuer.O | string | | GoProxy |
action_result.data.\*.data.\*.attributes.tls.\*.issuer.OU | string | | GoProxy |
action_result.data.\*.data.\*.attributes.tls.\*.issuer.ST | string | | Center |
action_result.data.\*.data.\*.attributes.tls.\*.serial_number | string | | 57a8bcf99c087105 |
action_result.data.\*.data.\*.attributes.tls.\*.sni | string | | armmf.adobe.com |
action_result.data.\*.data.\*.attributes.tls.\*.subject.CN | string | | armmf.adobe.com |
action_result.data.\*.data.\*.attributes.tls.\*.subject.O | string | | GoProxy untrusted MITM proxy Inc |
action_result.data.\*.data.\*.attributes.tls.\*.thumbprint | string | | ee020afe7f083ef7565244d3b82bce2157406e91 |
action_result.data.\*.data.\*.attributes.tls.\*.version | string | | TLSv1 |
action_result.data.\*.data.\*.attributes.verdict_confidence | numeric | | 50 |
action_result.data.\*.data.\*.attributes.verdict_labels | string | | Netcat |
action_result.data.\*.data.\*.attributes.verdicts | string | | MALWARE |
action_result.data.\*.data.\*.attributes.windows_hidden.\* | string | | C:\\Users\\Admin\\AppData\\Roaming\\acrotray.exe |
action_result.data.\*.data.\*.id | string | | dea20c241265e2995244187c8476570893df41b9623784a4ca6ed075721b8cdf_DAS-Security Orcas |
action_result.data.\*.data.\*.links.self | string | `url` | https://www.virustotal.com/api/v3/file_behaviours/dea20c241265e2995244187c8476570893df41b9623784a4ca6ed075721b8cdf_DAS-Security Orcas |
action_result.data.\*.data.\*.type | string | | file_behaviour |
action_result.data.\*.links.self | string | | https://www.virustotal.com/api/v3/files/dea20c241265e2995244187c8476570893df41b9623784a4ca6ed075721b8cdf/behaviours?limit=10 |
action_result.data.\*.meta.count | numeric | | 1 |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'scan private url'

Privately scan and analyze a URL to retrieve associated threat intelligence

Type: **investigate** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | Private URL to scan | string | `url` |
**user_agent** | optional | User agent string | string | |
**sandboxes** | optional | Comma separated eg: cape_win,zenbox_windows; Possible values cape_win,cape_linux,zenbox_windows,chrome_headless_linux | string | |
**retention_period_days** | optional | Number of days the report and URL are kept in VT (between 1 and 28); if not set, defaults to the group's retention policy preference (1 day by default) | numeric | |
**storage_region** | optional | Storage region where the URL will be stored; By default uses the group's private_scanning.storage_region preference. Allowed values are US, CA, EU, GB | string | |
**interaction_sandbox** | optional | Select the sandbox desired for interactive use | string | |
**interaction_timeout** | optional | Interaction timeout in seconds, minimum value: 60. (1 minute.) Max value: 1800: (30 minutes) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.interaction_sandbox | string | | cape_win |
action_result.parameter.interaction_timeout | numeric | | 60 |
action_result.parameter.retention_period_days | numeric | | 1 |
action_result.parameter.sandboxes | string | | cape_win |
action_result.parameter.storage_region | string | | US |
action_result.parameter.url | string | `url` | https://google.com |
action_result.parameter.user_agent | string | | v3 |
action_result.data | string | | |
action_result.data.\*.data.attributes.expiration | numeric | | 1743749689 |
action_result.data.\*.data.attributes.gti_assessment.contributing_factors.safebrowsing_verdict | string | | harmless |
action_result.data.\*.data.attributes.gti_assessment.description | string | | This indicator did not match our detection criteria and there is currently no evidence of malicious activity. |
action_result.data.\*.data.attributes.gti_assessment.severity.value | string | | SEVERITY_NONE |
action_result.data.\*.data.attributes.gti_assessment.threat_score.value | numeric | | 1 |
action_result.data.\*.data.attributes.gti_assessment.verdict.value | string | | VERDICT_UNDETECTED |
action_result.data.\*.data.attributes.last_final_url | string | | https://intranet.example.com/hr/employee-handbook |
action_result.data.\*.data.attributes.outgoing_links.\* | string | | |
action_result.data.\*.data.attributes.redirection_chain.\* | string | | |
action_result.data.\*.data.attributes.tags | string | | |
action_result.data.\*.data.attributes.title | string | | |
action_result.data.\*.data.attributes.tld | string | | com |
action_result.data.\*.data.attributes.url | string | | https://intranet.example.com/hr/employee-handbook |
action_result.data.\*.data.id | string | | ce0599972c064d772cb253a866ce1524c06050556830b9637ae2a80f4b21a2bb |
action_result.data.\*.data.links.self | string | | https://www.virustotal.com/api/v3/private/urls/ce0599972c064d772cb253a866ce1524c06050556830b9637ae2a80f4b21a2bb |
action_result.data.\*.data.type | string | | private_url |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get curated associations'

Fetch curated threat actors, malware families, campaigns, and reports for an IP address, URL, domain, or file

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity** | required | Entity (IP, URL, Domain, File [Vault ID in SOAR or MD5/SHA1/SHA256]) to fetch the Curated Threat Actors/Malware Families/Campaigns/Reports | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` |
**password** | optional | Password to decompress and scan a file contained in a protected ZIP file | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` | |
action_result.parameter.password | string | | |
action_result.data | string | | |
action_result.data.\*.data.attributes.as_owner | string | | CLOUDFLARENET |
action_result.data.\*.data.attributes.asn | numeric | | 13335 |
action_result.data.\*.data.attributes.autostart_locations.\*.entry | string | | cmd.exe |
action_result.data.\*.data.attributes.available_tools.\* | string | | |
action_result.data.\*.data.attributes.categories.BitDefender | string | | computersandsoftware |
action_result.data.\*.data.attributes.categories.Forcepoint ThreatSeeker | string | | personal network storage and backup |
action_result.data.\*.data.attributes.categories.Sophos | string | | information technology |
action_result.data.\*.data.attributes.categories.alphaMountain.ai | string | | File Sharing/Storage, Information Technology, Productivity Applications (alphaMountain.ai) |
action_result.data.\*.data.attributes.creation_date | numeric | | 874306800 |
action_result.data.\*.data.attributes.downloadable | boolean | | True |
action_result.data.\*.data.attributes.exiftool.FileType | string | | TXT |
action_result.data.\*.data.attributes.exiftool.FileTypeExtension | string | | txt |
action_result.data.\*.data.attributes.exiftool.LineCount | string | | 1 |
action_result.data.\*.data.attributes.exiftool.MIMEEncoding | string | | us-ascii |
action_result.data.\*.data.attributes.exiftool.MIMEType | string | | text/plain |
action_result.data.\*.data.attributes.exiftool.Newlines | string | | (none) |
action_result.data.\*.data.attributes.exiftool.WordCount | string | | 1 |
action_result.data.\*.data.attributes.expiration_date | numeric | | 1852516800 |
action_result.data.\*.data.attributes.favicon.dhash | string | | f0cc929ab296cc71 |
action_result.data.\*.data.attributes.favicon.raw_md5 | string | | 30e26a059b7b858731e172c431d55bb4 |
action_result.data.\*.data.attributes.filecondis.dhash | string | | 8500000000800080 |
action_result.data.\*.data.attributes.filecondis.raw_md5 | string | | 057ff28c103dc5b51d69647b5aa9cf50 |
action_result.data.\*.data.attributes.first_seen_itw_date | numeric | | 1662944531 |
action_result.data.\*.data.attributes.first_submission_date | numeric | | 1264671553 |
action_result.data.\*.data.attributes.has_content | boolean | | |
action_result.data.\*.data.attributes.html_meta.referrer.\* | string | | origin |
action_result.data.\*.data.attributes.jarm | string | | 27d40d40d29d40d1dc42d43d00041d4689ee210389f4f6b4b5b1b93f92252d |
action_result.data.\*.data.attributes.known_distributors.data_sources.\* | string | | National Software Reference Library (NSRL) |
action_result.data.\*.data.attributes.known_distributors.distributors.\* | string | | MandrakeSoft |
action_result.data.\*.data.attributes.known_distributors.filenames.\* | string | | tobs-c3.in |
action_result.data.\*.data.attributes.known_distributors.products.\* | string | | SUSE LINUX personal |
action_result.data.\*.data.attributes.last_analysis_date | numeric | | 1747219124 |
action_result.data.\*.data.attributes.last_analysis_results.0xSI_f33d.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.0xSI_f33d.engine_name | string | | 0xSI_f33d |
action_result.data.\*.data.attributes.last_analysis_results.0xSI_f33d.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.0xSI_f33d.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.ADMINUSLabs.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ADMINUSLabs.engine_name | string | | ADMINUSLabs |
action_result.data.\*.data.attributes.last_analysis_results.ADMINUSLabs.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ADMINUSLabs.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.AILabs (MONITORAPP).category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.AILabs (MONITORAPP).engine_name | string | | AILabs (MONITORAPP) |
action_result.data.\*.data.attributes.last_analysis_results.AILabs (MONITORAPP).method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AILabs (MONITORAPP).result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.engine_name | string | | ALYac |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.engine_version | string | | 2.0.0.10 |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ALYac.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.APEX.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.APEX.engine_name | string | | APEX |
action_result.data.\*.data.attributes.last_analysis_results.APEX.engine_update | string | | 20250513 |
action_result.data.\*.data.attributes.last_analysis_results.APEX.engine_version | string | | 6.654 |
action_result.data.\*.data.attributes.last_analysis_results.APEX.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.APEX.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.AVG.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.AVG.engine_name | string | | AVG |
action_result.data.\*.data.attributes.last_analysis_results.AVG.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.AVG.engine_version | string | | 23.9.8494.0 |
action_result.data.\*.data.attributes.last_analysis_results.AVG.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AVG.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Abusix.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Abusix.engine_name | string | | Abusix |
action_result.data.\*.data.attributes.last_analysis_results.Abusix.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Abusix.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.engine_name | string | | Acronis |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.engine_update | string | | 20240328 |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.engine_version | string | | 1.2.0.121 |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Acronis.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.engine_name | string | | AhnLab-V3 |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.engine_version | string | | 3.27.2.10550 |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AhnLab-V3.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.engine_name | string | | Alibaba |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.engine_update | string | | 20190527 |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.engine_version | string | | 0.3.0.5 |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Alibaba.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.AlienVault.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.AlienVault.engine_name | string | | AlienVault |
action_result.data.\*.data.attributes.last_analysis_results.AlienVault.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AlienVault.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.AlphaSOC.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.AlphaSOC.engine_name | string | | AlphaSOC |
action_result.data.\*.data.attributes.last_analysis_results.AlphaSOC.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AlphaSOC.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.engine_name | string | | Antiy-AVL |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.engine_version | string | | 3.0 |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Antiy-AVL.result | string | | Trojan[APT]/Win32.APT29 |
action_result.data.\*.data.attributes.last_analysis_results.ArcSight Threat Intelligence.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ArcSight Threat Intelligence.engine_name | string | | ArcSight Threat Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.ArcSight Threat Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ArcSight Threat Intelligence.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.engine_name | string | | Arcabit |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.engine_version | string | | 2022.0.0.18 |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Arcabit.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Artists Against 419.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Artists Against 419.engine_name | string | | Artists Against 419 |
action_result.data.\*.data.attributes.last_analysis_results.Artists Against 419.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Artists Against 419.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.AutoShun.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.AutoShun.engine_name | string | | AutoShun |
action_result.data.\*.data.attributes.last_analysis_results.AutoShun.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.AutoShun.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.engine_name | string | | Avast-Mobile |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.engine_version | string | | 250514-00 |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Avast-Mobile.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Avast.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Avast.engine_name | string | | Avast |
action_result.data.\*.data.attributes.last_analysis_results.Avast.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Avast.engine_version | string | | 23.9.8494.0 |
action_result.data.\*.data.attributes.last_analysis_results.Avast.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Avast.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Avira.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Avira.engine_name | string | | Avira |
action_result.data.\*.data.attributes.last_analysis_results.Avira.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Avira.engine_version | string | | 8.3.3.20 |
action_result.data.\*.data.attributes.last_analysis_results.Avira.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Avira.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Axur.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Axur.engine_name | string | | Axur |
action_result.data.\*.data.attributes.last_analysis_results.Axur.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Axur.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.engine_name | string | | Baidu |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.engine_update | string | | 20190318 |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.engine_version | string | | 1.0.0.2 |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Baidu.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Bfore.Ai PreCrime.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Bfore.Ai PreCrime.engine_name | string | | Bfore.Ai PreCrime |
action_result.data.\*.data.attributes.last_analysis_results.Bfore.Ai PreCrime.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Bfore.Ai PreCrime.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.engine_name | string | | BitDefender |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.engine_version | string | | 7.2 |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.BitDefender.result | string | | Trojan.Autoruns.GenericKDS.41616931 |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.engine_name | string | | BitDefenderFalx |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.engine_update | string | | 20250416 |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.engine_version | string | | 2.0.936 |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.BitDefenderFalx.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.engine_name | string | | Bkav |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.engine_version | string | | 2.0.0.1 |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Bkav.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.BlockList.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.BlockList.engine_name | string | | BlockList |
action_result.data.\*.data.attributes.last_analysis_results.BlockList.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.BlockList.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Blueliv.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Blueliv.engine_name | string | | Blueliv |
action_result.data.\*.data.attributes.last_analysis_results.Blueliv.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Blueliv.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.engine_name | string | | CAT-QuickHeal |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.engine_update | string | | 20250513 |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.engine_version | string | | 22.00 |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CAT-QuickHeal.result | string | | TrojanDwnLdr.Clouduke.WR4 |
action_result.data.\*.data.attributes.last_analysis_results.CINS Army.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.CINS Army.engine_name | string | | CINS Army |
action_result.data.\*.data.attributes.last_analysis_results.CINS Army.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CINS Army.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CMC Threat Intelligence.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.CMC Threat Intelligence.engine_name | string | | CMC Threat Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.CMC Threat Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CMC Threat Intelligence.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CMC.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.CMC.engine_name | string | | CMC |
action_result.data.\*.data.attributes.last_analysis_results.CMC.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.CMC.engine_version | string | | 2.4.2022.1 |
action_result.data.\*.data.attributes.last_analysis_results.CMC.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CMC.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.CRDF.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.CRDF.engine_name | string | | CRDF |
action_result.data.\*.data.attributes.last_analysis_results.CRDF.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CRDF.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CSIS Security Group.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.CSIS Security Group.engine_name | string | | CSIS Security Group |
action_result.data.\*.data.attributes.last_analysis_results.CSIS Security Group.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CSIS Security Group.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.CTX.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.CTX.engine_name | string | | CTX |
action_result.data.\*.data.attributes.last_analysis_results.CTX.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.CTX.engine_version | string | | 2024.8.29.1 |
action_result.data.\*.data.attributes.last_analysis_results.CTX.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CTX.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Certego.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Certego.engine_name | string | | Certego |
action_result.data.\*.data.attributes.last_analysis_results.Certego.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Certego.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Chong Lua Dao.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Chong Lua Dao.engine_name | string | | Chong Lua Dao |
action_result.data.\*.data.attributes.last_analysis_results.Chong Lua Dao.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Chong Lua Dao.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.engine_name | string | | ClamAV |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.engine_version | string | | 1.4.2.0 |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ClamAV.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Cluster25.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Cluster25.engine_name | string | | Cluster25 |
action_result.data.\*.data.attributes.last_analysis_results.Cluster25.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cluster25.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Criminal IP.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Criminal IP.engine_name | string | | Criminal IP |
action_result.data.\*.data.attributes.last_analysis_results.Criminal IP.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Criminal IP.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.engine_name | string | | CrowdStrike |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.engine_update | string | | 20230417 |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.engine_version | string | | 1.0 |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CrowdStrike.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.CyRadar.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.CyRadar.engine_name | string | | CyRadar |
action_result.data.\*.data.attributes.last_analysis_results.CyRadar.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.CyRadar.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Cyan.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Cyan.engine_name | string | | Cyan |
action_result.data.\*.data.attributes.last_analysis_results.Cyan.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cyan.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Cyble.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Cyble.engine_name | string | | Cyble |
action_result.data.\*.data.attributes.last_analysis_results.Cyble.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cyble.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.engine_name | string | | Cylance |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.engine_update | string | | 20250424 |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.engine_version | string | | 3.0.0.0 |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cylance.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.engine_name | string | | Cynet |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.engine_version | string | | 4.0.3.4 |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Cynet.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.DNS8.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.DNS8.engine_name | string | | DNS8 |
action_result.data.\*.data.attributes.last_analysis_results.DNS8.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.DNS8.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.engine_name | string | | DeepInstinct |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.engine_update | string | | 20250513 |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.engine_version | string | | 5.0.0.8 |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.DeepInstinct.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Dr.Web.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Dr.Web.engine_name | string | | Dr.Web |
action_result.data.\*.data.attributes.last_analysis_results.Dr.Web.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Dr.Web.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.engine_name | string | | DrWeb |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.engine_version | string | | 7.0.67.2170 |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.DrWeb.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.engine_name | string | | ESET-NOD32 |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.engine_version | string | | 31195 |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ESET-NOD32.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ESET.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ESET.engine_name | string | | ESET |
action_result.data.\*.data.attributes.last_analysis_results.ESET.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ESET.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.ESTsecurity.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ESTsecurity.engine_name | string | | ESTsecurity |
action_result.data.\*.data.attributes.last_analysis_results.ESTsecurity.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ESTsecurity.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.engine_name | string | | Elastic |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.engine_update | string | | 20250505 |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.engine_version | string | | 4.0.203 |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Elastic.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.EmergingThreats.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.EmergingThreats.engine_name | string | | EmergingThreats |
action_result.data.\*.data.attributes.last_analysis_results.EmergingThreats.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.EmergingThreats.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.engine_name | string | | Emsisoft |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.engine_version | string | | 2024.1.0.53752 |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Emsisoft.result | string | | Trojan.Autoruns.GenericKDS.41616931 (B) |
action_result.data.\*.data.attributes.last_analysis_results.Ermes.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Ermes.engine_name | string | | Ermes |
action_result.data.\*.data.attributes.last_analysis_results.Ermes.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Ermes.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.engine_name | string | | F-Secure |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.engine_version | string | | 18.10.1547.307 |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.F-Secure.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Feodo Tracker.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Feodo Tracker.engine_name | string | | Feodo Tracker |
action_result.data.\*.data.attributes.last_analysis_results.Feodo Tracker.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Feodo Tracker.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Forcepoint ThreatSeeker.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Forcepoint ThreatSeeker.engine_name | string | | Forcepoint ThreatSeeker |
action_result.data.\*.data.attributes.last_analysis_results.Forcepoint ThreatSeeker.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Forcepoint ThreatSeeker.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.engine_name | string | | Fortinet |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.engine_version | string | | None |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Fortinet.result | string | | W32/Generic.AC.1FF018 |
action_result.data.\*.data.attributes.last_analysis_results.G-Data.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.G-Data.engine_name | string | | G-Data |
action_result.data.\*.data.attributes.last_analysis_results.G-Data.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.G-Data.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.GCP Abuse Intelligence.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.GCP Abuse Intelligence.engine_name | string | | GCP Abuse Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.GCP Abuse Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.GCP Abuse Intelligence.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.GData.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.GData.engine_name | string | | GData |
action_result.data.\*.data.attributes.last_analysis_results.GData.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.GData.engine_version | string | | GD:27.40321AVA:64.29189 |
action_result.data.\*.data.attributes.last_analysis_results.GData.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.GData.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Google Safebrowsing.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Google Safebrowsing.engine_name | string | | Google Safebrowsing |
action_result.data.\*.data.attributes.last_analysis_results.Google Safebrowsing.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Google Safebrowsing.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Google.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Google.engine_name | string | | Google |
action_result.data.\*.data.attributes.last_analysis_results.Google.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Google.engine_version | string | | 1747211443 |
action_result.data.\*.data.attributes.last_analysis_results.Google.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Google.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.GreenSnow.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.GreenSnow.engine_name | string | | GreenSnow |
action_result.data.\*.data.attributes.last_analysis_results.GreenSnow.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.GreenSnow.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.engine_name | string | | Gridinsoft |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.engine_version | string | | 1.0.177.174 |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Gridinsoft.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Heimdal Security.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Heimdal Security.engine_name | string | | Heimdal Security |
action_result.data.\*.data.attributes.last_analysis_results.Heimdal Security.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Heimdal Security.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Hunt.io Intelligence.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Hunt.io Intelligence.engine_name | string | | Hunt.io Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.Hunt.io Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Hunt.io Intelligence.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.IPsum.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.IPsum.engine_name | string | | IPsum |
action_result.data.\*.data.attributes.last_analysis_results.IPsum.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.IPsum.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.engine_name | string | | Ikarus |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.engine_version | string | | 6.3.30.0 |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Ikarus.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.engine_name | string | | Jiangmin |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.engine_update | string | | 20250513 |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.engine_version | string | | 16.0.100 |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Jiangmin.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Juniper Networks.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Juniper Networks.engine_name | string | | Juniper Networks |
action_result.data.\*.data.attributes.last_analysis_results.Juniper Networks.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Juniper Networks.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.engine_name | string | | K7AntiVirus |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.engine_version | string | | 12.236.55746 |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.K7AntiVirus.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.engine_name | string | | K7GW |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.engine_version | string | | 12.160.52066 |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.K7GW.result | string | | Trojan ( 004c89e61 ) |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.engine_name | string | | Kaspersky |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.engine_version | string | | 22.0.1.28 |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Kaspersky.result | string | | Trojan.Win32.CloudLook.a |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.engine_name | string | | Kingsoft |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.engine_version | string | | None |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Kingsoft.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.engine_name | string | | Lionic |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.engine_version | string | | 7.5 |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Lionic.result | string | | Trojan.ZIP.Autoruns.4!c |
action_result.data.\*.data.attributes.last_analysis_results.Lumu.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Lumu.engine_name | string | | Lumu |
action_result.data.\*.data.attributes.last_analysis_results.Lumu.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Lumu.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.MalwarePatrol.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.MalwarePatrol.engine_name | string | | MalwarePatrol |
action_result.data.\*.data.attributes.last_analysis_results.MalwarePatrol.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.MalwarePatrol.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.MalwareURL.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.MalwareURL.engine_name | string | | MalwareURL |
action_result.data.\*.data.attributes.last_analysis_results.MalwareURL.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.MalwareURL.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.engine_name | string | | Malwarebytes |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.engine_version | string | | 4.5.5.54 |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Malwarebytes.result | string | | Malware.AI.3477432298 |
action_result.data.\*.data.attributes.last_analysis_results.Malwared.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Malwared.engine_name | string | | Malwared |
action_result.data.\*.data.attributes.last_analysis_results.Malwared.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Malwared.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.engine_name | string | | MaxSecure |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.engine_version | string | | 1.0.0.1 |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.MaxSecure.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.engine_name | string | | McAfee |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.engine_update | string | | 20240522 |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.engine_version | string | | 6.0.6.653 |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.McAfee.result | string | | Artemis!BFD2D6BF8E99 |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.engine_name | string | | McAfeeD |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.engine_version | string | | 1.2.0.7977 |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.McAfeeD.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.engine_name | string | | MicroWorld-eScan |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.engine_version | string | | 14.0.409.0 |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.MicroWorld-eScan.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.engine_name | string | | Microsoft |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.engine_version | string | | 1.1.25030.1 |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Microsoft.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Mimecast.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Mimecast.engine_name | string | | Mimecast |
action_result.data.\*.data.attributes.last_analysis_results.Mimecast.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Mimecast.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.engine_name | string | | NANO-Antivirus |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.engine_version | string | | 1.0.170.26531 |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.NANO-Antivirus.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Netcraft.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Netcraft.engine_name | string | | Netcraft |
action_result.data.\*.data.attributes.last_analysis_results.Netcraft.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Netcraft.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.OpenPhish.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.OpenPhish.engine_name | string | | OpenPhish |
action_result.data.\*.data.attributes.last_analysis_results.OpenPhish.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.OpenPhish.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.PREBYTES.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.PREBYTES.engine_name | string | | PREBYTES |
action_result.data.\*.data.attributes.last_analysis_results.PREBYTES.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.PREBYTES.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.engine_name | string | | Paloalto |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.engine_version | string | | 0.9.0.1003 |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Paloalto.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Panda.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Panda.engine_name | string | | Panda |
action_result.data.\*.data.attributes.last_analysis_results.Panda.engine_update | string | | 20250513 |
action_result.data.\*.data.attributes.last_analysis_results.Panda.engine_version | string | | 4.6.4.2 |
action_result.data.\*.data.attributes.last_analysis_results.Panda.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Panda.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.PhishFort.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.PhishFort.engine_name | string | | PhishFort |
action_result.data.\*.data.attributes.last_analysis_results.PhishFort.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.PhishFort.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.PhishLabs.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.PhishLabs.engine_name | string | | PhishLabs |
action_result.data.\*.data.attributes.last_analysis_results.PhishLabs.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.PhishLabs.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Phishing Database.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Phishing Database.engine_name | string | | Phishing Database |
action_result.data.\*.data.attributes.last_analysis_results.Phishing Database.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Phishing Database.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Phishtank.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Phishtank.engine_name | string | | Phishtank |
action_result.data.\*.data.attributes.last_analysis_results.Phishtank.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Phishtank.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.PrecisionSec.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.PrecisionSec.engine_name | string | | PrecisionSec |
action_result.data.\*.data.attributes.last_analysis_results.PrecisionSec.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.PrecisionSec.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Quick Heal.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Quick Heal.engine_name | string | | Quick Heal |
action_result.data.\*.data.attributes.last_analysis_results.Quick Heal.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Quick Heal.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Quttera.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Quttera.engine_name | string | | Quttera |
action_result.data.\*.data.attributes.last_analysis_results.Quttera.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Quttera.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Rising.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Rising.engine_name | string | | Rising |
action_result.data.\*.data.attributes.last_analysis_results.Rising.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Rising.engine_version | string | | 25.0.0.27 |
action_result.data.\*.data.attributes.last_analysis_results.Rising.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Rising.result | string | | Malware.FakePDF/ICON!1.9C3A (CLASSIC) |
action_result.data.\*.data.attributes.last_analysis_results.SCUMWARE.org.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.SCUMWARE.org.engine_name | string | | SCUMWARE.org |
action_result.data.\*.data.attributes.last_analysis_results.SCUMWARE.org.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SCUMWARE.org.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.SOCRadar.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.SOCRadar.engine_name | string | | SOCRadar |
action_result.data.\*.data.attributes.last_analysis_results.SOCRadar.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SOCRadar.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.engine_name | string | | SUPERAntiSpyware |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.engine_update | string | | 20250513 |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.engine_version | string | | 5.6.0.1032 |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SUPERAntiSpyware.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.SafeToOpen.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.SafeToOpen.engine_name | string | | SafeToOpen |
action_result.data.\*.data.attributes.last_analysis_results.SafeToOpen.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SafeToOpen.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.engine_name | string | | Sangfor |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.engine_update | string | | 20240521 |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.engine_version | string | | 2.23.0.0 |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Sangfor.result | string | | Trojan.Win32.APT29.IOC |
action_result.data.\*.data.attributes.last_analysis_results.Sansec eComscan.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Sansec eComscan.engine_name | string | | Sansec eComscan |
action_result.data.\*.data.attributes.last_analysis_results.Sansec eComscan.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Sansec eComscan.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Scantitan.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Scantitan.engine_name | string | | Scantitan |
action_result.data.\*.data.attributes.last_analysis_results.Scantitan.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Scantitan.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Seclookup.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Seclookup.engine_name | string | | Seclookup |
action_result.data.\*.data.attributes.last_analysis_results.Seclookup.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Seclookup.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.SecureBrain.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.SecureBrain.engine_name | string | | SecureBrain |
action_result.data.\*.data.attributes.last_analysis_results.SecureBrain.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SecureBrain.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.engine_name | string | | SentinelOne |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.engine_update | string | | 20250114 |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.engine_version | string | | 25.1.1.1 |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SentinelOne.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.engine_name | string | | Skyhigh |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.engine_update | string | | 20240522 |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.engine_version | string | | v2021.2.0+4045 |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Skyhigh.result | string | | BehavesLike.Generic.gc |
action_result.data.\*.data.attributes.last_analysis_results.Snort IP sample list.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Snort IP sample list.engine_name | string | | Snort IP sample list |
action_result.data.\*.data.attributes.last_analysis_results.Snort IP sample list.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Snort IP sample list.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.engine_name | string | | Sophos |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.engine_version | string | | 2.5.5.0 |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Sophos.result | string | | Mal/Generic-S |
action_result.data.\*.data.attributes.last_analysis_results.Spam404.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Spam404.engine_name | string | | Spam404 |
action_result.data.\*.data.attributes.last_analysis_results.Spam404.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Spam404.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.StopForumSpam.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.StopForumSpam.engine_name | string | | StopForumSpam |
action_result.data.\*.data.attributes.last_analysis_results.StopForumSpam.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.StopForumSpam.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Sucuri SiteCheck.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Sucuri SiteCheck.engine_name | string | | Sucuri SiteCheck |
action_result.data.\*.data.attributes.last_analysis_results.Sucuri SiteCheck.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Sucuri SiteCheck.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.engine_name | string | | Symantec |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.engine_version | string | | 1.22.0.0 |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Symantec.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.engine_name | string | | SymantecMobileInsight |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.engine_update | string | | 20250124 |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.engine_version | string | | 2.0 |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.SymantecMobileInsight.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.engine_name | string | | TACHYON |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.engine_version | string | | 2025-05-14.02 |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.TACHYON.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.engine_name | string | | Tencent |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.engine_version | string | | 1.0.0.1 |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Tencent.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ThreatHive.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ThreatHive.engine_name | string | | ThreatHive |
action_result.data.\*.data.attributes.last_analysis_results.ThreatHive.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ThreatHive.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Threatsourcing.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Threatsourcing.engine_name | string | | Threatsourcing |
action_result.data.\*.data.attributes.last_analysis_results.Threatsourcing.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Threatsourcing.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.engine_name | string | | Trapmine |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.engine_update | string | | 20250417 |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.engine_version | string | | 4.0.4.0 |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Trapmine.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.engine_name | string | | TrendMicro-HouseCall |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.engine_version | string | | 24.550.0.1002 |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro-HouseCall.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.engine_name | string | | TrendMicro |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.engine_version | string | | 24.550.0.1002 |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.TrendMicro.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.engine_name | string | | Trustlook |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.engine_version | string | | 1.0 |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Trustlook.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Trustwave.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Trustwave.engine_name | string | | Trustwave |
action_result.data.\*.data.attributes.last_analysis_results.Trustwave.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Trustwave.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.URLQuery.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.URLQuery.engine_name | string | | URLQuery |
action_result.data.\*.data.attributes.last_analysis_results.URLQuery.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.URLQuery.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.URLhaus.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.URLhaus.engine_name | string | | URLhaus |
action_result.data.\*.data.attributes.last_analysis_results.URLhaus.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.URLhaus.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Underworld.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Underworld.engine_name | string | | Underworld |
action_result.data.\*.data.attributes.last_analysis_results.Underworld.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Underworld.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.engine_name | string | | VBA32 |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.engine_version | string | | 5.3.2 |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.VBA32.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.engine_name | string | | VIPRE |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.engine_update | string | | 20240522 |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.engine_version | string | | 6.0.0.35 |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.VIPRE.result | string | | Trojan.Autoruns.GenericKDS.41616931 |
action_result.data.\*.data.attributes.last_analysis_results.VX Vault.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.VX Vault.engine_name | string | | VX Vault |
action_result.data.\*.data.attributes.last_analysis_results.VX Vault.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.VX Vault.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Varist.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Varist.engine_name | string | | Varist |
action_result.data.\*.data.attributes.last_analysis_results.Varist.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Varist.engine_version | string | | 6.6.1.3 |
action_result.data.\*.data.attributes.last_analysis_results.Varist.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Varist.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.engine_name | string | | ViRobot |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.engine_version | string | | 2014.3.20.0 |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ViRobot.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Viettel Threat Intelligence.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Viettel Threat Intelligence.engine_name | string | | Viettel Threat Intelligence |
action_result.data.\*.data.attributes.last_analysis_results.Viettel Threat Intelligence.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Viettel Threat Intelligence.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.engine_name | string | | VirIT |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.engine_update | string | | 20250513 |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.engine_version | string | | 9.5.953 |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.VirIT.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ViriBack.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ViriBack.engine_name | string | | ViriBack |
action_result.data.\*.data.attributes.last_analysis_results.ViriBack.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ViriBack.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.engine_name | string | | Webroot |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.engine_update | string | | 20240523 |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.engine_version | string | | 1.0.0.403 |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Webroot.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium Verdict Cloud.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium Verdict Cloud.engine_name | string | | Xcitium Verdict Cloud |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium Verdict Cloud.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium Verdict Cloud.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.engine_name | string | | Xcitium |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.engine_update | string | | 20250513 |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.engine_version | string | | 37720 |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Xcitium.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Yandex Safebrowsing.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.Yandex Safebrowsing.engine_name | string | | Yandex Safebrowsing |
action_result.data.\*.data.attributes.last_analysis_results.Yandex Safebrowsing.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Yandex Safebrowsing.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.engine_name | string | | Yandex |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.engine_version | string | | 5.5.2.24 |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Yandex.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.ZeroCERT.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.ZeroCERT.engine_name | string | | ZeroCERT |
action_result.data.\*.data.attributes.last_analysis_results.ZeroCERT.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ZeroCERT.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.ZeroFox.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ZeroFox.engine_name | string | | ZeroFox |
action_result.data.\*.data.attributes.last_analysis_results.ZeroFox.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ZeroFox.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.category | string | | malicious |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.engine_name | string | | Zillya |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.engine_update | string | | 20240522 |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.engine_version | string | | 2.0.0.5118 |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Zillya.result | string | | Trojan.CozyCar.Win32.1 |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.engine_name | string | | ZoneAlarm |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.engine_version | string | | 6.16-103870578 |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.ZoneAlarm.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.engine_name | string | | Zoner |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.engine_version | string | | 2.2.2.0 |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.Zoner.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.engine_name | string | | alibabacloud |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.engine_update | string | | 20250321 |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.engine_version | string | | 2.2.0 |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.alibabacloud.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.alphaMountain.ai.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.alphaMountain.ai.engine_name | string | | alphaMountain.ai |
action_result.data.\*.data.attributes.last_analysis_results.alphaMountain.ai.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.alphaMountain.ai.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.benkow.cc.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.benkow.cc.engine_name | string | | benkow.cc |
action_result.data.\*.data.attributes.last_analysis_results.benkow.cc.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.benkow.cc.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.desenmascara.me.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.desenmascara.me.engine_name | string | | desenmascara.me |
action_result.data.\*.data.attributes.last_analysis_results.desenmascara.me.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.desenmascara.me.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.engine_name | string | | google_safebrowsing |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.engine_version | string | | 1.0 |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.google_safebrowsing.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.huorong.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.huorong.engine_name | string | | huorong |
action_result.data.\*.data.attributes.last_analysis_results.huorong.engine_update | string | | 20250513 |
action_result.data.\*.data.attributes.last_analysis_results.huorong.engine_version | string | | 9efd0f5:9efd0f5:8ec5796:8ec5796 |
action_result.data.\*.data.attributes.last_analysis_results.huorong.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.huorong.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.malwares.com URL checker.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.malwares.com URL checker.engine_name | string | | malwares.com URL checker |
action_result.data.\*.data.attributes.last_analysis_results.malwares.com URL checker.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.malwares.com URL checker.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.securolytics.category | string | | harmless |
action_result.data.\*.data.attributes.last_analysis_results.securolytics.engine_name | string | | securolytics |
action_result.data.\*.data.attributes.last_analysis_results.securolytics.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.securolytics.result | string | | clean |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.category | string | | type-unsupported |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.engine_name | string | | tehtris |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.engine_update | string | | 20250514 |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.engine_version | string | | |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.tehtris.result | string | | |
action_result.data.\*.data.attributes.last_analysis_results.zvelo.category | string | | undetected |
action_result.data.\*.data.attributes.last_analysis_results.zvelo.engine_name | string | | zvelo |
action_result.data.\*.data.attributes.last_analysis_results.zvelo.method | string | | blacklist |
action_result.data.\*.data.attributes.last_analysis_results.zvelo.result | string | | unrated |
action_result.data.\*.data.attributes.last_analysis_stats.confirmed-timeout | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.failure | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.harmless | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.malicious | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.suspicious | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.timeout | numeric | | |
action_result.data.\*.data.attributes.last_analysis_stats.type-unsupported | numeric | | 15 |
action_result.data.\*.data.attributes.last_analysis_stats.undetected | numeric | | 62 |
action_result.data.\*.data.attributes.last_dns_records.\*.priority | numeric | | 10 |
action_result.data.\*.data.attributes.last_dns_records.\*.ttl | numeric | | 25 |
action_result.data.\*.data.attributes.last_dns_records.\*.type | string | | MX |
action_result.data.\*.data.attributes.last_dns_records.\*.value | string | | smtp.google.com |
action_result.data.\*.data.attributes.last_dns_records_date | numeric | | 1747213079 |
action_result.data.\*.data.attributes.last_final_url | string | | https://www.google.com/ |
action_result.data.\*.data.attributes.last_http_response_code | numeric | | 200 |
action_result.data.\*.data.attributes.last_http_response_content_length | numeric | | 161888 |
action_result.data.\*.data.attributes.last_http_response_content_sha256 | string | | 4a79cebe13cb6edeb4f048ec31798e2ae8dd9f5855ba2fb6ff2e6f58a953056e |
action_result.data.\*.data.attributes.last_http_response_cookies.AEC | string | | AVcja2f65OcbkAEKZ2mQm7DnCgqA5cvhPhvlLPjTZ--UNG6aYqLKXaYjJg |
action_result.data.\*.data.attributes.last_http_response_cookies.NID | string | | 524=OHAvO7oSlr3MW-MGOEm0JTG7BCSZ43KEYWA3qDRlN_T5JIpY7bFYiENSdjI-BrLcI9jZPvQLWdTTV9aOqfhTFS4s5tOnR57yzTgMHI3C1kdehPt14AcCZ3dioZ1LvQyzVJ1vQC_Y3pG5RxE-jWHhbpQuDo2-5L4VWDRbq8ksbky7RM3igCLJWD5ABqg |
action_result.data.\*.data.attributes.last_http_response_headers.Accept-CH | string | | Sec-CH-Prefers-Color-Scheme, Downlink, RTT, Sec-CH-UA-Form-Factors, Sec-CH-UA-Platform, Sec-CH-UA-Platform-Version, Sec-CH-UA-Full-Version, Sec-CH-UA-Arch, Sec-CH-UA-Model, Sec-CH-UA-Bitness, Sec-CH-UA-Full-Version-List, Sec-CH-UA-WoW64 |
action_result.data.\*.data.attributes.last_http_response_headers.Alt-Svc | string | | h3=":443"; ma=2592000,h3-29=":443"; ma=2592000 |
action_result.data.\*.data.attributes.last_http_response_headers.Cache-Control | string | | private, max-age=0 |
action_result.data.\*.data.attributes.last_http_response_headers.Content-Encoding | string | | br |
action_result.data.\*.data.attributes.last_http_response_headers.Content-Length | string | | 161888 |
action_result.data.\*.data.attributes.last_http_response_headers.Content-Security-Policy-Report-Only | string | | object-src 'none';base-uri 'self';script-src 'nonce-fLKEJ3mZqMxV6lm_oGYG_w' 'strict-dynamic' 'report-sample' 'unsafe-eval' 'unsafe-inline' https: http:;report-uri https://csp.withgoogle.com/csp/gws/other-hp |
action_result.data.\*.data.attributes.last_http_response_headers.Content-Type | string | | text/html; charset=UTF-8 |
action_result.data.\*.data.attributes.last_http_response_headers.Cross-Origin-Opener-Policy | string | | same-origin-allow-popups; report-to="gws" |
action_result.data.\*.data.attributes.last_http_response_headers.Date | string | | Wed, 14 May 2025 10:30:45 GMT |
action_result.data.\*.data.attributes.last_http_response_headers.Expires | string | | -1 |
action_result.data.\*.data.attributes.last_http_response_headers.P3P | string | | CP="This is not a P3P policy! See g.co/p3phelp for more info." |
action_result.data.\*.data.attributes.last_http_response_headers.Permissions-Policy | string | | unload=() |
action_result.data.\*.data.attributes.last_http_response_headers.Report-To | string | | {"group":"gws","max_age":2592000,"endpoints":[{"url":"https://csp.withgoogle.com/csp/report-to/gws/other"}]} |
action_result.data.\*.data.attributes.last_http_response_headers.Server | string | | gws |
action_result.data.\*.data.attributes.last_http_response_headers.Set-Cookie | string | | Dummy Cookie |
action_result.data.\*.data.attributes.last_http_response_headers.X-Frame-Options | string | | SAMEORIGIN |
action_result.data.\*.data.attributes.last_http_response_headers.X-XSS-Protection | string | | 0 |
action_result.data.\*.data.attributes.last_https_certificate.cert_signature.signature | string | | 24fd62b23f7a7556aa6307b882fa1d16a54b80038f12b4faf9744e9309fa111b18a78d44fabda6999df4659d9fae743b529eaf7d87f41f5206a9a1448e93cbce7269ef9ba458c3fb581169ba8f687e2cb7be6c418bd73314f72fa6e443b1dc9e4900a4df7c5cbf01f516d25faddc82bd25d1fc6d6390cace1c0581e1f2a4fa18dfe6bcf824212069bb743b31cd152e47d5be99aa4466c3cee3a1302d9a380ac1d472375d11b8f3181dfc0d420d759998919bc8f94f992be6b762c7ca42ca5d0f5cb396d3f760533d31b30bbe112121bc2d02aa523e6a2de8e35c1aa28c460daba286fc5be40d56d40691ca2be86d219caeabeabd940b87f24973dfac2ec86a5f |
action_result.data.\*.data.attributes.last_https_certificate.cert_signature.signature_algorithm | string | | sha256RSA |
action_result.data.\*.data.attributes.last_https_certificate.extensions.1.3.6.1.4.1.11129.2.4.2 | string | | 0481f300f100770012f14e34bd53724c840619c38f3f7a13f8e7b56287889c6d |
action_result.data.\*.data.attributes.last_https_certificate.extensions.CA | boolean | | |
action_result.data.\*.data.attributes.last_https_certificate.extensions.authority_key_identifier.keyid | string | | de1b1eed7915d43e3724c321bbec34396d42b230 |
action_result.data.\*.data.attributes.last_https_certificate.extensions.ca_information_access.CA Issuers | string | | http://i.pki.goog/wr2.crt |
action_result.data.\*.data.attributes.last_https_certificate.extensions.ca_information_access.OCSP | string | | http://o.pki.goog/wr2 |
action_result.data.\*.data.attributes.last_https_certificate.extensions.certificate_policies.\* | string | | 2.23.140.1.2.1 |
action_result.data.\*.data.attributes.last_https_certificate.extensions.crl_distribution_points.\* | string | | http://c.pki.goog/wr2/9UVbN0w5E6Y.crl |
action_result.data.\*.data.attributes.last_https_certificate.extensions.extended_key_usage.\* | string | | serverAuth |
action_result.data.\*.data.attributes.last_https_certificate.extensions.key_usage.\* | string | | digitalSignature |
action_result.data.\*.data.attributes.last_https_certificate.extensions.subject_alternative_name.\* | string | | \*.google.com |
action_result.data.\*.data.attributes.last_https_certificate.extensions.subject_key_identifier | string | | b3397ca6824f2d3e9b70abb0e18ba2c83eb2a638 |
action_result.data.\*.data.attributes.last_https_certificate.issuer.C | string | | US |
action_result.data.\*.data.attributes.last_https_certificate.issuer.CN | string | | WR2 |
action_result.data.\*.data.attributes.last_https_certificate.issuer.O | string | | Google Trust Services |
action_result.data.\*.data.attributes.last_https_certificate.public_key.algorithm | string | | EC |
action_result.data.\*.data.attributes.last_https_certificate.public_key.ec.oid | string | | secp256r1 |
action_result.data.\*.data.attributes.last_https_certificate.public_key.ec.pub | string | | 3059301306072a8648ce3d020106082a8648ce3d03010703420004c9fd2afb7e2538c658c206ad878018247c72322db84dd203ad1860ad2cba40d56e3e18f9aae5935d1622051d2e2c8213f8f2c6ee672074df9622593d1c88bd0d |
action_result.data.\*.data.attributes.last_https_certificate.serial_number | string | | da4c71f767da54d512c6f93d8a9f2d5b |
action_result.data.\*.data.attributes.last_https_certificate.size | numeric | | 3635 |
action_result.data.\*.data.attributes.last_https_certificate.subject.C | string | | US |
action_result.data.\*.data.attributes.last_https_certificate.subject.CN | string | | \*.google.com |
action_result.data.\*.data.attributes.last_https_certificate.subject.L | string | | San Francisco |
action_result.data.\*.data.attributes.last_https_certificate.subject.O | string | | Cloudflare, Inc. |
action_result.data.\*.data.attributes.last_https_certificate.subject.ST | string | | California |
action_result.data.\*.data.attributes.last_https_certificate.thumbprint | string | | 2fbce9f21341f13e3453d6f4e9178e401082d13e |
action_result.data.\*.data.attributes.last_https_certificate.thumbprint_sha256 | string | | 30fb9699da9e78103e4fcc8b2afd0274dc4f963f1a2deb8efc134acd31ceeed4 |
action_result.data.\*.data.attributes.last_https_certificate.validity.not_after | string | | 2025-07-14 08:40:41 |
action_result.data.\*.data.attributes.last_https_certificate.validity.not_before | string | | 2025-04-21 08:40:42 |
action_result.data.\*.data.attributes.last_https_certificate.version | string | | V3 |
action_result.data.\*.data.attributes.last_https_certificate_date | numeric | | 1747213079 |
action_result.data.\*.data.attributes.last_modification_date | numeric | | 1747219155 |
action_result.data.\*.data.attributes.last_seen_itw_date | numeric | | 1675144537 |
action_result.data.\*.data.attributes.last_submission_date | numeric | | 1747219124 |
action_result.data.\*.data.attributes.last_update_date | numeric | | 1722565053 |
action_result.data.\*.data.attributes.magic | string | | ASCII text, with no line terminators |
action_result.data.\*.data.attributes.magika | string | | TXT |
action_result.data.\*.data.attributes.mandiant_ic_score | numeric | | |
action_result.data.\*.data.attributes.md5 | string | | e2fc714c4727ee9395f324cd2e7f331f |
action_result.data.\*.data.attributes.meaningful_name | string | | Test_File.txt |
action_result.data.\*.data.attributes.names.\* | string | | Test_File.txt |
action_result.data.\*.data.attributes.network | string | | 1.1.1.0/24 |
action_result.data.\*.data.attributes.outgoing_links.\* | string | | https://about.dummyurl.com/?utm_source=google-ZZ&utm_medium=referral&utm_campaign=hp-footer&fg=1 |
action_result.data.\*.data.attributes.popularity_ranks.Alexa.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Alexa.timestamp | numeric | | 1684083480 |
action_result.data.\*.data.attributes.popularity_ranks.Cisco Umbrella.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Cisco Umbrella.timestamp | numeric | | 1747147091 |
action_result.data.\*.data.attributes.popularity_ranks.Cloudflare Radar.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Cloudflare Radar.timestamp | numeric | | 1747147083 |
action_result.data.\*.data.attributes.popularity_ranks.Majestic.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Majestic.timestamp | numeric | | 1747147095 |
action_result.data.\*.data.attributes.popularity_ranks.Quantcast.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Quantcast.timestamp | numeric | | 1585755370 |
action_result.data.\*.data.attributes.popularity_ranks.Statvoo.rank | numeric | | 1 |
action_result.data.\*.data.attributes.popularity_ranks.Statvoo.timestamp | numeric | | 1684083481 |
action_result.data.\*.data.attributes.rdap.entities.\*.as_event_actor.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.autnums.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.entities.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.events.\*.event_action | string | | last changed |
action_result.data.\*.data.attributes.rdap.entities.\*.events.\*.event_actor | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.events.\*.event_date | string | | 2017-12-11T15:40:13.000+00:00 |
action_result.data.\*.data.attributes.rdap.entities.\*.events.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.handle | string | | 2138514_DOMAIN_COM-VRSN |
action_result.data.\*.data.attributes.rdap.entities.\*.lang | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.networks.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.object_class_name | string | | entity |
action_result.data.\*.data.attributes.rdap.entities.\*.port43 | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.public_ids.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.rdap_conformance.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.remarks.\*.description.\* | string | | Some of the data in this object has been removed. |
action_result.data.\*.data.attributes.rdap.entities.\*.remarks.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.remarks.\*.title | string | | REDACTED FOR PRIVACY |
action_result.data.\*.data.attributes.rdap.entities.\*.remarks.\*.type | string | | object redacted due to authorization |
action_result.data.\*.data.attributes.rdap.entities.\*.roles.\* | string | | administrative |
action_result.data.\*.data.attributes.rdap.entities.\*.status.\* | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.url | string | | |
action_result.data.\*.data.attributes.rdap.entities.\*.vcard_array.\*.name | string | | version |
action_result.data.\*.data.attributes.rdap.entities.\*.vcard_array.\*.type | string | | text |
action_result.data.\*.data.attributes.rdap.entities.\*.vcard_array.\*.values.\* | string | | 4.0 |
action_result.data.\*.data.attributes.rdap.events.\*.event_action | string | | expiration |
action_result.data.\*.data.attributes.rdap.events.\*.event_actor | string | | |
action_result.data.\*.data.attributes.rdap.events.\*.event_date | string | | 2028-09-13T07:00:00.000+00:00 |
action_result.data.\*.data.attributes.rdap.events.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.handle | string | | 2138514_DOMAIN_COM-VRSN |
action_result.data.\*.data.attributes.rdap.lang | string | | |
action_result.data.\*.data.attributes.rdap.ldh_name | string | | google.com |
action_result.data.\*.data.attributes.rdap.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.entities.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.events.\*.event_action | string | | last changed |
action_result.data.\*.data.attributes.rdap.nameservers.\*.events.\*.event_actor | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.events.\*.event_date | string | | 2008-06-08T04:46:18.000+00:00 |
action_result.data.\*.data.attributes.rdap.nameservers.\*.events.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.handle | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.lang | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.ldh_name | string | | ns1.google.com |
action_result.data.\*.data.attributes.rdap.nameservers.\*.links.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.notices.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.object_class_name | string | | nameserver |
action_result.data.\*.data.attributes.rdap.nameservers.\*.port43 | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.remarks.\* | string | | |
action_result.data.\*.data.attributes.rdap.nameservers.\*.status.\* | string | | active |
action_result.data.\*.data.attributes.rdap.nameservers.\*.unicode_name | string | | |
action_result.data.\*.data.attributes.rdap.nask0_state | string | | |
action_result.data.\*.data.attributes.rdap.notices.\*.description.\* | string | | By submitting an RDAP query, you agree that you will use this data only for |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.href | string | | https://www.markmonitor.com/legal/domain-management-terms-and-conditions |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.href_lang.\* | string | | |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.media | string | | |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.rel | string | | related |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.title | string | | |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.type | string | | text/html |
action_result.data.\*.data.attributes.rdap.notices.\*.links.\*.value | string | | https://www.markmonitor.com/legal/domain-management-terms-and-conditions |
action_result.data.\*.data.attributes.rdap.notices.\*.title | string | | Terms of Use |
action_result.data.\*.data.attributes.rdap.notices.\*.type | string | | |
action_result.data.\*.data.attributes.rdap.object_class_name | string | | domain |
action_result.data.\*.data.attributes.rdap.port43 | string | | whois.markmonitor.com |
action_result.data.\*.data.attributes.rdap.public_ids.\* | string | | |
action_result.data.\*.data.attributes.rdap.punycode | string | | |
action_result.data.\*.data.attributes.rdap.rdap_conformance.\* | string | | rdap_level_0 |
action_result.data.\*.data.attributes.rdap.remarks.\* | string | | |
action_result.data.\*.data.attributes.rdap.secure_dns.delegation_signed | boolean | | |
action_result.data.\*.data.attributes.rdap.secure_dns.ds_data.\* | string | | |
action_result.data.\*.data.attributes.rdap.secure_dns.key_data.\* | string | | |
action_result.data.\*.data.attributes.rdap.secure_dns.max_sig_life | numeric | | |
action_result.data.\*.data.attributes.rdap.secure_dns.zone_signed | boolean | | |
action_result.data.\*.data.attributes.rdap.status.\* | string | | client update prohibited |
action_result.data.\*.data.attributes.rdap.switch_name | string | | |
action_result.data.\*.data.attributes.rdap.type | string | | |
action_result.data.\*.data.attributes.rdap.unicode_name | string | | |
action_result.data.\*.data.attributes.rdap.variants.\* | string | | |
action_result.data.\*.data.attributes.redirection_chain.\* | string | | https://www.google.com/ |
action_result.data.\*.data.attributes.registrar | string | | MarkMonitor Inc. |
action_result.data.\*.data.attributes.reputation | numeric | | -1 |
action_result.data.\*.data.attributes.sha1 | string | | 81fe8bfe87576c3ecb22426f8e57847382917acf |
action_result.data.\*.data.attributes.sha256 | string | | 88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589 |
action_result.data.\*.data.attributes.size | numeric | | 4 |
action_result.data.\*.data.attributes.ssdeep | string | | 3:uW:uW |
action_result.data.\*.data.attributes.tags.\* | string | | text |
action_result.data.\*.data.attributes.threat_names.\* | string | | |
action_result.data.\*.data.attributes.threat_severity.last_analysis_date | string | | 1717867483 |
action_result.data.\*.data.attributes.threat_severity.level_description | string | | No severity score data |
action_result.data.\*.data.attributes.threat_severity.threat_severity_data.belongs_to_bad_collection | boolean | | True |
action_result.data.\*.data.attributes.threat_severity.threat_severity_data.domain_rank | string | | 1 |
action_result.data.\*.data.attributes.threat_severity.threat_severity_data.has_bad_communicating_files_high | boolean | | True |
action_result.data.\*.data.attributes.threat_severity.threat_severity_data.has_bad_communicating_files_medium | boolean | | True |
action_result.data.\*.data.attributes.threat_severity.threat_severity_level | string | | SEVERITY_NONE |
action_result.data.\*.data.attributes.threat_severity.version | numeric | | 5 |
action_result.data.\*.data.attributes.times_submitted | numeric | | 84 |
action_result.data.\*.data.attributes.title | string | | Google |
action_result.data.\*.data.attributes.tld | string | | com |
action_result.data.\*.data.attributes.total_votes.harmless | numeric | | |
action_result.data.\*.data.attributes.total_votes.malicious | numeric | | 1 |
action_result.data.\*.data.attributes.type_description | string | | Text |
action_result.data.\*.data.attributes.type_extension | string | | txt |
action_result.data.\*.data.attributes.type_tag | string | | text |
action_result.data.\*.data.attributes.type_tags.\* | string | | text |
action_result.data.\*.data.attributes.unique_sources | numeric | | 62 |
action_result.data.\*.data.attributes.url | string | | https://www.google.com/ |
action_result.data.\*.data.attributes.vhash | string | | 9eecb7db59d16c80417c72d1e1f4fbf1 |
action_result.data.\*.data.attributes.whois | string | | Dummy Whois |
action_result.data.\*.data.attributes.whois_date | numeric | | 1746621240 |
action_result.data.\*.data.id | string | | dea20c241265e2995244187c8476570893df41b9623784a4ca6ed075721b8cdf |
action_result.data.\*.data.links.self | string | | https://www.virustotal.com/api/v3/files/dea20c241265e2995244187c8476570893df41b9623784a4ca6ed075721b8cdf |
action_result.data.\*.data.relationships.campaigns.data.\* | string | | |
action_result.data.\*.data.relationships.campaigns.links.self | string | | https://www.virustotal.com/api/v3/files/88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589/campaigns?limit=20&attributes=name%2Cid%2Corigin%2Ccollection_type%2Cdescription%2Ctargeted_regions%2Ctargeted_industries%2Csponsor_region |
action_result.data.\*.data.relationships.malware_families.data.\*.attributes.collection_type | string | | malware-family |
action_result.data.\*.data.relationships.malware_families.data.\*.attributes.description | string | | Autogenerated malware family ursnif from detections by virustotal_cape |
action_result.data.\*.data.relationships.malware_families.data.\*.attributes.name | string | | ursnif |
action_result.data.\*.data.relationships.malware_families.data.\*.attributes.origin | string | | Partner |
action_result.data.\*.data.relationships.malware_families.data.\*.attributes.targeted_industries.\* | string | | |
action_result.data.\*.data.relationships.malware_families.data.\*.attributes.targeted_regions.\* | string | | |
action_result.data.\*.data.relationships.malware_families.data.\*.context_attributes.role | string | | viewer |
action_result.data.\*.data.relationships.malware_families.data.\*.context_attributes.shared_with_me | boolean | | |
action_result.data.\*.data.relationships.malware_families.data.\*.id | string | | analysis_virustotal_cape_ursnif |
action_result.data.\*.data.relationships.malware_families.data.\*.links.self | string | | https://www.virustotal.com/api/v3/collections/analysis_virustotal_cape_ursnif |
action_result.data.\*.data.relationships.malware_families.data.\*.type | string | | collection |
action_result.data.\*.data.relationships.malware_families.links.next | string | | Dummy Value |
action_result.data.\*.data.relationships.malware_families.links.self | string | | https://www.virustotal.com/api/v3/files/88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589/malware_families?limit=20&attributes=name%2Cid%2Corigin%2Ccollection_type%2Cdescription%2Ctargeted_regions%2Ctargeted_industries%2Csponsor_region |
action_result.data.\*.data.relationships.malware_families.meta.cursor | string | | eyJsaW1pdCI6IDIwLCAib2Zmc2V0IjogMjB9 |
action_result.data.\*.data.relationships.related_threat_actors.data.\* | string | | |
action_result.data.\*.data.relationships.related_threat_actors.links.self | string | | https://www.virustotal.com/api/v3/files/88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589/related_threat_actors?limit=20&attributes=name%2Cid%2Corigin%2Ccollection_type%2Cdescription%2Ctargeted_regions%2Ctargeted_industries%2Csponsor_region |
action_result.data.\*.data.relationships.reports.data.\*.attributes.collection_type | string | | report |
action_result.data.\*.data.relationships.reports.data.\*.attributes.name | string | | QATEST-TestReport-CMS Migration - Version:1 |
action_result.data.\*.data.relationships.reports.data.\*.attributes.origin | string | | Google Threat Intelligence |
action_result.data.\*.data.relationships.reports.data.\*.attributes.source_regions_hierarchy.\*.confidence | string | | possible |
action_result.data.\*.data.relationships.reports.data.\*.attributes.source_regions_hierarchy.\*.country | string | | Bangladesh |
action_result.data.\*.data.relationships.reports.data.\*.attributes.source_regions_hierarchy.\*.country_iso2 | string | | BD |
action_result.data.\*.data.relationships.reports.data.\*.attributes.source_regions_hierarchy.\*.description | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.source_regions_hierarchy.\*.first_seen | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.source_regions_hierarchy.\*.last_seen | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.source_regions_hierarchy.\*.region | string | | Asia |
action_result.data.\*.data.relationships.reports.data.\*.attributes.source_regions_hierarchy.\*.source | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.source_regions_hierarchy.\*.sub_region | string | | Southern Asia |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_industries_tree.\*.confidence | string | | possible |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_industries_tree.\*.description | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_industries_tree.\*.first_seen | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_industries_tree.\*.industry | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_industries_tree.\*.industry_group | string | | Aerospace & Defense |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_industries_tree.\*.last_seen | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_industries_tree.\*.source | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_regions_hierarchy.\*.confidence | string | | possible |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_regions_hierarchy.\*.country | string | | Andorra |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_regions_hierarchy.\*.country_iso2 | string | | AD |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_regions_hierarchy.\*.description | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_regions_hierarchy.\*.first_seen | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_regions_hierarchy.\*.last_seen | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_regions_hierarchy.\*.region | string | | Europe |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_regions_hierarchy.\*.source | string | | |
action_result.data.\*.data.relationships.reports.data.\*.attributes.targeted_regions_hierarchy.\*.sub_region | string | | Southern Europe |
action_result.data.\*.data.relationships.reports.data.\*.context_attributes.role | string | | viewer |
action_result.data.\*.data.relationships.reports.data.\*.context_attributes.shared_with_me | boolean | | |
action_result.data.\*.data.relationships.reports.data.\*.id | string | | report--18-00003660 |
action_result.data.\*.data.relationships.reports.data.\*.links.self | string | | https://www.virustotal.com/api/v3/collections/report--18-00003660 |
action_result.data.\*.data.relationships.reports.data.\*.type | string | | collection |
action_result.data.\*.data.relationships.reports.links.next | string | | Dummy URL for next |
action_result.data.\*.data.relationships.reports.links.self | string | | https://www.virustotal.com/api/v3/files/88d4266fd4e6338d13b845fcf289579d209c897823b9217da3e161936f031589/reports?limit=20&attributes=name%2Cid%2Ccollection_type%2Corigin%2Csource_regions_hierarchy%2Ctargeted_industries_tree%2Ctargeted_regions_hierarchy |
action_result.data.\*.data.relationships.reports.meta.cursor | string | | eyJsaW1pdCI6IDIwLCAib2Zmc2V0IjogMjB9 |
action_result.data.\*.data.type | string | | file |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add comment'

Add a comment to an IP address, URL, domain, or file

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity** | required | Entity (IP, URL, Domain, File [Vault ID in SOAR or MD5/SHA1/SHA256]) to add comment | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` |
**comment_text** | required | Add the comment text | string | |
**password** | optional | Password to decompress and scan a file contained in a protected ZIP file | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment_text | string | | Added comment |
action_result.parameter.entity | string | `vault id` `sha1` `sha256` `md5` `ip` `ipv6` `url` `domain` | |
action_result.parameter.password | string | | comment |
action_result.data | string | | |
action_result.data.\*.data.attributes.date | numeric | | 1744699510 |
action_result.data.\*.data.attributes.html | string | | Added comment to File |
action_result.data.\*.data.attributes.tags.\* | string | | |
action_result.data.\*.data.attributes.text | string | | Added comment to File |
action_result.data.\*.data.attributes.votes.abuse | numeric | | |
action_result.data.\*.data.attributes.votes.negative | numeric | | |
action_result.data.\*.data.attributes.votes.positive | numeric | | |
action_result.data.\*.data.id | string | | f-c79691701daf5d1c4887812a7a0cf3633b87cbe52e7f655c870ab087ce0aac44-eaef9c4f |
action_result.data.\*.data.links.self | string | | https://www.virustotal.com/api/v3/comments/f-c79691701daf5d1c4887812a7a0cf3633b87cbe52e7f655c870ab087ce0aac44-eaef9c4f |
action_result.data.\*.data.type | string | | comment |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'delete comment'

Delete a specific comment

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**comment_id** | required | Comment ID of the comment | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment_id | string | | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get passive dns data'

Fetch passive DNS data for a domain or IP address

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity** | required | Entity (IP or Domain) to fetch the Passive DNS data (Max 100 records will be returned) | string | `ip` `ipv6` `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.entity | string | `ip` `ipv6` `domain` | |
action_result.data | string | | |
action_result.data.\*.attributes.date | numeric | | 1744708487 |
action_result.data.\*.attributes.host_name | string | | centrplane.com |
action_result.data.\*.attributes.host_name_last_analysis_stats | numeric | | |
action_result.data.\*.attributes.host_name_last_analysis_stats.\* | numeric | | |
action_result.data.\*.attributes.ip_address | string | | 1.1.1.1 |
action_result.data.\*.attributes.ip_address_last_analysis_stats | numeric | | 1 |
action_result.data.\*.attributes.ip_address_last_analysis_stats.\* | numeric | | 1 |
action_result.data.\*.attributes.resolver | string | | VirusTotal |
action_result.data.\*.id | string | | 1.1.1.1centrplane.com |
action_result.data.\*.links.next | string | | https://www.virustotal.com/api/v3/ip_addresses/1.1.1.1/resolutions?limit=10&cursor=ClwKEQoEZGF0ZRIJCP-pgdSm2YwDEkNqEXN-dmlydXN0b3RhbGNsb3Vkci4LEgpSZXNvbHV0aW9uIh4xLjEuMS4xdHJhaW5pbmcuYWNtY2hyaXMuc3BhY2UMGAAgAQ%3D%3D |
action_result.data.\*.links.self | string | | https://www.virustotal.com/api/v3/resolutions/1.1.1.1centrplane.com |
action_result.data.\*.links.self | string | | https://www.virustotal.com/api/v3/ip_addresses/1.1.1.1/resolutions?limit=10 |
action_result.data.\*.meta.count | numeric | | 200 |
action_result.data.\*.meta.cursor | string | | ClwKEQoEZGF0ZRIJCP-pgdSm2YwDEkNqEXN-dmlydXN0b3RhbGNsb3Vkci4LEgpSZXNvbHV0aW9uIh4xLjEuMS4xdHJhaW5pbmcuYWNtY2hyaXMuc3BhY2UMGAAgAQ== |
action_result.data.\*.type | string | | resolution |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get vulnerability report'

Fetch the vulnerability report for a given vulnerability ID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vulnerability_id** | required | Vulnerability ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.vulnerability_id | string | | |
action_result.data | string | | |
action_result.data.\*.data.attributes.affected_systems.\* | string | | |
action_result.data.\*.data.attributes.alt_names.\* | string | | |
action_result.data.\*.data.attributes.alt_names_details.\* | string | | |
action_result.data.\*.data.attributes.analysis | string | | Mandiant Threat Intelligence considers this a Medium-risk vulnerability. |
action_result.data.\*.data.attributes.autogenerated_tags.\* | string | | |
action_result.data.\*.data.attributes.available_mitigation | string | | Patch |
action_result.data.\*.data.attributes.capabilities.\* | string | | |
action_result.data.\*.data.attributes.collection_links.\* | string | | |
action_result.data.\*.data.attributes.collection_type | string | | vulnerability |
action_result.data.\*.data.attributes.counters | numeric | | |
action_result.data.\*.data.attributes.counters.\* | numeric | | |
action_result.data.\*.data.attributes.cpes.\*.end_cpe | string | | |
action_result.data.\*.data.attributes.cpes.\*.end_rel | string | | |
action_result.data.\*.data.attributes.cpes.\*.start_cpe.product | string | | FortiWLC |
action_result.data.\*.data.attributes.cpes.\*.start_cpe.uri | string | | cpe:2.3:a:fortinet:fortiwlc:8.1.3:\*:\*:\*:\*:\*:\*:\* |
action_result.data.\*.data.attributes.cpes.\*.start_cpe.vendor | string | | Fortinet |
action_result.data.\*.data.attributes.cpes.\*.start_cpe.version | string | | 8.1.3 |
action_result.data.\*.data.attributes.cpes.\*.start_rel | string | | = |
action_result.data.\*.data.attributes.creation_date | numeric | | 1643296210 |
action_result.data.\*.data.attributes.cve_id | string | | CVE-2021-42758 |
action_result.data.\*.data.attributes.cvss.cvssv2_0.base_score | numeric | | 9 |
action_result.data.\*.data.attributes.cvss.cvssv2_0.temporal_score | numeric | | 6.7 |
action_result.data.\*.data.attributes.cvss.cvssv2_0.vector | string | | AV:N/AC:L/Au:S/C:C/I:C/A:C/E:U/RL:OF/RC:C |
action_result.data.\*.data.attributes.cvss.cvssv3_x.base_score | numeric | | 8.8 |
action_result.data.\*.data.attributes.cvss.cvssv3_x.temporal_score | numeric | | 8.8 |
action_result.data.\*.data.attributes.cvss.cvssv3_x.vector | string | | CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H |
action_result.data.\*.data.attributes.cwe.id | string | | CWE-284 |
action_result.data.\*.data.attributes.cwe.title | string | | Access Control Issues |
action_result.data.\*.data.attributes.date_of_disclosure | numeric | | 1638835200 |
action_result.data.\*.data.attributes.days_to_report | numeric | | 51 |
action_result.data.\*.data.attributes.description | string | | The National Vulnerability Database (NVD) has provided the following description: \*An improper access control vulnerability [CWE-284] in FortiWLC 8.6.1 and below may allow an authenticated and remote attacker with low privileges to execute any command as an admin user with full access rights via bypassing the GUI restrictions.\* |
action_result.data.\*.data.attributes.detection_names.\* | string | | |
action_result.data.\*.data.attributes.domains_count | numeric | | |
action_result.data.\*.data.attributes.epss.percentile | numeric | | 0.60842 |
action_result.data.\*.data.attributes.epss.score | numeric | | 0.00225 |
action_result.data.\*.data.attributes.executive_summary | string | | * An Access Control Issues vulnerability exists that, when exploited, allows a remote, privileged attacker to execute arbitrary code. * We are currently unaware of exploitation activity in the wild. Exploit code is not publicly available. * Mandiant Intelligence considers this a Medium-risk vulnerability due to the potential for arbitrary code execution. * Mitigation options include a patch. |
action_result.data.\*.data.attributes.exploit_availability | string | | No Known |
action_result.data.\*.data.attributes.exploitation.exploit_release_date | string | | |
action_result.data.\*.data.attributes.exploitation.first_exploitation | string | | |
action_result.data.\*.data.attributes.exploitation.tech_details_release_date | string | | |
action_result.data.\*.data.attributes.exploitation_consequence | string | | Code Execution |
action_result.data.\*.data.attributes.exploitation_state | string | | No Known |
action_result.data.\*.data.attributes.exploitation_vectors.\* | string | | General Network Connectivity |
action_result.data.\*.data.attributes.field_sources.\*.field | string | | cvss.cvssv3_x |
action_result.data.\*.data.attributes.field_sources.\*.source.field_type | string | | Ranked |
action_result.data.\*.data.attributes.field_sources.\*.source.source_name | string | | Mandiant Intelligence |
action_result.data.\*.data.attributes.field_sources.\*.source.source_url | string | | |
action_result.data.\*.data.attributes.field_sources.\*.source.sources.\* | string | | |
action_result.data.\*.data.attributes.files_count | numeric | | |
action_result.data.\*.data.attributes.first_seen_details.\* | string | | |
action_result.data.\*.data.attributes.intended_effects.\* | string | | |
action_result.data.\*.data.attributes.ip_addresses_count | numeric | | |
action_result.data.\*.data.attributes.last_modification_date | numeric | | 1722834319 |
action_result.data.\*.data.attributes.last_seen_details.\* | string | | |
action_result.data.\*.data.attributes.malware_roles.\* | string | | |
action_result.data.\*.data.attributes.mati_genids_dict.cve_id | string | | vulnerability--cb62f6c1-fd3e-5eb2-b79f-383ef157f274 |
action_result.data.\*.data.attributes.mati_genids_dict.mve_id | string | | vulnerability--23f038c9-39ac-5182-aa82-7bb5ac11ab5f |
action_result.data.\*.data.attributes.mati_genids_dict.report_id | string | | report--30591557-76b0-54d3-b9ab-25d2b1138154 |
action_result.data.\*.data.attributes.merged_actors.\* | string | | |
action_result.data.\*.data.attributes.mitigations.\* | string | | |
action_result.data.\*.data.attributes.motivations.\* | string | | |
action_result.data.\*.data.attributes.mve_id | string | | MVE-2021-8671 |
action_result.data.\*.data.attributes.name | string | | CVE-2021-42758 |
action_result.data.\*.data.attributes.operating_systems.\* | string | | |
action_result.data.\*.data.attributes.origin | string | | Google Threat Intelligence |
action_result.data.\*.data.attributes.predicted_risk_rating | string | | MEDIUM |
action_result.data.\*.data.attributes.priority | string | | P3 |
action_result.data.\*.data.attributes.private | boolean | | True |
action_result.data.\*.data.attributes.recent_activity_summary.\* | string | | |
action_result.data.\*.data.attributes.references_count | numeric | | |
action_result.data.\*.data.attributes.risk_factors | string | | |
action_result.data.\*.data.attributes.risk_rating | string | | MEDIUM |
action_result.data.\*.data.attributes.source_regions_hierarchy.\* | string | | |
action_result.data.\*.data.attributes.sources.\*.cvss | string | | |
action_result.data.\*.data.attributes.sources.\*.cvss.\* | string | | |
action_result.data.\*.data.attributes.sources.\*.md5 | string | | 16cb3968bbc5220f1f34cd5504fccc80 |
action_result.data.\*.data.attributes.sources.\*.name | string | | Mitre Corporation |
action_result.data.\*.data.attributes.sources.\*.published_date | numeric | | 1638960783 |
action_result.data.\*.data.attributes.sources.\*.source_description | string | | |
action_result.data.\*.data.attributes.sources.\*.title | string | | |
action_result.data.\*.data.attributes.sources.\*.unique_id | string | | |
action_result.data.\*.data.attributes.sources.\*.url | string | | https://github.com/CVEProject/cvelistV5/blob/main/cves/2021/42xxx/CVE-2021-42758.json |
action_result.data.\*.data.attributes.status | string | | COMPUTED |
action_result.data.\*.data.attributes.subscribers_count | numeric | | |
action_result.data.\*.data.attributes.tags.\* | string | | |
action_result.data.\*.data.attributes.tags_details.\* | string | | |
action_result.data.\*.data.attributes.targeted_industries.\* | string | | |
action_result.data.\*.data.attributes.targeted_industries_tree.\* | string | | |
action_result.data.\*.data.attributes.targeted_informations.\* | string | | |
action_result.data.\*.data.attributes.targeted_regions.\* | string | | |
action_result.data.\*.data.attributes.targeted_regions_hierarchy.\* | string | | |
action_result.data.\*.data.attributes.technologies.\* | string | | |
action_result.data.\*.data.attributes.threat_scape.\* | string | | |
action_result.data.\*.data.attributes.top_icon_md5.\* | string | | |
action_result.data.\*.data.attributes.urls_count | numeric | | |
action_result.data.\*.data.attributes.vendor_fix_references.\*.cvss | string | | |
action_result.data.\*.data.attributes.vendor_fix_references.\*.md5 | string | | |
action_result.data.\*.data.attributes.vendor_fix_references.\*.name | string | | Fortinet Inc. |
action_result.data.\*.data.attributes.vendor_fix_references.\*.published_date | numeric | | 1638896400 |
action_result.data.\*.data.attributes.vendor_fix_references.\*.source_description | string | | |
action_result.data.\*.data.attributes.vendor_fix_references.\*.title | string | | FortiWLC - Improper authenticated access control |
action_result.data.\*.data.attributes.vendor_fix_references.\*.unique_id | string | | FG-IR-21-200 |
action_result.data.\*.data.attributes.vendor_fix_references.\*.url | string | | https://fortiguard.com/advisory/FG-IR-21-200 |
action_result.data.\*.data.attributes.version_history.\*.date | numeric | | 1739499164 |
action_result.data.\*.data.attributes.version_history.\*.version_notes.\* | string | | priority: Added |
action_result.data.\*.data.attributes.vulnerable_products | string | | |
action_result.data.\*.data.attributes.workarounds.\* | string | | |
action_result.data.\*.data.context_attributes.role | string | | viewer |
action_result.data.\*.data.context_attributes.shared_with_me | boolean | | |
action_result.data.\*.data.id | string | | vulnerability--cve-2021-42758 |
action_result.data.\*.data.links.self | string | | https://www.virustotal.com/api/v3/collections/vulnerability--cve-2021-42758 |
action_result.data.\*.data.type | string | | collection |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update dtm alert status'

Update the status of a DTM alert

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | The ID of the alert | string | |
**status** | required | Status of the alert | string | |
**tags** | optional | Tags to add to alert | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | | |
action_result.parameter.status | string | | new |
action_result.parameter.tags | string | | test_tag test_tag2 |
action_result.data | string | | |
action_result.data.\*.ai_doc_summary | string | | Dummy AI summary |
action_result.data.\*.alert_summary | string | | Dummy Alert summary |
action_result.data.\*.alert_type | string | | Message |
action_result.data.\*.analysis | string | | |
action_result.data.\*.confidence | numeric | | 0.5410931651580755 |
action_result.data.\*.confidence_reasoning.benign_count | numeric | | |
action_result.data.\*.confidence_reasoning.confidence_count | string | | |
action_result.data.\*.confidence_reasoning.explanation | string | | |
action_result.data.\*.confidence_reasoning.malicious_count | numeric | | |
action_result.data.\*.confidence_reasoning.response_count | numeric | | |
action_result.data.\*.confidence_reasoning.version | string | | |
action_result.data.\*.created_at | string | | 2025-04-21T11:23:22.735Z |
action_result.data.\*.doc_matches.\* | string | | |
action_result.data.\*.doc_url | string | | https://api.intelligence.mandiant.com/v4/dtm/docs/message/4cab55d4-45df-4f27-97f4-2c3392cea967 |
action_result.data.\*.email_sent_at | string | | |
action_result.data.\*.has_analysis | boolean | | |
action_result.data.\*.id | string | | d032laift9uskgdprke0 |
action_result.data.\*.ignore | boolean | | |
action_result.data.\*.label_matches.\* | string | | |
action_result.data.\*.labels_url | string | | https://api.intelligence.mandiant.com/v4/dtm/docs/message/4cab55d4-45df-4f27-97f4-2c3392cea967/labels |
action_result.data.\*.monitor_id | string | | d032k9oprvanesm0sdgg |
action_result.data.\*.monitor_version | numeric | | 1 |
action_result.data.\*.severity | string | | low |
action_result.data.\*.severity_reasoning.rule | string | | |
action_result.data.\*.status | string | | new |
action_result.data.\*.tags.\* | string | | test_tag |
action_result.data.\*.title | string | | Found topic "amazon" posted by actor "Faramarz Apllanadi" on Telegram channel "szpmarket" |
action_result.data.\*.topic_matches.\*.topic_id | string | | doc_type:message |
action_result.data.\*.topic_matches.\*.value | string | | message |
action_result.data.\*.topics_url | string | | https://api.intelligence.mandiant.com/v4/dtm/docs/message/4cab55d4-45df-4f27-97f4-2c3392cea967/topics |
action_result.data.\*.updated_at | string | | 2025-05-19T10:25:27Z |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update asm issue status'

Update the status of an ASM issue

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** | required | The ID of the issue | string | |
**status** | required | Status of the issue | string | |
**project_id** | optional | Project ID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | | |
action_result.parameter.project_id | string | | |
action_result.parameter.status | string | | open_triaged |
action_result.data | string | | |
action_result.data.\*.message | string | | Successfully reported status as open_triaged |
action_result.data.\*.result | string | | open_triaged |
action_result.data.\*.success | boolean | | True |
action_result.summary | string | | |
action_result.message | string | | Action has been executed successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2026 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
