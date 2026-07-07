# GIB TI Splunk Integration. 

### v0.2.0
Pre-release version for early access.

### v0.8.2
Add all the collection from API.

#### v1.0.0
Provides basic jsoned TI&A items.  

#### v1.0.1
Darkweb and Breached DB collections items added. 

### v1.0.2
Add search

### v1.1.0
Global update include refactor end optimization.
1. Add global search in real time 
2. Add views into dashboard
3. Refactor code


### v1.1.5
Added the ability to choose save images from collections apt/threat, hi/threat.

### v1.2.0
Added new endpoint:
1. "compromised/bank_card_group": "Compromised::Group_Card",
2. "compromised/masked_card": "Compromised::Masked Card",
3. "compromised/reaper": "Compromised::Darkweb",
4. "compromised/access": "Compromised::Access",
5. "compromised/discord": "Compromised::Discord",
6. "compromised/messenger": "Compromised::Messenger",
7. "ioc/common": "IOC::Common",
8. "attacks/phishing_group": "Attacks::Phishing Kit",
9. "osi/git_repository": "OSI::Git Repository",
10. "suspicious_ip/scanner": "Suspicious IP::Scanner",
11. "suspicious_ip/vpn": "Suspicious IP::VPN",
12. "malware/config": "Malware::Config",
13. "malware/signature": "Malware::Signature",
14. "malware/malware": "Malware::Malware",
15. "malware/yara": "Malware::yara",

Remove old endpoint:
1. "bp/phishing": "BP::Phishing",
2. "bp/phishing_kit": "BP::Phishing Kit",
3. "osi/git_leak": "OSI::Git Leak",
4. "malware/targeted_malware": "Malware::Targeted Malware"

Update Global search command:
1. Refactor struct of command | gibtiasearch global_search='' -> | gibsearch search=''
2. Enlarge mount of data, add WhoIS information, add more attribution

Add Graph search command:
| gibgraph search=''
This command provide you data about IP's and domain

### v1.2.0
Added more WhoIs information and attribution

### v1.4.0
Refactored search logic
Removed deprecated collections
Refactored Attribution logic

### v1.4.4
- New hunting rules filter option across most of collections;
- Possibility to work with several accounts with different indexes;
- Updated library and code refactoring;
- Fixed bug with missing Data Inputs.

### v1.5.4
- Changed sourseTypes from "gib_tia" to "gib_ti";
- The maximum size of logs of the main part of the application is set to 500 mb;
- Improved error catching in state_store;
- Removed the ability to download images.

### v1.6.4
- Added a checkbox to limit the size of collected logs;
- Improved display of search command information.

### v1.7.4
- Added checkbox to control logging level;
- Added a limit on the logs collected when using commands;
- Fixed log duplication and log size limitation;
- Added the ability to link Splunk with different IP addresses.

### v1.7.5
- Improved logging.

### v1.8.0
- History and images have been removed from malware/malware;
- Added the compromised/spd collection; 
- Updated the cyberintegrations library to version 0.10.0;
- The names of some collections in the Data Inputs settings window have been changed;
- Fixed bug with logging level selection;
- Removed the deprecated compromised/mule collection.

### v1.9.0
- Improved the interface for basic application configuration;
- Fixed a bug with filling in credentials for multi-account functionality;
- Fixed a bug where different accounts referred to the same seqUpdate;
- Added support for selecting an account when running the gibsearch command.    