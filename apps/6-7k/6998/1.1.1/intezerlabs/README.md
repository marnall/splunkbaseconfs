# Intezer

Publisher: Intezer Labs \
Connector Version: 1.1.1 \
Product Vendor: Intezer Labs \
Product Name: Intezer \
Minimum Product Version: 5.5.0

Intezer connector for Splunk SOAR enables security teams to automate the analysis, detection, and response of threats by integrating Intezer's technology into their Splunk workflows

# Intezer Labs

Publisher: Intezer Labs\
Connector Version: 1.1.1\
Product Vendor: Intezer Labs\
Product Name: Intezer\
Product Version Supported (regex): ".\*"\
Minimum Product Version: 5.5.0

## About Intezer Splunk SOAR Connector

Intezer connector for Splunk SOAR enables security teams to automate the analysis, detection, and
response of threats by integrating Intezer's technology into their Splunk workflows.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Intezer server. Below are the default
ports used by Splunk SOAR.

| Service Name | Transport Protocol | Port |
|--------------|--------------------|------|
| http | tcp | 80 |
| https | tcp | 443 |

### Configuration Variables

| VARIABLE | REQUIRED | TYPE | DESCRIPTION |
|------------|----------|----------|-----------------|
| **apikey** | required | password | Intezer API key |

### Supported Actions

- [test connectivity](#action-test-connectivity) - Test connection to Intezer.
- [detonate_file](#action-detonate-file) - Analyze a file from Splunk vault with Intezer.
- [detonate_hash](#action-detonate-hash) - Analyze a file hash (SHA1, SHA256, or MD5) on Intezer Analyze.
- [get_file_report](#action-get-file-report) - Get a file analysis report based on an analysis ID or a file hash.
- [detonate_url](#action-detonate-url) - Analyze a suspicious URL with Intezer.
- [get_url_report](#action-get-url-report) - Get a URL analysis report based on a URL analysis ID.
- [submit_alert](#action-submit-alert) - Submit a new alert, including the raw alert information, to Intezer for processing.
- [submit_suspicious_email](#action-submit-suspicious-email) - Submit a suspicious phishing email in a raw format (.MSG or .EML) to Intezer for processing.
- [get_alert](#action-get-alert) - Get an ingested alert triage and response information using alert ID.
- [index_file](#action-index-file) - Index the file's genes into the organizational database.
- [unset_index_file](#action-unset-index-file) - Unset file's indexing.

## action: 'test connectivity'

Test connection to Intezer.

Type: **test**\
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------|---------|--------------------------------------------------|----------------|
| is_available | boolean | Whether the connection to Intezer was successful | true |

## action: 'detonate file'

Analyze a file from Splunk vault with Intezer.

Type: **investigate**\
Read only: **True**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|----------------------|----------|------------------------------|--------|------------|
| **vault_id** | required | File's vault ID | string | `vault id` |\
| **related_alert_id** | optional | alert id the file related to | string | `alert id` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-----------------|--------|-------------------------|------------------------------------------------------|
| analysis_id | string | Intezer analysis ID | |
| analysis_status | string | Intezer analysis status | `created` `in_progress` `queued` `failed` `finished` |
| analysis_type | string | File Analysis | `file` |
| identifier | string | vault id requested | `vault id` |

## action: 'detonate hash'

Analyze a file hash (SHA1, SHA256, or MD5) on Intezer Analyze.

Type: **investigate**\
Read only: **True**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|---------------|----------|-------------------------------|--------|---------------------------------|
| **file_hash** | required | Analyze hash file via Intezer | string | `hash` `sha256` `sha1` `md5` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-----------------|--------|-------------------------|------------------------------------------------------|
| analysis_id | string | Intezer analysis ID | |
| analysis_status | string | Intezer analysis status | `created` `in_progress` `queued` `failed` `finished` |
| analysis_type | string | File Analysis | `file` |
| identifier | string | hash requested | |

## action: 'get file report'

Get a file analysis report based on an analysis ID or a file hash.

Type: **generic**\
Read only: **True**

#### Action Parameters

Provide either analysis_id or file_hash.

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-------------------------|----------|---------------------------------------------------------------------------------------------|---------|---------------------------------|
| **analysis_id** | optional | File analysis ID. The analysis ID is returned when submitting a file or a hash for analysis | string | |\
| **file_hash** | optional | Hash of the desired report | string | `hash` `sha256` `sha1` `md5` |\
| **private_only** | optional | Whether to show only private reports (relevant only for hashes). | boolean | |\
| **wait_for_completion** | optional | Whether to wait for the analysis to complete before returning the report. | boolean | |

#### Action Output

For more details take a look here:

- [get analysis details](https://analyze.intezer.com/api-docs.html#/paths/analyses-analysis_id/get)

- [iocs](https://analyze.intezer.com/api-docs.html#/paths/analyses-analysis_id--iocs/get)

- [dynamic ttps](https://analyze.intezer.com/api-docs.html#/paths/analyses-analysis_id--dynamic-ttps/get)

- [detect and hunt](https://analyze.intezer.com/api-docs.html#/paths/analyses-analysis_id--detect/get)

- [code reuse](https://analyze.intezer.com/api-docs.html#/paths/analyses-analysis_id--sub-analyses-root-code-reuse/get)

- [metadata](https://analyze.intezer.com/api-docs.html#/paths/analyses-analysis_id--sub-analyses-root-metadata/get)

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|----------------------------------|------------|-------------------------|------------------------------------------------------|
| analysis_status | string | Intezer analysis status | `created` `in_progress` `queued` `failed` `finished` |
| analysis_type | string | File Analysis | `file` |
| analysis_id | string | Intezer analysis ID | |
| analysis_content.analysis | dictionary | analysis report | |
| analysis_content.iocs | dictionary | iocs report | |
| analysis_content.ttps | dictionary | ttps report | |
| analysis_content.metadata | dictionary | metadata report | |
| analysis_content.root-code-reuse | dictionary | root-code-reuse report | |

## action: 'detonate url'

Analyze a suspicious URL with Intezer.

Type: **investigate**\
Read only: **True**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------|----------|----------------|--------|-------------|
| **url** | required | URL to analyze | string | `valid url` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-----------------|--------|-------------------------|------------------------------------------------------|
| analysis_id | string | Intezer analysis ID | |
| analysis_status | string | Intezer analysis status | `created` `in_progress` `queued` `failed` `finished` |
| analysis_type | string | URL Analysis | `url` |
| identifier | string | url requested | |

## action: 'get url report'

Get a URL analysis report based on a URL analysis ID.

Type: **generic**\
Read only: **True**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-------------------------|----------|---------------------------------------------------------------------------------|---------|----------|
| **analysis_id** | required | URL analysis ID. The analysis ID is returned when submitting a URL for analysis | string | |\
| **wait_for_completion** | optional | Whether to wait for the analysis to finish. | boolean | |

#### Action Output

For more details take a look here:

- [url-analysis-id](https://analyze.intezer.com/api-docs.html#/paths/url-analysis_id/get)

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|---------------------------|------------|-------------------------|------------------------------------------------------|
| analysis_status | string | Intezer analysis status | `created` `in_progress` `queued` `failed` `finished` |
| analysis_type | string | URL Analysis | `url` |
| analysis_id | string | Intezer analysis ID | |
| analysis_content.analysis | dictionary | analysis report | |

## action: 'get alert'

Get an ingested alert triage and response information using alert ID.

Type: **generic**\
Read only: **True**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-------------------------|----------|---------------------------------------------|---------|----------|
| **alert_id** | required | The alert id to query | string | |\
| **wait_for_completion** | optional | Whether to wait for the analysis to finish. | boolean | |

#### Action Output

For more details take a look here:

- [get alert](https://analyze.intezer.com/api-docs.html#/paths/alerts-search/get)

## action: 'submit alert'

Submit a new alert, including the raw alert information, to Intezer for processing.

Type: **Generic**\
Read only: **True**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-------------------|----------|----------------------------------------------|--------|--------------|
| **source** | required | The source of the alert | string | alert source |\
| **raw_alert** | required | alert raw data in JSON format | string | JSON format |\
| **alert_mapping** | required | mapping to use for the alert in JSON formant | string | JSON format |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------|--------|----------|----------------|
| **alert_id** | string | alert ID | |

## action: 'submit suspicious email'

Submit a suspicious phishing email in a raw format (.MSG or .EML) to Intezer for processing

Type: **Generic**\
Read only: **True**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|--------------|----------|------------------|--------|------------|
| **vault_id** | required | Email's vault ID | string | `vault id` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------|--------|----------|----------------|
| **alert_id** | string | alert ID | |

## action: 'index file'

Index the file's genes into the organizational database.

Type: **correct**\
Read only: **True**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------------|----------|-------------------------------|--------|------------------------|
| **index_as** | required | Index as trusted or malicious | string | `trusted` `malicious` |\
| **sha256** | optional | sha256 to index | string | `sha256` |\
| **family_name** | optional | family name to index as | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------|--------|----------|----------------|
| **index_id** | string | Index ID | |

## action: 'unset index file'

Unset file's indexing.

Type: **correct**\
Read only: **True**

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|---------------|----------|---------------------------------|--------|---------------------------------|
| **file_hash** | required | Hash file to unset the indexing | string | `hash` `sha256` `sha1` `md5` |

#### Action Output

No output

### Configuration variables

This table lists the configuration variables required to operate Intezer. These variables are specified when configuring a Intezer asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**intezer_api_key** | required | password | API key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[detonate file](#action-detonate-file) - Analyze a file from Splunk vault with Intezer \
[detonate hash](#action-detonate-hash) - Analyze a file hash (SHA1, SHA256, or MD5) with Intezer \
[get file report](#action-get-file-report) - Get a file analysis report based on an analysis ID or a file hash \
[detonate url](#action-detonate-url) - Analyze a suspicious URL with Intezer \
[get url report](#action-get-url-report) - Get a URL analysis report based on a URL analysis ID \
[get alert](#action-get-alert) - Get an ingested alert triage and response information using alert ID \
[submit alert](#action-submit-alert) - Submit a new alert, including the raw alert information, to Intezer for processing \
[submit suspicious email](#action-submit-suspicious-email) - Submit a suspicious phishing email in a raw format (.MSG or .EML) to Intezer for processing \
[index file](#action-index-file) - Index the file's genes into the organizational database \
[unset index file](#action-unset-index-file) - Unset file's indexing

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

Test connection with Intezer.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'detonate file'

Analyze a file from Splunk vault with Intezer

Type: **generic** \
Read only: **False**

Analyze a file from Splunk Vault. The action returns the analysis ID and status.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | File's vault ID | string | `vault id` |
**related_alert_id** | optional | The alert ID that the file is related to | string | `alert id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.vault_id | string | `vault id` | |
action_result.parameter.related_alert_id | string | `alert id` | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.analysis_id | string | `analysis id` | |
action_result.data.\*.analysis_status | string | | created in_progress queued failed finished |
action_result.data.\*.analysis_type | string | | file |
action_result.data.\*.identifier | string | `vault id` | |
action_result.summary | string | | |

## action: 'detonate hash'

Analyze a file hash (SHA1, SHA256, or MD5) with Intezer

Type: **generic** \
Read only: **False**

Analyze a hash from Splunk Vault. The action returns the analysis ID and status.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_hash** | required | File hash (SHA1, SHA256, or MD5) | string | `hash` `sha1` `sha256` `md5` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.file_hash | string | `hash` `sha1` `sha256` `md5` | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.analysis_id | string | `analysis id` | |
action_result.data.\*.analysis_status | string | | created in_progress queued failed finished |
action_result.data.\*.analysis_type | string | | file |
action_result.data.\*.identifier | string | `hash` `sha1` `sha256` `md5` | |
action_result.summary | string | | |

## action: 'get file report'

Get a file analysis report based on an analysis ID or a file hash

Type: **investigate** \
Read only: **True**

Get a file analysis report based on an analysis ID or a file hash.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | optional | File analysis ID. The analysis ID is returned when submitting a file or a hash for analysis | string | `analysis id` |
**file_hash** | optional | File's hash (SHA1, SHA256, MD5) | string | `hash` `sha1` `sha256` `md5` |
**private_only** | optional | The "private_only" parameter, used when retrieving analysis reports by file hash, determines database access: "false" (default) uses both public and private databases, consuming additional quota for first-time public access; "true" uses only your private database, conserving quota | boolean | |
**wait_for_completion** | optional | Whether to wait for the analysis to finish | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.analysis_id | string | `analysis id` | |
action_result.parameter.file_hash | string | `hash` `sha1` `sha256` `md5` | |
action_result.parameter.private_only | boolean | | |
action_result.parameter.wait_for_completion | boolean | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.analysis_type | string | `file` | |
action_result.data.\*.analysis_id | string | `analysis id` | |
action_result.data.\*.analysis_status | string | | created in_progress queued failed finished |
action_result.data.\*.analysis_content.analysis.analysis_time | string | `time utc format` | |
action_result.data.\*.analysis_content.analysis.analysis_url | string | `analysis url` | |
action_result.data.\*.analysis_content.analysis.file_name | string | `file name` | |
action_result.data.\*.analysis_content.analysis.is_private | boolean | `is private analysis` | |
action_result.data.\*.analysis_content.analysis.sha256 | string | `sha256` | |
action_result.data.\*.analysis_content.analysis.sub_verdict | string | | file_based memory_threat suspicious_powershell_command blocklisted_software custom_rule suspicious_script suspicious_behavior testing_activity custom |
action_result.data.\*.analysis_content.analysis.iocs.files.\*.sha256 | string | `sha256` | |
action_result.data.\*.analysis_content.analysis.iocs.network.\*.ip | string | `ip` | |
action_result.data.\*.analysis_content.analysis.iocs.network.\*.url | string | `url` | |
action_result.data.\*.analysis_content.analysis.ttps.\*.ttp.ttp | string | `ttp` | |
action_result.summary | string | | |

## action: 'detonate url'

Analyze a suspicious URL with Intezer

Type: **generic** \
Read only: **False**

Analyze a suspicious URL with Intezer.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to analyze | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.url | string | `url` | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.analysis_id | string | `analysis id` | |
action_result.data.\*.analysis_status | string | | created in_progress queued failed finished |
action_result.summary | string | | |

## action: 'get url report'

Get a URL analysis report based on a URL analysis ID

Type: **investigate** \
Read only: **True**

Get a URL analysis report based on a URL analysis ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**analysis_id** | required | URL analysis ID. The analysis ID is returned when submitting a URL for analysis | string | `analysis id` |
**wait_for_completion** | optional | Whether to wait for the analysis to finish | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.analysis_id | string | `analysis id` | |
action_result.parameter.wait_for_completion | boolean | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.analysis_type | string | `url` | |
action_result.data.\*.analysis_id | string | `analysis id` | |
action_result.data.\*.analysis_status | string | | created in_progress queued failed finished |
action_result.data.\*.analysis_content.analysis.downloaded_file.analysis_id | string | `analysis id` | |
action_result.data.\*.analysis_content.analysis.downloaded_file.sha256 | string | `sha256` | |
action_result.data.\*.analysis_content.analysis.domain_info.domain_name | string | `domain name` | |
action_result.data.\*.analysis_content.analysis.indicators.\*.text | string | `indicator` | |
action_result.data.\*.analysis_content.analysis.ip | string | `ip` | |
action_result.data.\*.analysis_content.analysis.scanned_url | string | `url` | |
action_result.data.\*.analysis_content.analysis.submitted_url | string | `ip` | |
action_result.data.\*.analysis_content.analysis.summary.verdict_type | string | `verdict` | |
action_result.data.\*.analysis_content.analysis.summary.verdict_name | string | `verdict name` | |
action_result.data.\*.analysis_content.analysis.summary.title | string | `title` | |
action_result.summary | string | | |

## action: 'get alert'

Get an ingested alert triage and response information using alert ID

Type: **investigate** \
Read only: **True**

Get an ingested alert triage and response information using alert ID.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**alert_id** | required | The alert ID to query | string | `alert id` |
**wait_for_completion** | optional | Whether to wait for the analysis to finish | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.alert_id | string | `alert id` | |
action_result.parameter.wait_for_completion | boolean | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.data.\*.alert_url | string | `url` | |
action_result.data.\*.source | string | `source` | |
action_result.data.\*.alert.alert_id | string | `alert id` | |
action_result.data.\*.alert.alert_title | string | `alert title` | |
action_result.data.\*.alert.severity | string | `alert severity` | |
action_result.data.\*.alert.creation_time | string | `time in utc` | |
action_result.data.\*.alert.is_mitigated | boolean | | |
action_result.data.\*.alert.device.hostname | string | `hostname` | |
action_result.data.\*.alert.device.os_type | string | `os type` | |
action_result.data.\*.triage_result.alert_verdict | string | `verdict` | |
action_result.data.\*.triage_result.risk_category | string | `risk category` | |
action_result.data.\*.triage_result.risk_level | string | `risk level` | |
action_result.data.\*.triage_result.threat_name | string | `threat name` | |
action_result.data.\*.scans.\*.file_analysis.analysis_id | string | `analysis id` | |
action_result.data.\*.scans.\*.file_analysis.verdict | string | `verdict` | |
action_result.data.\*.scans.file_analysis.sha256 | string | `sha256` | |
action_result.data.\*.response.status | string | `response status` | |
action_result.data.\*.scans | string | `scan` | |
action_result.summary | string | | |

## action: 'submit alert'

Submit a new alert, including the raw alert information, to Intezer for processing

Type: **generic** \
Read only: **False**

Submit a new alert, including the raw alert information, to Intezer for processing.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**source** | required | Where the alert came from | string | |
**raw_alert** | required | The alert raw data in JSON format | string | |
**alert_mapping** | required | The mapping to use for the alert in JSON formant | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.source | string | | |
action_result.parameter.raw_alert | string | | |
action_result.parameter.alert_mapping | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
summary.data.\*.alert_id | string | | |
action_result.summary | string | | |
action_result.data | string | | |

## action: 'submit suspicious email'

Submit a suspicious phishing email in a raw format (.MSG or .EML) to Intezer for processing

Type: **generic** \
Read only: **False**

Submit a suspicious phishing email in a raw format (.MSG or .EML) to Intezer for processing.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** | required | The vault ID of the email to submit | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.vault_id | string | | |
action_result.status | string | | success failed |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
summary.data.\*.alert_id | string | | |
action_result.data | string | | |
action_result.summary | string | | |

## action: 'index file'

Index the file's genes into the organizational database

Type: **correct** \
Read only: **False**

Index the file's genes into the organizational database.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**index_as** | required | "trusted" or "malicious" | string | |
**vault_id** | optional | File's vault ID | string | `vault id` |
**family_name** | optional | Family name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.index_as | string | | |
action_result.parameter.vault_id | string | `vault id` | |
action_result.parameter.family_name | string | | |
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
summary.data.\*.index_id | string | | |
action_result.summary | string | | |

## action: 'unset index file'

Unset file's indexing

Type: **correct** \
Read only: **False**

Unset file's indexing.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_hash** | required | File's hash (SHA1, SHA256, MD5) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.file_hash | string | | |
action_result.status | string | | success failed |
action_result.data | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.summary | string | | |

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
