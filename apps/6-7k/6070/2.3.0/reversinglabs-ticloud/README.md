[comment]: # "Auto-generated SOAR connector documentation"
# RL TitaniumCloud REST APIs

Publisher: ReversingLabs  
Connector Version: 2\.3\.0  
Product Vendor: ReversingLabs  
Product Name: TitaniumCloud  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.1\.0  

This app integrates with ReversingLabs cloud services to implement reputation and investigative actions for file samples and their metadata

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) ReversingLabs Inc 2016-2022"
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
# ReversingLabs TitaniumCloud File Reputation

This app implements the investigative action 'file reputation' on the ReversingLabs TitaniumCloud
file reputation service. Information includes ReversingLabs Malware Presence information and
Anti-Virus scanner information.  
  
The ReversingLabs TitaniumCloud File Reputation, part of ReversingLabs Threat Intelligence provides
up-to-date file reputation, Anti-Virus scan information and internal analysis information on
billions of goodware and malware samples.  
  
Malware samples are continually reanalyzed to ensure that the reputation information is relevant at
all times.  
  
In addition to file reputation and historical AV reputation, additional Threat Intelligence can be
obtained from TitaniumCloud via multiple APIs and Feeds, which allow users to search for files by
hash or anti-virus detection name. It is also possible to hunt for files from a single malware
family, search for functionally similar samples, perform bulk queries, and receive alerts on file
reputation changes.  
  
For more information, consult the [official product
website.](https://www.reversinglabs.com/products/file-reputation-service.html)

## How to Configure the App

Access the Asset Settings tab on the Asset Configuration page. The variables described in the
previous section are displayed in this tab.  
[![](img/reversinglabs_ticloud_asset.png)](img/reversinglabs_ticloud_asset.png)  
  
  
Input the username and password required to connect to ReversingLabs TitaniumCloud File Reputation
service.  
  
  
Select the "Verify server certificate" checkbox to ensure that the self-signed certificates are not
accepted.

Note: Action parameter 'hunting report vault id' expects JSON type of content from file.

**Playbook Backward Compatibility**

Following new actions have been added:

-   certificate analytics
-   uri statistics
-   file similarity analytics
-   advanced search
-   joe sandbox adapter

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the RL TitaniumCloud REST APIs server.
Below are the default ports used by the Splunk SOAR Connector.

| SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|--------------|--------------------|------|
| http         | tcp                | 80   |
| https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a TitaniumCloud asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**username** |  required  | string | Username
**password** |  required  | password | Password
**url** |  optional  | string | TitaniumCloud or T1000 url
**verify\_server\_cert** |  optional  | boolean | Verify server certificate

### Supported Actions  
[joe sandbox adapter](#action-joe-sandbox-adapter) - ReversingLabs plug\-in for Joe Sandbox which will update threat hunting metadata with dynamic analysis results  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity  
[file reputation](#action-file-reputation) - Queries ReversingLabs for file reputation info  
[advanced search](#action-advanced-search) - Queries ReversingLabs Advanced Search with specified search query  
[file similarity analytics](#action-file-similarity-analytics) - Queries ReversingLabs file similarity analytics for the specified file  
[uri statistics](#action-uri-statistics) - Queries ReversingLabs URI statistics for the specified URI  
[certificate analytics](#action-certificate-analytics) - Queries ReversingLabs certificate analytics for the specified certificate thumbprint  

## action: 'joe sandbox adapter'
ReversingLabs plug\-in for Joe Sandbox which will update threat hunting metadata with dynamic analysis results

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**joe\_report\_vault\_id** |  optional  | Joe Sandbox dynamic analysis report vault ID | string |  `vault id` 
**hunting\_report\_vault\_id** |  required  | Threat hunting report vault id | string |  `vault id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.parameter\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.parameter\.joe\_report\_vault\_id | string |  `vault id` 
action\_result\.data\.\*\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.data\.\*\.readable\_summary\.classification\.classification | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.reason | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.factor | numeric | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.name | string | 
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.summary | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'test connectivity'
Validate the asset configuration for connectivity

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'file reputation'
Queries ReversingLabs for file reputation info

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** |  optional  | File hash to query | string |  `md5`  `sha1`  `sha256` 
**hunting\_report\_vault\_id** |  optional  | Threat hunting report vault id | string |  `vault id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.parameter\.hash | string |  `md5`  `sha1`  `sha256` 
action\_result\.parameter\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.data\.\*\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.data\.\*\.readable\_summary\.classification\.classification | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.reason | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.factor | numeric | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.name | string | 
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.summary | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'advanced search'
Queries ReversingLabs Advanced Search with specified search query

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**search\_parameter** |  optional  | RL Advanced Search query search field | string | 
**results\_per\_page** |  optional  | Number of results per one page \(Default\:1000\) | numeric | 
**page\_number** |  optional  | Page number \(Default\:1\) | numeric | 
**hunting\_report\_vault\_id** |  optional  | Threat hunting report vault id | string |  `vault id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.parameter\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.parameter\.page\_number | numeric | 
action\_result\.parameter\.results\_per\_page | numeric | 
action\_result\.parameter\.search\_parameter | string | 
action\_result\.data\.\*\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.data\.\*\.readable\_summary\.classification\.classification | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.reason | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.factor | numeric | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.name | string | 
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.summary | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'file similarity analytics'
Queries ReversingLabs file similarity analytics for the specified file

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** |  optional  | File SHA1 hash value | string |  `sha1` 
**sample\_type** |  optional  | RL TitaniumCore sample type | string | 
**hunting\_report\_vault\_id** |  optional  | Threat hunting report that represents current state of the hunting workflow | string |  `vault id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.parameter\.hash | string |  `sha1` 
action\_result\.parameter\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.parameter\.sample\_type | string | 
action\_result\.data\.\*\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.data\.\*\.readable\_summary\.classification\.classification | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.reason | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.factor | numeric | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.name | string | 
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.summary | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'uri statistics'
Queries ReversingLabs URI statistics for the specified URI

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**uri** |  optional  | URI value that will get queried\. Can be\: url, domain, email address or ip address | string | 
**hunting\_report\_vault\_id** |  optional  | Threat hunting report that represent current state of the hunting workflow | string |  `vault id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.parameter\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.parameter\.uri | string | 
action\_result\.data\.\*\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.data\.\*\.readable\_summary\.classification\.classification | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.reason | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.factor | numeric | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.name | string | 
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.summary | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'certificate analytics'
Queries ReversingLabs certificate analytics for the specified certificate thumbprint

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**thumbprint** |  optional  | Certificate thumbprint that will get queried\. Can be\: url, domain, email address or ip address | string | 
**hunting\_report\_vault\_id** |  optional  | Threat hunting report that represents current state of the hunting workflow | string |  `vault id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.parameter\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.parameter\.thumbprint | string | 
action\_result\.data\.\*\.hunting\_report\_vault\_id | string |  `vault id` 
action\_result\.data\.\*\.readable\_summary\.classification\.classification | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.reason | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.description | string | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.factor | numeric | 
action\_result\.data\.\*\.readable\_summary\.classification\.threat\.name | string | 
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.summary | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 