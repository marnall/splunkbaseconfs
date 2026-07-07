# Intezer Labs

Publisher: Intezer Labs\
Connector Version: 1.1.0\
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
