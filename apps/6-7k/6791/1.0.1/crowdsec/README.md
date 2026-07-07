[comment]: # "Auto-generated SOAR connector documentation"
# CrowdSec

Publisher: CrowdSec  
Connector Version: 1\.0\.1  
Product Vendor: CrowdSec  
Product Name: CrowdSec  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.5\.0  

Splunk SOAR App which integrates with CrowdSec\. It provides the ability to lookup an IP address in CrowdSec's threat intelligence feed

[comment]: # "File: README.md"
[comment]: # "Copyright (c) 2023 CrowdSec"
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
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a CrowdSec asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**CROWDSEC\_CTI\_API\_KEY** |  required  | string | API key for CrowdSec CTI API

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration  
[lookup ip](#action-lookup-ip) - Check for the presence of an IP in a threat intelligence feed  

## action: 'test connectivity'
Validate the asset configuration for connectivity using supplied configuration

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'lookup ip'
Check for the presence of an IP in a threat intelligence feed

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** |  required  | IP to lookup | string |  `ip` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action\_result\.status | string |  |   success  failed 
action\_result\.parameter\.ip | string |  `ip`  |  
action\_result\.data\.\*\.as\_name | string |  |  
action\_result\.data\.\*\.as\_num | string |  |  
action\_result\.data\.\*\.background\_noise\_score | string |  |  
action\_result\.data\.\*\.behaviors\.\*\.description | string |  |  
action\_result\.data\.\*\.behaviors\.\*\.label | string |  |  
action\_result\.data\.\*\.behaviors\.\*\.name | string |  |  
action\_result\.data\.\*\.history\.days\_age | string |  |  
action\_result\.data\.\*\.history\.first\_seen | string |  |  
action\_result\.data\.\*\.history\.full\_age | string |  |  
action\_result\.data\.\*\.history\.last\_seen | string |  |  
action\_result\.data\.\*\.ip | string |  |  
action\_result\.data\.\*\.ip\_range | string |  |  
action\_result\.data\.\*\.ip\_range\_score | string |  |  
action\_result\.data\.\*\.location\.city | string |  |  
action\_result\.data\.\*\.location\.country | string |  |  
action\_result\.data\.\*\.location\.latitude | string |  |  
action\_result\.data\.\*\.location\.longitude | string |  |  
action\_result\.data\.\*\.reverse\_dns | string |  |  
action\_result\.data\.\*\.scores\.last\_day\.aggressiveness | numeric |  |  
action\_result\.data\.\*\.scores\.last\_day\.anomaly | numeric |  |  
action\_result\.data\.\*\.scores\.last\_day\.threat | numeric |  |  
action\_result\.data\.\*\.scores\.last\_day\.total | numeric |  |  
action\_result\.data\.\*\.scores\.last\_day\.trust | numeric |  |  
action\_result\.data\.\*\.scores\.last\_month\.aggressiveness | numeric |  |  
action\_result\.data\.\*\.scores\.last\_month\.threat | numeric |  |  
action\_result\.data\.\*\.scores\.last\_week\.aggressiveness | numeric |  |  
action\_result\.data\.\*\.scores\.overall\.aggressiveness | numeric |  |  
action\_result\.data\.\*\.scores\.overall\.anomaly | numeric |  |  
action\_result\.data\.\*\.scores\.overall\.threat | numeric |  |  
action\_result\.data\.\*\.scores\.overall\.total | numeric |  |  
action\_result\.data\.\*\.scores\.overall\.trust | numeric |  |  
action\_result\.summary | string |  |  
action\_result\.message | string |  |  
summary\.total\_objects | numeric |  |  
summary\.total\_objects\_successful | numeric |  |  