[comment]: # "Auto-generated SOAR connector documentation"
# NIST NVD

Publisher: Trisha Pancho  
Connector Version: 1.0.1  
Product Vendor: NIST  
Product Name: NVD  
Product Version Supported (regex): ".\*"  
Minimum Product Version: 5.3.2.88192  

App to query NIST for CVEs

### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a NVD asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_version** |  required  | string | Supported API Version

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[cve lookup](#action-cve-lookup) - Query NVD for specific CVE ID  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'cve lookup'
Query NVD for specific CVE ID

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**cve** |  required  | CVE ID | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.cve | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.cisaVulnerabilityName | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.descriptions.\*.value | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.references.\*.url | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.published | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.metrics.cvssMetricV31.\*.cvssData.baseScore | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.metrics.cvssMetricV31.\*.cvssData.baseSeverity | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.metrics.cvssMetricV31.\*.cvssData.attackVector | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.metrics.cvssMetricV31.\*.impactScore | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.metrics.cvssMetricV31.\*.exploitabilityScore | string |  |  
action_result.data.\*.vulnerabilities.\*.cve.metrics.cvssMetricV31.\*.cvssData.attackComplexity | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
summary.total_objects | numeric |  |  
summary.total_objects_successful | numeric |  |  
action_result.summary | string |  |  