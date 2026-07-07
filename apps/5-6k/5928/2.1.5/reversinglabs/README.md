[comment]: # "Auto-generated SOAR connector documentation"
# ReversingLabs

Publisher: Splunk  
Connector Version: 2\.1\.5  
Product Vendor: ReversingLabs  
Product Name: TitaniumCloud  
Product Version Supported (regex): "\.\*"  
Minimum Product Version: 5\.1\.0  

This app implements an investigative action on the ReversingLabs reputation service

[comment]: # " File: README.md"
[comment]: # "  Copyright (c) 2014-2022 Splunk Inc."
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
# Splunk> Phantom

Welcome to the open-source repository for Splunk> Phantom’s reversinglabs App.

Please have a look at our [Contributing
Guide](https://github.com/Splunk-SOAR-Apps/.github/blob/main/.github/CONTRIBUTING.md) if you are
interested in contributing, raising issues, or learning more about open-source Phantom apps.

## Legal and License

This Phantom App is licensed under the Apache 2.0 license. Please see our [Contributing
Guide](https://github.com/Splunk-SOAR-Apps/.github/blob/main/.github/CONTRIBUTING.md#legal-notice)
for further details.

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the ReversingLabs server. Below are the
default ports used by Splunk SOAR.

|         Service Name | Transport Protocol | Port |
|----------------------|--------------------|------|
|         http         | tcp                | 80   |
|         https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a TitaniumCloud asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**username** |  required  | string | Username
**password** |  required  | password | Password
**verify\_server\_cert** |  optional  | boolean | Verify server certificate

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity  
[file reputation](#action-file-reputation) - Queries ReversingLabs for file info  

## action: 'test connectivity'
Validate the asset configuration for connectivity

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'file reputation'
Queries ReversingLabs for file info

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** |  required  | File hash to query | string |  `hash`  `sha256`  `sha1`  `md5` 

#### Action Output
DATA PATH | TYPE | CONTAINS
--------- | ---- | --------
action\_result\.status | string | 
action\_result\.parameter\.hash | string |  `hash`  `sha256`  `sha1`  `md5` 
action\_result\.data\.\*\.first\_scanned\_on | string | 
action\_result\.data\.\*\.first\_seen\_on | string | 
action\_result\.data\.\*\.last\_scanned\_on | string | 
action\_result\.data\.\*\.last\_seen\_on | string | 
action\_result\.data\.\*\.md5 | string |  `md5` 
action\_result\.data\.\*\.ripemd160 | string | 
action\_result\.data\.\*\.sample\_size | numeric | 
action\_result\.data\.\*\.sample\_type | string | 
action\_result\.data\.\*\.sha1 | string |  `sha1` 
action\_result\.data\.\*\.sha256 | string |  `sha256` 
action\_result\.data\.\*\.sha384 | string | 
action\_result\.data\.\*\.sha512 | string | 
action\_result\.data\.\*\.single\_scan | boolean | 
action\_result\.data\.\*\.status | string | 
action\_result\.data\.\*\.xref\.\*\.results\.\*\.result | string | 
action\_result\.data\.\*\.xref\.\*\.results\.\*\.scanner | string | 
action\_result\.data\.\*\.xref\.\*\.scanned\_on | string | 
action\_result\.data\.\*\.xref\.\*\.scanner\_count | numeric | 
action\_result\.data\.\*\.xref\.\*\.scanner\_match | numeric | 
action\_result\.data\.\*\.xref\.\*\.scanners\.\*\.name | string | 
action\_result\.data\.\*\.xref\.\*\.scanners\.\*\.timestamp | string | 
action\_result\.data\.\*\.xref\.\*\.scanners\.\*\.version | string | 
action\_result\.summary\.positives | numeric | 
action\_result\.summary\.total\_scans | numeric | 
action\_result\.message | string | 
summary\.total\_objects | numeric | 
summary\.total\_objects\_successful | numeric | 
summary\.total\_positives | numeric | 