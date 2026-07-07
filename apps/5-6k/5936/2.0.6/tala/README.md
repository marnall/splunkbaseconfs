[comment]: # "Auto-generated SOAR connector documentation"
# Tala

Publisher: Splunk Community  
Connector Version: 2\.0\.2  
Product Vendor: Tala Security  
Product Name: Tala  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.0\.0  

This app implements various endpoint actions using Tala

[comment]: # " File: readme.md"
[comment]: # ""
[comment]: # "Copyright (c) 2018-2021 Splunk Inc."
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
[comment]: # ""
[comment]: # "without a valid written license from Splunk Inc. is PROHIBITED. Phantom App imports"
[comment]: # ""
The app uses HTTP/ HTTPS protocol for communicating with the Tala server. Below are the default
ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http         | tcp                | 80   |
|         https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Tala asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base\_url** |  required  | string | Base url
**auth\_token** |  required  | password | Authorization token

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[create project](#action-create-project) - Create a new project  
[list projects](#action-list-projects) - List information about all projects  
[get project](#action-get-project) - Get information about a project  
[update project](#action-update-project) - Update an existing project  
[delete project](#action-delete-project) - Delete a project  
[scan url](#action-scan-url) - Initiate a scan on a project that has already been scanned  
[get scan settings](#action-get-scan-settings) - Retrieve the settings related to scanning a project  
[get results](#action-get-results) - Get the abstract information model \(AIM\) representation of the latest scan on a project  
[get policy](#action-get-policy) - Download an AIM policy bundle and import it to the vault  
[synchronize projects](#action-synchronize-projects) - Synchronize projects to return a newer policy, which will be added to the vault  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'create project'
Create a new project

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** |  required  | Name of project to create | string |  `tala project name` 
**url** |  required  | Url to analyze | string |  `url` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.name | string |  `tala project name` 
action\_result\.parameter\.url | string |  `url` 
action\_result\.data\.\*\.id | numeric |  `tala project id` 
action\_result\.data\.\*\.created | string | 
action\_result\.data\.\*\.name | string |  `tala project name` 
action\_result\.data\.\*\.url | string |  `url` 
action\_result\.summary\.project\_id | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list projects'
List information about all projects

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.data\.\*\.completed | string | 
action\_result\.data\.\*\.created | string | 
action\_result\.data\.\*\.end | string | 
action\_result\.data\.\*\.id | numeric |  `tala project id` 
action\_result\.data\.\*\.max\-pages | numeric | 
action\_result\.data\.\*\.name | string |  `tala project name` 
action\_result\.data\.\*\.automationMode | string | 
action\_result\.data\.\*\.scan\-status | string | 
action\_result\.data\.\*\.url | string |  `url` 
action\_result\.data\.\*\.scans\.failed\-scans | numeric | 
action\_result\.data\.\*\.scans\.last\-failed\-scan\-at | string | 
action\_result\.data\.\*\.scans\.last\-successful\-scan\-at | string | 
action\_result\.data\.\*\.scans\.successful\-scans | numeric | 
action\_result\.data\.\*\.start | string | 
action\_result\.data\.\*\.started | string | 
action\_result\.data\.\*\.total\-pages\-scanned | numeric | 
action\_result\.summary\.num\_projects | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get project'
Get information about a project

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**project\_id** |  required  | Id of project | numeric |  `tala project id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.project\_id | numeric |  `tala project id` 
action\_result\.data\.\*\.completed | string | 
action\_result\.data\.\*\.created | string | 
action\_result\.data\.\*\.id | numeric |  `tala project id` 
action\_result\.data\.\*\.max\-pages | numeric | 
action\_result\.data\.\*\.name | string |  `tala project name` 
action\_result\.data\.\*\.url | string |  `url` 
action\_result\.data\.\*\.automationMode | string | 
action\_result\.data\.\*\.scan\-status | string | 
action\_result\.data\.\*\.scan\-id | string |  `tala scan id` 
action\_result\.data\.\*\.scans\.failed\-scans | numeric | 
action\_result\.data\.\*\.scans\.last\-failed\-scan\-at | string | 
action\_result\.data\.\*\.scans\.last\-successful\-scan\-at | string | 
action\_result\.data\.\*\.scans\.successful\-scans | numeric | 
action\_result\.data\.\*\.start | string | 
action\_result\.data\.\*\.started | string | 
action\_result\.data\.\*\.total\-pages\-scanned | numeric | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'update project'
Update an existing project

Type: **generic**  
Read only: **False**

Update the name, url, and/or automation\_mode for the project\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**project\_id** |  required  | Id of project to update | string |  `tala project id` 
**name** |  optional  | Updated project name | string |  `tala project name` 
**url** |  optional  | Updated project url | string |  `url` 
**automation\_mode** |  optional  | Means of deploying a policy\. 'manual' indicates a control via UI and 'triggered' indicates control via APIs | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.automation\_mode | string | 
action\_result\.parameter\.name | string |  `tala project name` 
action\_result\.parameter\.project\_id | string |  `tala project id` 
action\_result\.parameter\.url | string |  `url` 
action\_result\.data\.\*\.id | numeric |  `tala project id` 
action\_result\.data\.\*\.name | string |  `tala project name` 
action\_result\.data\.\*\.url | string |  `url` 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'delete project'
Delete a project

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**project\_id** |  required  | Id of project to delete | numeric |  `tala project id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.project\_id | numeric |  `tala project id` 
action\_result\.data\.\*\.created | string | 
action\_result\.data\.\*\.deleted | string | 
action\_result\.data\.\*\.id | numeric |  `tala project id` 
action\_result\.data\.\*\.name | string |  `tala project name` 
action\_result\.data\.\*\.url | string |  `url` 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'scan url'
Initiate a scan on a project that has already been scanned

Type: **generic**  
Read only: **False**

The project scan details from the previous project's scan will be used\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**project\_ids** |  required  | Comma separated project ids | string |  `tala project id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.project\_ids | string |  `tala project id` 
action\_result\.data\.\*\.error | string | 
action\_result\.data\.\*\.error\.error\-details | string | 
action\_result\.data\.\*\.project\-id | string |  `tala project id` 
action\_result\.data\.\*\.scan\-id | string |  `tala scan id` 
action\_result\.data\.\*\.success | boolean | 
action\_result\.data\.\*\.error\.error\-message | string | 
action\_result\.summary\.message | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get scan settings'
Retrieve the settings related to scanning a project

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**project\_id** |  required  | Id of project to settings of | numeric |  `tala project id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.project\_id | numeric |  `tala project id` 
action\_result\.data\.\*\.policy\-preferences\.block\-mixed\-content | boolean | 
action\_result\.data\.\*\.scan\-config\.max\-pages | numeric | 
action\_result\.data\.\*\.scan\-config\.callback\-url | string |  `url` 
action\_result\.data\.\*\.scan\-config\.url\-filter\-pattern\-regex\-inclusive | string | 
action\_result\.data\.\*\.policy\-preferences\.enforcement\-type | string | 
action\_result\.data\.\*\.policy\-preferences\.frame\-ancestors | string | 
action\_result\.data\.\*\.policy\-preferences\.report\-uri | string | 
action\_result\.data\.\*\.scan\-config\.auth\-info | string | 
action\_result\.data\.\*\.scan\-config\.clickables\-config\.profile | string | 
action\_result\.data\.\*\.scan\-config\.max\-depth | numeric | 
action\_result\.data\.\*\.scan\-config\.url\-filter\-pattern\-regex\-exclusive | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get results'
Get the abstract information model \(AIM\) representation of the latest scan on a project

Type: **investigate**  
Read only: **True**

Summarize the abstract information model \(AIM\) representation of the latest scan on a given project\. The AIM details includes the number of resources identified by the Tala scan, as well as relevant security headers, the Tala security score \(out of 100\) assigned to the site \(both before and after applying the Tala policy generated for this scan\), and suggestions for how the scan can be improved\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**project\_id** |  required  | Id of project to summary of | numeric |  `tala project id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.project\_id | numeric |  `tala project id` 
action\_result\.data | string | 
action\_result\.data\.\*\.current\_score | string | 
action\_result\.data\.\*\.previous\_score | string | 
action\_result\.data\.\*\.resources\.pages\_event\_handlers\_count | string | 
action\_result\.data\.\*\.resources\.pages\_explicit\_scripts\_count | string | 
action\_result\.data\.\*\.resources\.pages\_external\_domain\_scripts\_count | string |  `domain` 
action\_result\.data\.\*\.resources\.pages\_font\_count | string | 
action\_result\.data\.\*\.resources\.pages\_form\_count | string | 
action\_result\.data\.\*\.resources\.pages\_iframes\_count | string | 
action\_result\.data\.\*\.resources\.pages\_iframes\_not\_sandboxed\_count | string | 
action\_result\.data\.\*\.resources\.pages\_inline\_scripts\_count | string | 
action\_result\.data\.\*\.resources\.pages\_using\_ajax\_count | string | 
action\_result\.data\.\*\.resources\.pages\_using\_eval\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.ad\_network\_links\_pages\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.ad\_network\_links\_total\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.alexa\_10k\_links\_pages\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.alexa\_10k\_links\_total\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.cdn\_10k\_links\_pages\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.cdn\_links\_total\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.js\_library\_links\_pages\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.js\_library\_links\_total\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.social\_media\_links\_pages\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.social\_media\_links\_total\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.third\_party\_links\_pages\_count | string | 
action\_result\.data\.\*\.resources\.third\_party\_usage\.third\_party\_links\_total\_count | string | 
action\_result\.data\.\*\.resources\.total\_ajax\_count | string | 
action\_result\.data\.\*\.resources\.total\_eval\_count | string | 
action\_result\.data\.\*\.resources\.total\_event\_handlers\_count | string | 
action\_result\.data\.\*\.resources\.total\_explicit\_scripts\_count | string | 
action\_result\.data\.\*\.resources\.total\_external\_domain\_scripts\_count | string |  `domain` 
action\_result\.data\.\*\.resources\.total\_font\_count | string | 
action\_result\.data\.\*\.resources\.total\_form\_count | string | 
action\_result\.data\.\*\.resources\.total\_iframes\_count | string | 
action\_result\.data\.\*\.resources\.total\_iframes\_not\_sandboxed\_count | string | 
action\_result\.data\.\*\.resources\.total\_inline\_scripts\_count | string | 
action\_result\.data\.\*\.security\_headers\.content\_security\_policy | boolean | 
action\_result\.data\.\*\.security\_headers\.content\_security\_policy\_report\_only | boolean | 
action\_result\.data\.\*\.security\_headers\.expect\_ct | boolean | 
action\_result\.data\.\*\.security\_headers\.hpkp | boolean | 
action\_result\.data\.\*\.security\_headers\.hsts | boolean | 
action\_result\.data\.\*\.security\_headers\.x\_content\_type\_options | boolean | 
action\_result\.data\.\*\.security\_headers\.x\_frame\_options | boolean | 
action\_result\.data\.\*\.security\_headers\.x\_permitted\_cross\_domain\_policies | boolean |  `domain` 
action\_result\.data\.\*\.security\_headers\.x\_xss\_protection | boolean | 
action\_result\.data\.\*\.suggestions | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get policy'
Download an AIM policy bundle and import it to the vault

Type: **generic**  
Read only: **False**

Download the AIM bundle, which contains configuration data for enforcing a policy on one or more projects \(Blocking\)\. If server\_conf is provided, the web server injection module, template matching library, and latest AIM policy are downloaded\. If the configuration of the server is not binary compatible with a pre\-built version of the web module, the source code for the web module will be downloaded instead\. If the configuration of the server is invalid, an empty zip file will be returned\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**project\_ids** |  required  | One or more project IDs to get summary of, separated by commas | string |  `tala project id` 
**tracking\_id** |  required  | Tracking id | numeric |  `tala tracking id` 
**server\_conf** |  optional  | Server configuration | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.project\_ids | string |  `tala project id` 
action\_result\.parameter\.server\_conf | string | 
action\_result\.parameter\.tracking\_id | numeric |  `tala tracking id` 
action\_result\.data\.\*\.name | string | 
action\_result\.data\.\*\.size | numeric | 
action\_result\.data\.\*\.vault\_id | string |  `vault id`  `sha1` 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'synchronize projects'
Synchronize projects to return a newer policy, which will be added to the vault

Type: **generic**  
Read only: **False**

Because validation cannot be done on a scan id, if an invalid scan id is provided, then an empty zip file will be returned\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**scan\_id** |  required  | Scan id | string |  `tala scan id` 
**project\_ids** |  required  | Comma separated project ids | string |  `tala project id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.project\_ids | string |  `tala project id` 
action\_result\.data\.\*\.vault\_id | string |  `sha1`  `vault id` 
action\_result\.parameter\.scan\_id | string |  `tala scan id` 
action\_result\.data\.\*\.name | string | 
action\_result\.data\.\*\.size | numeric | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 