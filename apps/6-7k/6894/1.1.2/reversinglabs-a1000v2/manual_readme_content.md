# Reversinglabs A1000 v2

Publisher: ReversingLabs\
Connector Version: 1.1.1\
Product Vendor: ReversingLabs\
Product Name: A1000\
Product Version Supported (regex): ".\*"\
Minimum Product Version: 5.5.0

App integrates with ReversingLabs A1000 Malware Analysis Appliance APIs

### Configuration Variables

The below configuration variables are required for this Connector to operate. These variables are specified when configuring a A1000 asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** | required | string | A1000 url
**token** | required | password | A1000 token

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration\
[detonate file](#action-detonate-file) - Upload file to A1000\
[submit url](#action-submit-url) - Detonate file from url\
[check submitted url status](#action-check-submitted-url-status) - Check submitted url status\
[create pdf report](#action-create-pdf-report) - Create pdf report\
[check pdf report creation](#action-check-pdf-report-creation) - Check pdf report creation\
[download pdf report](#action-download-pdf-report) - Download pdf report\
[get titaniumcore report](#action-get-titaniumcore-report) - Get TitaniumCore report\
[url reputation](#action-url-reputation) - Queries URL info\
[domain reputation](#action-domain-reputation) - Queries domain info\
[ip reputation](#action-ip-reputation) - Queries IP info\
[network ip to domain](#action-network-ip-to-domain) - Get a list of IP-to-domain mappings\
[network urls from ip](#action-network-urls-from-ip) - Get a list of URLs hosted on the requested IP address\
[network files from ip](#action-network-files-from-ip) - Get a a list of hashes and classifications for files found on the requested IP address\
[advanced search](#action-advanced-search) - Search for samples using multi-part search criteria\
[advanced search ticloud](#action-advanced-search-ticloud) - Search for samples available on the TitaniumCloud\
[advanced search local](#action-advanced-search-local) - Search for samples available on the A1000 appliance\
[create dynamic analysis report](#action-create-dynamic-analysis-report) - Initiate the creation of dynamic analysis PDF report\
[check dynamic analysis report status](#action-check-dynamic-analysis-report-status) - Get status of the report previously requested\
[download dynamic analysis report](#action-download-dynamic-analysis-report) - Download previously requested dynamic analysis report in pdf\
[get summary report](#action-get-summary-report) - Get a summary report for hash\
[get detailed report](#action-get-detailed-report) - Get detailed analysis report\
[get classification](#action-get-classification) - Get classification for a sample\
[get user tags](#action-get-user-tags) - List existing tags for the requested sample\
[create user tags](#action-create-user-tags) - Add one or more user tags\
[delete user tags](#action-delete-user-tags) - Remove one or more user tags\
[set sample classification](#action-set-sample-classification) - Set the classification of a sample\
[delete sample classification](#action-delete-sample-classification) - Delete the (user set) classification of a sample\
[yara get rulesets](#action-yara-get-rulesets) - Get a list of YARA rulesets that are on the A1000\
[yara get ruleset text](#action-yara-get-ruleset-text) - Get the full contents of the requested ruleset\
[yara get matches](#action-yara-get-matches) - Retrieve the list of YARA matches\
[yara create or update ruleset](#action-yara-create-or-update-ruleset) - Creates a new YARA ruleset if it doesn't exist\
[yara delete ruleset](#action-yara-delete-ruleset) - Delete a specific YARA ruleset and its matches\
[yara enable or disable ruleset](#action-yara-enable-or-disable-ruleset) - Enable or disable a ruleset on the appliance\
[yara get synchronization time](#action-yara-get-synchronization-time) - Get the current synchronization time\
[yara set ruleset synchronization time](#action-yara-set-ruleset-synchronization-time) - Modify the TiCloud sync time for TiCloud enabled rulesets\
[yara start or stop local retro scan](#action-yara-start-or-stop-local-retro-scan) - Allow users to start or stop the Local Retro scan on the appliance\
[yara manage cloud retro scan](#action-yara-manage-cloud-retro-scan) - Allow users to start, stop or clear a Cloud Retro scan\
[yara status retro scan local](#action-yara-status-retro-scan-local) - Allow users to check the status of a Local Retro scan\
[yara status retro scan cloud](#action-yara-status-retro-scan-cloud) - Allow users to check the status of Cloud Retro scan\
[list containers for hash](#action-list-containers-for-hash) - Get a list of containers from which the requested samples\
[delete sample](#action-delete-sample) - Delete the sample with the requested hash value\
[download extracted files](#action-download-extracted-files) - Download files extracted from local sample\
[reanalyze local samples](#action-reanalyze-local-samples) - Submit a set of samples that already exist on the A1000

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test**\
Read only: **True**

Validate the asset configuration for connectivity using supplied configuration.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'detonate file'

Upload file to A1000

Type: **investigate**\
Read only: **True**

Upload file to A1000.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-------------------------------|----------|---------------------------------------------------|----------|--------------------------------------------------------------|
| **vault_id** | required | Vault ID of file to detonate | string | `vault_id` |
| **file_name** | optional | Filename to use | string | `file name` |
| **custom_file_name** | optional | Custom file name for upload | string | `file name` |
| **archive_password** | optional | password for the file if it is password protected | password | |
| **rl_cloud_sandbox_platform** | optional | Cloud Sandbox platform | string | |
| **tags** | optional | Comma separated list of tags to assign to sample | string | |
| **comment** | optional | Comment to add to sample | string | |
| **cloud_analysis** | optional | Use cloud analysis | boolean | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|---------------------------------------------------|----------|--------------------------------------------------------------|-------------------------------------------------------|
| action_result.parameter.vault_id | string | `vault_id` | |
| action_result.parameter.file_name | string | `file name` | |
| action_result.parameter.custom_file_name | string | `file name` | |
| action_result.parameter.rl_cloud_sandbox_platform | string | | "windows7" "windows10" "macos_11" "windows11" "linux" |
| action_result.parameter.tags | string | | |
| action_result.parameter.comment | string | | |
| action_result.parameter.cloud_analysis | boolean | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'submit url'

Detonate file from url

Type: **generic**\
Read only: **False**

Detonate file from url.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-------------------------------|----------|-------------------------------------------------------|----------|----------|
| **file_url** | required | URL from which the appliance should download the data | string | `url` |
| **crawler** | optional | Crawler method (local or cloud) | password | |
| **archive_password** | optional | Password, if file is a password-protected archive | string | |
| **rl_cloud_sandbox_platform** | optional | Cloud Sandbox platform | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|---------------------------------------------------|---------|----------|-------------------------------------------------------|
| action_result.parameter.file_url | string | `url` | |
| action_result.parameter.crawler | string | | "local" "cloud" |
| action_result.parameter.rl_cloud_sandbox_platform | string | | "windows7" "windows10" "macos_11" "windows11" "linux" |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'check submitted url status'

Check submitted url status

Type: **generic**\
Read only: **False**

Check submitted url status. Returns report if ready.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**task_id** | required | Id of the task | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.task_id | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'create pdf report'

Create pdf report

Type: **generic**\
Read only: **False**

Initiate pdf report creation.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'check pdf report creation'

Check pdf report creation

Type: **generic**\
Read only: **False**

Check pdf report creation status.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'download pdf report'

Download pdf report

Type: **generic**\
Read only: **False**

Download pdf report.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get titaniumcore report'

Get TitaniumCore report

Type: **generic**\
Read only: **False**

Accepts a single hash string and gets the full TitaniumCore static analysis report for the requested sample.The requested sample must be present on the appliance. If the optional fields parameter is not provided in the request, all available parts of the static analysis report are returned in the response.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'url reputation'

Queries URL info

Type: **investigate**\
Read only: **True**

Queries URL info.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to query | string | `url`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.url | string | `url` |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'domain reputation'

Queries domain info

Type: **investigate**\
Read only: **True**

Queries domain info.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain to query | string | `domain` `url`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.domain | string | `domain` `url` |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'ip reputation'

Queries IP info

Type: **investigate**\
Read only: **True**

Queries IP info.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP to query | string | `ip`

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.ip | string | `ip` |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'network ip to domain'

Get a list of IP-to-domain mappings

Type: **generic**\
Read only: **False**

Accepts an IP address string and returns a list of IP-to-domain mappings.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|---------------|----------|-------------------|---------|----------|
| **ip** | required | IP address | string | `ip` |
| **page** | optional | SHA1 hash of page | string | |
| **page_size** | optional | Page size | numeric | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-----------------------------------|---------|----------|----------------|
| action_result.parameter.ip | string | `ip` | |
| action_result.parameter.page | string | | |
| action_result.parameter.page_size | numeric | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'network urls from ip'

Get a list of URLs hosted on the requested IP address

Type: **generic**\
Read only: **False**

Accepts an IP address string and returns a list of URLs hosted on the requested IP address.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|---------------|----------|-------------------|---------|----------|
| **ip** | required | IP address | string | `ip` |
| **page** | optional | SHA1 hash of page | string | |
| **page_size** | optional | Page size | numeric | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-----------------------------------|---------|----------|----------------|
| action_result.parameter.ip | string | `ip` | |
| action_result.parameter.page | string | | |
| action_result.parameter.page_size | numeric | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'network files from ip'

Get a a list of hashes and classifications for files found on the requested IP address

Type: **generic**\
Read only: **False**

Accepts an IP address string and returns a list of hashes and classifications for files found on the requested IP address.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|---------------|----------|-------------------|---------|----------|
| **ip** | required | IP address | string | `ip` |
| **page** | optional | SHA1 hash of page | string | |
| **page_size** | optional | Page size | numeric | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-----------------------------------|---------|----------|----------------|
| action_result.parameter.ip | string | `ip` | |
| action_result.parameter.page | string | | |
| action_result.parameter.page_size | numeric | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'advanced search'

Search for samples using multi-part search criteria

Type: **generic**\
Read only: **True**

Search for samples available on the local A1000 instance and TitaniumCloud using the Advanced Search capabilities.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------------------|----------|---------------------------|---------|----------------|
| **query** | required | Advanced Search query | string | `search query` |
| **limit** | optional | Maximum number of results | numeric | |
| **only_cloud_results** | optional | Show only TiCloud results | boolean | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------------------------------------|---------|----------------|----------------------------|
| action_result.parameter.query | string | `search query` | "classification:malicious" |
| action_result.parameter.limit | numeric | | |
| action_result.parameter.only_cloud_results | boolean | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'advanced search ticloud'

Search for samples available on the TitaniumCloud using the V3 endpoint

Type: **generic**\
Read only: **True**

All restricted words and characters must be escaped with double quotation marks. This action will work only if A1000 is set up with the access to TiCloud.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------------------|----------|--------------------------------------------------------------------------------|---------|----------------|
| **query** | required | Advanced Search query | string | `search query` |
| **start_search_date** | required | The starting date for the search (later date) | string | |
| **end_search_date** | required | The ending date for the search (earlier date) | string | |
| **sorting_order** | optional | Ascending or descending | string | |
| **sorting_criteria** | optional | Sort results on this column | string | |
| **limit** | optional | Get at most <limit> search results, if page is set max value is 100 | numeric | |
| **page** | optional | Use pagination instead of aggregated getter, off by default, index starts at 1 | numeric | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-------------------------------------------|---------|----------------|-----------------------------------------------------------------|
| action_result.parameter.query | string | `search query` | "classification:malicious" |
| action_result.parameter.start_search_date | string | | "2024-05-30" |
| action_result.parameter.end_search_date | string | | "2024-05-01" |
| action_result.parameter.sorting_order | string | | "asc" "desc" |
| action_result.parameter.sorting_criteria | string | | "sha1" "firstseen" "threatname" "sampletype" "filecount" "size" |
| action_result.parameter.limit | numeric | | |
| action_result.parameter.page | numeric | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'advanced search local'

Search for samples available on the A1000 appliance using the V3 endpoint

Type: **generic**\
Read only: **True**

All restricted words and characters must be escaped with double quotation marks.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------------------|----------|--------------------------------------------------------------------------------|---------|----------------|
| **query** | required | Advanced Search query | string | `search query` |
| **sorting_order** | optional | Ascending or descending | string | |
| **sorting_criteria** | optional | Sort results on this column | string | |
| **limit** | optional | Get at most <limit> search results, if page is set max value is 100 | numeric | |
| **page** | optional | Use pagination instead of aggregated getter, off by default, index starts at 1 | numeric | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|------------------------------------------|---------|----------------|-----------------------------------------------------------------|
| action_result.parameter.query | string | `search query` | "classification:malicious" |
| action_result.parameter.sorting_order | string | | "asc" "desc" |
| action_result.parameter.sorting_criteria | string | | "sha1" "firstseen" "threatname" "sampletype" "filecount" "size" |
| action_result.parameter.limit | numeric | | |
| action_result.parameter.page | numeric | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'create dynamic analysis report'

Initiate the creation of dynamic analysis PDF report

Type: **generic**\
Read only: **False**

Accepts a single hash string and and a report format and initiates the creation of PDF or HTML reports for samples that have gone through dynamic analysis in the ReversingLabs Cloud Sandbox.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'check dynamic analysis report status'

Get status of the report previously requested

Type: **generic**\
Read only: **False**

Accepts a single hash string and report format parameters that should correspond to the parameters used in the request with create_dynamic_analysis_report method. The response includes an informative message about the status of the report previously requested.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'download dynamic analysis report'

Download previously requested dynamic analysis report in pdf

Type: **generic**\
Read only: **False**

Accepts a single hash string and report format parameters that should correspond to the parameters used in the request with create_dynamic_analysis_report method.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.hash | string | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get summary report'

Get a summary report for hash

Type: **generic**\
Read only: **False**

Get a summary report for hash.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |
**retry** | optional | If set to False there will only be one try at obtaining the analysis report | boolean |
**fields** | optional | List of A1000 report 'fields' to query | string |
**include_network_threat_intelligence** | optional | Include network threat intelligence in the summary report | boolean |
**skip_reanalysis** | optional | Skip sample reanalysis when fetching the summary report | boolean |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.fields | string | |\
action_result.parameter.hash | string | |\
action_result.parameter.include_network_threat_intelligence | boolean | |\
action_result.parameter.retry | boolean | |\
action_result.parameter.skip_reanalysis | boolean | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get detailed report'

Get detailed analysis report

Type: **generic**\
Read only: **False**

Get detailed analysis report for sample.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |
**retry** | optional | If set to False there will only be one try at obtaining the analysis report | boolean |
**fields** | optional | List of A1000 report 'fields' to query | string |
**skip_reanalysis** | optional | Skip sample reanalysis when fetching the summary report | boolean |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.fields | string | |\
action_result.parameter.hash | string | |\
action_result.parameter.retry | boolean | |\
action_result.parameter.skip_reanalysis | boolean | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get classification'

Get classification for a sample

Type: **generic**\
Read only: **False**

Get classification for one sample. The default value of local_only is False, which, if not changed, will send a request to TitaniumCloud to get the sample. The av_scanners parameter decides if the AV scanner results will be included in the classification report.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | Hash | string |
**local_only** | optional | Return only local samples without querying TitaniumCloud | boolean |
**av_scanners** | optional | Return AV scanner results | boolean |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | |\
action_result.parameter.av_scanners | boolean | |\
action_result.parameter.hash | string | |\
action_result.parameter.local_only | boolean | |\
action_result.data | string | |\
action_result.summary | string | |\
action_result.message | string | |\
summary.total_objects | numeric | |\
summary.total_objects_successful | numeric | |

## action: 'get user tags'

List existing tags for the requested sample

Type: **generic**\
Read only: **True**

List existing tags for the requested sample, if there are any.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------|----------|-------------|--------|------------------------------|
| **hash** | required | sample hash | string | `hash` `sha1` `sha256` `md5` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|----------------------------------|---------|------------------------------|----------------|
| action_result.parameter.hash | string | `hash` `sha1` `sha256` `md5` | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'create user tags'

Add one or more user tags

Type: **generic**\
Read only: **False**

Add one or more User Tags to the sample, regardless of whether the sample already has any tags.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------|----------|------------------------------|--------|------------------------------|
| **hash** | required | Hash | string | `hash` `sha1` `sha256` `md5` |
| **tags** | required | List of comma separated tags | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|----------------------------------|---------|------------------------------|----------------|
| action_result.parameter.hash | string | `hash` `sha1` `sha256` `md5` | |
| action_result.parameter.tags | string | | tag1,tag2,tag3 |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'delete user tags'

Remove one or more user tags

Type: **generic**\
Read only: **False**

Remove one or more User Tags from the requested sample.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------|----------|-----------------------------|--------|------------------------------|
| **hash** | required | Hash | string | `hash` `sha1` `sha256` `md5` |
| **tags** | required | List of comm separated tags | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|----------------------------------|---------|------------------------------|----------------|
| action_result.parameter.hash | string | `hash` `sha1` `sha256` `md5` | |
| action_result.parameter.tags | string | | tag1,tag2,tag3 |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'set sample classification'

Set the classification of a sample

Type: **generic**\
Read only: **False**

This API allows the user to set the classification of a sample, either in TitaniumCloud or locally on the A1000.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|---------------------|----------|-------------------------------------------------------|--------|------------------------------|
| **hash** | required | Hash | string | `hash` `sha1` `sha256` `md5` |
| **system** | required | Where to set the classification | string | |
| **classification** | required | Classification to set | string | |
| **risk_score** | optional | Risk score to set for classification | string | |
| **threat_platform** | optional | Threat platfrom to set, must be on the supported list | string | |
| **threat_type** | optional | Threat type to set, must be on the supported list | string | |
| **threat_name** | optional | Threat name to set, must be on the supported list | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-----------------------------------------|---------|------------------------------|-------------------------------------|
| action_result.parameter.hash | string | `hash` `sha1` `sha256` `md5` | |
| action_result.parameter.system | string | | "cloud" "local" |
| action_result.parameter.classification | string | | "goodware" "malicious" "suspicious" |
| action_result.parameter.risk_score | string | | 0 \<= risk_score \<= 10 |
| action_result.parameter.threat_platform | string | | |
| action_result.parameter.threat_type | string | | |
| action_result.parameter.threat_name | string | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'delete sample classification'

Delete the (user set) classification of a sample

Type: **generic**\
Read only: **False**

This API allows the user to delete the classification of a sample, either in TitaniumCloud or locally on the A1000.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------|----------|---------------------------------|--------|------------------------------|
| **hash** | required | Hash | string | `hash` `sha1` `sha256` `md5` |
| **system** | required | Where to set the classification | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|----------------------------------|---------|------------------------------|-----------------|
| action_result.parameter.hash | string | `hash` `sha1` `sha256` `md5` | |
| action_result.parameter.system | string | | "cloud" "local" |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara get rulesets'

Get a list of YARA rulesets that are on the A1000

Type: **generic**\
Read only: **True**

For every ruleset in the list, the output includes additional info such as: rule name, number of matches, last matched date, and more.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|---------------|----------|-------------|---------|----------|
| **type** | optional | Owner type | string | |
| **status** | optional | Status | string | |
| **source** | optional | Source | string | |
| **page** | optional | Page | numeric | |
| **page_size** | optional | Page size | numeric | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-----------------------------------|---------|----------|----------------------------------------------------------------|
| action_result.parameter.type | string | | "my" "user" "system" "all" |
| action_result.parameter.status | string | | "all" "error" "active" "disabled" "pending" "invalid" "capped" |
| action_result.parameter.source | string | | "all" "local" "cloud" |
| action_result.parameter.page | numeric | | |
| action_result.parameter.page_size | numeric | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara get ruleset text'

Get the full contents of the requested ruleset

Type: **generic**\
Read only: **True**

Get the full contents of the requested ruleset in raw text. All rulesets can be retrieved.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------------|----------|--------------|--------|----------------|
| **ruleset_name** | reuired | Ruleset name | string | `ruleset name` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------------------------------|---------|----------------|----------------|
| action_result.parameter.ruleset_name | string | `ruleset_name` | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara get matches'

Retrieve the list of YARA matches

Type: **investigate**\
Read only: **True**

Retrieve the list of YARA matches (local & cloud) for requested ruleset. Names are case-sensitive.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------------|----------|--------------|---------|----------------|
| **ruleset_name** | required | Ruleset name | string | `ruleset name` |
| **page** | optional | Page | numeric | |
| **page_size** | optional | Page size | numeric | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------------------------------|---------|----------------|----------------|
| action_result.parameter.ruleset_name | string | `ruleset name` | |
| action_result.parameter.page | numeric | | |
| action_result.parameter.page_size | numeric | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara create or update ruleset'

Creates a new YARA ruleset if it doesn't exist

Type: **generic**\
Read only: **False**

Creates a new YARA ruleset if it doesn't exist. If it exists a new revision is created. TiCloud rules cannot be updated using this API.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------------|----------|--------------------------------------|---------|----------------|
| **ruleset_name** | required | Ruleset name | string | `ruleset name` |
| **ruleset_text** | required | Text of the yara ruleset | string | |
| **publish** | optional | Publish to C1000 in the same cluster | boolean | |
| **ticloud** | optional | Sync with TiCloud | boolean | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------------------------------|---------|----------------|----------------|
| action_result.parameter.ruleset_name | string | `ruleset name` | |
| action_result.parameter.ruleset_text | string | | |
| action_result.parameter.publish | boolean | | |
| action_result.parameter.ticloud | boolean | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara delete ruleset'

Delete a specific YARA ruleset and its matches

Type: **generic**\
Read only: **False**

Delete a specific YARA ruleset and its matches from the appliance.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------------|----------|--------------------------------------|---------|----------------|
| **ruleset_name** | required | Ruleset name | string | `ruleset name` |
| **publish** | optional | Publish to c1000 in the same cluster | boolean | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------------------------------|---------|----------------|----------------|
| action_result.parameter.ruleset_name | string | `ruleset name` | |
| action_result.parameter.publish | boolean | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara enable or disable ruleset'

Enable or disable a ruleset on the appliance

Type: **generic**\
Read only: **False**

Administrators can manage any ruleset while regular A1000 users can only manage their own.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------------|----------|--------------------------------------|---------|----------------|
| **ruleset_name** | required | Ruleset name | string | `ruleset name` |
| **enabled** | required | Enable or disable the ruleset | boolean | |
| **publish** | optional | Publish to c1000 in the same cluster | boolean | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------------------------------|---------|----------------|----------------|
| action_result.parameter.ruleset_name | string | `ruleset name` | |
| action_result.parameter.enabled | boolean | | |
| action_result.parameter.publish | boolean | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara get synchronization time'

Get the current synchronization time

Type: **generic**\
Read only: **True**

Provides information about the current synchronization status for TiCloud enabled rulesets.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------|----------|-------------|------|----------|

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-------------------------------------|---------|----------|----------------|
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara set ruleset synchronization time'

Modify the TiCloud sync time for TiCloud enabled rulesets

Type: **generic**\
Read only: **False**

Modify the TiCloud sync time for TiCloud enabled rulesets. Time parameter must be a UTC timestamp <YYYY-MM-DD hh:mm:ss>."

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------|----------|----------------------|--------|----------|
| **time** | required | Synchronization time | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|----------------------------------|---------|----------|-----------------------|
| action_result.parameter.time | string | | "2024-05-29 10:00:00" |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara start or stop local retro scan'

Allow users to start or stop the local Retro scan on the appliance

Type: **generic**\
Read only: **False**

Allow users to start or stop the Local Retro scan on the appliance.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|---------------|----------|---------------|--------|----------|
| **operation** | required | START or STOP | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-----------------------------------|---------|----------|----------------|
| action_result.parameter.operation | string | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara manage cloud retro scan'

Allow users to start, stop or clear a Cloud Retro scan

Type: **generic**\
Read only: **False**

Start/Stop or Clear a Cloud Retro scan for a specified ruleset on the A1000.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------------|----------|----------------------|--------|----------------|
| **ruleset_name** | required | Ruleset name | string | `ruleset name` |
| **operation** | required | START, STOP or CLEAR | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------------------------------|---------|----------------|----------------|
| action_result.parameter.ruleset_name | string | `ruleset name` | |
| action_result.parameter.operation | string | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara status retro scan local'

Allow users to check the status of a Local Retro scan

Type: **generic**\
Read only: **True**

The response indicates the current state of Local Retro scan, time and date when the latest Local Retro scan was started and/or stopped, and a list of previous Local Retro scans with the same details.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------|----------|-------------|------|----------|

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|-------------------------------------|---------|----------|----------------|
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'yara status retro scan cloud'

Allow users to check the status of Cloud Retro scan for specified ruleset

Type: **generic**\
Read only: **True**

The response indicates the current state of Cloud Retro, time and date when the latest Cloud Retro scan was started and/or stopped, and a list of previous Cloud Retro scans with the same details.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------------|----------|--------------|--------|----------------|
| **ruleset_name** | required | Ruleset name | string | `ruleset name` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------------------------------|---------|----------------|----------------|
| action_result.parameter.ruleset_name | string | `ruleset name` | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'list containers for hash'

Get a list of containers from which the requested samples has been extracted

Type: **investigate**
Read only: **True**

Get a list of all top-level containers from which the requested samples have been extracted during analysis. If a requested hash doesn't have a container, it will not be included in the response.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|------------|----------|--------------------------------|--------|------------------------------|
| **hashes** | required | Comma separated list of hashes | string | `hash` `sha1` `sha256` `md5` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|----------------------------------|---------|------------------------------|----------------|
| action_result.parameter.hashes | string | `hash` `sha1` `sha256` `md5` | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'delete sample'

Delete the sample with the requested hash value

Type: **generic**\
Read only: **False**

All related data, including extracted samples and metadata, will be deleted from the current A1000 instance.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------|----------|-------------------------------|--------|------------------------------|
| **hash** | required | Hash of a sample to e deleted | string | `hash` `sha1` `sha256` `md5` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|--------------------------------------------|---------|------------------------------|----------------|
| action_result.parameter.hash | string | `hash` `sha1` `sha256` `md5` | |
| action_result.data.*.results.code | numeric | | |
| action_result.data.*.results.message | string | | |
| action_result.data.*.results.detail.md5 | string | `hash` `md5` | |
| action_result.data.*.results.detail.sha1 | string | `hash` `sha1` | |
| action_result.data.*.results.detail.sha256 | string | `hash` `sha256` | |
| action_result.data.*.results.detail.sha512 | string | `hash` `sha512` | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'download extracted files'

Download files extracted from local sample

Type: **generic**\
Read only: **True**

The files are obtained through the unpacking process during sample analysis with the TitaniumCore static analysis engine.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-----------|----------|-------------------------------|--------|------------------------------|
| **hash** | required | Hash of a sample to e deleted | string | `hash` `sha1` `sha256` `md5` |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|----------------------------------|---------|------------------------------|----------------|
| action_result.parameter.hash | string | `hash` `sha1` `sha256` `md5` | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |

## action: 'reanalyze local samples'

Submit a set fo samples that already exist on the A1000

Type: **investigate**\
Read only: **False**

Get classification for one sample. The default value of local_only is False, which, if not changed, will send a request to TitaniumCloud to get the sample. The av_scanners parameter decides if the AV scanner results will be included in the classification report.

#### Action Parameters

| PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS |
|-------------------------------|----------|---------------------------------------------------|---------|------------------------------|
| **hashes** | required | Comma separated list of hashes | string | `hash` `sha1` `sha256` `md5` |
| **titanium_cloud** | optional | Titanium Cloud analysis | boolean | |
| **titanium_core** | optional | Titanium Core analysis | boolean | |
| **rl_cloud_sandbox** | optional | RL cloud sandbox analysis | boolean | |
| **cuckoo_sandbox** | optional | Cuckoo sandbox analysis | boolean | |
| **fireeye** | optional | FireEye analysis | boolean | |
| **joe_sandbox** | optional | Joe sandbox analysis | boolean | |
| **cape** | optional | Cape analysis | boolean | |
| **rl_cloud_sandbox_platform** | optional | Platform on which the samples should be detonated | string | |

#### Action Output

| DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES |
|---------------------------------------------------|---------|------------------------------|----------------|
| action_result.parameter.hashes | string | `hash` `sha1` `sha256` `md5` | |
| action_result.parameter.titanium_cloud | boolean | | |
| action_result.parameter.titanium_core | boolean | | |
| action_result.parameter.rl_cloud_sandbox | boolean | | |
| action_result.parameter.cuckoo_sandbox | boolean | | |
| action_result.parameter.fireeye | boolean | | |
| action_result.parameter.joe_sandbox | boolean | | |
| action_result.parameter.cape | boolean | | |
| action_result.parameter.rl_cloud_sandbox_platform | string | | |
| action_result.status | string | | |
| action_result.data | string | | |
| action_result.summary | string | | |
| action_result.message | string | | |
| summary.total_objects | numeric | | |
| summary.total_objects_successful | numeric | | |
