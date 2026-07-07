# CheckPhish

Publisher: Splunk Community\
Connector Version: 1.0.1\
Product Vendor: Bolster\
Product Name: Checkphish\
Product Version Supported (regex): ".\*"\
Minimum Product Version: 5.0.0

This app provides investigative actions for bolster.ai and checkphish.ai

Please note that running the test connectivity action on this app will submit a URL for detonation
potentially counting against API key quota.

### Configuration Variables

The below configuration variables are required for this Connector to operate. These variables are specified when configuring a Checkphish asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_url** | required | string | API URL for Scan Requests
**api_key** | required | password | API Key

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration\
[check status](#action-check-status) - Get URL scan Results\
[detonate url](#action-detonate-url) - Submit a URL for scan

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test**\
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'check status'

Get URL scan Results

Type: **investigate**\
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**job_id** | required | Job ID retrieved during a previous URL scan | string | `checkphish job id`

#### Action Output

DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action_result.parameter.job_id | string | `checkphish job id`
action_result.data.\*.brand | string |
action_result.data.\*.disposition | string |
action_result.data.\*.error | boolean |
action_result.data.\*.insights | string |
action_result.data.\*.job_id | string | `checkphish job id`
action_result.data.\*.resolved | boolean |
action_result.data.\*.screenshot_path | string |
action_result.data.\*.status | string |
action_result.data.\*.url | string | `url`
action_result.data.\*.url_sha256 | string | `url` `sha256`
action_result.status | string |
action_result.message | string |
action_result.summary | string |
summary.total_objects | numeric |
summary.total_objects_successful | numeric |

## action: 'detonate url'

Submit a URL for scan

Type: **generic**\
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to be scanned | string | `url`
**scan_type** | required | Type of scan to run | string |

#### Action Output

DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action_result.parameter.scan_type | string |
action_result.parameter.url | string | `url`
action_result.data.\*.jobID | string | `checkphish job id`
action_result.data.\*.timestamp | numeric |
action_result.status | string |
action_result.message | string |
action_result.summary | string |
action_result.summary.job_id | string | `checkphish job id`
summary.total_objects | numeric |
summary.total_objects_successful | numeric |
