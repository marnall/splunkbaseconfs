[comment]: # "Auto-generated SOAR connector documentation"
# Kenna Security

Publisher: Splunk Community  
Connector Version: 2\.0\.0  
Product Vendor: Kenna Security  
Product Name: Kenna Security  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.1\.0  

This app integrates with Kenna Security to implement various investigative actions

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Kenna Security asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**risk\_token** |  required  | password | Risk token

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[list patches](#action-list-patches) - List patches for a specified device  
[update device](#action-update-device) - Update device information  
[list devices](#action-list-devices) - List devices  
[run connector](#action-run-connector) - Run a connector  
[list connectors](#action-list-connectors) - List all connectors  
[update vulnerability](#action-update-vulnerability) - Update a vulnerability  
[get vulnerabilities](#action-get-vulnerabilities) - Get vulnerabilities for a specific device  
[run query](#action-run-query) - Run query on vulnerabilities  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'list patches'
List patches for a specified device

Type: **investigate**  
Read only: **True**

If parameter <b>Vulnerability ID</b> is provided then other parameters would be ignored\.<br>If user requires data based on IP, Hostname or MAC Address then he needs to select appropriate filter type and provide related value for it\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter\_type** |  optional  | Type of filter | string | 
**filter** |  optional  | Filter for vulnerability | string |  `ip`  `host name`  `mac address` 
**vulnerability\_id** |  optional  | ID of the vulnerability for patches | numeric |  `kenna vulnerability id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.filter | string |  `ip`  `host name`  `mac address` 
action\_result\.parameter\.filter\_type | string | 
action\_result\.parameter\.vulnerability\_id | numeric |  `kenna vulnerability id` 
action\_result\.data\.\*\.assets\.\*\.display\_locator | string |  `ip`  `host name`  `mac address` 
action\_result\.data\.\*\.assets\.\*\.id | numeric |  `kenna device id` 
action\_result\.data\.\*\.assets\.\*\.locator | string |  `ip`  `host name`  `mac address` 
action\_result\.data\.\*\.assets\.\*\.primary\_locator | string | 
action\_result\.data\.\*\.category | string | 
action\_result\.data\.\*\.consequence | string | 
action\_result\.data\.\*\.cves | string | 
action\_result\.data\.\*\.diagnosis | string | 
action\_result\.data\.\*\.id | numeric | 
action\_result\.data\.\*\.max\_vuln\_score | numeric | 
action\_result\.data\.\*\.patch\_publication\_date | string | 
action\_result\.data\.\*\.reference\_links | string | 
action\_result\.data\.\*\.scanner\_ids | string | 
action\_result\.data\.\*\.solution | string | 
action\_result\.data\.\*\.title | string | 
action\_result\.data\.\*\.updated\_at | string | 
action\_result\.data\.\*\.url | string |  `url` 
action\_result\.data\.\*\.vendor | string | 
action\_result\.data\.\*\.vuln\_count | numeric | 
action\_result\.data\.\*\.vulnerabilities\.\*\.id | numeric |  `kenna vulnerability id` 
action\_result\.data\.\*\.vulnerabilities\.\*\.scanner\_ids | string | 
action\_result\.data\.\*\.vulnerabilities\.\*\.service\_ticket\_status | string | 
action\_result\.summary\.total\_patches | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'update device'
Update device information

Type: **generic**  
Read only: **False**

At least one of <b>ID</b> or <b>IP</b> or <b>Hostname</b> needs to be provided as a parameter\.<br>Priority would be given in order of ID, IP and Hostname\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**device\_id** |  optional  | ID of the device | numeric |  `kenna device id` 
**ip** |  optional  | IP of the device | string |  `ip` 
**hostname** |  optional  | Host name of the device | string |  `host name` 
**active** |  optional  | Status of the device \(Default\: No action\) | string | 
**notes** |  optional  | Notes for the device | string | 
**owner** |  optional  | Owner of the device | string |  `user name` 
**tags** |  optional  | Tags on the device | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.active | string | 
action\_result\.parameter\.device\_id | numeric |  `kenna device id` 
action\_result\.parameter\.hostname | string |  `host name` 
action\_result\.parameter\.ip | string |  `ip` 
action\_result\.parameter\.notes | string | 
action\_result\.parameter\.owner | string |  `user name` 
action\_result\.parameter\.tags | string | 
action\_result\.data | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list devices'
List devices

Type: **investigate**  
Read only: **True**

The parameter search must contain any valid parameter found in data of assets for filtering\.<br>The search string entered by user should be in format &quotParameter\:Value&quot\.<br>Some examples of valid search string are as follows\:<br><ul><li>primary\_locator\:mac\_address</li><li>hostname\:foobar</li><li>max\_priority\:10&min\_priority\:1</li><li>service\_ports\:8080</li></ul>

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**search** |  optional  | Search string | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.search | string | 
action\_result\.data\.\*\.application | string | 
action\_result\.data\.\*\.created\_at | string | 
action\_result\.data\.\*\.database | string | 
action\_result\.data\.\*\.domains\.vulnerabilities | string |  `domain` 
action\_result\.data\.\*\.ec2 | string | 
action\_result\.data\.\*\.external\_id | string | 
action\_result\.data\.\*\.file | string |  `file name` 
action\_result\.data\.\*\.fqdn | string |  `domain` 
action\_result\.data\.\*\.hostname | string |  `host name` 
action\_result\.data\.\*\.id | numeric |  `kenna device id` 
action\_result\.data\.\*\.ip\_address | string |  `ip` 
action\_result\.data\.\*\.ipv6 | string |  `ip` 
action\_result\.data\.\*\.last\_booted\_at | string | 
action\_result\.data\.\*\.last\_seen\_time | string | 
action\_result\.data\.\*\.locator | string |  `ip`  `host name`  `mac address` 
action\_result\.data\.\*\.mac\_address | string |  `mac address` 
action\_result\.data\.\*\.netbios | string | 
action\_result\.data\.\*\.network\_ports\.\*\.extra\_info | string | 
action\_result\.data\.\*\.network\_ports\.\*\.hostname | string |  `host name` 
action\_result\.data\.\*\.network\_ports\.\*\.id | numeric | 
action\_result\.data\.\*\.network\_ports\.\*\.name | string | 
action\_result\.data\.\*\.network\_ports\.\*\.ostype | string | 
action\_result\.data\.\*\.network\_ports\.\*\.port\_number | numeric |  `port` 
action\_result\.data\.\*\.network\_ports\.\*\.product | string | 
action\_result\.data\.\*\.network\_ports\.\*\.protocol | string | 
action\_result\.data\.\*\.network\_ports\.\*\.state | string | 
action\_result\.data\.\*\.network\_ports\.\*\.version | string | 
action\_result\.data\.\*\.notes | string | 
action\_result\.data\.\*\.operating\_system | string | 
action\_result\.data\.\*\.owner | string |  `user name` 
action\_result\.data\.\*\.primary\_locator | string | 
action\_result\.data\.\*\.priority | numeric | 
action\_result\.data\.\*\.risk\_meter\_score | numeric | 
action\_result\.data\.\*\.status | string | 
action\_result\.data\.\*\.tags | string | 
action\_result\.data\.\*\.url | string |  `url` 
action\_result\.data\.\*\.urls\.vulnerabilities | string |  `url` 
action\_result\.data\.\*\.vulnerabilities\_count | numeric | 
action\_result\.summary\.total\_devices | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'run connector'
Run a connector

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**connector** |  required  | ID or name of the connector | string |  `kenna connector id`  `kenna connector name` 
**vault\_id** |  required  | Vault ID | string |  `vault id`  `sha1` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.connector | string |  `kenna connector id`  `kenna connector name` 
action\_result\.parameter\.vault\_id | string |  `vault id`  `sha1` 
action\_result\.data\.\*\.error | string | 
action\_result\.data\.\*\.success | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'list connectors'
List all connectors

Type: **investigate**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.data\.\*\.host | string |  `host name` 
action\_result\.data\.\*\.id | numeric |  `kenna connector id` 
action\_result\.data\.\*\.name | string |  `kenna connector name` 
action\_result\.data\.\*\.running | boolean | 
action\_result\.summary\.total\_connectors | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'update vulnerability'
Update a vulnerability

Type: **generic**  
Read only: **False**

The due date should be entered in <b>YYYY\-MM\-DD</b> or valid &quotiso8601 timestamp&quot format\.<br>Some examples of valid time formats are\:<ul><li>2018\-09\-24</li><li>2018\-09\-23T14\:40\:44Z</li><li>2018\-09\-23T14\:40\:44\+05\:30</li><li>2020\-08\-30T01\:45\:36\.123Z</li><li>2021\-12\-13T21\:20\:37\.593194\+05\:30</li></ul>

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vulnerability\_id** |  required  | ID of the vulnerability | numeric |  `kenna vulnerability id` 
**vulnerability\_status** |  optional  | Status of the vulnerability \(Default\: Open\) | string | 
**notes** |  optional  | Notes for vulnerability | string | 
**priority** |  optional  | Priority flag for vulnerability \(Default\: No action\) | string | 
**due\_date** |  optional  | Due date for vulnerability \(YYYY\-MM\-DD or valid iso8601 format\) | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.due\_date | string | 
action\_result\.parameter\.notes | string | 
action\_result\.parameter\.priority | string | 
action\_result\.parameter\.vulnerability\_id | numeric |  `kenna vulnerability id` 
action\_result\.parameter\.vulnerability\_status | string | 
action\_result\.data | string | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get vulnerabilities'
Get vulnerabilities for a specific device

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**filter\_type** |  required  | Type of filter \(Default\: Hostname\) | string | 
**filter** |  required  | Filter for vulnerability | string |  `ip`  `host name`  `mac address` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.filter | string |  `ip`  `host name`  `mac address` 
action\_result\.parameter\.filter\_type | string | 
action\_result\.data\.\*\.active\_internet\_breach | boolean | 
action\_result\.data\.\*\.asset\_id | numeric |  `kenna device id` 
action\_result\.data\.\*\.closed | boolean | 
action\_result\.data\.\*\.closed\_at | string | 
action\_result\.data\.\*\.connectors\.\*\.connector\_definition\_name | string | 
action\_result\.data\.\*\.connectors\.\*\.id | numeric |  `kenna connector id` 
action\_result\.data\.\*\.connectors\.\*\.name | string |  `kenna connector name` 
action\_result\.data\.\*\.connectors\.\*\.vendor | string | 
action\_result\.data\.\*\.created\_at | string | 
action\_result\.data\.\*\.custom\_fields | string | 
action\_result\.data\.\*\.cve\_description | string | 
action\_result\.data\.\*\.cve\_id | string | 
action\_result\.data\.\*\.cve\_published\_at | string | 
action\_result\.data\.\*\.description | string | 
action\_result\.data\.\*\.domains\.asset | string |  `domain` 
action\_result\.data\.\*\.due\_date | string | 
action\_result\.data\.\*\.easily\_exploitable | boolean | 
action\_result\.data\.\*\.first\_found\_on | string | 
action\_result\.data\.\*\.fix\_id | numeric | 
action\_result\.data\.\*\.id | numeric |  `kenna vulnerability id` 
action\_result\.data\.\*\.identifiers | string | 
action\_result\.data\.\*\.last\_seen\_time | string | 
action\_result\.data\.\*\.malware\_exploitable | boolean | 
action\_result\.data\.\*\.notes | string | 
action\_result\.data\.\*\.patch | boolean | 
action\_result\.data\.\*\.patch\_published\_at | string | 
action\_result\.data\.\*\.popular\_target | boolean | 
action\_result\.data\.\*\.predicted\_exploitable | boolean | 
action\_result\.data\.\*\.priority | string | 
action\_result\.data\.\*\.risk\_meter\_score | numeric | 
action\_result\.data\.\*\.scanner\_vulnerabilities\.\*\.external\_unique\_id | string | 
action\_result\.data\.\*\.scanner\_vulnerabilities\.\*\.open | boolean | 
action\_result\.data\.\*\.scanner\_vulnerabilities\.\*\.port | string |  `port` 
action\_result\.data\.\*\.service\_ticket | string | 
action\_result\.data\.\*\.severity | numeric | 
action\_result\.data\.\*\.solution | string | 
action\_result\.data\.\*\.status | string | 
action\_result\.data\.\*\.threat | numeric | 
action\_result\.data\.\*\.top\_priority | boolean | 
action\_result\.data\.\*\.urls\.asset | string |  `url` 
action\_result\.data\.\*\.wasc\_id | string | 
action\_result\.summary\.total\_vulnerabilities | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'run query'
Run query on vulnerabilities

Type: **investigate**  
Read only: **True**

If parameter <b>search</b> is provided then all other parameters are ignored\.<br>The search string must contain any valid parameter found in data of vulnerabilities for filtering\.<br>The search string entered by user should be in format &quotParameter\:Value&quot\.<br>Some examples of valid search string are as follows\:<br><ul><li>cve\:2014\-0160</li><li>hostname\:foobar</li><li>max\_priority\:10&min\_priority\:1</li><li>top\_priority\:true</li></ul>

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**search** |  optional  | Search string | string | 
**vulnerability\_status** |  optional  | Status of the vulnerability \(Default\: Open\) | string | 
**connector** |  optional  | Connector name | string |  `kenna connector name` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.connector | string |  `kenna connector name` 
action\_result\.parameter\.search | string | 
action\_result\.parameter\.vulnerability\_status | string | 
action\_result\.data\.\*\.active\_internet\_breach | boolean | 
action\_result\.data\.\*\.asset\_id | numeric |  `kenna device id` 
action\_result\.data\.\*\.closed | boolean | 
action\_result\.data\.\*\.closed\_at | string | 
action\_result\.data\.\*\.connectors\.\*\.connector\_definition\_name | string | 
action\_result\.data\.\*\.connectors\.\*\.id | numeric |  `kenna connector id` 
action\_result\.data\.\*\.connectors\.\*\.name | string |  `kenna connector name` 
action\_result\.data\.\*\.connectors\.\*\.vendor | string | 
action\_result\.data\.\*\.created\_at | string | 
action\_result\.data\.\*\.custom\_fields | string | 
action\_result\.data\.\*\.cve\_description | string | 
action\_result\.data\.\*\.cve\_id | string | 
action\_result\.data\.\*\.cve\_published\_at | string | 
action\_result\.data\.\*\.description | string | 
action\_result\.data\.\*\.domains\.asset | string |  `domain` 
action\_result\.data\.\*\.due\_date | string | 
action\_result\.data\.\*\.easily\_exploitable | boolean | 
action\_result\.data\.\*\.first\_found\_on | string | 
action\_result\.data\.\*\.fix\_id | numeric | 
action\_result\.data\.\*\.id | numeric |  `kenna vulnerability id` 
action\_result\.data\.\*\.identifiers | string | 
action\_result\.data\.\*\.last\_seen\_time | string | 
action\_result\.data\.\*\.malware\_exploitable | boolean | 
action\_result\.data\.\*\.notes | string | 
action\_result\.data\.\*\.patch | boolean | 
action\_result\.data\.\*\.patch\_published\_at | string | 
action\_result\.data\.\*\.popular\_target | boolean | 
action\_result\.data\.\*\.port | numeric |  `port` 
action\_result\.data\.\*\.predicted\_exploitable | boolean | 
action\_result\.data\.\*\.priority | string | 
action\_result\.data\.\*\.risk\_meter\_score | numeric | 
action\_result\.data\.\*\.scanner\_vulnerabilities\.\*\.external\_unique\_id | string | 
action\_result\.data\.\*\.scanner\_vulnerabilities\.\*\.open | boolean | 
action\_result\.data\.\*\.scanner\_vulnerabilities\.\*\.port | string |  `port` 
action\_result\.data\.\*\.service\_ticket | string | 
action\_result\.data\.\*\.severity | numeric | 
action\_result\.data\.\*\.solution | string | 
action\_result\.data\.\*\.status | string | 
action\_result\.data\.\*\.threat | numeric | 
action\_result\.data\.\*\.top\_priority | boolean | 
action\_result\.data\.\*\.urls\.asset | string |  `url` 
action\_result\.data\.\*\.wasc\_id | string | 
action\_result\.summary\.total\_vulnerabilities | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 