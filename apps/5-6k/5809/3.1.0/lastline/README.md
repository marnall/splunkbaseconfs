[comment]: # "Auto-generated SOAR connector documentation"
# Lastline

Publisher: Splunk Community  
Connector Version: 3.1.0  
Product Vendor: Lastline  
Product Name: Lastline  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.1.0  

This app supports executing investigative actions to analyze executables and URLs on the online Lastline sandbox

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2015-2023 Splunk Inc."
[comment]: # ""
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Lastline asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** |  required  | string | Base URL for lastline service
**verify_server_cert** |  optional  | boolean | Verify Server Certificate
**timeout** |  required  | numeric | Timeout (seconds)
**license_key** |  required  | password | License Key
**api_token** |  required  | password | API Token
**account_username** |  optional  | string | Push Account
**report_url** |  optional  | string | Report URL for lastline service

### Supported Actions  
[detonate file](#action-detonate-file) - Run the file in the Lastline sandbox and retrieve the analysis results  
[get report](#action-get-report) - Query for results of an already completed task in Lastline  
[detonate url](#action-detonate-url) - Load a URL in the Lastline sandbox and retrieve the analysis results  
[test connectivity](#action-test-connectivity) - This action connects to the server to verify the connection  
[get artifact](#action-get-artifact) - Download Lastline generated artifact and store to SOAR/Phantom Vault  

## action: 'detonate file'
Run the file in the Lastline sandbox and retrieve the analysis results

Type: **investigate**  
Read only: **True**

This action requires the input file to be present in the vault and therefore takes the vault id as the input parameter. <br/> This action supports PE, PDF, doc, etc. for analysis.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** |  required  | Vault ID of file to detonate | string |  `vault id`  `pe file` 
**file_name** |  optional  | Filename to use | string |  `file name` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.file_name | string |  `file name`  |   abc.pdf  pip.exe 
action_result.parameter.vault_id | string |  `vault id`  `pe file`  |   TESTc0561edabf40928e49f0589b9bf41ef70fea 
action_result.data.\*.report.analysis.network.requests.\*.content_length | numeric |  |   904198 
action_result.data.\*.report.analysis.network.requests.\*.content_md5 | string |  |   TESTa182c22d26c78872d009298ba7e6 
action_result.data.\*.report.analysis.network.requests.\*.content_sha1 | string |  |   TEST7f7e2989ef79522e36e103b2270adc81abd80 
action_result.data.\*.report.analysis.network.requests.\*.content_type | string |  |   application/pdf 
action_result.data.\*.report.analysis.network.requests.\*.end | numeric |  |   100 
action_result.data.\*.report.analysis.network.requests.\*.error | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.filename | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.ip | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.parent_url | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.relation_type | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.relation_type_str | numeric |  |   6 
action_result.data.\*.report.analysis.network.requests.\*.start | numeric |  |   0 
action_result.data.\*.report.analysis.network.requests.\*.status | numeric |  |   200 
action_result.data.\*.report.analysis.network.requests.\*.task_uuid | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.url | string |  |   file://TESTf7e2989ef79522e36e103b2270adc81abd80 
action_result.data.\*.report.analysis.result.analysis_ended | string |  |   2021-07-23 14:33:42+0000 
action_result.data.\*.report.analysis.result.detector | string |  |   3.1.2490 
action_result.data.\*.report.analysis.subject.md5 | string |  |   TESTa182c22d26c78872d009298ba7e6 
action_result.data.\*.report.analysis.subject.subject | string |  |  
action_result.data.\*.report.analysis.subject.type | string |  |   file 
action_result.data.\*.report.analysis.text_from_documents.\*.doc_md5 | string |  |   TESTa182c22d26c78872d009298ba7e6 
action_result.data.\*.report.analysis.text_from_documents.\*.doc_sha1 | string |  |   92TEST7e2989ef79522e36e103b2270adc81abd80 
action_result.data.\*.report.analysis.text_from_documents.\*.text | string |  |   Anomali ThreatStream API

Reference Guide

Version: v2.5.5

December 21, 2020

Copyright Notice

 2020 Anomali, Inc. All rights reserved.
ThreatStream is a registered servicemark. Optic, Anomali Harmony, and Anomali Reports are registered trademarks.
All other brands, products, and company names used herein may be trademarks of their respective owners.

Support

Support Portal

Email

Phone

Twitter

https://support.threatstream.com

support@threatstream.com

+1 844-4-THREATS

@threatstream

Documentation Updates

Date

12/21/2020

11/23/2020

10/14/2020

9/1/2020

7/20/2020

7/2/2020

6/23/2020

6/11/2020

Product Version

Description

v2.5.5

v2.5.5

v2.5.5

v2.5.5

v2.5.5

v2.5.5

v2.5.5

v2.5.5

Updated "Passive DNS" on page39.

Updated "Introduction" on page5 and
"Threat Model " on page65. Added
"SSO History" on page62.

Updated "Threat Model " on page65.

Updated "User Audit" on page120.

Updated "Import (without approval)" on
page17.

Updated "Authenticating to
ThreatStream" on page5.

Updated "Appstorehistory" on page125
and "Feed" on page132.

Added "Appstorehistory" on page125.

Anomali ThreatStream API (v2.5.5)

Page 2 of 158

CONTENTS

Introduction

Accessing the API
Prerequisites
Using API to Access ThreatStream OnPrem

Import

Import (with approval)
Import (without approval)

Intelligence

Managing Threat Model Entity and Observable Tags

Confidence

Managing Observable Tags in Bulk

Intelligence Enrichments

Rules

Examples

Sandbox

Snapshot

SSO History

Threat Model

Threat Model Search
Actors
Campaigns
Incidents
Signatures
Tipreport

5
5
8
8

10
10
17

24

33

35

37

39

43
49

50

54

62

65
65
70
76
82
87
91

Anomali ThreatStream API (v2.5.5)

Page 3 of 158

Reference Guide

TTPs (Tactics, Techniques, and Procedures)
Vulnerabilities
Managing Threat Model Associations

Investigation

User Administration

Request

Attributes

User Audit

Attributes

Appstorehistory

Whitelist

Feed

Attributes
Examples

Appendix 1: Intelligence Fields in ThreatStream

Appendix 2: Indicator Types in ThreatStream

Appendix 3: Fraud Indicator Types for ThreatStream OnPrem

Appendix 4: Threat Types in ThreatStream

Send Documentation Feedback

97
102
106

109

116
116
116

120
120

125

128

132
132
132

134

138

153

155

158

Anomali ThreatStream API (v2.5.5)

Page 4 of 158

Introduction

Anomali ThreatStream (previously known as ThreatStream Optic) is accessible through RESTAPIs,
which are available to all Premium customers. The APIs offers bi-directional interaction with the
ThreatStream platform.
The APIs allow you to pull threat intelligence from the ThreatStream platform for use with other third-
party tools, import observables into ThreatStream from any source, manage threat model entities and
investigations, and so on.

Accessing the API

To access the API, use the following base URL:

https://api.threatstream.com/api/<api_version>/<resource>/
where
api_version is either v1 or v2. Refer to each API call to determine the version to use.
resource is APIendpoint; for example, import, intelligence, tipreport

Authenticating to ThreatStream
Making requests through the APIrequires authenticating to ThreatStream using your usernamethe
email address associated with your ThreatStream accountand your dedicated APIKey. You can
reference your username and APIKey on the My Profile tab within ThreatStream settings.

Anomali ThreatStream API (v2.5.5)

Page 5 of 158

Reference Guide
Introduction

Specifying your username and API Key in the header of the request is the most secure method of
authentication. Anomali recommends using this authentication method, as shown in the following
example:

curl 'https://api.threatstream.com/api/v2/intelligence/?itype=bot_ip' -H
'Authorization: apikey <username>:<api_key>'

Note: Specifying usernames and API Keys in the URL of the request will be deprecated as an
available authentication method for ThreatStream in a future release.

Using Operators
The first API operator called after the resource must start with a question mark and subsequent
operators must begin with an ampersand.
Example:

curl 'https://api.threatstream.com/api/v1/intelligence/?itype=bot_ip&status=active'
-H 'Authorization: apikey <username>:<api_key>'

APIMetadata
The following is an example of typical ThreatStream API metadata:

Anomali ThreatStream API (v2.5.5)

Page 6 of 158

Reference Guide
Introduction

l total_countthe total number of results that can be retrieved by the API call.

l approximate_countset to true in cases where API calls yield exceptionally large datasets to

indicate that the total count may not include all results.

Note: The approximate_count metadata attribute is only included in API query responses
under certain conditions. Typically, these are scenarios where results are exceptionally large
and approximation improves application performance.

l tooktime in milliseconds ThreatStream took to retrieve the data.

l nextcall that can be used to iteratively retrieve the next set of data in the total results.

l limitnumber of results returned when API call is made. See "Limiting Results" below.

l o
... 
action_result.data.\*.report.analysis.urls_from_documents.\*.child_url_type | string |  |   url-in-pdf-text 
action_result.data.\*.report.analysis.urls_from_documents.\*.source_url | string |  |   file://testf7e2989ef79522e36e103b2270adc81atest 
action_result.data.\*.report.analysis.urls_from_documents.\*.task_uuid | string |  |  
action_result.data.\*.report.analysis.urls_from_documents.\*.url | string |  |   http://ui.test.com 
action_result.data.\*.report.analysis_engine_version | numeric |  |   50399674 
action_result.data.\*.report.analysis_metadata.\*.analysis_reason | string |  |  
action_result.data.\*.report.analysis_metadata.\*.analysis_subject_id | numeric |  |  
action_result.data.\*.report.analysis_metadata.\*.delete_date | string |  |  
action_result.data.\*.report.analysis_metadata.\*.description | string |  |  
action_result.data.\*.report.analysis_metadata.\*.ext_info.create_timestamp | string |  |  
action_result.data.\*.report.analysis_metadata.\*.ext_info.file_info | string |  |  
action_result.data.\*.report.analysis_metadata.\*.ext_info.llfile | string |  |  
action_result.data.\*.report.analysis_metadata.\*.ext_info.md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis_metadata.\*.ext_info.mime | string |  |  
action_result.data.\*.report.analysis_metadata.\*.ext_info.sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis_metadata.\*.ext_info.sha256 | string |  `hash`  `sha256`  |  
action_result.data.\*.report.analysis_metadata.\*.ext_info.size | numeric |  |  
action_result.data.\*.report.analysis_metadata.\*.file.abs_path | string |  |  
action_result.data.\*.report.analysis_metadata.\*.file.ext_info.create_timestamp | string |  |  
action_result.data.\*.report.analysis_metadata.\*.file.ext_info.file_info | string |  |  
action_result.data.\*.report.analysis_metadata.\*.file.ext_info.llfile | string |  |  
action_result.data.\*.report.analysis_metadata.\*.file.ext_info.md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis_metadata.\*.file.ext_info.mime | string |  |  
action_result.data.\*.report.analysis_metadata.\*.file.ext_info.sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis_metadata.\*.file.ext_info.sha256 | string |  `hash`  `sha256`  |  
action_result.data.\*.report.analysis_metadata.\*.file.ext_info.size | numeric |  |  
action_result.data.\*.report.analysis_metadata.\*.file.filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_metadata.\*.metadata_type | string |  |  
action_result.data.\*.report.analysis_metadata.\*.name | string |  |  
action_result.data.\*.report.analysis_metadata.\*.retention_date | string |  |   2021-10-21 14:33:44 
action_result.data.\*.report.analysis_metadata.\*.timestamp | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.dns_queries.\*.dns_server | string |  |  
action_result.data.\*.report.analysis_subjects.\*.dns_queries.\*.hostname | string |  `host name`  |  
action_result.data.\*.report.analysis_subjects.\*.dns_queries.\*.response_flags | string |  |  
action_result.data.\*.report.analysis_subjects.\*.dns_queries.\*.results | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_queries.\*.filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.file_queries.\*.status | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.abs_path | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.accesses.\*.disposition | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.accesses.\*.options | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.ext_info.create_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.ext_info.file_info | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.ext_info.llfile | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.ext_info.md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.ext_info.mime | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.ext_info.sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.ext_info.sha256 | string |  `hash`  `sha256`  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.ext_info.size | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.file_attributes | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.iostatus | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.static_pe_information.author | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.static_pe_information.compile_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.static_pe_information.description | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.static_pe_information.imphash | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.static_pe_information.original_filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.file_reads.\*.static_pe_information.version | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_renames.\*.existing_file | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_renames.\*.new_file | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_searches | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.abs_path | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.accesses.\*.disposition | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.accesses.\*.options | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.ext_info.create_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.ext_info.file_info | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.ext_info.llfile | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.ext_info.md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.ext_info.mime | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.ext_info.sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.ext_info.sha256 | string |  `hash`  `sha256`  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.ext_info.size | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.file_attributes | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.iostatus | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.static_pe_information.author | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.static_pe_information.compile_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.static_pe_information.description | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.static_pe_information.imphash | string |  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.static_pe_information.original_filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.file_writes.\*.static_pe_information.version | string |  |  
action_result.data.\*.report.analysis_subjects.\*.frequent_api_calls.\*.count | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.frequent_api_calls.\*.name | string |  |  
action_result.data.\*.report.analysis_subjects.\*.frequent_api_calls.\*.pid | numeric |  `pid`  |  
action_result.data.\*.report.analysis_subjects.\*.frequent_api_calls.\*.tid | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.loaded_libraries.\*.end_address | string |  |  
action_result.data.\*.report.analysis_subjects.\*.loaded_libraries.\*.filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.loaded_libraries.\*.start_address | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.number_of_stages | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.access | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.characteristics | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.executed_pages | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.id | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.md5_phys | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.name | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.offset | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.physical_size | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.rva | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.trusted | boolean |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_data.virtual_size | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_description | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_type | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.object_uuid | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.stages.\*.virtual_address | string |  |  
action_result.data.\*.report.analysis_subjects.\*.memory_region_stages.\*.virtual_address | string |  |  
action_result.data.\*.report.analysis_subjects.\*.mutex_creates.\*.mutex_name | string |  |  
action_result.data.\*.report.analysis_subjects.\*.mutex_opens.\*.mutex_name | string |  |  
action_result.data.\*.report.analysis_subjects.\*.network_connections.\*.dst_ip | string |  `ip`  |  
action_result.data.\*.report.analysis_subjects.\*.network_connections.\*.dst_port | numeric |  `port`  |  
action_result.data.\*.report.analysis_subjects.\*.network_connections.\*.protocol | string |  |  
action_result.data.\*.report.analysis_subjects.\*.network_connections.\*.src_ip | string |  `ip`  |  
action_result.data.\*.report.analysis_subjects.\*.network_connections.\*.src_port | numeric |  `port`  |  
action_result.data.\*.report.analysis_subjects.\*.network_connections.\*.type | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.analysis_reason | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.ext_info.create_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.ext_info.file_info | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.ext_info.llfile | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.ext_info.md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis_subjects.\*.overview.ext_info.mime | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.ext_info.sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis_subjects.\*.overview.ext_info.sha256 | string |  `hash`  `sha256`  |  
action_result.data.\*.report.analysis_subjects.\*.overview.ext_info.size | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.id | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.kernel_mode | boolean |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.parent_id | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.analysis_subject_id | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.arguments | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.bitsize | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.abs_path | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.accesses.\*.disposition | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.accesses.\*.options | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.ext_info.create_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.ext_info.file_info | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.ext_info.llfile | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.ext_info.md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.ext_info.mime | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.ext_info.sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.ext_info.sha256 | string |  `hash`  `sha256`  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.ext_info.size | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.file_attributes | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.iostatus | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.static_pe_information.author | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.static_pe_information.compile_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.static_pe_information.description | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.static_pe_information.imphash | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.static_pe_information.original_filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.executable.static_pe_information.version | string |  |  
action_result.data.\*.report.analysis_subjects.\*.overview.process.process_id | string |  `pid`  |  
action_result.data.\*.report.analysis_subjects.\*.patched_sleeps.\*.count | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.patched_sleeps.\*.new_value | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.patched_sleeps.\*.old_value | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.process.analysis_subject_id | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.process.arguments | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.bitsize | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.abs_path | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.accesses.\*.disposition | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.accesses.\*.options | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.ext_info.create_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.ext_info.file_info | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.ext_info.llfile | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.ext_info.md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.ext_info.mime | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.ext_info.sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.ext_info.sha256 | string |  `hash`  `sha256`  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.ext_info.size | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.file_attributes | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.iostatus | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.static_pe_information.author | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.static_pe_information.compile_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.static_pe_information.description | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.static_pe_information.imphash | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.static_pe_information.original_filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.process.executable.static_pe_information.version | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process.process_id | string |  `pid`  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.analysis_subject_id | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.arguments | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.bitsize | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.abs_path | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.accesses.\*.disposition | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.accesses.\*.options | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.ext_info.create_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.ext_info.file_info | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.ext_info.llfile | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.ext_info.md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.ext_info.mime | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.ext_info.sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.ext_info.sha256 | string |  `hash`  `sha256`  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.ext_info.size | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.file_attributes | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.iostatus | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.static_pe_information.author | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.static_pe_information.compile_timestamp | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.static_pe_information.description | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.static_pe_information.imphash | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.static_pe_information.original_filename | string |  `pe file`  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.executable.static_pe_information.version | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.operations | string |  |  
action_result.data.\*.report.analysis_subjects.\*.process_interactions.\*.process_id | string |  `pid`  |  
action_result.data.\*.report.analysis_subjects.\*.raised_exceptions.\*.addr | string |  |  
action_result.data.\*.report.analysis_subjects.\*.raised_exceptions.\*.code | string |  |  
action_result.data.\*.report.analysis_subjects.\*.raised_exceptions.\*.exception_count | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.raised_exceptions.\*.exception_name | string |  |  
action_result.data.\*.report.analysis_subjects.\*.registry_deletions.\*.key | string |  |  
action_result.data.\*.report.analysis_subjects.\*.registry_deletions.\*.value | string |  |  
action_result.data.\*.report.analysis_subjects.\*.registry_reads.\*.data | string |  |  
action_result.data.\*.report.analysis_subjects.\*.registry_reads.\*.key | string |  |  
action_result.data.\*.report.analysis_subjects.\*.registry_reads.\*.value | string |  |  
action_result.data.\*.report.analysis_subjects.\*.registry_writes.\*.data | string |  |  
action_result.data.\*.report.analysis_subjects.\*.registry_writes.\*.key | string |  |  
action_result.data.\*.report.analysis_subjects.\*.registry_writes.\*.value | string |  |  
action_result.data.\*.report.analysis_subjects.\*.service_starts.\*.service_name | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.analysis_reason | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.bitsize | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.loaded_libraries.\*.object_description | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.loaded_libraries.\*.object_type | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.loaded_libraries.\*.virtual_address | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.memory_blocks.\*.object_data.access | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.memory_blocks.\*.object_data.executed_pages | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.memory_blocks.\*.object_data.trusted | boolean |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.memory_blocks.\*.object_description | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.memory_blocks.\*.object_type | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.memory_blocks.\*.object_uuid | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.memory_blocks.\*.virtual_address | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.pe_images.\*.object_description | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.pe_images.\*.object_type | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.pe_images.\*.object_uuid | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.pe_images.\*.virtual_address | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.snapshot_id | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.snapshot_timestamp | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.thread_eips.\*.eip | string |  |  
action_result.data.\*.report.analysis_subjects.\*.snapshots.\*.thread_eips.\*.tid | numeric |  |  
action_result.data.\*.report.analysis_subjects.\*.strings_lists.\*.name | string |  |  
action_result.data.\*.report.analysis_subjects.\*.strings_lists.\*.strings | string |  |  
action_result.data.\*.report.format.build_version | numeric |  |  
action_result.data.\*.report.format.major_version | numeric |  |  
action_result.data.\*.report.format.minor_version | numeric |  |  
action_result.data.\*.report.format.name | string |  |  
action_result.data.\*.report.malicious_activity.\*.description | string |  |  
action_result.data.\*.report.malicious_activity.\*.type | string |  |  
action_result.data.\*.report.md5 | string |  |   9657a182c22d26c78872d009298ba7e6 
action_result.data.\*.report.mime_type | string |  |   application/pdf 
action_result.data.\*.report.overview.analysis_end | string |  |  
action_result.data.\*.report.overview.analysis_engine | string |  |  
action_result.data.\*.report.overview.analysis_engine_version | string |  |  
action_result.data.\*.report.overview.analysis_start | string |  |  
action_result.data.\*.report.overview.analysis_termination_reason | string |  |  
action_result.data.\*.report.prefilter_scanners.\*.detector_id | string |  |   llweb:prefilter-document-mime-type 
action_result.data.\*.report.prefilter_scanners.\*.score | numeric |  |   0 
action_result.data.\*.report.prefilter_scanners.\*.test | boolean |  |   True  False 
action_result.data.\*.report.prefilter_scanners.\*.version | numeric |  |   1 
action_result.data.\*.report.prefilter_score | numeric |  |   0 
action_result.data.\*.report.remarks.info | string |  |  
action_result.data.\*.report.score | numeric |  |   5 
action_result.data.\*.report.uuid | string |  |  
action_result.summary.id | string |  `lastline task id`  |   test35be81a8001007bd9a6056161111 
action_result.summary.result_url | string |  `url`  `domain`  |   https://test.lastline.com/malscape/#/task/fc1935be81a8001007bd9a6056164528 
action_result.summary.score | numeric |  |   50 
action_result.summary.target | string |  `file name`  |   Unknown 
action_result.summary.type | string |  |   file 
action_result.message | string |  |   Id: fc1935be81a8001007bd9a6056164528, Result url: https://user.lastline.com/portal#/analyst/task/fc1935be81a8001007bd9a6056164528, Type: file, Target: Unknown 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'get report'
Query for results of an already completed task in Lastline

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | Task ID to get the results of | string |  `lastline task id` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.id | string |  `lastline task id`  |   test35be81a8001007bd9a605616test 
action_result.data.\*.report.analysis.network.requests.\*.content_length | numeric |  |  
action_result.data.\*.report.analysis.network.requests.\*.content_md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis.network.requests.\*.content_sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis.network.requests.\*.content_type | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.end | numeric |  |  
action_result.data.\*.report.analysis.network.requests.\*.ip | string |  `ip`  |  
action_result.data.\*.report.analysis.network.requests.\*.parent_url | string |  `url`  `domain`  |  
action_result.data.\*.report.analysis.network.requests.\*.relation_type | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.start | numeric |  |  
action_result.data.\*.report.analysis.network.requests.\*.status | numeric |  |  
action_result.data.\*.report.analysis.network.requests.\*.url | string |  `url`  `domain`  |  
action_result.data.\*.report.analysis.result.analysis_ended | string |  |  
action_result.data.\*.report.analysis.result.detector | string |  |  
action_result.data.\*.report.analysis.statics.\*.code | string |  |  
action_result.data.\*.report.analysis.statics.\*.media_type | string |  |  
action_result.data.\*.report.analysis.strings.\*.str_len | numeric |  |  
action_result.data.\*.report.analysis.strings.\*.str_type | string |  |  
action_result.data.\*.report.analysis.strings.\*.value | string |  |  
action_result.data.\*.report.analysis.subject.type | string |  |  
action_result.data.\*.report.analysis.subject.url | string |  `url`  `domain`  |  
action_result.data.\*.report.analysis_engine_version | numeric |  |  
action_result.data.\*.report.analysis_error | string |  |  
action_result.data.\*.report.analysis_metadata.\*.metadata_type | string |  |  
action_result.data.\*.report.analysis_metadata.\*.name | string |  |  
action_result.data.\*.report.analysis_metadata.\*.retention_date | string |  |  
action_result.data.\*.report.extracted_files.\*.file_name | string |  |   test.py 
action_result.data.\*.report.extracted_files.\*.md5 | string |  |   test6ed13853dfa68bf88a72d649test 
action_result.data.\*.report.extracted_files.\*.mime_type | string |  |   text/x-python 
action_result.data.\*.report.extracted_files.\*.sha1 | string |  |   testdae1fecb61ece28e5825729d58c6821test 
action_result.data.\*.report.extracted_files.\*.task_score | numeric |  |   0 
action_result.data.\*.report.extracted_files.\*.task_uuid | string |  |   test174fe5f700102a7dda179f83test 
action_result.data.\*.report.format.build_version | numeric |  |  
action_result.data.\*.report.format.major_version | numeric |  |  
action_result.data.\*.report.format.minor_version | numeric |  |  
action_result.data.\*.report.format.name | string |  |  
action_result.data.\*.report.malicious_activity.\*.description | string |  |  
action_result.data.\*.report.malicious_activity.\*.type | string |  |  
action_result.data.\*.report.md5 | string |  |   testd5e4d630bc063b5305d91ce53tes 
action_result.data.\*.report.mime_type | string |  |   application/x-gzip 
action_result.data.\*.report.score | numeric |  |  
action_result.data.\*.report.uuid | string |  |  
action_result.summary.id | string |  `lastline task id`  |   test35be81a8001007bd9a6056161111 
action_result.summary.result_url | string |  `url`  `domain`  |   https://test.lastline.com/malscape/#/task/fc1935be81a8001007bd9a6056164528 
action_result.summary.score | numeric |  |   50 
action_result.summary.target | string |  `file name`  |   Unknown 
action_result.summary.type | string |  |   file 
action_result.message | string |  |   Id: fc1TESTbe81a8001007bd9a6056164528, Result url: https://user.lastline.com/portal#/analyst/task/TEST35be81a8001007bd9a6056164528, Type: file, Target: Unknown 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'detonate url'
Load a URL in the Lastline sandbox and retrieve the analysis results

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | URL to detonate | string |  `url` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.url | string |  `url`  |   https://www.test.com 
action_result.data.\*.report.analysis.network.requests.\*.activities.\*.desc | string |  |   Info: Page contains a form 
action_result.data.\*.report.analysis.network.requests.\*.activities.\*.is_test | boolean |  |   True  False 
action_result.data.\*.report.analysis.network.requests.\*.activities.\*.name | string |  |   llweb:info-page-contains-form 
action_result.data.\*.report.analysis.network.requests.\*.activities.\*.score | numeric |  |   0 
action_result.data.\*.report.analysis.network.requests.\*.activities.\*.version | numeric |  |   1 
action_result.data.\*.report.analysis.network.requests.\*.content_length | numeric |  |  
action_result.data.\*.report.analysis.network.requests.\*.content_md5 | string |  `hash`  `md5`  |  
action_result.data.\*.report.analysis.network.requests.\*.content_sha1 | string |  `hash`  `sha1`  |  
action_result.data.\*.report.analysis.network.requests.\*.content_type | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.end | numeric |  |  
action_result.data.\*.report.analysis.network.requests.\*.error | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.filename | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.ip | string |  `ip`  |  
action_result.data.\*.report.analysis.network.requests.\*.parent_url | string |  `url`  |  
action_result.data.\*.report.analysis.network.requests.\*.relation_type | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.relation_type_str | string |  |   USER 
action_result.data.\*.report.analysis.network.requests.\*.start | numeric |  |  
action_result.data.\*.report.analysis.network.requests.\*.status | numeric |  |  
action_result.data.\*.report.analysis.network.requests.\*.task_uuid | string |  |  
action_result.data.\*.report.analysis.network.requests.\*.url | string |  `url`  |  
action_result.data.\*.report.analysis.result.analysis_ended | string |  |  
action_result.data.\*.report.analysis.result.detector | string |  |  
action_result.data.\*.report.analysis.statics.\*.code | string |  |  
action_result.data.\*.report.analysis.statics.\*.media_type | string |  |  
action_result.data.\*.report.analysis.statics.\*.source_url | string |  |  
action_result.data.\*.report.analysis.strings.\*.str_len | numeric |  |  
action_result.data.\*.report.analysis.strings.\*.str_type | string |  |  
action_result.data.\*.report.analysis.strings.\*.value | string |  |  
action_result.data.\*.report.analysis.subject.type | string |  |  
action_result.data.\*.report.analysis.subject.url | string |  `url`  |  
action_result.data.\*.report.analysis_engine_version | numeric |  |  
action_result.data.\*.report.analysis_metadata.\*.metadata_type | string |  |  
action_result.data.\*.report.analysis_metadata.\*.name | string |  |  
action_result.data.\*.report.analysis_metadata.\*.retention_date | string |  |  
action_result.data.\*.report.analysis_metadata.\*.timestamp | numeric |  |   6 
action_result.data.\*.report.format.build_version | numeric |  |  
action_result.data.\*.report.format.major_version | numeric |  |  
action_result.data.\*.report.format.minor_version | numeric |  |  
action_result.data.\*.report.format.name | string |  |  
action_result.data.\*.report.malicious_activity.\*.description | string |  |  
action_result.data.\*.report.malicious_activity.\*.type | string |  |  
action_result.data.\*.report.prefilter_scanners.\*.activity | string |  |   A script used the fromCharCode function 
action_result.data.\*.report.prefilter_scanners.\*.detector_id | string |  |   llweb:prefilter-from-char-code-function 
action_result.data.\*.report.prefilter_scanners.\*.score | numeric |  |   5 
action_result.data.\*.report.prefilter_scanners.\*.test | boolean |  |   False  True 
action_result.data.\*.report.prefilter_scanners.\*.version | numeric |  |   2 
action_result.data.\*.report.prefilter_score | numeric |  |   5 
action_result.data.\*.report.score | numeric |  |  
action_result.data.\*.report.uuid | string |  |  
action_result.summary.id | string |  `lastline task id`  |   test35be81a8001007bd9a6056161111 
action_result.summary.result_url | string |  `url`  `domain`  |   https://test.lastline.com/malscape/#/task/fc1935be81a8001007bd9a6056164528 
action_result.summary.score | numeric |  |   50 
action_result.summary.target | string |  `file name`  |   Unknown 
action_result.summary.type | string |  |   file 
action_result.message | string |  |   Id: EXAMPLE35be81a8001007bd9a6056164528, Result url: https://user.lastline.com/portal#/analyst/task/fcTESTbe81a8001007bd9a6056164528, Type: file, Target: Unknown 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'test connectivity'
This action connects to the server to verify the connection

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'get artifact'
Download Lastline generated artifact and store to SOAR/Phantom Vault

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | Task ID to get the results of | string | 
**artifact_name** |  optional  | Name of the Artifact (when not specified all artifacts will be stored) | string | 
**password** |  optional  | Optional for artifact encryption | string | 
**container_id** |  optional  | Optional container id for artifact storage (Is detected automatically) | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |  
action_result.parameter.artifact_name | string |  |  
action_result.parameter.container_id | numeric |  |  
action_result.parameter.id | string |  |  
action_result.parameter.password | string |  |  
action_result.data.\*.container | numeric |  |  
action_result.data.\*.created_via | string |  |   automation 
action_result.data.\*.file_name | string |  |   putty.exe_68d12b2ce8df00200223a837f005aa30_0_screenshot_122.png 
action_result.data.\*.hash | string |  |   TESTa847064436052305646d97a5317277e40ebf 
action_result.data.\*.id | numeric |  |  
action_result.data.\*.message | string |  |   success 
action_result.data.\*.metadata_type | string |  |   screenshot 
action_result.data.\*.name | string |  |   putty.exe_TEST2b2ce8df00200223a837f005aa30_0_screenshot_122.png 
action_result.data.\*.retention_date | string |  |   2023-12-05 13:39:31.000000 
action_result.data.\*.size | numeric |  |  
action_result.data.\*.source_file | string |  |   putty.exe 
action_result.data.\*.succeeded | boolean |  |  
action_result.data.\*.task_id | string |  |   TEST00200223a837f000200223aEXAMPLE 
action_result.data.\*.timestamp | numeric |  |   122 
action_result.data.\*.vault_id | string |  |   TESTa847064436052305646d97a5317277e40ebf 
action_result.data.\*.vault_state | string |  |   stored  failed 
action_result.summary | string |  |  
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  