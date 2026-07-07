[comment]: # "Auto-generated SOAR connector documentation"
# Cyphort

Publisher: Splunk Community  
Connector Version: 2\.0\.1  
Product Vendor: Cyphort  
Product Name: Cyphort  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.0\.0  

This app supports executing investigative actions to analyze executables on the Cyphort sandbox

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Cyphort asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**server** |  required  | string | Server IP/Hostname
**verify\_server\_cert** |  required  | boolean | Verify server certificate
**api\_key** |  required  | password | API Key

### Supported Actions  
[detonate file](#action-detonate-file) - Run the file in the Cyphort sandbox and retrieve the analysis results  
[get report](#action-get-report) - Query for results of an already completed task in Cyphort  
[test connectivity](#action-test-connectivity) - This action connects to the server to verify the connection  

## action: 'detonate file'
Run the file in the Cyphort sandbox and retrieve the analysis results

Type: **investigate**  
Read only: **True**

This action requires the input file to be present in the vault and therefore takes the vault id as the input parameter\.

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault\_id** |  required  | Vault ID of file to detonate | string |  `hash`  `pe file` 
**file\_name** |  optional  | Filename to use | string |  `file name` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.file\_name | string |  `file name` 
action\_result\.parameter\.vault\_id | string |  `hash`  `pe file` 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.analysis\_done\_time | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.analysis\_start\_time | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_md5\_string | string |  `hash`  `md5` 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_sha1\_string | string |  `hash`  `sha1` 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_sha256\_string | string |  `hash`  `sha256` 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_size | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_suffix | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_type\_string | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.has\_behavior\_log | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.has\_behavioral\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.has\_reputation\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.has\_static\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.local\_path | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.malware\_category | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.malware\_classname | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.malware\_name | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.malware\_severity | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.microsoft\_name | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.mime\_type\_string | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.reputation\_score | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.screen\_shots | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.source\_url\_rank | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.analysis\_done\_time | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.analysis\_start\_time | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_md5\_string | string |  `hash`  `md5` 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_sha1\_string | string |  `hash`  `sha1` 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_sha256\_string | string |  `hash`  `sha256` 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_size | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_suffix | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_type\_string | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.has\_behavior\_log | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.has\_behavioral\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.has\_reputation\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.has\_static\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.local\_path | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.malware\_category | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.malware\_classname | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.malware\_name | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.malware\_severity | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.microsoft\_name | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.mime\_type\_string | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.reputation\_score | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.screen\_shots | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.source\_url\_rank | string | 
action\_result\.data\.\*\.analysis\_details\.status | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.files\_opened\.\*\.file\_name | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.files\_opened\.\*\.for\_pipe | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.files\_opened\.\*\.for\_read | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.files\_opened\.\*\.for\_write | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.has\_ivp | boolean | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.mutexes\.\*\.mutex\_name | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.mutexes\.\*\.was\_created | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.os\_type | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.processes\_spawned\.\*\.command\_name | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.processes\_spawned\.\*\.remote\_process\_id | numeric |  `pid` 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.registry\_changes\.\*\.key\_path | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.registry\_changes\.\*\.was\_created | numeric | 
action\_result\.data\.\*\.behavior\_details\.max\_cook\_size | numeric | 
action\_result\.data\.\*\.behavior\_details\.server\_ip | string |  `ip` 
action\_result\.data\.\*\.behavior\_details\.server\_name | string | 
action\_result\.data\.\*\.behavior\_details\.session\_timeout\_sec | numeric | 
action\_result\.data\.\*\.behavior\_details\.status | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_correlation\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_downstream\_web\_collector | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_fc\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_hre\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_internet\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_mode | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_sc\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_sigeng\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_web\_collector | numeric | 
action\_result\.summary\.event\_id | numeric |  `cyphort event id` 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'get report'
Query for results of an already completed task in Cyphort

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**id** |  required  | Task ID to get the results of | string |  `cyphort event id` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.id | string |  `cyphort event id` 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.analysis\_done\_time | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.analysis\_start\_time | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_md5\_string | string |  `hash`  `md5` 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_sha1\_string | string |  `hash`  `sha1` 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_sha256\_string | string |  `hash`  `sha256` 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_size | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_suffix | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.file\_type\_string | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.has\_behavior\_log | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.has\_behavioral\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.has\_reputation\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.has\_static\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.local\_path | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.malware\_category | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.malware\_classname | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.malware\_name | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.malware\_severity | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.microsoft\_name | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.mime\_type\_string | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.reputation\_score | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.screen\_shots | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_array\.\*\.source\_url\_rank | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.analysis\_done\_time | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.analysis\_start\_time | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_md5\_string | string |  `hash`  `md5` 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_sha1\_string | string |  `hash`  `sha1` 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_sha256\_string | string |  `hash`  `sha256` 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_size | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_suffix | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.file\_type\_string | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.has\_behavior\_log | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.has\_behavioral\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.has\_reputation\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.has\_static\_detection | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.local\_path | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.malware\_category | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.malware\_classname | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.malware\_name | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.malware\_severity | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.microsoft\_name | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.mime\_type\_string | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.reputation\_score | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.screen\_shots | string | 
action\_result\.data\.\*\.analysis\_details\.analysis\_details\.source\_url\_rank | string | 
action\_result\.data\.\*\.analysis\_details\.status | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.files\_opened\.\*\.file\_name | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.files\_opened\.\*\.for\_pipe | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.files\_opened\.\*\.for\_read | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.files\_opened\.\*\.for\_write | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.has\_ivp | boolean | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.mutexes\.\*\.mutex\_name | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.mutexes\.\*\.was\_created | numeric | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.os\_type | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.processes\_spawned\.\*\.command\_name | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.processes\_spawned\.\*\.remote\_process\_id | numeric |  `pid` 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.registry\_changes\.\*\.key\_path | string | 
action\_result\.data\.\*\.behavior\_details\.behavior\_details\.registry\_changes\.\*\.was\_created | numeric | 
action\_result\.data\.\*\.behavior\_details\.max\_cook\_size | numeric | 
action\_result\.data\.\*\.behavior\_details\.server\_ip | string |  `ip` 
action\_result\.data\.\*\.behavior\_details\.server\_name | string | 
action\_result\.data\.\*\.behavior\_details\.session\_timeout\_sec | numeric | 
action\_result\.data\.\*\.behavior\_details\.status | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_correlation\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_downstream\_web\_collector | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_fc\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_hre\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_internet\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_mode | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_sc\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_sigeng\_on | numeric | 
action\_result\.data\.\*\.behavior\_details\.status\_web\_collector | numeric | 
action\_result\.summary | string | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'test connectivity'
This action connects to the server to verify the connection

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output