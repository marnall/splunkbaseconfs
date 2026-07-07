# ReversingLabs External Lookup for Splunk

The ReversingLabs External Lookup for Splunk is a custom security and threat intelligence solution that enriches the Splunk Search & Reporting app with additional data on potential threats to the system and network.

When used in search queries, the ReversingLabs External Lookup append file reputation analysis data to the search results based on selected file hashes.

For each SHA-1, SHA-256 or MD5 hash value group in the search results ReversingLabs External Lookup can obtain detailed file reputation results, which contain classification statements, threat level indicators, discovery dates and specific malware family / category / subcategory nomenclature, as well as CVE statements if applicable.

## About TitaniumCloud
ReversingLabs TitaniumCloud offers multiple API endpoints for advanced threat hunting, file reputation, AV scanner cross references, functional hash similarity, advanced malware intel feeds and much more.  
ReversingLabs’ TitaniumCloud Reputation Services are powerful threat intelligence solutions with up-to-date, threat classification and rich context on over 8 billion goodware and malware files. ReversingLabs does not depend on crowd-sourced collection but instead curates the harvesting of files from software vendors and diverse malware sources. All files are processed using unique ReversingLabs File Decomposition Technology, combined with other dynamic and detection information to provide industry reputation consensus. 

### Features
Increase detection, analysis and response efficiency by identifying files from queries to an authoritative global goodware and malware database.

### Usage
#### Dashboard
Credentials are configured through the configuration editor dashboard in the ReversingLabs External Lookup app on the Splunk web interface.
#### Titanium Cloud configuration
After the app package is installed, the TitaniumCloud address and credentials need to be configured in order for the app to successfully make calls to the ReversingLabs TitaniumCloud
#### Proxy configuration
Optionally, if you have gateway proxy configured you have the option to set proxy address, port and credentials.

After filling out all  text fields with needed data, click “Submit”.

This enables the lookup function of the ReversingLabs External Lookup in the Splunk Search & Reporting app. Lookup can be accessed either through the “Search” panel in the current app, or by opening the Search & Reporting app through the Splunk web main menu.

To use the Splunk lookup functionalities, use the “lookup” keyword while writing a search query inside the Search & Reporting app.

#### File Reputation lookup usage
| lookup RL_filereputation hash_value AS <selected_hash_field>

#### File Analysis lookup usage
| lookup RL_fileanalysis hash_value AS <selected_hash_field>

selected_hash_field  - name of the SHA-1, SHA-256 or MD5 hash field from the search results that will be used for the external file analysis lookup.

### Prerequisites
**File Reputation lookup**
- a valid **ReversingLabs TitaniumCloud** account enabled to use the File Reputation API

**File Analysis lookup**
- a valid **ReversingLabs TitaniumCloud** account enabled to use the File analysis API

Apply for a TitaniumCloud demo through the ReversingLabs web interface: https://register.reversinglabs.com/demo


### Installation
- Download the .tgz app archive and install it using the “Install app from file” function of the Splunk Apps section.

### Upgrade
- On a new app version release Splunk interface will automatically prompt user for update.
- Optionally download the latest version of the application and perform the same procedure as when installing it. This will provide an option to upgrade the existing version.

### Uninstallation
- `$SPLUNK_HOME/bin/splunk remove app reversinglabs-externa-lookup -auth <username>:<password>`



### Documentation
Additional documentation is available in the app package under appserver/static/ in the form of a PDF user manual document.

### Links
##### TitaniumCloud: 
https://www.reversinglabs.com/products/file-reputation-service
##### ReversingLabs:
https://www.reversinglabs.com/