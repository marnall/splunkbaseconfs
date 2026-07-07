# ReversingLabs Workflow Actions for Splunk 
The ReversingLabs Workflow Actions for Splunk is a custom security and threat intelligence solution that enriches the Splunk Search & Reporting app with direct links to ReversingLabs file analysis appliances.

When used in search query results, the ReversingLabs Workflow Actions enable direct links towards analysis views on ReversingLabs file analysis appliances from each hash value field defined in the extension configuration or in the Splunk Common Information Model data sets.

### ReversingLabs A1000 Workflow Actions
For each linked hash field the ReversingLabs A1000 Malware Analysis Platform can display:
- detailed classification statements
- static analysis results 
- threat level indicators
- discovery dates
- specific malware family / category / subcategory nomenclature, as well as CVE statements if applicable
- AV scanner classifications
- dynamic analysis results

## About A1000
The A1000 Malware Analysis Platform supports advanced hunting and investigations through the TitaniumCore high-speed automated static analysis engine. It is integrated with file reputation services to provide in-depth rich context and threat classification on over 8 billion files and across all file types. The A1000 supports visualization, APIs for integration with automated workflows, a dedicated database for malware search, global and local YARA Rules matching, as well as integration with 3rd party sandbox tools.

### Prerequisites
- To use this extension you need to have a **ReversingLabs A1000** Malware Analysis Platform instance
- You can apply for an A1000 demo through the ReversingLabs web interface: https://www.reversinglabs.com/products/malware-analysis-appliance

### Installation
- Download the .tgz app archive and install it using the “Install app from file” function of the Splunk Apps section.
### Upgrade
- Download the latest version of the application and perform the same procedure as when installing it. This will provide an option to upgrade the existing version.
### Uninstallation
- `$SPLUNK_HOME/bin/splunk remove app reversinglabs_workflow_actions -auth <username>:<password>`

#### ReversingLabs:
https://www.reversinglabs.com/
