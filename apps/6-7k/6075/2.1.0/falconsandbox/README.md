[comment]: # "Auto-generated SOAR connector documentation"
# Falcon Sandbox

Publisher: Hybrid Analysis  
Connector Version: 2.1.0  
Product Vendor: Hybrid Analysis  
Product Name: Falcon Sandbox  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.1.1  

This app integrates with Falcon Sandbox Services to provide investigative actions


##### Usage

Should you not be using hybrid-analysis.com as the application server, but a private cloud or on
premise instance, please E-Mail support@crowdstrike.com for help on enabling the Phantom integration
on your instance.

##### Testing connectivity

After creating the Falcon Sandbox asset, we recommended to test the application server connectivity.
That way, you make sure that the provided base URL and API credentials are working correctly.

Port Information

The app uses HTTP/ HTTPS protocol for communicating with the Okta server. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http         | tcp                | 80   |
|         https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Falcon Sandbox asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** |  required  | string | Base URL to Falcon Sandbox Application Server
**verify_server_cert** |  optional  | boolean | Verify server certificate
**api_key** |  required  | password | API Key

### Supported Actions  
[search terms](#action-search-terms) - Search for samples in Falcon Sandbox database using search terms  
[hunt similar](#action-hunt-similar) - Search for similar samples by given Sha256 hash in the Falcon Sandbox database  
[hunt ip](#action-hunt-ip) - Search for a given IP in the Falcon Sandbox database  
[hunt hash](#action-hunt-hash) - Search for a file by one kind of hash(Sha1, Md5, Sha256) in the Falcon Sandbox database  
[hunt file](#action-hunt-file) - Search for a file by one kind of data(Sha1, Md5, Sha256 or File name) in the Falcon Sandbox database  
[hunt malware family](#action-hunt-malware-family) - Search for a given malware family in the Falcon Sandbox database  
[hunt domain](#action-hunt-domain) - Search for a given domain in the Falcon Sandbox database  
[hunt url](#action-hunt-url) - Search for a given URL in the Falcon Sandbox database  
[get file from url](#action-get-file-from-url) - Download file from a url  
[get pcap](#action-get-pcap) - Download the pcap file of sample from Falcon Sandbox and add it to vault  
[get file](#action-get-file) - Download sample result data from Falcon Sandbox and add it to vault  
[get report](#action-get-report) - Fetch results of an already completed analysis in the Falcon Sandbox  
[check status](#action-check-status) - Check status of sample (file or URL) submitted in the Falcon Sandbox  
[check url hash](#action-check-url-hash) - Determine a SHA256 that an online file or URL submission will have when being processed by the Falcon Sandbox  
[detonate url](#action-detonate-url) - Detonate a URL in the Falcon Sandbox  
[detonate online file](#action-detonate-online-file) - Detonate an online file in the Falcon Sandbox  
[detonate file](#action-detonate-file) - Detonate the file in the Falcon Sandbox  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity  

## action: 'search terms'
Search for samples in Falcon Sandbox database using search terms

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_name** |  optional  | File name e.g. invoice.exe | string |  `file name` 
**file_type** |  optional  | File type e.g. docx | string | 
**file_type_substring** |  optional  | File type description e.g. PE32 executable | string | 
**environment_id** |  optional  | Environment Id | numeric | 
**country** |  optional  | Country (3 digit ISO) e.g. swe | string | 
**verdict** |  optional  | Verdict | string |  `falcon sandbox verdict` 
**av_detection** |  optional  | AV Multiscan range e.g. 50-70 (min 0, max 100) | string | 
**av_family_substring** |  optional  | AV Family Substring e.g. nemucod | string |  `malware family` 
**hashtag** |  optional  | Hashtag e.g. ransomware | string |  `falcon sandbox tag` 
**port** |  optional  | Port e.g. 8080 | numeric |  `port` 
**host** |  optional  | Host e.g. 192.168.0.1 | string |  `ip` 
**domain** |  optional  | Domain e.g. checkip.dyndns.org | string |  `domain` 
**url** |  optional  | HTTP Request Substring e.g. google | string |  `url` 
**similar_samples** |  optional  | Similar Samples e.g. <sha256> | string |  `sha256` 
**similar_context** |  optional  | Sample Context e.g. <sha256> | string |  `sha256` 
**imphash** |  optional  |  | string |  `imphash` 
**ssdeep** |  optional  |  | string |  `ssdeep` 
**authentihash** |  optional  |  | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.authentihash | string |  |  
action_result.parameter.av_detection | string |  |  
action_result.parameter.av_family_substring | string |  `malware family`  |  
action_result.parameter.country | string |  |  
action_result.parameter.domain | string |  `domain`  |  
action_result.parameter.environment_id | numeric |  |  
action_result.parameter.file_name | string |  `file name`  |  
action_result.parameter.file_type | string |  |  
action_result.parameter.file_type_substring | string |  |  
action_result.parameter.hashtag | string |  `falcon sandbox tag`  |  
action_result.parameter.host | string |  `ip`  |  
action_result.parameter.imphash | string |  `imphash`  |  
action_result.parameter.port | numeric |  `port`  |  
action_result.parameter.similar_context | numeric |  `sha256`  |  
action_result.parameter.similar_samples | string |  `sha256`  |  
action_result.parameter.ssdeep | string |  `ssdeep`  |  
action_result.parameter.url | string |  `url`  |  
action_result.parameter.verdict | string |  `falcon sandbox verdict`  |  
action_result.data.\*.environment | string |  |  
action_result.data.\*.environment_description | string |  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.job_id | string |  `falcon sandbox job id`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.threat_score | string |  |  
action_result.data.\*.threat_score_verbose | string |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.summary.found | numeric |  |  
action_result.summary.found_by_verdict_name.malicious | numeric |  |  
action_result.summary.found_by_verdict_name.no_specific_threat | numeric |  |  
action_result.summary.found_by_verdict_name.no_verdict | numeric |  |  
action_result.summary.found_by_verdict_name.suspicious | numeric |  |  
action_result.summary.found_by_verdict_name.unknown | numeric |  |  
action_result.summary.found_by_verdict_name.whitelisted | numeric |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'hunt similar'
Search for similar samples by given Sha256 hash in the Falcon Sandbox database

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sha256** |  required  | Sample Sha256 | string |  `sha256` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.sha256 | string |  `sha256`  |  
action_result.data.\*.environment | string |  |  
action_result.data.\*.environment_description | string |  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.job_id | string |  `falcon sandbox job id`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.threat_score | string |  |  
action_result.data.\*.threat_score_verbose | string |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.summary.found | numeric |  |  
action_result.summary.found_by_verdict_name.malicious | numeric |  |  
action_result.summary.found_by_verdict_name.no_specific_threat | numeric |  |  
action_result.summary.found_by_verdict_name.no_verdict | numeric |  |  
action_result.summary.found_by_verdict_name.suspicious | numeric |  |  
action_result.summary.found_by_verdict_name.unknown | numeric |  |  
action_result.summary.found_by_verdict_name.whitelisted | numeric |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'hunt ip'
Search for a given IP in the Falcon Sandbox database

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**host** |  required  | IP | string |  `ip` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.host | string |  `ip`  |  
action_result.data.\*.environment | string |  |  
action_result.data.\*.environment_description | string |  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.job_id | string |  `falcon sandbox job id`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.threat_score | string |  |  
action_result.data.\*.threat_score_verbose | string |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.summary.found | numeric |  |  
action_result.summary.found_by_verdict_name.malicious | numeric |  |  
action_result.summary.found_by_verdict_name.no_specific_threat | numeric |  |  
action_result.summary.found_by_verdict_name.no_verdict | numeric |  |  
action_result.summary.found_by_verdict_name.suspicious | numeric |  |  
action_result.summary.found_by_verdict_name.unknown | numeric |  |  
action_result.summary.found_by_verdict_name.whitelisted | numeric |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'hunt hash'
Search for a file by one kind of hash(Sha1, Md5, Sha256) in the Falcon Sandbox database

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** |  required  | Sha1, Md5, Sha256 | string |  `sha256`  `sha1`  `md5` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.hash | string |  `sha256`  `sha1`  `md5`  |  
action_result.data.\*.environment | string |  |  
action_result.data.\*.environment_description | string |  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.job_id | string |  `falcon sandbox job id`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.threat_score | string |  |  
action_result.data.\*.threat_score_verbose | string |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.summary.found | numeric |  |  
action_result.summary.found_by_verdict_name.malicious | numeric |  |  
action_result.summary.found_by_verdict_name.no_specific_threat | numeric |  |  
action_result.summary.found_by_verdict_name.no_verdict | numeric |  |  
action_result.summary.found_by_verdict_name.suspicious | numeric |  |  
action_result.summary.found_by_verdict_name.unknown | numeric |  |  
action_result.summary.found_by_verdict_name.whitelisted | numeric |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'hunt file'
Search for a file by one kind of data(Sha1, Md5, Sha256 or File name) in the Falcon Sandbox database

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_name** |  required  | File name | string |  `file name` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.file_name | string |  `file name`  |  
action_result.data.\*.environment | string |  |  
action_result.data.\*.environment_description | string |  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.job_id | string |  `falcon sandbox job id`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.threat_score | string |  |  
action_result.data.\*.threat_score_verbose | string |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.summary.found | numeric |  |  
action_result.summary.found_by_verdict_name.malicious | numeric |  |  
action_result.summary.found_by_verdict_name.no_specific_threat | numeric |  |  
action_result.summary.found_by_verdict_name.no_verdict | numeric |  |  
action_result.summary.found_by_verdict_name.suspicious | numeric |  |  
action_result.summary.found_by_verdict_name.unknown | numeric |  |  
action_result.summary.found_by_verdict_name.whitelisted | numeric |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'hunt malware family'
Search for a given malware family in the Falcon Sandbox database

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malware_family** |  required  | AV Family Substring e.g. nemucod | string |  `malware family` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.malware_family | string |  `malware family`  |  
action_result.data.\*.environment | string |  |  
action_result.data.\*.environment_description | string |  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.job_id | string |  `falcon sandbox job id`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.threat_score | string |  |  
action_result.data.\*.threat_score_verbose | string |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.summary.found | numeric |  |  
action_result.summary.found_by_verdict_name.malicious | numeric |  |  
action_result.summary.found_by_verdict_name.no_specific_threat | numeric |  |  
action_result.summary.found_by_verdict_name.no_verdict | numeric |  |  
action_result.summary.found_by_verdict_name.suspicious | numeric |  |  
action_result.summary.found_by_verdict_name.unknown | numeric |  |  
action_result.summary.found_by_verdict_name.whitelisted | numeric |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'hunt domain'
Search for a given domain in the Falcon Sandbox database

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** |  required  | Domain e.g. checkip.dyndns.org | string |  `domain` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.domain | string |  `domain`  |  
action_result.data.\*.environment | string |  |  
action_result.data.\*.environment_description | string |  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.job_id | string |  `falcon sandbox job id`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.threat_score | string |  |  
action_result.data.\*.threat_score_verbose | string |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.summary.found | numeric |  |  
action_result.summary.found_by_verdict_name.malicious | numeric |  |  
action_result.summary.found_by_verdict_name.no_specific_threat | numeric |  |  
action_result.summary.found_by_verdict_name.no_verdict | numeric |  |  
action_result.summary.found_by_verdict_name.suspicious | numeric |  |  
action_result.summary.found_by_verdict_name.unknown | numeric |  |  
action_result.summary.found_by_verdict_name.whitelisted | numeric |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'hunt url'
Search for a given URL in the Falcon Sandbox database

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | HTTP Request Substring e.g. google | string |  `url` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.url | string |  `url`  |  
action_result.data.\*.environment | string |  |  
action_result.data.\*.environment_description | string |  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.job_id | string |  `falcon sandbox job id`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.threat_score | string |  |  
action_result.data.\*.threat_score_verbose | string |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.summary.found | numeric |  |  
action_result.summary.found_by_verdict_name.malicious | numeric |  |  
action_result.summary.found_by_verdict_name.no_specific_threat | numeric |  |  
action_result.summary.found_by_verdict_name.no_verdict | numeric |  |  
action_result.summary.found_by_verdict_name.suspicious | numeric |  |  
action_result.summary.found_by_verdict_name.unknown | numeric |  |  
action_result.summary.found_by_verdict_name.whitelisted | numeric |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'get file from url'
Download file from a url

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | Url containing file | string |  `url` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.url | string |  `url`  |  
action_result.data.\*.file_name | string |  `file name`  |  
action_result.data.\*.file_type | string |  |  
action_result.data.\*.vault_id | string |  `vault id`  |  
action_result.summary.file_name | string |  `file name`  |  
action_result.summary.file_type | string |  |  
action_result.summary.vault_id | string |  `vault id`  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'get pcap'
Download the pcap file of sample from Falcon Sandbox and add it to vault

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | Sample Id in one of format: 'jobId' or 'sha256:environmentId' | string |  `falcon sandbox job id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.id | string |  `falcon sandbox job id`  |  
action_result.data.\*.file_name | string |  `file name`  |  
action_result.data.\*.file_type | string |  |  
action_result.data.\*.vault_id | string |  `vault id`  |  
action_result.summary.file_name | string |  `file name`  |  
action_result.summary.file_type | string |  |  
action_result.summary.vault_id | string |  `vault id`  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'get file'
Download sample result data from Falcon Sandbox and add it to vault

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | Sample Id in one of format: 'jobId' or 'sha256:environmentId' | string |  `falcon sandbox job id` 
**file_type** |  required  | File type | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.file_type | string |  |  
action_result.parameter.id | string |  `falcon sandbox job id`  |  
action_result.data.\*.file_name | string |  `file name`  |  
action_result.data.\*.file_type | string |  |  
action_result.data.\*.vault_id | string |  `vault id`  |  
action_result.summary.file_name | string |  `file name`  |  
action_result.summary.file_type | string |  |  
action_result.summary.vault_id | string |  `vault id`  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'get report'
Fetch results of an already completed analysis in the Falcon Sandbox

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | Sample Id in one of format: 'jobId' or 'sha256:environmentId' | string |  `falcon sandbox job id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.id | string |  `falcon sandbox job id`  |  
action_result.data.\*.classification_tags.\* | string |  `malware family`  `falcon sandbox tag`  |  
action_result.data.\*.compromised_hosts.\* | string |  `ip`  |  
action_result.data.\*.domains.\* | string |  `domain`  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.hosts.\* | string |  `ip`  |  
action_result.data.\*.imphash | string |  `imphash`  |  
action_result.data.\*.interesting | boolean |  |  
action_result.data.\*.md5 | string |  `md5`  |  
action_result.data.\*.sha1 | string |  `sha1`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.size | string |  `file size`  |  
action_result.data.\*.ssdeep | string |  `ssdeep`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.target_url | string |  `url`  |  
action_result.data.\*.threat_score | numeric |  |  
action_result.data.\*.total_network_connections | numeric |  |  
action_result.data.\*.total_processes | numeric |  |  
action_result.data.\*.total_signatures | numeric |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.url_analysis | boolean |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.data.job_id | string |  `falcon sandbox job id`  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'check status'
Check status of sample (file or URL) submitted in the Falcon Sandbox

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | Sample Id in one of format: 'jobId' or 'sha256:environmentId' | string |  `falcon sandbox job id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.id | string |  `falcon sandbox job id`  |  
action_result.data.\*.error_msg | string |  |  
action_result.data.\*.status | string |  |  
action_result.summary.error_msg | string |  |  
action_result.summary.status | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'check url hash'
Determine a SHA256 that an online file or URL submission will have when being processed by the Falcon Sandbox

Type: **investigate**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | Url to check | string |  `url` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.url | string |  `url`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'detonate url'
Detonate a URL in the Falcon Sandbox

Type: **investigate**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | Url | string |  `url` 
**environment_id** |  required  | Environment Id | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.environment_id | numeric |  |  
action_result.parameter.url | string |  `url`  |  
action_result.data.\*.classification_tags.\* | string |  `malware family`  `falcon sandbox tag`  |  
action_result.data.\*.compromised_hosts.\* | string |  `ip`  |  
action_result.data.\*.domains.\* | string |  `domain`  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.hosts.\* | string |  `ip`  |  
action_result.data.\*.imphash | string |  `imphash`  |  
action_result.data.\*.interesting | boolean |  |  
action_result.data.\*.md5 | string |  `md5`  |  
action_result.data.\*.sha1 | string |  `sha1`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.size | string |  `file size`  |  
action_result.data.\*.ssdeep | string |  `ssdeep`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.target_url | string |  `url`  |  
action_result.data.\*.threat_score | numeric |  |  
action_result.data.\*.total_network_connections | numeric |  |  
action_result.data.\*.total_processes | numeric |  |  
action_result.data.\*.total_signatures | numeric |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.url_analysis | boolean |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.data.job_id | string |  `falcon sandbox job id`  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'detonate online file'
Detonate an online file in the Falcon Sandbox

Type: **investigate**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | Url | string |  `url` 
**environment_id** |  required  | Environment Id | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.environment_id | numeric |  |  
action_result.parameter.url | string |  `url`  |  
action_result.data.\*.classification_tags.\* | string |  `malware family`  `falcon sandbox tag`  |  
action_result.data.\*.compromised_hosts.\* | string |  `ip`  |  
action_result.data.\*.domains.\* | string |  `domain`  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.hosts.\* | string |  `ip`  |  
action_result.data.\*.imphash | string |  `imphash`  |  
action_result.data.\*.interesting | boolean |  |  
action_result.data.\*.md5 | string |  `md5`  |  
action_result.data.\*.sha1 | string |  `sha1`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.size | string |  `file size`  |  
action_result.data.\*.ssdeep | string |  `ssdeep`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.target_url | string |  `url`  |  
action_result.data.\*.threat_score | numeric |  |  
action_result.data.\*.total_network_connections | numeric |  |  
action_result.data.\*.total_processes | numeric |  |  
action_result.data.\*.total_signatures | numeric |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.url_analysis | boolean |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.data.job_id | string |  `falcon sandbox job id`  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'detonate file'
Detonate the file in the Falcon Sandbox

Type: **investigate**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** |  required  | Vault ID of file to submit | string |  `vault id` 
**environment_id** |  required  | Environment ID | numeric | 
**file_name** |  required  | File name to use | string |  `file name` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.environment_id | numeric |  |  
action_result.parameter.file_name | string |  `file name`  |  
action_result.parameter.vault_id | string |  `vault id`  |  
action_result.data.\*.classification_tags.\* | string |  `malware family`  `falcon sandbox tag`  |  
action_result.data.\*.compromised_hosts.\* | string |  `ip`  |  
action_result.data.\*.domains.\* | string |  `domain`  |  
action_result.data.\*.environment_id | numeric |  |  
action_result.data.\*.hosts.\* | string |  `ip`  |  
action_result.data.\*.imphash | string |  `imphash`  |  
action_result.data.\*.interesting | boolean |  |  
action_result.data.\*.md5 | string |  `md5`  |  
action_result.data.\*.sha1 | string |  `sha1`  |  
action_result.data.\*.sha256 | string |  `sha256`  |  
action_result.data.\*.size | string |  `file size`  |  
action_result.data.\*.ssdeep | string |  `ssdeep`  |  
action_result.data.\*.submit_name | string |  `file name`  |  
action_result.data.\*.target_url | string |  `url`  |  
action_result.data.\*.threat_score | numeric |  |  
action_result.data.\*.total_network_connections | numeric |  |  
action_result.data.\*.total_processes | numeric |  |  
action_result.data.\*.total_signatures | numeric |  |  
action_result.data.\*.type | string |  |  
action_result.data.\*.url_analysis | boolean |  |  
action_result.data.\*.verdict | string |  `falcon sandbox verdict`  |  
action_result.data.job_id | string |  `falcon sandbox job id`  |  
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |    

## action: 'test connectivity'
Validate the asset configuration for connectivity

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output