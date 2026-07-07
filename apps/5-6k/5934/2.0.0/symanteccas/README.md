[comment]: # "Auto-generated SOAR connector documentation"
# Symantec CAS

Publisher: Splunk Community  
Connector Version: 2\.0\.0  
Product Vendor: Symantec  
Product Name: Symantec CAS  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.1\.0  

This app supports file investigation on the Symantec Content Analysis System

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Symantec CAS asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** |  required  | string | URL \(e\.g\. https\://10\.10\.10\.10\:8082\)
**verify\_server\_cert** |  optional  | boolean | Verify server certificate
**api\_key** |  required  | password | API key
**timeout** |  optional  | numeric | Websocket timeout in sec

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity  
[detonate file](#action-detonate-file) - Run file in Symantec CAS sandbox and retrieve analysis results  

## action: 'test connectivity'
Validate the asset configuration for connectivity

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'detonate file'
Run file in Symantec CAS sandbox and retrieve analysis results

Type: **investigate**  
Read only: **True**

This action requires input file to be present in the vault and therefore takes vault ID as an input parameter\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault\_id** |  required  | Vault ID of file to detonate | string |  `vault id` 
**file\_name** |  optional  | Filename | string |  `file name` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.data\.\*\.server\_time | string | 
action\_result\.data\.\*\.id | string | 
action\_result\.data\.\*\.client\_id | string | 
action\_result\.data\.\*\.exec\_time | string | 
action\_result\.data\.\*\.filename | string |  `file name` 
action\_result\.data\.\*\.score | numeric | 
action\_result\.data\.\*\.status | numeric | 
action\_result\.data\.\*\.expect\_sandbox | string | 
action\_result\.data\.\*\.sha1 | string |  `sha1` 
action\_result\.data\.\*\.sha256 | string |  `sha256` 
action\_result\.data\.\*\.md5 | string |  `md5` 
action\_result\.data\.\*\.file\_reputation\.score | numeric | 
action\_result\.data\.\*\.file\_reputation\.status | numeric | 
action\_result\.data\.\*\.user\_hash\_list\.score | numeric | 
action\_result\.data\.\*\.user\_hash\_list\.status | numeric | 
action\_result\.data\.\*\.cylance\.score | numeric | 
action\_result\.data\.\*\.cylance\.status | numeric | 
action\_result\.data\.\*\.cylance\.data\_version | string | 
action\_result\.data\.\*\.cylance\.engine\_version | string | 
action\_result\.data\.\*\.cylance\.details | string | 
action\_result\.data\.\*\.policy\.score | numeric | 
action\_result\.data\.\*\.policy\.status | numeric | 
action\_result\.data\.\*\.policy\.code | string | 
action\_result\.data\.\*\.policy\.details | string | 
action\_result\.data\.\*\.kaspersky\.score | numeric | 
action\_result\.data\.\*\.kaspersky\.status | numeric | 
action\_result\.data\.\*\.kaspersky\.engine\_version | string | 
action\_result\.data\.\*\.kaspersky\.pattern\_version | string | 
action\_result\.data\.\*\.kaspersky\.pattern\_date | string | 
action\_result\.data\.\*\.kaspersky\.file\_name | string |  `file name` 
action\_result\.data\.\*\.kaspersky\.subfile\_name | string |  `file name` 
action\_result\.data\.\*\.kaspersky\.error\_code | string | 
action\_result\.data\.\*\.kaspersky\.error\_details | string | 
action\_result\.data\.\*\.kaspersky\.virus\_name | string | 
action\_result\.data\.\*\.sophos\.score | numeric | 
action\_result\.data\.\*\.sophos\.status | numeric | 
action\_result\.data\.\*\.sophos\.engine\_version | string | 
action\_result\.data\.\*\.sophos\.pattern\_version | string | 
action\_result\.data\.\*\.sophos\.pattern\_date | string | 
action\_result\.data\.\*\.sophos\.file\_name | string |  `file name` 
action\_result\.data\.\*\.sophos\.subfile\_name | string |  `file name` 
action\_result\.data\.\*\.sophos\.error\_code | string | 
action\_result\.data\.\*\.sophos\.error\_details | string | 
action\_result\.data\.\*\.sophos\.virus\_name | string | 
action\_result\.data\.\*\.mcafee\.score | numeric | 
action\_result\.data\.\*\.mcafee\.status | numeric | 
action\_result\.data\.\*\.mcafee\.engine\_version | string | 
action\_result\.data\.\*\.mcafee\.pattern\_version | string | 
action\_result\.data\.\*\.mcafee\.pattern\_date | string | 
action\_result\.data\.\*\.mcafee\.file\_name | string |  `file name` 
action\_result\.data\.\*\.mcafee\.subfile\_name | string |  `file name` 
action\_result\.data\.\*\.mcafee\.error\_code | string | 
action\_result\.data\.\*\.mcafee\.error\_details | string | 
action\_result\.data\.\*\.mcafee\.virus\_name | string | 
action\_result\.data\.\*\.malware\_analysis\.score | numeric | 
action\_result\.data\.\*\.malware\_analysis\.status | numeric | 
action\_result\.data\.\*\.malware\_analysis\.report\_url | string |  `url` 
action\_result\.data\.\*\.malware\_analysis\.pdf\_url | string |  `url` 
action\_result\.data\.\*\.malware\_analysis\.error | string | 
action\_result\.data\.\*\.bcma\.score | numeric | 
action\_result\.data\.\*\.bcma\.status | numeric | 
action\_result\.data\.\*\.bcma\.report\_url | string |  `url` 
action\_result\.data\.\*\.bcma\.pdf\_url | string |  `url` 
action\_result\.data\.\*\.bcma\.error | string | 
action\_result\.data\.\*\.lastline\.score | numeric | 
action\_result\.data\.\*\.lastline\.status | numeric | 
action\_result\.data\.\*\.lastline\.report\_url | string |  `url` 
action\_result\.data\.\*\.lastline\.pdf\_url | string |  `url` 
action\_result\.data\.\*\.lastline\.error | string | 
action\_result\.data\.\*\.FireEye\.score | numeric | 
action\_result\.data\.\*\.FireEye\.status | numeric | 
action\_result\.data\.\*\.FireEye\.report\_url | string |  `url` 
action\_result\.data\.\*\.FireEye\.pdf\_url | string |  `url` 
action\_result\.data\.\*\.FireEye\.error | string | 
action\_result\.data\.\*\.error | string | 
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.parameter\.vault\_id | string |  `vault id` 
action\_result\.parameter\.file\_name | string |  `file name` 
action\_result\.summary\.global\_score | numeric | 
action\_result\.summary\.global\_status | numeric | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 