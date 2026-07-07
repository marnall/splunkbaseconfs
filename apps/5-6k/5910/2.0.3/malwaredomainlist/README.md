[comment]: # "Auto-generated SOAR connector documentation"
# Malware Domain List

Publisher: Splunk  
Connector Version: 2\.0\.3  
Product Vendor: Malware Domain List  
Product Name: Malware Domain List  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.1\.0  

This app retrieves IOC reputation from Malware Domain List

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a Malware Domain List asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**url** |  required  | string | URL \(e\.g\. https\://www\.malwaredomainlist\.com\)

### Supported Actions  
[ip reputation](#action-ip-reputation) - Query for IP reputation  
[domain reputation](#action-domain-reputation) - Query for domain reputation  
[test connectivity](#action-test-connectivity) - Verifies connectivity with the Malware Domain List website  

## action: 'ip reputation'
Query for IP reputation

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** |  required  | IP | string |  `ip` 
**include\_inactive** |  optional  | Include inactive sites | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.data\.\*\.Domain | string |  `domain` 
action\_result\.data\.\*\.Description | string | 
action\_result\.data\.\*\.IP | string |  `ip` 
action\_result\.data\.\*\.ASN | string | 
action\_result\.data\.\*\.ReverseLookup | string |  `domain` 
action\_result\.data\.\*\.DateUTC | string | 
action\_result\.data\.\*\.Registrant | string | 
action\_result\.data\.\*\.Country | string | 
action\_result\.data\.\*\.CountryCode | string | 
action\_result\.parameter\.ip | string |  `ip` 
action\_result\.parameter\.include\_inactive | boolean | 
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.summary\.matching\_records | numeric | 
action\_result\.summary\.malicious | boolean | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 
action\_result\.data\.\*\.Path | string |   

## action: 'domain reputation'
Query for domain reputation

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** |  required  | Domain | string |  `domain`  `url` 
**include\_inactive** |  optional  | Include inactive sites | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.data\.\*\.Domain | string |  `domain` 
action\_result\.data\.\*\.Path | string | 
action\_result\.data\.\*\.Description | string | 
action\_result\.data\.\*\.IP | string |  `ip` 
action\_result\.data\.\*\.ASN | string | 
action\_result\.data\.\*\.ReverseLookup | string |  `domain` 
action\_result\.data\.\*\.DateUTC | string | 
action\_result\.data\.\*\.Registrant | string | 
action\_result\.data\.\*\.Country | string | 
action\_result\.data\.\*\.CountryCode | string | 
action\_result\.parameter\.domain | string |  `domain`  `url` 
action\_result\.parameter\.include\_inactive | boolean | 
action\_result\.status | string | 
action\_result\.message | string | 
action\_result\.summary\.matching\_records | numeric | 
action\_result\.summary\.malicious | boolean | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric |   

## action: 'test connectivity'
Verifies connectivity with the Malware Domain List website

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output