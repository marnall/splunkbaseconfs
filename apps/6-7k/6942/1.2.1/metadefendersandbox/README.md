[comment]: # "Auto-generated SOAR connector documentation"
# Metadefender Sandbox

Publisher: OPSWAT  
Connector Version: 1.2.1  
Product Vendor: OPSWAT  
Product Name: MetaDefender Sandbox  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 6.2.1  

MetaDefender Sandbox (previously known as OPSWAT Filescan Sandbox) is a unique adaptive threat analysis technology, enabling zero-day malware detection and comprehensive Indicator of Compromise (IOC) extraction

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) OPSWAT, 2024"
[comment]: # "Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "you may not use this file except in compliance with the License."
[comment]: # "You may obtain a copy of the License at"
[comment]: # "    http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # "Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "either express or implied. See the License for the specific language governing permissions"
[comment]: # "and limitations under the License."
[comment]: # ""
# MetaDefender Sandbox App

MetaDefender Sandbox (previously known as OPSWAT Filescan Sandbox) is a unique adaptive threat analysis technology, enabling zero-day malware detection and comprehensive Indicator of Compromise (IOC) extraction.

## What does this App do?

This app includes the MetaDefender Sandbox basic integration that does the following:

**Detonate file**  
Retrieve detonation analysis results for file

**Detonate URL**  
Retrieve detonation analysis results for URL

**Search report**  
Search for scan reports on MetaDefender Sandbox using parameters specified in the 'query' field.

**File reputation**  
Get the fast reputation for one given hash (returns the last 10 MetaDefender Sandbox reports)

**IP/Domain/URL reputation**  
Get the fast reputation for one given IOC. E.g.: IP, Domain or URL (returns the last 10 MetaDefender Sandbox reports)

This app requires a correctly set up MetaDefender Sandbox API key to use.

## Port Information

The app uses HTTPS protocol if it uses the MetaDefender Sandbox community server (default). You can deviate from this if you want to use your own, on-prem MetaDefender Sandbox server. Below are
the default ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a MetaDefender Sandbox asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server_url** |  required  | string | Server URL (e.g. https://www.filescan.io)
**api_key** |  required  | password | The MetaDefender Sandbox API Key to use for connection
**poll_interval** |  optional  | numeric | Number of seconds to poll for a detonation result (Default: 5, Range: [1:30])
**timeout** |  optional  | numeric | Request Timeout (Default: 60 seconds, Range: [30:300])

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[detonate url](#action-detonate-url) - Retrieve detonation analysis results for URL  
[detonate file](#action-detonate-file) - Retrieve detonation analysis results for file  
[search terms](#action-search-terms) - Search for scan reports on MetaDefender Sandbox using parameters specified in the 'query' field  
[file reputation](#action-file-reputation) - Get the reputation for one given hash (returns with the last 10 MetaDefender Sandbox reports)  
[ip reputation](#action-ip-reputation) - Get the reputation for one given IP address (returns with the last 10 MetaDefender Sandbox reports)  
[domain reputation](#action-domain-reputation) - Get the reputation for one given Domain address (returns with the last 10 MetaDefender Sandbox reports)  
[url reputation](#action-url-reputation) - Get the reputation for one given URL address (returns with the last 10 MetaDefender Sandbox reports)  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'detonate url'
Retrieve detonation analysis results for URL

Type: **investigate**  
Read only: **True**

Detonate url will send an URL to MetaDefender Sandbox for analysis.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | URL to be analyzed | string |  `url`  `domain` 
**password** |  optional  | Custom password, in case uploaded archive is protected | string | 
**is_private** |  optional  | If file should not be available for download by other users | boolean | 
**description** |  optional  | Uploaded file/url description | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.description | string |  |   This is test desciption 
action_result.parameter.is_private | boolean |  |   True  False 
action_result.parameter.password | string |  |   EAMPLEdajjccds 
action_result.parameter.url | string |  `url`  |   https://www.test.com 
action_result.data.\*.allSignalGroups.\*.averageSignalStrength | numeric |  |   0.25 
action_result.data.\*.allSignalGroups.\*.description | string |  |   Found a base64 encoded http(s) URL prefix 
action_result.data.\*.allSignalGroups.\*.finalSignalStrength | numeric |  |   0.25 
action_result.data.\*.allSignalGroups.\*.identifier | string |  |   S001 
action_result.data.\*.allSignalGroups.\*.peakSignalStrength | numeric |  |   0.25 
action_result.data.\*.allSignalGroups.\*.signals.\*.isStrictlyBasedOnInputData | boolean |  |   True  False 
action_result.data.\*.allSignalGroups.\*.signals.\*.originIdentifier | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.allSignalGroups.\*.signals.\*.originPath | string |  |   file.strings.references 
action_result.data.\*.allSignalGroups.\*.signals.\*.originType | string |  |   EXTRACTED_FILE 
action_result.data.\*.allSignalGroups.\*.signals.\*.signalReadable | string |  |   Found artifact in string 
action_result.data.\*.allSignalGroups.\*.signals.\*.strength | numeric |  |   0.25 
action_result.data.\*.allSignalGroups.\*.verdict.confidence | numeric |  |   1 
action_result.data.\*.allSignalGroups.\*.verdict.threatLevel | numeric |  |   0.2 
action_result.data.\*.allSignalGroups.\*.verdict.verdict | string |  |   NO_THREAT 
action_result.data.\*.allTags.\*.isRootTag | boolean |  |   True  False 
action_result.data.\*.allTags.\*.source | string |  |   MEDIA_TYPE 
action_result.data.\*.allTags.\*.sourceIdentifier | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.allTags.\*.tag.descriptions.cluster.authors.\* | string |  |   John Doe 
action_result.data.\*.allTags.\*.tag.descriptions.cluster.type | string |  |   malpedia 
action_result.data.\*.allTags.\*.tag.descriptions.description | string |  |   This is a description 
action_result.data.\*.allTags.\*.tag.name | string |  |   html 
action_result.data.\*.allTags.\*.tag.synonyms.\* | string |  |   synonym 
action_result.data.\*.allTags.\*.tag.verdict.confidence | numeric |  |   1 
action_result.data.\*.allTags.\*.tag.verdict.threatLevel | numeric |  |   0.75 
action_result.data.\*.allTags.\*.tag.verdict.verdict | string |  |   LIKELY_MALICIOUS 
action_result.data.\*.file.hash | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.file.name | string |  |   https://www.test.com 
action_result.data.\*.file.type | string |  |   other 
action_result.data.\*.finalVerdict.confidence | numeric |  |   0 
action_result.data.\*.finalVerdict.threatLevel | numeric |  |   0 
action_result.data.\*.finalVerdict.verdict | string |  |   malicious 
action_result.data.\*.overallState | string |  |   success 
action_result.data.\*.postprocessIocs.\* | string |  |   url 
action_result.data.\*.subtaskReferences.\*.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.subtaskReferences.\*.additionalInfo | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.subtaskReferences.\*.name | string |  |   osint 
action_result.data.\*.subtaskReferences.\*.opcount | numeric |  |   4 
action_result.data.\*.subtaskReferences.\*.processTime | numeric |  |   1006 
action_result.data.\*.subtaskReferences.\*.resourceReference.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.subtaskReferences.\*.resourceReference.name | string |  |   osint 
action_result.data.\*.subtaskReferences.\*.resourceReference.type | string |  |   OSINT 
action_result.data.\*.subtaskReferences.\*.state | string |  |   SUCCESS 
action_result.data.\*.taskReference.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.additionalInfo.digests.SHA-256 | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.taskReference.additionalInfo.submitName | string |  |   bad_file.exe 
action_result.data.\*.taskReference.additionalInfo.submitTime | numeric |  |   1684846900889 
action_result.data.\*.taskReference.name | string |  |   transform-file 
action_result.data.\*.taskReference.resourceReference.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.isRootTag | boolean |  |   True  False 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.source | string |  |   MEDIA_TYPE 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.sourceIdentifier | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.descriptions.cluster.authors.\* | string |  |   John Doe 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.descriptions.cluster.type | string |  |   malpedia 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.descriptions.description | string |  |   This is a description 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.name | string |  |   html 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.synonyms.\* | string |  |   synonym 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.verdict.confidence | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.verdict.threatLevel | numeric |  |   0.75 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.verdict.verdict | string |  |   LIKELY_MALICIOUS 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.averageSignalStrength | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.description | string |  |   Matched a malicious YARA rule 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.finalSignalStrength | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.identifier | string |  |   Y002 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.peakSignalStrength | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.additionalInfo | string |  |   PUP_InstallRex_AntiFWb 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.isStrictlyBasedOnInputData | boolean |  |   True  False 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.originIdentifier | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.originPath | string |  |   file.yaraMatches 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.originType | string |  |   INPUT_FILE 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.signalReadable | string |  |   Matched YARA rule PUP_InstallRex_AntiFWb with strength 0.75 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.strength | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.verdict.confidence | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.verdict.threatLevel | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.verdict.verdict | string |  |   MALICIOUS 
action_result.data.\*.taskReference.resourceReference.created_date | string |  |   05/23/2023, 13:01:40 
action_result.data.\*.taskReference.resourceReference.estimatedTime | numeric |  |   12 
action_result.data.\*.taskReference.resourceReference.estimated_progress | numeric |  |   1.0 
action_result.data.\*.taskReference.resourceReference.file.hash | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.taskReference.resourceReference.file.name | string |  |   bad_file.exe 
action_result.data.\*.taskReference.resourceReference.file.type | string |  |   pe 
action_result.data.\*.taskReference.resourceReference.filesDownloadFinished | boolean |  |   True  False 
action_result.data.\*.taskReference.resourceReference.name | string |  |   file 
action_result.data.\*.taskReference.resourceReference.opcount | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.processTime | numeric |  |   8000 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.additionalInfo | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.name | string |  |   visualization 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.opcount | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.processTime | numeric |  |   235 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.resourceReference.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.resourceReference.name | string |  |   visualization 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.resourceReference.type | string |  |   VISUALIZATION 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.state | string |  |   SUCCESS 
action_result.data.\*.taskReference.resourceReference.type | string |  |   TRANSFORM_FILE 
action_result.data.\*.taskReference.state | string |  |   SUCCESS 
action_result.summary.flow_id | string |  |   0123456789abcdefghijklmn 
action_result.summary.rejected_reasons.\* | string |  |   ARCHIVE_ENCRYPTED 
action_result.summary.total_benign | numeric |  |   3 
action_result.summary.total_no_threat | numeric |  |   3 
action_result.summary.total_likely_malicious | numeric |  |   3 
action_result.summary.total_malicious | numeric |  |   3 
action_result.summary.total_rejected | numeric |  |   1 
action_result.summary.total_suspicious | numeric |  |   3 
action_result.summary.total_unknown | numeric |  |   3 
action_result.message | string |  |   Total benign: 1, Total unknown: 0, Total no threat: 0, Total suspicious: 0, Total likely malicious: 0, Total malicious: 0, Total rejected: 0, Rejected reasons: [], Flow id: 1234 
summary.total_objects | numeric |  |   2 
summary.total_objects_successful | numeric |  |   2   

## action: 'detonate file'
Retrieve detonation analysis results for file

Type: **investigate**  
Read only: **True**

Detonate url will send a file from Vault to MetaDefender Sandbox for analysis.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** |  required  | Vault ID of file to detonate | string |  `vault id`  `sha1` 
**password** |  optional  | Custom password, in case uploaded archive is protected | string | 
**is_private** |  optional  | If file should not be available for download by other users | boolean | 
**description** |  optional  | Uploaded file/url description | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.description | string |  |   This is a description 
action_result.parameter.is_private | boolean |  |   True  False 
action_result.parameter.password | string |  |   EAMPLEdajjccds 
action_result.parameter.vault_id | string |  `vault id`  `sha1`  |   0123456789abcdefghijklmnopqrstuvwxyz0123 
action_result.data.\*.allSignalGroups.\*.averageSignalStrength | numeric |  |   0.25 
action_result.data.\*.allSignalGroups.\*.description | string |  |   Found a base64 encoded http(s) URL prefix 
action_result.data.\*.allSignalGroups.\*.finalSignalStrength | numeric |  |   0.25 
action_result.data.\*.allSignalGroups.\*.identifier | string |  |   S001 
action_result.data.\*.allSignalGroups.\*.peakSignalStrength | numeric |  |   0.25 
action_result.data.\*.allSignalGroups.\*.signals.\*.isStrictlyBasedOnInputData | boolean |  |   True  False 
action_result.data.\*.allSignalGroups.\*.signals.\*.originIdentifier | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.allSignalGroups.\*.signals.\*.originPath | string |  |   file.strings.references 
action_result.data.\*.allSignalGroups.\*.signals.\*.originType | string |  |   EXTRACTED_FILE 
action_result.data.\*.allSignalGroups.\*.signals.\*.signalReadable | string |  |   Found artifact in string 
action_result.data.\*.allSignalGroups.\*.signals.\*.strength | numeric |  |   0.25 
action_result.data.\*.allSignalGroups.\*.verdict.confidence | numeric |  |   1 
action_result.data.\*.allSignalGroups.\*.verdict.threatLevel | numeric |  |   0.2 
action_result.data.\*.allSignalGroups.\*.verdict.verdict | string |  |   NO_THREAT 
action_result.data.\*.allTags.\*.isRootTag | boolean |  |   True  False 
action_result.data.\*.allTags.\*.source | string |  |   MEDIA_TYPE 
action_result.data.\*.allTags.\*.sourceIdentifier | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.allTags.\*.tag.descriptions.cluster.authors.\* | string |  |   John Doe 
action_result.data.\*.allTags.\*.tag.descriptions.cluster.type | string |  |   malpedia 
action_result.data.\*.allTags.\*.tag.descriptions.description | string |  |   This is a description 
action_result.data.\*.allTags.\*.tag.name | string |  |   html 
action_result.data.\*.allTags.\*.tag.synonyms.\* | string |  |   synonym 
action_result.data.\*.allTags.\*.tag.verdict.confidence | numeric |  |   1 
action_result.data.\*.allTags.\*.tag.verdict.threatLevel | numeric |  |   0.75 
action_result.data.\*.allTags.\*.tag.verdict.verdict | string |  |   LIKELY_MALICIOUS 
action_result.data.\*.file.hash | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.file.name | string |  |   https://www.test.com 
action_result.data.\*.file.type | string |  |   other 
action_result.data.\*.finalVerdict.confidence | numeric |  |   0 
action_result.data.\*.finalVerdict.threatLevel | numeric |  |   0 
action_result.data.\*.finalVerdict.verdict | string |  |   malicious 
action_result.data.\*.overallState | string |  |   success 
action_result.data.\*.postprocessIocs.\* | string |  |   url 
action_result.data.\*.subtaskReferences.\*.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.subtaskReferences.\*.additionalInfo | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.subtaskReferences.\*.name | string |  |   osint 
action_result.data.\*.subtaskReferences.\*.opcount | numeric |  |   4 
action_result.data.\*.subtaskReferences.\*.processTime | numeric |  |   1006 
action_result.data.\*.subtaskReferences.\*.resourceReference.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.subtaskReferences.\*.resourceReference.name | string |  |   osint 
action_result.data.\*.subtaskReferences.\*.resourceReference.type | string |  |   OSINT 
action_result.data.\*.subtaskReferences.\*.state | string |  |   SUCCESS 
action_result.data.\*.taskReference.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.additionalInfo.digests.SHA-256 | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.taskReference.additionalInfo.submitName | string |  |   bad_file.exe 
action_result.data.\*.taskReference.additionalInfo.submitTime | numeric |  |   1684846900889 
action_result.data.\*.taskReference.name | string |  |   transform-file 
action_result.data.\*.taskReference.resourceReference.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.isRootTag | boolean |  |   True  False 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.source | string |  |   MEDIA_TYPE 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.sourceIdentifier | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.descriptions.cluster.authors.\* | string |  |   John Doe 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.descriptions.cluster.type | string |  |   malpedia 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.descriptions.description | string |  |   This is a description 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.name | string |  |   html 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.synonyms.\* | string |  |   synonym 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.verdict.confidence | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.verdict.threatLevel | numeric |  |   0.75 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.allTags.\*.tag.verdict.verdict | string |  |   LIKELY_MALICIOUS 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.averageSignalStrength | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.description | string |  |   Matched a malicious YARA rule 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.finalSignalStrength | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.identifier | string |  |   Y002 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.peakSignalStrength | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.additionalInfo | string |  |   PUP_InstallRex_AntiFWb 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.isStrictlyBasedOnInputData | boolean |  |   True  False 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.originIdentifier | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.originPath | string |  |   file.yaraMatches 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.originType | string |  |   INPUT_FILE 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.signalReadable | string |  |   Matched YARA rule PUP_InstallRex_AntiFWb with strength 0.75 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.signals.\*.strength | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.verdict.confidence | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.verdict.threatLevel | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.allSignalGroups.\*.verdict.verdict | string |  |   MALICIOUS 
action_result.data.\*.taskReference.resourceReference.created_date | string |  |   05/23/2023, 13:01:40 
action_result.data.\*.taskReference.resourceReference.estimatedTime | numeric |  |   12 
action_result.data.\*.taskReference.resourceReference.estimated_progress | numeric |  |   1.0 
action_result.data.\*.taskReference.resourceReference.file.hash | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.taskReference.resourceReference.file.name | string |  |   bad_file.exe 
action_result.data.\*.taskReference.resourceReference.file.type | string |  |   pe 
action_result.data.\*.taskReference.resourceReference.filesDownloadFinished | boolean |  |   True  False 
action_result.data.\*.taskReference.resourceReference.name | string |  |   file 
action_result.data.\*.taskReference.resourceReference.opcount | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.processTime | numeric |  |   8000 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.additionalInfo | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.name | string |  |   visualization 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.opcount | numeric |  |   1 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.processTime | numeric |  |   235 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.resourceReference.ID | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.resourceReference.name | string |  |   visualization 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.resourceReference.type | string |  |   VISUALIZATION 
action_result.data.\*.taskReference.resourceReference.subtaskReferences.\*.state | string |  |   SUCCESS 
action_result.data.\*.taskReference.resourceReference.type | string |  |   TRANSFORM_FILE 
action_result.data.\*.taskReference.state | string |  |   SUCCESS 
action_result.summary.flow_id | string |  |   0123456789abcdefghijklmn 
action_result.summary.rejected_reasons.\* | string |  |   ARCHIVE_ENCRYPTED 
action_result.summary.total_benign | numeric |  |   3 
action_result.summary.total_no_threat | numeric |  |   3 
action_result.summary.total_likely_malicious | numeric |  |   3 
action_result.summary.total_malicious | numeric |  |   3 
action_result.summary.total_rejected | numeric |  |   1 
action_result.summary.total_suspicious | numeric |  |   3 
action_result.summary.total_unknown | numeric |  |   3 
action_result.message | string |  |   Total benign: 1, Total unknown: 0, Total no threat: 0, Total suspicious: 0, Total likely malicious: 0, Total malicious: 0, Total rejected: 0, Rejected reasons: [], Flow id: 1234 
summary.total_objects | numeric |  |   2 
summary.total_objects_successful | numeric |  |   2   

## action: 'search terms'
Search for scan reports on MetaDefender Sandbox using parameters specified in the 'query' field

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** |  required  | The query string | string | 
**limit** |  optional  | Number of total results, maximum 50 (if page and page_size was also provided, then it will be ignored) | numeric | 
**page** |  optional  | Page number, starting from 1 | numeric | 
**page_size** |  optional  | Page size. Can be 5, 10 or 20 | numeric | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.limit | numeric |  |   10 
action_result.parameter.page | numeric |  |   1 
action_result.parameter.page_size | numeric |  |   10 
action_result.parameter.query | string |  |   filename = test.exe 
action_result.data.\*.file.link | string |  |   https://jusrandomlink.com/1234 
action_result.data.\*.file.mime_type | string |  |   image/jpeg 
action_result.data.\*.file.name | string |  |   bad_file.exe 
action_result.data.\*.file.sha256 | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.file.short_type | string |  |   jpg 
action_result.data.\*.id | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.matches.\*.matches.sha1.\*.value | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123 
action_result.data.\*.matches.\*.origin.filetype | string |  |   jpg 
action_result.data.\*.matches.\*.origin.mime_type | string |  |   image/jpeg 
action_result.data.\*.matches.\*.origin.relation | string |  |   source 
action_result.data.\*.matches.\*.origin.sha256 | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.original_verdict | string |  |   malicious 
action_result.data.\*.scan_init.id | string |  |   0123456789abcdefghijklmn 
action_result.data.\*.state | string |  |   success_partial 
action_result.data.\*.tags.\*.isRootTag | boolean |  |   True  False 
action_result.data.\*.tags.\*.source | string |  |   MEDIA_TYPE 
action_result.data.\*.tags.\*.sourceIdentifier | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.tags.\*.tag.descriptions.cluster.authors.\* | string |  |   John Doe 
action_result.data.\*.tags.\*.tag.descriptions.cluster.type | string |  |   malpedia 
action_result.data.\*.tags.\*.tag.descriptions.description | string |  |   This is a description 
action_result.data.\*.tags.\*.tag.name | string |  |   html 
action_result.data.\*.tags.\*.tag.synonyms.\* | string |  |   synonym 
action_result.data.\*.tags.\*.tag.verdict.confidence | numeric |  |   1 
action_result.data.\*.tags.\*.tag.verdict.threatLevel | numeric |  |   0.75 
action_result.data.\*.tags.\*.tag.verdict.verdict | string |  |   BENIGN 
action_result.data.\*.updated_date | string |  |   02/14/2023, 02:34:51 
action_result.data.\*.verdict | string |  |   no_threat 
action_result.summary.available_report_count | numeric |  |   3 
action_result.summary.total_benign | numeric |  |   3 
action_result.summary.total_no_threat | numeric |  |   3 
action_result.summary.total_likely_malicious | numeric |  |   3 
action_result.summary.total_malicious | numeric |  |   3 
action_result.summary.total_suspicious | numeric |  |   3 
action_result.summary.total_unknown | numeric |  |   3 
action_result.message | string |  |   Total benign: 0, Total unknown: 0, Total no threat: 0, Total suspicious: 2, Total likely malicious: 0, Total malicious: 0, Available report count: 5 
summary.total_objects | numeric |  |   2 
summary.total_objects_successful | numeric |  |   2   

## action: 'file reputation'
Get the reputation for one given hash (returns with the last 10 MetaDefender Sandbox reports)

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**sha256** |  required  | SHA256 value of the file | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.sha256 | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.community.vote_benign | numeric |  |   0 
action_result.data.\*.community.vote_malicious | numeric |  |   0 
action_result.data.\*.filescan_reports.\*.report_date | string |  |   2023-05-25T01:15:45.789000 
action_result.data.\*.filescan_reports.\*.report_id | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.filescan_reports.\*.verdict | string |  |   malicious 
action_result.data.\*.fuzzyhash.hash | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.data.\*.fuzzyhash.verdict | string |  |   no_threat 
action_result.data.\*.mdcloud.detected_av_engines | numeric |  |   30 
action_result.data.\*.mdcloud.scan_time | string |  |   2023-05-25T01:15:45.789000 
action_result.data.\*.mdcloud.total_av_engines | numeric |  |   30 
action_result.data.\*.overall_verdict | string |  |   malicious 
action_result.data.\*.sha256 | string |  |   0123456789abcdefghijklmnopqrstuvwxyz0123456789abcdefghijklmnopqr 
action_result.summary.verdict | string |  |   3 
action_result.message | string |  |   Verdict: malicious 
summary.total_objects | numeric |  |   2 
summary.total_objects_successful | numeric |  |   2   

## action: 'ip reputation'
Get the reputation for one given IP address (returns with the last 10 MetaDefender Sandbox reports)

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** |  required  | The IP address | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.ip | string |  |   8.8.8.8 
action_result.data.\*.community.vote_benign | numeric |  |   0 
action_result.data.\*.community.vote_malicious | numeric |  |   0 
action_result.data.\*.filescan_reports.\*.report_date | string |  |   2023-05-25T01:15:45.789000 
action_result.data.\*.filescan_reports.\*.report_id | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.filescan_reports.\*.verdict | string |  |   malicious 
action_result.data.\*.ioc_type | string |  |   ip 
action_result.data.\*.ioc_value | string |  |   test.com 
action_result.data.\*.mdcloud.detected | numeric |  |   0 
action_result.data.\*.mdcloud.scan_time | string |  |   2023-05-25T01:15:45.789000 
action_result.data.\*.overall_verdict | string |  |   malicious 
action_result.summary.verdict | string |  |   3 
action_result.message | string |  |   Verdict: malicious 
summary.total_objects | numeric |  |   2 
summary.total_objects_successful | numeric |  |   2   

## action: 'domain reputation'
Get the reputation for one given Domain address (returns with the last 10 MetaDefender Sandbox reports)

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** |  required  | The Domain address | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.domain | string |  |   test.com 
action_result.data.\*.community.vote_benign | numeric |  |   0 
action_result.data.\*.community.vote_malicious | numeric |  |   0 
action_result.data.\*.filescan_reports.\*.report_date | string |  |   2023-05-25T01:15:45.789000 
action_result.data.\*.filescan_reports.\*.report_id | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.filescan_reports.\*.verdict | string |  |   malicious 
action_result.data.\*.ioc_type | string |  |   domain 
action_result.data.\*.ioc_value | string |  |   test.com 
action_result.data.\*.mdcloud.detected | numeric |  |   0 
action_result.data.\*.mdcloud.scan_time | string |  |   2023-05-25T01:15:45.789000 
action_result.data.\*.overall_verdict | string |  |   malicious 
action_result.summary.verdict | string |  |   3 
action_result.message | string |  |   Verdict: malicious 
summary.total_objects | numeric |  |   2 
summary.total_objects_successful | numeric |  |   2   

## action: 'url reputation'
Get the reputation for one given URL address (returns with the last 10 MetaDefender Sandbox reports)

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** |  required  | The URL address | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string |  |   success  failed 
action_result.parameter.url | string |  |   https://jusrandomlink.com/1234 
action_result.data.\*.community.vote_benign | numeric |  |   0 
action_result.data.\*.community.vote_malicious | numeric |  |   0 
action_result.data.\*.filescan_reports.\*.report_date | string |  |   2023-05-25T01:15:45.789000 
action_result.data.\*.filescan_reports.\*.report_id | string |  |   00000000-aaaa-aaaa-aaaa-aaaaaaaaaaaa 
action_result.data.\*.filescan_reports.\*.verdict | string |  |   malicious 
action_result.data.\*.ioc_type | string |  |   url 
action_result.data.\*.ioc_value | string |  |   test.com 
action_result.data.\*.mdcloud.detected | numeric |  |   0 
action_result.data.\*.mdcloud.scan_time | string |  |   2023-05-25T01:15:45.789000 
action_result.data.\*.overall_verdict | string |  |   malicious 
action_result.summary.verdict | string |  |   3 
action_result.message | string |  |   Verdict: malicious 
summary.total_objects | numeric |  |   2 
summary.total_objects_successful | numeric |  |   2 